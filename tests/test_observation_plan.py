"""Synthetic observation planning only; no live health or deployment evidence."""
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
from cloudforge.planner import derive_requirements
from cloudforge.observation_plan import (
    ObservationProbe, prepare_observation_plan, verify_observation_plan,
)


def _sample(target="staging", artifact=b"synthetic-observation-artifact"):
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, target)
    handoff = authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "handoff-reviewer"),
    )
    local_request = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(local_request.digest, "local-reviewer")
    receipt = authorize_local_execution(handoff, artifact, local_request, approval)
    return handoff, artifact, approval, receipt


def _probes():
    return (
        ObservationProbe("readiness", 10, 2, 3),
        ObservationProbe("liveness", 30, 5, 5),
    )


def test_proposal_is_deterministic_redacted_and_not_health_evidence():
    handoff, artifact, approval, receipt = _sample()
    plan = prepare_observation_plan(handoff, artifact, approval, receipt, _probes())
    assert plan == prepare_observation_plan(handoff, artifact, approval, receipt, _probes())
    assert verify_observation_plan(handoff, artifact, approval, receipt, plan) is True
    payload = json.loads(plan.to_json())
    assert payload["status"] == "proposed-only"
    assert payload["infrastructure_mutated"] is False
    assert payload["deployment_observed"] is False
    assert payload["recovery_performed"] is False
    assert payload["authorization_request_digest"] == receipt.request_digest
    assert payload["authorization_receipt_sha256"] == hashlib.sha256(
        receipt.to_json().encode("ascii")
    ).hexdigest()
    assert "staging" not in plan.to_json()
    assert "handoff-reviewer" not in plan.to_json()
    assert "local-reviewer" not in plan.to_json()
    assert artifact.decode() not in plan.to_json()


def test_startup_probe_is_optional_and_does_not_imply_execution():
    handoff, artifact, approval, receipt = _sample()
    probes = (ObservationProbe("startup", 5, 1, 10),) + _probes()
    result = prepare_observation_plan(handoff, artifact, approval, receipt, probes)
    assert verify_observation_plan(handoff, artifact, approval, receipt, result)
    assert result.deployment_observed is False


@pytest.mark.parametrize("probes", [
    [],
    [ObservationProbe("readiness", 10, 2, 3), ObservationProbe("liveness", 10, 2, 3)],
    (),
    (ObservationProbe("readiness", 10, 2, 3),),
    (ObservationProbe("liveness", 10, 2, 3),),
    (ObservationProbe("readiness", 10, 2, 3), ObservationProbe("readiness", 10, 2, 3)),
    (ObservationProbe("readiness", 10, 2, 3), ObservationProbe("shell", 10, 2, 3)),
    (ObservationProbe("readiness", 10, 2, 3), ObservationProbe("liveness", 10, 2, 3),
     ObservationProbe("startup", 10, 2, 3), ObservationProbe("startup", 10, 2, 3)),
    (ObservationProbe("readiness", True, 2, 3), ObservationProbe("liveness", 10, 2, 3)),
    (ObservationProbe("readiness", 10, True, 3), ObservationProbe("liveness", 10, 2, 3)),
    (ObservationProbe("readiness", 10, 2, True), ObservationProbe("liveness", 10, 2, 3)),
    (ObservationProbe("readiness", 0, 2, 3), ObservationProbe("liveness", 10, 2, 3)),
    (ObservationProbe("readiness", 10, 11, 3), ObservationProbe("liveness", 10, 2, 3)),
    (ObservationProbe("readiness", 10, 2, 0), ObservationProbe("liveness", 10, 2, 3)),
    (ObservationProbe("readiness", 301, 2, 3), ObservationProbe("liveness", 10, 2, 3)),
    (ObservationProbe("readiness", 10, 2, 11), ObservationProbe("liveness", 10, 2, 3)),
    (ObservationProbe("readiness", 10, 2, 3), {"kind": "liveness"}),
])
def test_invalid_probe_configs_fail_closed(probes):
    handoff, artifact, approval, receipt = _sample()
    with pytest.raises(ValueError):
        prepare_observation_plan(handoff, artifact, approval, receipt, probes)


@pytest.mark.parametrize("field,value", [
    ("status", "healthy"),
    ("infrastructure_mutated", True),
    ("deployment_observed", True),
    ("recovery_performed", True),
    ("format_version", True),
    ("format_version", 2),
    ("authorization_request_digest", "0" * 64),
    ("authorization_receipt_sha256", "f" * 64),
])
def test_forged_plan_claims_or_bindings_fail_closed(field, value):
    handoff, artifact, approval, receipt = _sample()
    plan = prepare_observation_plan(handoff, artifact, approval, receipt, _probes())
    forged = replace(plan, **{field: value})
    with pytest.raises(ValueError):
        verify_observation_plan(handoff, artifact, approval, receipt, forged)
    if field not in ("authorization_request_digest", "authorization_receipt_sha256"):
        with pytest.raises(ValueError):
            forged.to_json()


def test_stale_artifact_and_approval_cannot_reuse_observation_plan():
    handoff, artifact, approval, receipt = _sample()
    plan = prepare_observation_plan(handoff, artifact, approval, receipt, _probes())
    with pytest.raises(ValueError):
        verify_observation_plan(handoff, b"changed", approval, receipt, plan)
    with pytest.raises(ApprovalRequiredError):
        verify_observation_plan(
            handoff, artifact, LocalExecutionApproval("0" * 64, "local-reviewer"),
            receipt, plan,
        )
    other_handoff, other_artifact, other_approval, other_receipt = _sample(target="production")
    with pytest.raises(ValueError):
        verify_observation_plan(
            other_handoff, other_artifact, other_approval, other_receipt, plan,
        )


def test_no_external_probe_is_executed(monkeypatch):
    import socket
    import subprocess
    import os

    def forbidden(*args, **kwargs):
        raise AssertionError("observation planning must not execute probes")

    handoff, artifact, approval, receipt = _sample()
    with monkeypatch.context() as guard:
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(subprocess, "run", forbidden)
        guard.setattr(os, "system", forbidden)
        plan = prepare_observation_plan(handoff, artifact, approval, receipt, _probes())
        assert verify_observation_plan(handoff, artifact, approval, receipt, plan)
    assert plan.status == "proposed-only"
