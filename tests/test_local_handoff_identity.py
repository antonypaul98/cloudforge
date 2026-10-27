"""Ensure execution approval binds the complete accepted handoff receipt."""
from dataclasses import replace
import pytest
from cloudforge.approval import ApprovalRequiredError
from cloudforge.deployment import DeploymentApproval, prepare_deployment_request, authorize_deployment_handoff
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import LocalExecutionApproval, prepare_local_execution_request, authorize_local_execution
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements

def test_changing_handoff_approver_invalidates_prior_execution_approval():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    handoff_request = prepare_deployment_request(plan, proposal, "staging")
    handoff = authorize_deployment_handoff(
        plan, proposal, handoff_request,
        DeploymentApproval(handoff_request.digest, "handoff-reviewer-A"),
    )
    artifact = b"synthetic-artifact"
    request = prepare_local_execution_request(handoff, artifact)
    changed_handoff = replace(handoff, approved_by="handoff-reviewer-B")
    changed_request = prepare_local_execution_request(changed_handoff, artifact)
    assert request.handoff_digest == changed_request.handoff_digest
    assert request.handoff_receipt_sha256 != changed_request.handoff_receipt_sha256
    assert request.digest != changed_request.digest
    with pytest.raises(ValueError):
        authorize_local_execution(
            changed_handoff, artifact, request,
            LocalExecutionApproval(request.digest, "execution-reviewer"),
        )
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(
            changed_handoff, artifact, changed_request,
            LocalExecutionApproval(request.digest, "execution-reviewer"),
        )

def test_receipt_digest_deterministic_and_does_not_embed_handoff_approver():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    handoff = authorize_deployment_handoff(plan, proposal, request, DeploymentApproval(request.digest, "reviewer"))
    first = prepare_local_execution_request(handoff, b"bytes")
    second = prepare_local_execution_request(handoff, b"bytes")
    assert first == second
    assert len(first.handoff_receipt_sha256) == 64
    assert "reviewer" not in str(first)
