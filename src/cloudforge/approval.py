from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from .models import InfrastructurePlan


class ApprovalRequiredError(PermissionError):
    """Raised when a consequential operation lacks valid human approval."""


def plan_digest(plan: InfrastructurePlan) -> str:
    """Return a deterministic identity for the exact reviewed plan."""
    payload = json.dumps(
        asdict(plan),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class PlanApproval:
    plan_digest: str
    approved_by: str


def require_plan_approval(
    plan: InfrastructurePlan,
    approval: PlanApproval | None,
) -> None:
    """Fail closed unless a named human approved this exact plan."""
    if not plan.requires_approval:
        return
    if approval is None:
        raise ApprovalRequiredError("explicit approval is required")
    if not approval.approved_by.strip():
        raise ApprovalRequiredError("approval must identify an approver")
    if approval.plan_digest != plan_digest(plan):
        raise ApprovalRequiredError("approval does not match the current plan")
