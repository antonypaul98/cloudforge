"""Default-ignorable variation marks must not obscure local review fields."""

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


INVISIBLE_MARKS = ("\u034f", "\u180b", "\u180f", "\ufe0e", "\ufe0f", "\U000e0100",
                   "\u115f", "\u1160", "\u2800", "\u3164", "\uffa0")


def _handoff(name="api", runtime="python", target="staging", reviewer="reviewer"):
    plan = derive_requirements(ApplicationProfile(name, runtime, port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, target)
    return authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, reviewer),
    )


@pytest.mark.parametrize("mark", INVISIBLE_MARKS)
def test_invisible_mark_in_application_rejected(mark):
    with pytest.raises(ValueError, match="malformed handoff provenance or document"):
        prepare_local_execution_request(_handoff(name="api" + mark + "service"), b"artifact")


@pytest.mark.parametrize("mark", INVISIBLE_MARKS)
def test_invisible_mark_in_resource_metadata_rejected(mark):
    with pytest.raises(ValueError, match="malformed handoff provenance or document"):
        prepare_local_execution_request(_handoff(runtime="py" + mark + "thon"), b"artifact")


@pytest.mark.parametrize("mark", INVISIBLE_MARKS)
def test_invisible_mark_in_target_rejected(mark):
    with pytest.raises(ValueError, match="control characters"):
        prepare_local_execution_request(_handoff(target="sta" + mark + "ging"), b"artifact")


@pytest.mark.parametrize("mark", INVISIBLE_MARKS)
def test_invisible_mark_in_handoff_reviewer_rejected(mark):
    with pytest.raises(ValueError, match="control characters"):
        prepare_local_execution_request(_handoff(reviewer="rev" + mark + "iewer"), b"artifact")


@pytest.mark.parametrize("mark", INVISIBLE_MARKS)
def test_invisible_mark_in_execution_reviewer_rejected(mark):
    handoff = _handoff()
    artifact = b"artifact"
    request = prepare_local_execution_request(handoff, artifact)
    with pytest.raises(ApprovalRequiredError, match="control characters"):
        authorize_local_execution(
            handoff, artifact, request,
            LocalExecutionApproval(request.digest, "rev" + mark + "iewer"),
        )


@pytest.mark.parametrize("name", ["api", "my api", "café", "cafe\u0301", "東京-api"])
def test_legitimate_unicode_application_names_remain_valid(name):
    handoff = _handoff(name=name)
    artifact = b"artifact"
    request = prepare_local_execution_request(handoff, artifact)
    receipt = authorize_local_execution(
        handoff, artifact, request,
        LocalExecutionApproval(request.digest, "reviewer"),
    )
    assert receipt.status == "authorized-local-only"
    assert receipt.infrastructure_mutated is False
