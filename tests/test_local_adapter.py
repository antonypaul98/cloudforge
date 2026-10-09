"""Bounded local execution authorization regression checks."""
import json
from dataclasses import replace
import pytest
from cloudforge.approval import ApprovalRequiredError
from cloudforge.deployment import DeploymentApproval, prepare_deployment_request, authorize_deployment_handoff
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import LocalExecutionApproval, prepare_local_execution_request, authorize_local_execution
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements

def sample():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    handoff = authorize_deployment_handoff(plan, proposal, request, DeploymentApproval(request.digest, "reviewer"))
    artifact = b"exact artifact"
    execution = prepare_local_execution_request(handoff, artifact)
    return handoff, artifact, execution

def test_deterministic_local_receipt():
    handoff, artifact, execution = sample()
    approval = LocalExecutionApproval(execution.digest, "reviewer")
    receipt = authorize_local_execution(handoff, artifact, execution, approval)
    assert receipt.infrastructure_mutated is False
    assert json.loads(receipt.to_json())["status"] == "authorized-local-only"

@pytest.mark.parametrize("changed", [b"new artifact", b"exact artifact "])
def test_artifact_mutation_requires_fresh_request(changed):
    handoff, _, execution = sample()
    with pytest.raises(ValueError):
        authorize_local_execution(handoff, changed, execution, LocalExecutionApproval(execution.digest, "reviewer"))

@pytest.mark.parametrize("field,value", [("target_id", "production"), ("operation", "deploy"), ("format_version", True)])
def test_request_mutation_rejected(field, value):
    handoff, artifact, execution = sample()
    with pytest.raises(ValueError):
        authorize_local_execution(handoff, artifact, replace(execution, **{field: value}), LocalExecutionApproval(execution.digest, "reviewer"))

@pytest.mark.parametrize("invalid", [None, True, "yes"])
def test_approval_bypass_rejected(invalid):
    handoff, artifact, execution = sample()
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(handoff, artifact, execution, invalid)


from dataclasses import FrozenInstanceError

@pytest.mark.parametrize("name", ["", " ", " bad", "bad ", "bad\\nname", None, 42])
def test_invalid_execution_approver_rejected(name):
    handoff, artifact, request = sample()
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(handoff, artifact, request, LocalExecutionApproval(request.digest, name))

def test_stale_approval_rejected():
    handoff, artifact, request = sample()
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(handoff, artifact, request, LocalExecutionApproval("0" * 64, "reviewer"))

def test_changed_target_requires_fresh_execution_approval():
    handoff, artifact, request = sample()
    new_request = replace(handoff.request, target_id="production")
    new_handoff = replace(handoff, request=new_request, request_digest=new_request.digest)
    new_execution = prepare_local_execution_request(new_handoff, artifact)
    assert new_execution.digest != request.digest
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(new_handoff, artifact, new_execution, LocalExecutionApproval(request.digest, "reviewer"))

@pytest.mark.parametrize("target", ["", " ", " bad", "bad\\n", "a\\x00b", None, 42])
def test_malformed_target_rejected(target):
    handoff, artifact, _ = sample()
    request = replace(handoff.request, target_id=target)
    changed = replace(handoff, request=request, request_digest=request.digest)
    with pytest.raises(ValueError):
        prepare_local_execution_request(changed, artifact)

def test_request_approval_and_receipt_are_immutable():
    handoff, artifact, request = sample()
    approval = LocalExecutionApproval(request.digest, "reviewer")
    receipt = authorize_local_execution(handoff, artifact, request, approval)
    with pytest.raises(FrozenInstanceError):
        request.target_id = "other"
    with pytest.raises(FrozenInstanceError):
        approval.approved_by = "other"
    with pytest.raises(FrozenInstanceError):
        receipt.infrastructure_mutated = True

def test_authorization_has_no_external_runtime_side_effects(monkeypatch):
    import builtins
    import os
    import pathlib
    import socket
    import subprocess
    handoff, artifact, request = sample()
    approval = LocalExecutionApproval(request.digest, "reviewer")
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected external runtime side effect")
    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(os, "system", forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(pathlib.Path, "open", forbidden)
        guard.setattr(pathlib.Path, "write_bytes", forbidden)
        receipt = authorize_local_execution(handoff, artifact, request, approval)
    assert receipt.infrastructure_mutated is False
