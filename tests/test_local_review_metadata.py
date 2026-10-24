"""Review-visible resource metadata must be unambiguous before local authorization."""
from dataclasses import replace

import pytest

from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import prepare_local_execution_request
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def _handoff(field, value):
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    resources = list(plan.resources)
    compute = resources[0]
    if field == "reason":
        resources[0] = replace(compute, reason=value)
    else:
        resources[0] = replace(
            compute, properties={**compute.properties, field: value},
        )
    plan = replace(plan, resources=tuple(resources))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    return authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "reviewer"),
    )


@pytest.mark.parametrize("field", ["reason", "runtime", "source"])
@pytest.mark.parametrize("char", [
    "\n", "\u202e", "\ud800", "\u2028", "\u00a0",
    "\ufdd0", "\U0010ffff",
])
def test_invisible_or_reserved_resource_metadata_rejected(field, char):
    handoff = _handoff(field, "safe" + char + "value")
    with pytest.raises(ValueError, match="malformed handoff provenance or document"):
        prepare_local_execution_request(handoff, b"synthetic-artifact")


@pytest.mark.parametrize("field", ["reason", "runtime", "source"])
def test_legitimate_unicode_resource_metadata_preserved(field):
    handoff = _handoff(field, "café 東京 service")
    request = prepare_local_execution_request(handoff, b"synthetic-artifact")
    assert request.target_id == "staging"
    assert len(request.artifact_sha256) == 64
