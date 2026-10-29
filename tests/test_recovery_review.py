"""Offline, no-execution tests for deterministic recovery review proposals."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import os
import socket
import sqlite3
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
from cloudforge.planner import derive_requirements
from cloudforge.recovery_review import propose_recovery_review

KEY = bytes(range(32))
NOW = 1_800_000_040


def context():
    infra = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(infra)
    request = prepare_deployment_request(infra, proposal, "synthetic-target")
    handoff = authorize_deployment_handoff(
        infra, proposal, request, DeploymentApproval(request.digest, "reviewer"),
    )
    artifact = b"synthetic-recovery-review"
    local_request = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(local_request.digest, "approver")
    receipt = authorize_local_execution(handoff, artifact, local_request, approval)
    plan = prepare_observation_plan(
        handoff, artifact, approval, receipt,
        (ObservationProbe("readiness", 10, 2, 3),
         ObservationProbe("liveness", 10, 2, 3)),
    )
    return handoff, artifact, approval, receipt, plan


def signed(ctx, outcomes, seq=1):
    return sign_observation_evidence(
        ctx[-1], tuple(ObservationSample(kind, outcome, 10)
                       for kind, outcome in zip(("readiness", "liveness"), outcomes)),
        "collector-1", 1_800_000_000 + seq * 10, seq, KEY,
    )


def review(ctx, window, **overrides):
    settings = dict(
        expected_source_id="collector-1", source_key=KEY, now_unix=NOW,
        max_age_seconds=60, last_sequence=0,
    )
    settings.update(overrides)
    return propose_recovery_review(*ctx, window, **settings)


def test_threshold_proposes_manual_investigation_only_and_binds_window():
    ctx = context()
    window = tuple(signed(ctx, ("fail", "pass"), seq) for seq in (1, 2, 3))
    result = review(ctx, window)
    assert result.status == "manual-review-recommended"
    assert result.threshold_kinds == ("readiness",)
    assert result.unknown_kinds == ()
    assert result.action == "manual-investigation-only"
    assert result.last_sequence == 3
    assert result == review(ctx, window)
    exported = json.loads(result.to_json())
    assert exported["infrastructure_mutated"] is False
    assert exported["recovery_performed"] is False
    assert exported["deployment_observed"] is False
    assert "synthetic-target" not in result.to_json()
    assert "reviewer" not in result.to_json()
    assert "collector-1" not in result.to_json()
    assert "synthetic-recovery-review" not in result.to_json()
    with pytest.raises(FrozenInstanceError):
        result.status = "deployed"


def test_unknown_is_not_success_or_automatic_recovery():
    ctx = context()
    result = review(ctx, (signed(ctx, ("unknown", "pass")),))
    assert result.status == "insufficient-evidence"
    assert result.unknown_kinds == ("readiness",)
    assert result.threshold_kinds == ()
    assert result.action == "none"


def test_no_threshold_is_not_a_health_claim():
    ctx = context()
    result = review(ctx, (signed(ctx, ("pass", "pass")),))
    assert result.status == "no-trigger-in-window"
    assert result.action == "none"
    assert not result.threshold_kinds
    assert not result.unknown_kinds


def test_multiple_thresholds_are_deterministically_ordered():
    ctx = context()
    window = tuple(signed(ctx, ("fail", "fail"), seq) for seq in (1, 2, 3))
    assert review(ctx, window).threshold_kinds == ("readiness", "liveness")


def test_any_tampered_or_changed_artifact_rejected_before_review():
    ctx = context()
    valid = signed(ctx, ("fail", "pass"))
    with pytest.raises(ValueError):
        review(ctx, (replace(valid, mac_sha256="0" * 64),))
    with pytest.raises(ValueError):
        review(ctx, (replace(valid, samples=(
            ObservationSample("readiness", "pass", 10), valid.samples[1])),))
    with pytest.raises(ValueError):
        review((ctx[0], b"changed", *ctx[2:]), (valid,))


def test_gap_and_accelerated_window_fail_closed():
    ctx = context()
    with pytest.raises(ValueError, match="sequence gap"):
        review(ctx, (signed(ctx, ("fail", "pass"), 1),
                     signed(ctx, ("fail", "pass"), 3)))
    with pytest.raises(ValueError, match="1-10"):
        review(ctx, ())


def test_source_pin_and_revocation_reused():
    ctx = context()
    pin = ObservationSourcePin(
        "collector-1", hashlib.sha256(ctx[-1].to_json().encode("ascii")).hexdigest(),
        hashlib.sha256(KEY).hexdigest(), 1_800_000_000, 1_800_000_060,
    )
    window = (signed(ctx, ("fail", "pass")),)
    assert review(ctx, window, source_pin=pin, require_source_pin=True)
    with pytest.raises(ValueError, match="pin required"):
        review(ctx, window, require_source_pin=True)
    with pytest.raises(ValueError, match="key is revoked"):
        review(ctx, window, source_pin=pin, require_source_pin=True,
               revoked_key_sha256=(hashlib.sha256(KEY).hexdigest(),))


def test_canonical_digest_binds_exact_evidence_window():
    ctx = context()
    first = review(ctx, (signed(ctx, ("pass", "pass"), 1),))
    second = review(ctx, (signed(ctx, ("pass", "pass"), 2),))
    assert first.plan_sha256 == second.plan_sha256
    assert first.evidence_window_sha256 != second.evidence_window_sha256
    assert first.to_json() == review(ctx, (signed(ctx, ("pass", "pass"), 1),)).to_json()


@pytest.mark.parametrize("field,value", [
    ("status", "deployed"), ("action", "restart-service"),
    ("recovery_performed", True), ("infrastructure_mutated", 0),
    ("deployment_observed", True), ("last_sequence", True),
    ("threshold_kinds", ("readiness", "readiness")),
    ("evidence_window_sha256", "not-a-digest"),
])
def test_forged_export_claims_are_rejected(field, value):
    ctx = context()
    result = review(ctx, (signed(ctx, ("pass", "pass")),))
    with pytest.raises(ValueError, match="invalid non-executing"):
        replace(result, **{field: value}).to_json()


def test_proposal_is_pure_and_does_not_contact_devices_or_services(monkeypatch):
    ctx = context()
    window = tuple(signed(ctx, ("fail", "pass"), seq) for seq in (1, 2, 3))

    def forbidden(*args, **kwargs):
        raise AssertionError("recovery review attempted external I/O")

    with monkeypatch.context() as guard:
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(os, "system", forbidden)
        guard.setattr(sqlite3, "connect", forbidden)
        guard.setattr(time, "time", forbidden)
        assert review(ctx, window).status == "manual-review-recommended"
