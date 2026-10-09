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
