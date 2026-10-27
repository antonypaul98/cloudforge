"""Credential-free, in-memory local authorization smoke demo.

This deliberately uses caller-constructed synthetic approvals. It does not
authenticate a reviewer, deploy, observe infrastructure, or perform recovery.
"""
from __future__ import annotations

import json
from dataclasses import replace

from .approval import ApprovalRequiredError
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
    """Exercise exact binding, redacted evidence and fail-closed paths."""
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

    # Even when the altered bytes receive a fresh, internally valid request,
    # the approval for the old request cannot be replayed. This is an
    # exact-artifact freshness check, not authenticated reviewer evidence.
    changed_artifact = artifact + b"-changed"
    changed_execution = prepare_local_execution_request(handoff, changed_artifact)
    try:
        authorize_local_execution(handoff, changed_artifact, changed_execution, approval)
    except ApprovalRequiredError:
        pass
    else:
        raise RuntimeError("stale execution approval authorized changed artifact")

    # A newly reviewed plan changes the handoff even if the target and
    # artifact bytes stay identical. The old local execution approval must
    # not carry over to a different infrastructure plan.
    changed_plan = derive_requirements(
        ApplicationProfile("synthetic-api", "python", port=8081)
    )
    changed_proposal = render_iac_proposal(changed_plan)
    changed_handoff_request = prepare_deployment_request(
        changed_plan, changed_proposal, "synthetic-target",
    )
    changed_handoff = authorize_deployment_handoff(
        changed_plan, changed_proposal, changed_handoff_request,
        DeploymentApproval(
            changed_handoff_request.digest, "synthetic-handoff-reviewer",
        ),
    )
    changed_plan_execution = prepare_local_execution_request(
        changed_handoff, artifact,
    )
    if changed_plan_execution.digest == execution.digest:
        raise RuntimeError("changed plan did not change execution request")
    try:
        authorize_local_execution(
            changed_handoff, artifact, changed_plan_execution, approval,
        )
    except ApprovalRequiredError:
        pass
    else:
        raise RuntimeError("stale execution approval authorized changed plan")

    # A fresh handoff for another target cannot inherit an earlier local
    # execution approval, even when the plan and artifact bytes are identical.
    retargeted_request = prepare_deployment_request(
        plan, proposal, "synthetic-other-target",
    )
    retargeted_handoff = authorize_deployment_handoff(
        plan, proposal, retargeted_request,
        DeploymentApproval(retargeted_request.digest, "synthetic-handoff-reviewer"),
    )
    retargeted_execution = prepare_local_execution_request(
        retargeted_handoff, artifact,
    )
    if retargeted_execution.digest == execution.digest:
        raise RuntimeError("retargeted handoff did not change execution request")
    try:
        authorize_local_execution(
            retargeted_handoff, artifact, retargeted_execution, approval,
        )
    except ApprovalRequiredError:
        pass
    else:
        raise RuntimeError("stale execution approval authorized changed target")

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

    # A redacted authorization event cannot be promoted to proof of
    # deployment observation or recovery by appending canonical JSON fields.
    for forbidden_claim in ("deployment_observed", "recovery_performed"):
        forged_claim_audit = json.dumps(
            {**json.loads(audit_json), forbidden_claim: True},
            sort_keys=True, indent=2, ensure_ascii=True,
        ) + "\n"
        try:
            verify_local_execution_audit_event(
                handoff, artifact, approval, receipt, forged_claim_audit,
            )
        except ValueError:
            pass
        else:
            raise RuntimeError(f"forged {forbidden_claim} audit claim was accepted")

    # A canonical-shaped audit must not accept substituted request or receipt
    # digests. These digests bind the redacted evidence to exact inputs; they
    # are not authenticated signatures or evidence of infrastructure activity.
    for digest_field in ("request_digest", "receipt_sha256"):
        forged_digest_payload = json.loads(audit_json)
        original_digest = forged_digest_payload[digest_field]
        forged_digest_payload[digest_field] = (
            ("0" if original_digest[0] != "0" else "f") * 64
        )
        forged_digest_audit = json.dumps(
            forged_digest_payload, sort_keys=True, indent=2, ensure_ascii=True,
        ) + "\n"
        try:
            verify_local_execution_audit_event(
                handoff, artifact, approval, receipt, forged_digest_audit,
            )
        except ValueError:
            pass
        else:
            raise RuntimeError(f"forged {digest_field} audit digest was accepted")

    return {
        "demo_only": True,
        "authenticated_review": False,
        "infrastructure_mutated": False,
        "deployment_observed": False,
        "recovery_performed": False,
        "synthetic_rejections": {
            "forged_recovery_status": True,
            "changed_artifact": True,
            "stale_approval_replay": True,
            "stale_plan_approval_replay": True,
            "stale_target_approval_replay": True,
            "forged_receipt_reviewer": True,
            "cross_target_authorization": True,
            "forged_mutation_evidence": True,
            "forged_observation_evidence": True,
            "forged_recovery_evidence": True,
            "forged_request_digest": True,
            "forged_receipt_digest": True,
        },
        "redacted_audit_event": json.loads(audit_json),
    }


if __name__ == "__main__":
    print(json.dumps(run_synthetic_local_authorization_demo(), sort_keys=True, indent=2))
