"""Bounded local execution authorization. This module never mutates infrastructure."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import asdict, dataclass

from .approval import ApprovalRequiredError
from .deployment import DeploymentHandoff, DeploymentRequest


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be nonblank text without surrounding whitespace")
    if any(unicodedata.category(char) in ("Cc", "Cf", "Cs", "Zl", "Zp") for char in value):
        raise ValueError(f"{name} must not contain control characters")


@dataclass(frozen=True)
class LocalExecutionRequest:
    format_version: int
    handoff_digest: str
    target_id: str
    artifact_sha256: str
    operation: str = "authorize-local-artifact"

    @property
    def digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class LocalExecutionApproval:
    request_digest: str
    approved_by: str


@dataclass(frozen=True)
class LocalExecutionReceipt:
    request: LocalExecutionRequest
    approved_by: str
    request_digest: str
    status: str = "authorized-local-only"
    infrastructure_mutated: bool = False

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def prepare_local_execution_request(
    handoff: DeploymentHandoff, artifact: bytes,
) -> LocalExecutionRequest:
    """Bind an accepted handoff to exact artifact bytes without executing anything."""
    if type(handoff) is not DeploymentHandoff:
        raise ValueError("expected an accepted deployment handoff")
    if type(handoff.request) is not DeploymentRequest:
        raise ValueError("expected a canonical deployment request")
    if (type(handoff.request.format_version) is not int
            or handoff.request.format_version != 1
            or handoff.request.operation != "deployment-handoff"):
        raise ValueError("unsupported deployment handoff format or operation")
    _text(handoff.approved_by, "handoff approved_by")
    if handoff.infrastructure_mutated is not False or handoff.status != "ready-for-adapter-review":
        raise ValueError("handoff is not eligible for local adapter review")
    if handoff.request_digest != handoff.request.digest:
        raise ValueError("handoff digest does not match its exact request")
    _text(handoff.request.target_id, "target_id")
    if type(artifact) is not bytes:
        raise ValueError("artifact must be exact bytes")
    return LocalExecutionRequest(
        1,
        handoff.request_digest,
        handoff.request.target_id,
        hashlib.sha256(artifact).hexdigest(),
    )


def authorize_local_execution(
    handoff: DeploymentHandoff,
    artifact: bytes,
    request: LocalExecutionRequest,
    approval: LocalExecutionApproval | None,
) -> LocalExecutionReceipt:
    """Authorize exact local bytes; deliberately performs no runtime mutation."""
    if type(request) is not LocalExecutionRequest:
        raise ValueError("expected a local execution request")
    expected = prepare_local_execution_request(handoff, artifact)
    if type(request.format_version) is not int or request != expected:
        raise ValueError("request differs from exact local execution inputs")
    if type(approval) is not LocalExecutionApproval:
        raise ApprovalRequiredError("fresh local execution approval is required")
    try:
        _text(approval.approved_by, "approved_by")
    except ValueError as exc:
        raise ApprovalRequiredError(str(exc)) from exc
    if approval.request_digest != expected.digest:
        raise ApprovalRequiredError("approval does not match the exact local execution request")
    return LocalExecutionReceipt(expected, approval.approved_by, expected.digest)
