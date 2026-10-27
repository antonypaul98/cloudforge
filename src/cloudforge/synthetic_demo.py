"""Credential-free, in-memory local authorization smoke demo.

This deliberately uses caller-constructed synthetic approvals. It does not
authenticate a reviewer, deploy, observe infrastructure, or perform recovery.
"""
from __future__ import annotations

import json
from dataclasses import replace

from .deployment import (
    DeploymentApproval,
    authorize_deployment_handoff,
    prepare_deployment_request,
)
from .iac import render_iac_proposal
from .local_adapter import (
    LocalExecutionApproval,
    authorize_local_execution,
    export_local_execution_audit_event,
    prepare_local_execution_request,
    verify_local_execution_audit_event,
    verify_local_execution_receipt_json,
)
from .models import ApplicationProfile
from .planner import derive_requirements


def run_synthetic_local_authorization_demo() -> dict[str, object]:
    """Exercise exact binding, redacted evidence and two fail-closed paths."""
    plan = derive_requirements(ApplicationProfile("synthetic-api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "synthetic-target")
    handoff = authorize_deployment_handoff(
        plan, proposal, request,
        DeploymentApproval(request.digest, "synthetic-handoff-reviewer"),
    )
    artifact = b"cloudforge-synthetic-artifact-v1"
    execution = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(execution.digest, "synthetic-execution-reviewer")
    receipt = authorize_local_execution(handoff, artifact, execution, approval)
    receipt_json = receipt.to_json()
    if verify_local_execution_receipt_json(handoff, artifact, approval, receipt_json) is not True:
        raise RuntimeError("synthetic receipt verification failed")
    audit_json = export_local_execution_audit_event(handoff, artifact, approval, receipt)
    if verify_local_execution_audit_event(handoff, artifact, approval, receipt, audit_json) is not True:
        raise RuntimeError("synthetic audit verification failed")

    # These are intentionally invalid, local-only observations. A forged
    # recovery claim and altered artifact must never pass the same approval.
    try:
        verify_local_execution_audit_event(
            handoff, artifact, approval, receipt,
            audit_json.replace("authorized-local-only", "recovered"),
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("forged recovery status was accepted")
    try:
        verify_local_execution_receipt_json(
            handoff, artifact + b"-changed", approval, receipt_json,
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("changed artifact reused a stale approval")

    # A receipt reviewer is caller-controlled text, never an authenticated
    # identity. Even a canonical forged receipt must fail exact revalidation.
    forged_reviewer_receipt = replace(receipt, approved_by="forged-reviewer")
    try:
        verify_local_execution_receipt_json(
            handoff, artifact, approval, forged_reviewer_receipt.to_json(),
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("forged receipt reviewer was accepted")

    # A separately constructed approval cannot authorize a different target
    # than the exact reviewed handoff, even when its own digest is consistent.
    cross_target_request = replace(execution, target_id="synthetic-other-target")
    cross_target_approval = LocalExecutionApproval(
        cross_target_request.digest, "synthetic-execution-reviewer",
    )
    try:
        authorize_local_execution(
            handoff, artifact, cross_target_request, cross_target_approval,
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("cross-target authorization was accepted")

    # A synthetic authorization receipt is not evidence of a real mutation.
    # Reject a canonical-shaped audit event that falsely claims one.
    forged_mutation_audit = audit_json.replace(
        '"infrastructure_mutated": false', '"infrastructure_mutated": true',
    )
    if forged_mutation_audit == audit_json:
        raise RuntimeError("synthetic audit mutation field was not found")
    try:
        verify_local_execution_audit_event(
            handoff, artifact, approval, receipt, forged_mutation_audit,
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("forged infrastructure mutation was accepted")

    return {
        "demo_only": True,
        "authenticated_review": False,
        "infrastructure_mutated": False,
        "deployment_observed": False,
        "recovery_performed": False,
        "synthetic_rejections": {
            "forged_recovery_status": True,
            "changed_artifact": True,
            "forged_receipt_reviewer": True,
            "cross_target_authorization": True,
            "forged_mutation_evidence": True,
        },
        "redacted_audit_event": json.loads(audit_json),
    }


if __name__ == "__main__":
    print(json.dumps(run_synthetic_local_authorization_demo(), sort_keys=True, indent=2))
