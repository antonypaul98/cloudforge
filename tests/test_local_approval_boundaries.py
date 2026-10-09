"""Execution authorization must never reuse earlier approval scopes or stale artifact bytes."""
import hashlib
import json
from dataclasses import replace

import pytest

from cloudforge.approval import ApprovalRequiredError, PlanApproval, plan_digest
from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution, prepare_local_execution_request,
)
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def _fixture():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    handoff_request = prepare_deployment_request(plan, proposal, "staging")
    handoff = authorize_deployment_handoff(
        plan, proposal, handoff_request,
        DeploymentApproval(handoff_request.digest, "reviewer"),
    )
    artifact = b"reviewed-artifact-v1"
    execution = prepare_local_execution_request(handoff, artifact)
    return plan, handoff, artifact, execution


def test_handoff_digest_cannot_be_reused_as_execution_approval():
    _, handoff, artifact, execution = _fixture()
    assert handoff.request_digest != execution.digest
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(
            handoff, artifact, execution,
            LocalExecutionApproval(handoff.request_digest, "reviewer"),
        )


@pytest.mark.parametrize("approval_kind", ["plan", "handoff"])
def test_prior_approval_receipt_types_cannot_authorize_execution(approval_kind):
    plan, handoff, artifact, execution = _fixture()
    approval = (
        PlanApproval(plan_digest(plan), "reviewer")
        if approval_kind == "plan"
        else DeploymentApproval(handoff.request_digest, "reviewer")
    )
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(handoff, artifact, execution, approval)


def test_same_length_artifact_mutation_requires_fresh_execution_approval():
    _, handoff, artifact, execution = _fixture()
    altered = artifact[:-1] + b"2"
    assert len(altered) == len(artifact)
    assert hashlib.sha256(altered).digest() != hashlib.sha256(artifact).digest()
    with pytest.raises(ValueError):
        authorize_local_execution(
            handoff, altered, execution,
            LocalExecutionApproval(execution.digest, "reviewer"),
        )
    new_execution = prepare_local_execution_request(handoff, altered)
    assert new_execution.digest != execution.digest
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(
            handoff, altered, new_execution,
            LocalExecutionApproval(execution.digest, "reviewer"),
        )


def test_local_receipt_serialization_is_deterministic_and_exactly_bound():
    _, handoff, artifact, execution = _fixture()
    approval = LocalExecutionApproval(execution.digest, "reviewer")
    first = authorize_local_execution(handoff, artifact, execution, approval)
    second = authorize_local_execution(handoff, artifact, execution, approval)
    assert first.to_json() == second.to_json()
    data = json.loads(first.to_json())
    assert data["request_digest"] == execution.digest
    assert data["request"]["handoff_digest"] == handoff.request_digest
    assert data["request"]["artifact_sha256"] == hashlib.sha256(artifact).hexdigest()
    assert data["infrastructure_mutated"] is False
    assert data["status"] == "authorized-local-only"


def test_handoff_approval_identity_change_does_not_preserve_execution_binding():
    _, handoff, artifact, execution = _fixture()
    altered = replace(handoff, approved_by="different-reviewer")
    # Execution binds the exact handoff request digest; identity metadata is
    # checked independently, and changing it never grants execution approval.
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(altered, artifact, execution, None)
