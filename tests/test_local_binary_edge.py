"""Exact binary artifact binding at the local-only authorization boundary."""
import hashlib

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


def _handoff():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    return authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "reviewer"),
    )


@pytest.mark.parametrize("artifact", [b"\x00\xff\x80\x00", b"\x00\x00", b""])
def test_binary_artifact_digest_binds_exact_bytes(artifact):
    handoff = _handoff()
    request = prepare_local_execution_request(handoff, artifact)
    assert request.artifact_sha256 == hashlib.sha256(artifact).hexdigest()
    receipt = authorize_local_execution(
        handoff, artifact, request, LocalExecutionApproval(request.digest, "reviewer"),
    )
    assert receipt.infrastructure_mutated is False


@pytest.mark.parametrize("invalid", [bytearray(b"\x00"), memoryview(b"\x00"), "text", None, True])
def test_noncanonical_artifact_types_fail_closed(invalid):
    with pytest.raises(ValueError, match="exact bytes"):
        prepare_local_execution_request(_handoff(), invalid)


def test_binary_mutation_requires_fresh_authorization():
    handoff = _handoff()
    original = b"\x00\xff\x80\x00"
    modified = b"\x00\xfe\x80\x00"
    request = prepare_local_execution_request(handoff, original)
    with pytest.raises(ValueError):
        authorize_local_execution(
            handoff, modified, request, LocalExecutionApproval(request.digest, "reviewer"),
        )
