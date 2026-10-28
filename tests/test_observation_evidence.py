"""Synthetic, credential-free tests for read-only observation evidence intake."""
from dataclasses import replace
import hashlib
import json

import pytest

from cloudforge.approval import ApprovalRequiredError
from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution, prepare_local_execution_request,
)
from cloudforge.models import ApplicationProfile
from cloudforge.observation_plan import (
    ObservationProbe, prepare_observation_plan,
)
from cloudforge.observation_evidence import (
    ObservationEvidence, ObservationSample, sign_observation_evidence,
    verify_observation_evidence,
)
from cloudforge.planner import derive_requirements
from cloudforge.observation_rollup import classify_verified_observation_samples
from cloudforge.observation_source_pin import ObservationSourcePin


_KEY = bytes(range(32))
_OTHER_KEY = bytes(range(1, 33))


def _context(target="staging", artifact=b"fixture-observation-bytes"):
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, target)
    handoff = authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "fixture-reviewer"),
    )
    local_request = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(local_request.digest, "fixture-approver")
    receipt = authorize_local_execution(handoff, artifact, local_request, approval)
    observation_plan = prepare_observation_plan(
        handoff, artifact, approval, receipt,
        (ObservationProbe("readiness", 10, 2, 3),
         ObservationProbe("liveness", 30, 5, 5)),
    )
    return handoff, artifact, approval, receipt, observation_plan


def _samples():
    return (ObservationSample("readiness", "pass", 21),
            ObservationSample("liveness", "unknown", 0))


def _evidence(plan, samples=None, source_id="collector-1", at=1_800_000_000, seq=1,
              key=_KEY):
    return sign_observation_evidence(
        plan, _samples() if samples is None else samples,
        source_id, at, seq, key,
    )


def _verify(context, evidence, **kwargs):
    handoff, artifact, approval, receipt, plan = context
    settings = dict(expected_source_id="collector-1", source_key=_KEY,
                    now_unix=1_800_000_015, max_age_seconds=30,
                    last_sequence=0)
    settings.update(kwargs)
    return verify_observation_evidence(
        handoff, artifact, approval, receipt, plan, evidence, **settings,
    )


def test_signed_evidence_is_deterministic_bounded_and_not_health_proof():
    context = _context()
    evidence = _evidence(context[-1])
    assert evidence == _evidence(context[-1])
    assert _verify(context, evidence) is True
    data = json.loads(evidence.to_json())
    assert data["format_version"] == 1
    assert [x["outcome"] for x in data["samples"]] == ["pass", "unknown"]
    assert "deployment_observed" not in data
    assert "healthy" not in data
    assert "staging" not in evidence.to_json()
    assert "fixture-reviewer" not in evidence.to_json()
    assert "fixture-approver" not in evidence.to_json()
    assert "fixture-observation-bytes" not in evidence.to_json()
    assert _verify(context, _evidence(context[-1], seq=2),
                   last_sequence=1) is True


@pytest.mark.parametrize("change", [
    {"source_id": "collector-2"},
    {"plan_sha256": "0" * 64},
    {"sequence": 2},
    {"observed_at_unix": 1_800_000_001},
    {"mac_sha256": "f" * 64},
    {"samples": (ObservationSample("readiness", "fail", 21),
                 ObservationSample("liveness", "unknown", 0))},
])
def test_mac_or_binding_tampering_fails(change):
    context = _context()
    with pytest.raises(ValueError):
        _verify(context, replace(_evidence(context[-1]), **change))


def test_cross_target_artifact_and_approval_cannot_reuse_evidence():
    context = _context()
    evidence = _evidence(context[-1])
    other = _context(target="production")
    with pytest.raises(ValueError):
        _verify(other, evidence)
    handoff, artifact, approval, receipt, plan = context
    with pytest.raises(ValueError):
        verify_observation_evidence(
            handoff, b"changed", approval, receipt, plan, evidence,
            expected_source_id="collector-1", source_key=_KEY,
            now_unix=1_800_000_015, max_age_seconds=30, last_sequence=0,
        )
    with pytest.raises(ApprovalRequiredError):
        verify_observation_evidence(
            handoff, artifact, LocalExecutionApproval("0" * 64, "fixture-approver"),
            receipt, plan, evidence,
            expected_source_id="collector-1", source_key=_KEY,
            now_unix=1_800_000_015, max_age_seconds=30, last_sequence=0,
        )


def test_wrong_key_source_stale_future_and_replay_fail():
    context = _context()
    evidence = _evidence(context[-1])
    for kwargs in (
        {"source_key": _OTHER_KEY},
        {"expected_source_id": "collector-2"},
        {"now_unix": 1_800_000_031},
        {"now_unix": 1_799_999_999},
        {"last_sequence": 1},
        {"last_sequence": 2},
    ):
        with pytest.raises(ValueError):
            _verify(context, evidence, **kwargs)


