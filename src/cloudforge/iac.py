from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .approval import plan_digest
from .models import InfrastructurePlan, ResourceRequirement


_KIND_ORDER = ("compute", "network", "database", "cache")
_PROPERTY = {"compute": "runtime", "network": "port", "database": "engine", "cache": "engine"}


@dataclass(frozen=True)
class IaCProposal:
    format_version: int
    plan_digest: str
    document: str


def _validate_reviewable_plan(plan: InfrastructurePlan) -> None:
    if not isinstance(plan, InfrastructurePlan):
        raise ValueError("expected an infrastructure plan")
    if not isinstance(plan.application, str) or not plan.application.strip():
        raise ValueError("application identity is required")
    if plan.requires_approval is not True:
        raise ValueError("IaC proposals require explicit approval")
    if not isinstance(plan.resources, tuple) or not 1 <= len(plan.resources) <= 4:
        raise ValueError("resources must contain one to four unambiguous requirements")
    seen = set()
    for resource in plan.resources:
        if not isinstance(resource, ResourceRequirement):
            raise ValueError("resources must be provider-neutral requirements")
        if not isinstance(resource.kind, str) or resource.kind not in _KIND_ORDER:
            raise ValueError(f"unsupported resource kind: {resource.kind}")
        if resource.kind in seen:
            raise ValueError("duplicate resource kind is ambiguous or conflicting")
        seen.add(resource.kind)
        if not isinstance(resource.reason, str) or not resource.reason.strip():
            raise ValueError("requirement provenance reason is required")
        key = _PROPERTY[resource.kind]
        props = resource.properties
        if not isinstance(props, dict) or key not in props or set(props) - {key, "source"}:
            raise ValueError("unsupported or missing provider-neutral properties")
        if "source" in props and (not isinstance(props["source"], str) or not props["source"].strip()):
            raise ValueError("source provenance must be nonblank text")
        value = props[key]
        if resource.kind == "network":
            if type(value) is not int or not 1 <= value <= 65535:
                raise ValueError("port must be an integer from 1 to 65535")
        elif not isinstance(value, str) or not value.strip():
            raise ValueError("runtime/engine must be nonblank text")
        elif resource.kind in {"database", "cache"}:
            expected = "postgresql" if resource.kind == "database" else "redis"
            if value != expected:
                raise ValueError("unsupported provider-neutral engine")


def render_iac_proposal(plan: InfrastructurePlan) -> IaCProposal:
    """Render a deterministic, review-only provider-neutral IaC proposal.

    This function deliberately does not apply, deploy, or mutate infrastructure.
    The embedded digest binds the proposal to the exact reviewed plan.
    """
    _validate_reviewable_plan(plan)
    payload = {
        "application": plan.application,
        "requires_approval": plan.requires_approval,
        "resources": [asdict(resource) for resource in sorted(
            plan.resources, key=lambda resource: _KIND_ORDER.index(resource.kind)
        )],
    }
    document = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    return IaCProposal(format_version=1, plan_digest=plan_digest(plan), document=document)
