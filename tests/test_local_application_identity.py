"""Fail closed on control characters in the reviewed application identity."""
import pytest
from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution, prepare_local_execution_request,
)
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def handoff_for(name):
    plan = derive_requirements(ApplicationProfile(name, "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    return authorize_deployment_handoff(plan, proposal, request,
                                        DeploymentApproval(request.digest, "reviewer"))


@pytest.mark.parametrize("identity", [
    "api\nservice", "api\x00service", "api\u0085service",
    "api\u202eservice", "api\u200dservice", "api\u2028service",
    "api\u00a0service", "api\ud800service",
])
def test_control_character_application_identity_rejected(identity):
    handoff = handoff_for(identity)
    with pytest.raises(ValueError, match="malformed handoff provenance or document"):
        prepare_local_execution_request(handoff, b"synthetic-artifact")


@pytest.mark.parametrize("identity", ["api", "café", "東京-api", "my api"])
def test_legitimate_application_identity_remains_accepted(identity):
    handoff = handoff_for(identity)
    artifact = b"synthetic-artifact"
    execution = prepare_local_execution_request(handoff, artifact)
    receipt = authorize_local_execution(
        handoff, artifact, execution,
        LocalExecutionApproval(execution.digest, "reviewer"),
    )
    assert receipt.infrastructure_mutated is False
    assert receipt.status == "authorized-local-only"

@pytest.mark.parametrize("identity", [" api", "api ", " api "])
def test_surrounding_ascii_whitespace_application_identity_rejected(identity):
    # The accepted handoff can carry this name; the local execution boundary
    # must not authorize visually ambiguous leading/trailing ASCII spaces.
    handoff = handoff_for(identity)
    with pytest.raises(ValueError, match="malformed handoff provenance or document"):
        prepare_local_execution_request(handoff, b"synthetic-artifact")