@pytest.mark.parametrize("samples", [
    [],
    tuple(),
    (ObservationSample("readiness", "pass", 1),),
    (ObservationSample("readiness", "pass", 1),
     ObservationSample("readiness", "pass", 1)),
    (ObservationSample("liveness", "pass", 1),
     ObservationSample("readiness", "pass", 1)),
    (ObservationSample("readiness", "healthy", 1),
     ObservationSample("liveness", "pass", 1)),
    (ObservationSample("readiness", "pass", True),
     ObservationSample("liveness", "pass", 1)),
    (ObservationSample("readiness", "pass", -1),
     ObservationSample("liveness", "pass", 1)),
    (ObservationSample("readiness", "pass", 300_001),
     ObservationSample("liveness", "pass", 1)),
    ({"kind": "readiness", "outcome": "pass", "elapsed_ms": 1},
     ObservationSample("liveness", "pass", 1)),
])
def test_malformed_samples_fail_closed(samples):
    context = _context()
    with pytest.raises(ValueError):
        _evidence(context[-1], samples=samples)


@pytest.mark.parametrize("override", [
    {"at": True},
    {"at": -1},
    {"seq": True},
    {"seq": 0},
    {"source_id": "https://example.com"},
    {"source_id": "collector\n1"},
    {"source_id": "COLLECTOR"},
    {"key": b"short"},
    {"key": bytearray(_KEY)},
])
def test_malformed_source_time_key_and_sequence_rejected(override):
    context = _context()
    with pytest.raises(ValueError):
        _evidence(context[-1], **override)


@pytest.mark.parametrize("kwargs", [
    {"now_unix": True},
    {"max_age_seconds": True},
    {"max_age_seconds": 0},
    {"max_age_seconds": 301},
    {"last_sequence": True},
    {"last_sequence": -1},
    {"source_key": b"short"},
    {"expected_source_id": "not a source"},
])
def test_malformed_verification_context_rejected(kwargs):
    context = _context()
    with pytest.raises(ValueError):
        _verify(context, _evidence(context[-1]), **kwargs)


def test_in_memory_evidence_intake_has_no_network_shell_or_clock_io(monkeypatch):
    import os
    import socket
    import subprocess
    import time

    def forbidden(*args, **kwargs):
        raise AssertionError("evidence intake must not perform external I/O")

    context = _context()
    with monkeypatch.context() as guard:
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(subprocess, "run", forbidden)
        guard.setattr(os, "system", forbidden)
        guard.setattr(time, "time", forbidden)
        evidence = _evidence(context[-1])
        assert _verify(context, evidence)
    assert isinstance(evidence, ObservationEvidence)


# Deterministic read-only sample rollup; never a service-health assertion.


def _rollup(context, evidence, **overrides):
    settings = dict(
        expected_source_id="collector-1", source_key=_KEY,
        now_unix=1_800_000_015, max_age_seconds=30, last_sequence=0,
    )
    settings.update(overrides)
    return classify_verified_observation_samples(
        *context, evidence, **settings,
    )


@pytest.mark.parametrize("outcomes,expected", [
    (("pass", "pass"), "pass"),
    (("pass", "unknown"), "unknown"),
    (("unknown", "pass"), "unknown"),
    (("unknown", "unknown"), "unknown"),
    (("fail", "pass"), "fail"),
    (("unknown", "fail"), "fail"),
    (("fail", "unknown"), "fail"),
])
def test_verified_sample_rollup_is_deterministic_and_conservative(outcomes, expected):
    context = _context()
    samples = tuple(
        ObservationSample(kind, outcome, 12)
        for kind, outcome in zip(("readiness", "liveness"), outcomes)
    )
    evidence = _evidence(context[-1], samples=samples)
    assert _rollup(context, evidence) == expected
    assert _rollup(context, evidence) == expected


@pytest.mark.parametrize("change", [
    {"mac_sha256": "0" * 64},
    {"samples": (ObservationSample("readiness", "fail", 1),
                 ObservationSample("liveness", "pass", 1))},
])
def test_rollup_never_classifies_tampered_evidence(change):
    context = _context()
    with pytest.raises(ValueError):
        _rollup(context, replace(_evidence(context[-1]), **change))


def test_rollup_rejects_stale_replayed_or_wrong_key_evidence():
    context = _context()
    evidence = _evidence(context[-1])
    for settings in (
        {"now_unix": 1_800_000_100},
        {"last_sequence": 1},
        {"source_key": _OTHER_KEY},
    ):
        with pytest.raises(ValueError):
            _rollup(context, evidence, **settings)


