"""Unicode noncharacters must not enter local approval identity bindings."""
from dataclasses import replace

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


NONCHARACTERS = ("\ufdd0", "\ufdef", "\ufffe", "\uffff", "\U0001fffe", "\U0010ffff")


def _handoff(name="api"):
    plan = derive_requirements(ApplicationProfile(name, "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    return authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "reviewer")
    )


@pytest.mark.parametrize("char", NONCHARACTERS)
def test_noncharacter_application_identity_rejected(char):
    with pytest.raises(ValueError, match="malformed handoff provenance or document"):
        prepare_local_execution_request(_handoff("api" + char + "service"), b"artifact")


@pytest.mark.parametrize("char", NONCHARACTERS)
def test_noncharacter_target_identity_rejected(char):
    handoff = _handoff()
    request = replace(handoff.request, target_id="sta" + char + "ging")
    forged = replace(handoff, request=request, request_digest=request.digest)
    with pytest.raises(ValueError, match="control characters"):
        prepare_local_execution_request(forged, b"artifact")


@pytest.mark.parametrize("char", NONCHARACTERS)
def test_noncharacter_handoff_approver_rejected(char):
    with pytest.raises(ValueError, match="control characters"):
        prepare_local_execution_request(
            replace(_handoff(), approved_by="rev" + char + "iewer"), b"artifact"
        )


@pytest.mark.parametrize("char", NONCHARACTERS)
def test_noncharacter_execution_approver_rejected(char):
    handoff = _handoff()
    artifact = b"artifact"
    execution = prepare_local_execution_request(handoff, artifact)
    with pytest.raises(ApprovalRequiredError, match="control characters"):
        authorize_local_execution(
            handoff, artifact, execution,
            LocalExecutionApproval(execution.digest, "rev" + char + "iewer"),
        )


@pytest.mark.parametrize("name", ["api", "café", "東京-api", "my api"])
def test_valid_application_identity_preserved(name):
    handoff = _handoff(name)
    artifact = b"artifact"
    execution = prepare_local_execution_request(handoff, artifact)
    receipt = authorize_local_execution(
        handoff, artifact, execution,
        LocalExecutionApproval(execution.digest, "reviewer"),
    )
    assert receipt.infrastructure_mutated is False
    assert receipt.status == "authorized-local-only"
