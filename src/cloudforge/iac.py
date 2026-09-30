from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .approval import plan_digest
from .models import InfrastructurePlan, ResourceRequirement


_ALLOWED_KINDS = frozenset({"compute", "network", "database", "cache"})


@dataclass(frozen=True)
class IaCProposal:
    format_version: int
    plan_digest: str
    document: str


def _validate_reviewable_plan(plan: InfrastructurePlan) -> None:
    if not plan.application.strip():
        raise ValueError("application identity is required")
    if not plan.requires_approval:
        raise ValueError("IaC proposals require explicit approval")
    for resource in plan.resources:
        if not isinstance(resource, ResourceRequirement):
            raise ValueError("resources must be provider-neutral requirements")
        if resource.kind not in _ALLOWED_KINDS:
            raise ValueError(f"unsupported resource kind: {resource.kind}")


def render_iac_proposal(plan: InfrastructurePlan) -> IaCProposal:
    """Render a deterministic, review-only provider-neutral IaC proposal.

    This function deliberately does not apply, deploy, or mutate infrastructure.
    The embedded digest binds the proposal to the exact reviewed plan.
    """
    _validate_reviewable_plan(plan)
    payload = {
        "application": plan.application,
        "requires_approval": plan.requires_approval,
        "resources": [asdict(resource) for resource in plan.resources],
    }
    document = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    return IaCProposal(format_version=1, plan_digest=plan_digest(plan), document=document)
