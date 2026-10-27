"""A valid local-only audit event cannot be reused for another approved artifact.

Both approvals below are synthetic caller-supplied values, not authenticated
human approval. No provider, filesystem, network, or runtime is involved.
"""
import pytest

from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution,
    export_local_execution_audit_event, prepare_local_execution_request,
    verify_local_execution_audit_event,
)
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def test_valid_redacted_audit_cannot_replay_across_fresh_artifact_approvals():
    plan = derive_requirements(ApplicationProfile("synthetic-api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "synthetic-target")
    handoff = authorize_deployment_handoff(
        plan, proposal, request,
        DeploymentApproval(request.digest, "synthetic-handoff-reviewer"),
    )

    def evidence(artifact):
        execution = prepare_local_execution_request(handoff, artifact)
        approval = LocalExecutionApproval(execution.digest, "synthetic-execution-reviewer")
        receipt = authorize_local_execution(handoff, artifact, execution, approval)
        audit = export_local_execution_audit_event(handoff, artifact, approval, receipt)
        assert verify_local_execution_audit_event(
            handoff, artifact, approval, receipt, audit,
        ) is True
        assert receipt.infrastructure_mutated is False
        return artifact, approval, receipt, audit

    first = evidence(b"synthetic-artifact-version-one")
    second = evidence(b"synthetic-artifact-version-two")
    assert first[3] != second[3]

    # Even though both authorizations are individually valid and have the same
    # target and reviewer text, neither redacted audit can attest to the other.
    with pytest.raises(ValueError):
        verify_local_execution_audit_event(
            handoff, second[0], second[1], second[2], first[3],
        )
    with pytest.raises(ValueError):
        verify_local_execution_audit_event(
            handoff, first[0], first[1], first[2], second[3],
        )

    for audit in (first[3], second[3]):
        for hidden in (
            "synthetic-target", "synthetic-handoff-reviewer",
            "synthetic-execution-reviewer", "synthetic-artifact-version",
        ):
            assert hidden not in audit