def test_rollup_rejects_changed_artifact_without_io(monkeypatch):
    import socket
    import subprocess
    import time

    def forbidden(*_args, **_kwargs):
        raise AssertionError("sample rollup must remain pure")

    context = _context()
    evidence = _evidence(context[-1])
    with monkeypatch.context() as guard:
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(time, "time", forbidden)
        assert _rollup(context, evidence) == "unknown"
        with pytest.raises(ValueError):
            _rollup((context[0], b"changed-artifact", *context[2:]), evidence)

# The pure rollup must honor the same opt-in caller trust policy as intake.

def _rollup_pin(context, key=_KEY):
    return ObservationSourcePin(
        "collector-1",
        hashlib.sha256(context[-1].to_json().encode("ascii")).hexdigest(),
        hashlib.sha256(key).hexdigest(),
        1_799_999_990, 1_800_000_030,
    )


@pytest.mark.parametrize("outcomes,expected", [
    (("pass", "pass"), "pass"),
    (("fail", "unknown"), "fail"),
    (("pass", "unknown"), "unknown"),
])
def test_rollup_accepts_valid_strict_source_pin(outcomes, expected):
    context = _context()
    samples = tuple(ObservationSample(kind, outcome, 1) for kind, outcome
                    in zip(("readiness", "liveness"), outcomes))
    evidence = _evidence(context[-1], samples=samples)
    assert _rollup(
        context, evidence, source_pin=_rollup_pin(context),
        require_source_pin=True, revoked_key_sha256=("0" * 64,),
    ) == expected


@pytest.mark.parametrize("settings", [
    {"require_source_pin": True},
    {"revoked_key_sha256": (hashlib.sha256(_KEY).hexdigest(),)},
])
def test_rollup_strict_policy_rejects_missing_pin(settings):
    context = _context()
    with pytest.raises(ValueError, match="pin required"):
        _rollup(context, _evidence(context[-1]), **settings)


def test_rollup_rejects_revoked_key_even_with_valid_mac_and_pin():
    context = _context()
    with pytest.raises(ValueError, match="key is revoked"):
        _rollup(
            context, _evidence(context[-1]),
            source_pin=_rollup_pin(context), require_source_pin=True,
            revoked_key_sha256=(hashlib.sha256(_KEY).hexdigest(),),
        )


@pytest.mark.parametrize("change", [
    {"source_id": "collector-2"},
    {"plan_sha256": "0" * 64},
    {"key_sha256": "0" * 64},
    {"valid_from_unix": 1_800_000_001},
    {"valid_until_unix": 1_800_000_014},
])
def test_rollup_rejects_mismatched_trusted_source_pin(change):
    context = _context()
    with pytest.raises(ValueError):
        _rollup(
            context, _evidence(context[-1]),
            source_pin=replace(_rollup_pin(context), **change),
            require_source_pin=True,
        )


@pytest.mark.parametrize("settings", [
    {"require_source_pin": 1},
    {"revoked_key_sha256": ["0" * 64]},
    {"revoked_key_sha256": ("G" * 64,)},
    {"revoked_key_sha256": ("0" * 64,) * 2},
])
def test_rollup_rejects_malformed_trust_policy(settings):
    context = _context()
    with pytest.raises(ValueError, match="invalid observation source trust policy"):
        _rollup(
            context, _evidence(context[-1]),
            source_pin=_rollup_pin(context), **settings,
        )


def test_rollup_key_rotation_requires_new_pin_and_valid_mac():
    context = _context()
    new_key = bytes(range(1, 33))
    evidence = _evidence(context[-1], key=new_key)
    with pytest.raises(ValueError, match="pin mismatch"):
        _rollup(context, evidence, source_key=new_key,
                source_pin=_rollup_pin(context), require_source_pin=True)
    assert _rollup(
        context, evidence, source_key=new_key,
        source_pin=_rollup_pin(context, key=new_key), require_source_pin=True,
        revoked_key_sha256=(hashlib.sha256(_KEY).hexdigest(),),
    ) == "unknown"


def test_rollup_strict_policy_remains_pure(monkeypatch):
    import socket
    import subprocess
    import time
    import os

    context = _context()
    evidence = _evidence(context[-1])
    def forbidden(*_args, **_kwargs):
        raise AssertionError("rollup trust check must not use external I/O")

    with monkeypatch.context() as guard:
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(os, "system", forbidden)
        guard.setattr(time, "time", forbidden)
        assert _rollup(
            context, evidence, source_pin=_rollup_pin(context),
            require_source_pin=True,
        ) == "unknown"
