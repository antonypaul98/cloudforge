"""Review-only deployment handoff. No provider adapter or mutation capability."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from .approval import ApprovalRequiredError
from .iac import IaCProposal, render_iac_proposal
from .models import InfrastructurePlan


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be nonblank text without surrounding whitespace")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{name} must not contain control characters")


@dataclass(frozen=True)
class DeploymentRequest:
    """Immutable snapshot of the exact reviewed proposal and target identity."""

    format_version: int
    plan_digest: str
    document: str
    target_id: str
    operation: str = "deployment-handoff"

    @property
    def digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class DeploymentApproval:
    request_digest: str
    approved_by: str


@dataclass(frozen=True)
class DeploymentHandoff:
    request: DeploymentRequest
    approved_by: str
    request_digest: str
    status: str = "ready-for-adapter-review"
    infrastructure_mutated: bool = False

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def prepare_deployment_request(
    plan: InfrastructurePlan, proposal: IaCProposal, target_id: str,
) -> DeploymentRequest:
    """Validate canonical IaC against its source plan before requesting approval."""
    _text(target_id, "target_id")
    expected = render_iac_proposal(plan)
    if (type(proposal) is not IaCProposal or type(proposal.format_version) is not int
            or proposal != expected):
        raise ValueError("proposal must exactly match the validated plan and supported format")
    return DeploymentRequest(1, expected.plan_digest, expected.document, target_id)


def authorize_deployment_handoff(
    plan: InfrastructurePlan, proposal: IaCProposal, request: DeploymentRequest,
    approval: DeploymentApproval | None,
) -> DeploymentHandoff:
    """Bind review approval to exact plan, bytes, target and operation.

    Caller must authenticate the human approver before constructing approval.
    This is an in-process integrity boundary, not an identity/signature service.
    The receipt does not grant cloud permission or prove a deployment succeeded.
    Every future adapter must enforce its own explicit execution authorization.
    """
    if type(request) is not DeploymentRequest:
        raise ValueError("expected a deployment request")
    expected = prepare_deployment_request(plan, proposal, request.target_id)
    if type(request.format_version) is not int or request != expected:
        raise ValueError("request differs from validated deployment handoff")
    if type(approval) is not DeploymentApproval:
        raise ApprovalRequiredError("explicit deployment handoff approval is required")
    try:
        _text(approval.approved_by, "approved_by")
    except ValueError as exc:
        raise ApprovalRequiredError(str(exc)) from exc
    if approval.request_digest != expected.digest:
        raise ApprovalRequiredError("approval does not match the exact deployment request")
    return DeploymentHandoff(expected, approval.approved_by, expected.digest)
