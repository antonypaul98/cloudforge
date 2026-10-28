"""No-network, exact-input runtime observation proposal regressions."""
from dataclasses import replace
import hashlib
import json
import socket
import subprocess

import pytest

from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution, prepare_local_execution_request,
)
from cloudforge.models import ApplicationProfile
from cloudforge.observation_plan import ObservationProbe, prepare_observation_plan
from cloudforge.observation_runtime_request import (
    RuntimeObservationTarget, prepare_runtime_observation_request,
    verify_runtime_observation_request,
)
from cloudforge.planner import derive_requirements


def _context():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "fixture")
    handoff = authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "reviewer"),
    )
    artifact = b"runtime-proposal-fixture"
    local_request = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(local_request.digest, "reviewer")
    receipt = authorize_local_execution(handoff, artifact, local_request, approval)
    observation = prepare_observation_plan(
        handoff, artifact, approval, receipt,
        (ObservationProbe("readiness", 10, 2, 3),
         ObservationProbe("liveness", 20, 2, 3)),
    )
    return handoff, artifact, approval, receipt, observation


def _targets():
    return (
        RuntimeObservationTarget("readiness", "https", "api.example.com", 443, "/ready"),
        RuntimeObservationTarget("liveness", "https", "api.example.com", 443, "/live"),
    )


def test_runtime_proposal_is_deterministic_redacted_and_not_authorized():
    context, targets = _context(), _targets()
    request = prepare_runtime_observation_request(*context, targets)
    assert request == prepare_runtime_observation_request(*context, targets)
    assert verify_runtime_observation_request(*context, targets, request)
    exported = request.to_json()
    assert json.loads(exported)["status"] == "pending-independent-approval"
    assert exported == json.dumps(json.loads(exported), sort_keys=True, indent=2) + "\n"
    for forbidden in ("api.example.com", "/ready", "/live", "reviewer",
                      "runtime-proposal-fixture", "healthy", "approved"):
        assert forbidden not in exported
    assert '"infrastructure_mutated": false' in exported
    assert '"deployment_observed": false' in exported
    assert '"recovery_performed": false' in exported
    assert request.observation_plan_sha256 == hashlib.sha256(
        context[-1].to_json().encode("ascii")
    ).hexdigest()


def test_changed_target_requires_new_proposal():
    context, targets = _context(), _targets()
    request = prepare_runtime_observation_request(*context, targets)
    changed = (replace(targets[0], path="/newready"), targets[1])
    with pytest.raises(ValueError, match="differs"):
        verify_runtime_observation_request(*context, changed, request)
    assert prepare_runtime_observation_request(*context, changed) != request


@pytest.mark.parametrize("mutation", [
    lambda ts: list(ts),
    lambda ts: ts[:1],
    lambda ts: ts[::-1],
    lambda ts: ts + ts[:1],
    lambda ts: (replace(ts[0], scheme="http"), ts[1]),
    lambda ts: (replace(ts[0], scheme=True), ts[1]),
    lambda ts: (replace(ts[0], host="localhost"), ts[1]),
    lambda ts: (replace(ts[0], host="169.254.169.254"), ts[1]),
    lambda ts: (replace(ts[0], host="api.example.com.evil/"), ts[1]),
    lambda ts: (replace(ts[0], host="API.example.com"), ts[1]),
    lambda ts: (replace(ts[0], host="user@api.example.com"), ts[1]),
    lambda ts: (replace(ts[0], host="api..example.com"), ts[1]),
    lambda ts: (replace(ts[0], host="api.exämple.com"), ts[1]),
    lambda ts: (replace(ts[0], host=True), ts[1]),
    lambda ts: (replace(ts[0], port=True), ts[1]),
    lambda ts: (replace(ts[0], port=65536), ts[1]),
    lambda ts: (replace(ts[0], path="//metadata"), ts[1]),
    lambda ts: (replace(ts[0], path="/ready?token=x"), ts[1]),
    lambda ts: (replace(ts[0], path="/../ready"), ts[1]),
    lambda ts: (replace(ts[0], kind="liveness"), ts[1]),
])
def test_rejects_unsafe_or_misordered_runtime_proposals(mutation):
    with pytest.raises(ValueError):
        prepare_runtime_observation_request(*_context(), mutation(_targets()))


@pytest.mark.parametrize("mutation", [
    lambda r: replace(r, observation_plan_sha256="0" * 64),
    lambda r: replace(r, ordered_targets_sha256="0" * 64),
    lambda r: replace(r, status="approved"),
    lambda r: replace(r, operation="execute-head"),
    lambda r: replace(r, infrastructure_mutated=True),
    lambda r: replace(r, deployment_observed=True),
    lambda r: replace(r, recovery_performed=True),
    lambda r: replace(r, format_version=True),
])
def test_tampered_proposal_fails_closed(mutation):
    context, targets = _context(), _targets()
    request = mutation(prepare_runtime_observation_request(*context, targets))
    with pytest.raises(ValueError):
        verify_runtime_observation_request(*context, targets, request)
    with pytest.raises(ValueError):
        request.to_json()


def test_changed_artifact_rejected_before_proposal():
    context = _context()
    with pytest.raises((ValueError, PermissionError)):
        prepare_runtime_observation_request(
            context[0], b"changed", *context[2:], _targets(),
        )


def test_runtime_proposal_never_uses_network_or_subprocess(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("proposal attempted network or process I/O")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    context, targets = _context(), _targets()
    request = prepare_runtime_observation_request(*context, targets)
    assert verify_runtime_observation_request(*context, targets, request)
