"""Synthetic, offline tests for contiguous verified observation failure streaks."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import os
import socket
import subprocess
import time

import pytest

from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution, prepare_local_execution_request,
)
from cloudforge.models import ApplicationProfile
from cloudforge.observation_evidence import ObservationSample, sign_observation_evidence
from cloudforge.observation_plan import ObservationProbe, prepare_observation_plan
from cloudforge.observation_source_pin import ObservationSourcePin
from cloudforge.observation_thresholds import evaluate_verified_observation_thresholds
from cloudforge.planner import derive_requirements

KEY = bytes(range(32))
NOW = 1_800_000_040


def context():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "fixture")
    handoff = authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "reviewer"),
    )
    artifact = b"fixture-window-artifact"
    local_request = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(local_request.digest, "approver")
    receipt = authorize_local_execution(handoff, artifact, local_request, approval)
    observation_plan = prepare_observation_plan(
        handoff, artifact, approval, receipt,
        (ObservationProbe("readiness", 10, 2, 3),
         ObservationProbe("liveness", 10, 2, 5)),
    )
    return handoff, artifact, approval, receipt, observation_plan


def signed(ctx, outcomes, *, seq=1, at=None, key=KEY, source="collector-1"):
    plan = ctx[-1]
    samples = tuple(
        ObservationSample(probe.kind, outcome, 10)
        for probe, outcome in zip(plan.probes, outcomes)
    )
    return sign_observation_evidence(
        plan, samples, source, 1_800_000_000 + seq * 10 if at is None else at,
        seq, key,
    )


def evaluate(ctx, window, **overrides):
    settings = dict(
        expected_source_id="collector-1", source_key=KEY,
        now_unix=NOW, max_age_seconds=60, last_sequence=0,
    )
    settings.update(overrides)
    return evaluate_verified_observation_thresholds(*ctx, window, **settings)


def test_threshold_is_reached_only_by_three_contiguous_explicit_failures():
    ctx = context()
    window = tuple(signed(ctx, ("fail", "pass"), seq=n) for n in (1, 2, 3))
    result = evaluate(ctx, window)
    assert [(r.kind, r.consecutive_failures, r.failure_threshold,
             r.threshold_reached, r.latest_outcome) for r in result] == [
        ("readiness", 3, 3, True, "fail"),
        ("liveness", 0, 5, False, "pass"),
    ]
    assert result == evaluate(ctx, window)
    with pytest.raises(FrozenInstanceError):
        result[0].threshold_reached = False


@pytest.mark.parametrize("outcomes,streak", [
    (("fail", "unknown", "fail"), 1),
    (("fail", "pass", "fail"), 1),
    (("fail", "fail", "pass"), 0),
    (("fail", "fail", "unknown"), 0),
    (("unknown", "fail", "fail"), 2),
])
def test_unknown_or_pass_breaks_proven_failure_streak(outcomes, streak):
    ctx = context()
    window = tuple(
        signed(ctx, (outcome, "pass"), seq=n)
        for n, outcome in enumerate(outcomes, 1)
    )
    result = evaluate(ctx, window)
    assert result[0].consecutive_failures == streak
    assert result[0].threshold_reached is False


def test_window_is_bounded_and_does_not_infer_missing_history():
    ctx = context()
    single = signed(ctx, ("fail", "fail"), seq=8, at=1_800_000_030)
    result = evaluate(ctx, (single,), last_sequence=7)
    assert [r.consecutive_failures for r in result] == [1, 1]
    for invalid in ([], [single], (), (single,) * 11):
        with pytest.raises(ValueError, match="1-10"):
            evaluate(ctx, invalid)


@pytest.mark.parametrize("seqs,times,error", [
    ((1, 3), (1_800_000_010, 1_800_000_030), "sequence gap"),
    ((1, 1), (1_800_000_010, 1_800_000_020), "replayed"),
    ((2, 1), (1_800_000_010, 1_800_000_020), "replayed"),
    ((1, 2), (1_800_000_020, 1_800_000_010), "clock moved backward"),
])
def test_rejects_gaps_replays_and_clock_reversal(seqs, times, error):
    ctx = context()
    window = tuple(
        signed(ctx, ("fail", "pass"), seq=seq, at=at)
        for seq, at in zip(seqs, times)
    )
    with pytest.raises(ValueError, match=error):
        evaluate(ctx, window)


def test_tampered_or_wrong_source_evidence_never_produces_threshold_result():
    ctx = context()
    valid = signed(ctx, ("fail", "pass"))
    for invalid in (
        replace(valid, mac_sha256="0" * 64),
        replace(valid, samples=(ObservationSample("readiness", "pass", 10),
                                valid.samples[1])),
        signed(ctx, ("fail", "pass"), source="other-source"),
    ):
        with pytest.raises(ValueError):
            evaluate(ctx, (invalid,))
    with pytest.raises(ValueError):
        evaluate((ctx[0], b"changed-artifact", *ctx[2:]), (valid,))
    with pytest.raises(ValueError):
        evaluate(ctx, (valid,), source_key=bytes(range(1, 33)))
    with pytest.raises(ValueError):
        evaluate(ctx, (valid,), now_unix=1_800_000_100)


def test_strict_pin_and_revocation_are_checked_for_each_envelope():
    ctx = context()
    pin = ObservationSourcePin(
        "collector-1",
        hashlib.sha256(ctx[-1].to_json().encode("ascii")).hexdigest(),
        hashlib.sha256(KEY).hexdigest(),
        1_800_000_000, 1_800_000_060,
    )
    window = tuple(signed(ctx, ("fail", "pass"), seq=n) for n in (1, 2, 3))
    assert evaluate(ctx, window, source_pin=pin, require_source_pin=True)[0].threshold_reached
    with pytest.raises(ValueError, match="pin required"):
        evaluate(ctx, window, require_source_pin=True)
    with pytest.raises(ValueError, match="key is revoked"):
        evaluate(
            ctx, window, source_pin=pin, require_source_pin=True,
            revoked_key_sha256=(hashlib.sha256(KEY).hexdigest(),),
        )
    with pytest.raises(ValueError, match="pin mismatch"):
        evaluate(ctx, window, source_pin=replace(pin, key_sha256="0" * 64))


def test_threshold_evaluation_has_no_external_io(monkeypatch):
    ctx = context()
    window = tuple(signed(ctx, ("fail", "pass"), seq=n) for n in (1, 2, 3))
    def forbidden(*_args, **_kwargs):
        raise AssertionError("threshold evaluator must remain pure")
    with monkeypatch.context() as guard:
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(os, "system", forbidden)
        guard.setattr(time, "time", forbidden)
        assert evaluate(ctx, window)[0].threshold_reached
