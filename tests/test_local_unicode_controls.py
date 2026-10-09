"""Unicode control, format, surrogate and line separators must not be accepted as execution identities."""
from dataclasses import replace

import pytest

from cloudforge.approval import ApprovalRequiredError
from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution,
    prepare_local_execution_request,
)
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def _sample():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    handoff = authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "reviewer")
    )
    artifact = b"exact artifact"
    execution = prepare_local_execution_request(handoff, artifact)
    return handoff, artifact, execution


@pytest.mark.parametrize("control", ["\u0085", "\u009f", "\u202e", "\u2066", "\u200d", "\u2028", "\u2029", "\ud800"])
def test_target_rejects_embedded_unicode_control(control):
    handoff, artifact, _ = _sample()
    request = replace(handoff.request, target_id="sta" + control + "ging")
    forged = replace(handoff, request=request, request_digest=request.digest)
    with pytest.raises(ValueError, match="control characters"):
        prepare_local_execution_request(forged, artifact)


@pytest.mark.parametrize("control", ["\u0085", "\u009f", "\u202e", "\u2066", "\u200d", "\u2028", "\u2029", "\ud800"])
def test_handoff_approver_rejects_embedded_unicode_control(control):
    handoff, artifact, _ = _sample()
    with pytest.raises(ValueError, match="control characters"):
        prepare_local_execution_request(
            replace(handoff, approved_by="rev" + control + "iewer"), artifact
        )


@pytest.mark.parametrize("control", ["\u0085", "\u009f", "\u202e", "\u2066", "\u200d", "\u2028", "\u2029", "\ud800"])
def test_execution_approver_rejects_embedded_unicode_control(control):
    handoff, artifact, execution = _sample()
    with pytest.raises(ApprovalRequiredError, match="control characters"):
        authorize_local_execution(
            handoff, artifact, execution,
            LocalExecutionApproval(execution.digest, "rev" + control + "iewer"),
        )
