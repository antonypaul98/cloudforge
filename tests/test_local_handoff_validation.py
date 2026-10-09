"""Fail-closed metadata regressions for the local-only adapter checkpoint."""
from dataclasses import replace
import pytest

from cloudforge.deployment import DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import prepare_local_execution_request
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def _handoff():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    return authorize_deployment_handoff(plan, proposal, request, DeploymentApproval(request.digest, "reviewer"))


@pytest.mark.parametrize("field,value", [
    ("format_version", 2), ("format_version", True), ("format_version", "1"), ("operation", "deploy"), ("operation", None),
])
def test_forged_handoff_metadata_fails_closed(field, value):
    handoff = _handoff()
    forged_request = replace(handoff.request, **{field: value})
    forged_handoff = replace(handoff, request=forged_request, request_digest=forged_request.digest)
    with pytest.raises(ValueError):
        prepare_local_execution_request(forged_handoff, b"exact artifact")


@pytest.mark.parametrize("name", ["", " ", "bad\nname", "bad\x00name", " reviewer", "reviewer ", None, 42])
def test_forged_handoff_approver_fails_closed(name):
    handoff = _handoff()
    with pytest.raises(ValueError):
        prepare_local_execution_request(replace(handoff, approved_by=name), b"exact artifact")


def test_noncanonical_handoff_request_type_fails_closed():
    handoff = _handoff()
    forged_handoff = replace(handoff, request={"target_id": "staging"}, request_digest="0" * 64)
    with pytest.raises(ValueError):
        prepare_local_execution_request(forged_handoff, b"exact artifact")
