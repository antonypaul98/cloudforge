"""Pure, short-lived operator-key permit for a proposed HTTPS HEAD pinset.

This binds caller-supplied policy, not an authenticated human or a trusted
collector. It never opens a socket, resolves DNS, or grants execution by itself.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass, replace

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_evidence import _validate_source
from .observation_plan import ObservationPlan
from .observation_runtime_dns import RuntimeDNSPinset, verify_runtime_dns_pinset
from .observation_runtime_request import RuntimeObservationRequest, RuntimeObservationTarget

_MAX_UNIX = (1 << 63) - 1


@dataclass(frozen=True)
class RuntimeHEADPermit:
    format_version: int
    runtime_request_sha256: str
    pinset_sha256: str
    source_id: str
    source_key_sha256: str
    sequence: int
    valid_from_unix: int
    valid_until_unix: int
    mac_sha256: str


def _digest(value: object) -> bool:
    return (type(value) is str and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _keys(source_id: str, source_key: bytes, operator_key: bytes) -> None:
    _validate_source(source_id, source_key)
    if (type(operator_key) is not bytes or not 32 <= len(operator_key) <= 128
            or hmac.compare_digest(source_key, operator_key)):
        raise ValueError("runtime permit requires a distinct operator key")


def _shape(permit: RuntimeHEADPermit) -> None:
    if (type(permit) is not RuntimeHEADPermit
            or type(permit.format_version) is not int or permit.format_version != 1
            or not all(_digest(value) for value in (
                permit.runtime_request_sha256, permit.pinset_sha256,
                permit.source_key_sha256, permit.mac_sha256,
            ))
            or type(permit.source_id) is not str
            or type(permit.sequence) is not int
            or not 1 <= permit.sequence <= _MAX_UNIX
            or type(permit.valid_from_unix) is not int
            or type(permit.valid_until_unix) is not int
            or not 0 <= permit.valid_from_unix < permit.valid_until_unix <= _MAX_UNIX
            or permit.valid_until_unix - permit.valid_from_unix > 300):
        raise ValueError("invalid runtime HEAD permit")


def _mac_bytes(permit: RuntimeHEADPermit) -> bytes:
    body = asdict(permit)
    del body["mac_sha256"]
    body["operation"] = "proposed-pinned-https-head-only-v1"
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _preflight(handoff, artifact, approval, receipt, plan, targets, request,
               resolved_ipv4, resolved_ipv6, pinset, allowed_ipv4, allowed_ipv6):
    verify_runtime_dns_pinset(
        handoff, artifact, approval, receipt, plan, targets, request,
        resolved_ipv4, resolved_ipv6, pinset,
        allowed_ipv4=allowed_ipv4, allowed_ipv6=allowed_ipv6,
    )


def issue_runtime_head_permit(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
    targets: tuple[RuntimeObservationTarget, ...],
    request: RuntimeObservationRequest,
    resolved_ipv4: tuple[tuple[str, ...], ...],
    resolved_ipv6: tuple[tuple[str, ...], ...],
    pinset: RuntimeDNSPinset,
    *,
    allowed_ipv4: tuple[tuple[str, ...], ...],
    allowed_ipv6: tuple[tuple[str, ...], ...],
    source_id: str,
    source_key: bytes,
    operator_key: bytes,
    sequence: int,
    valid_from_unix: int,
    valid_until_unix: int,
) -> RuntimeHEADPermit:
    """MAC-bind exact proposal/pinset to a caller-held operator policy key."""
    _keys(source_id, source_key, operator_key)
    _preflight(handoff, artifact, approval, receipt, plan, targets, request,
               resolved_ipv4, resolved_ipv6, pinset, allowed_ipv4, allowed_ipv6)
    permit = RuntimeHEADPermit(
        1,
        hashlib.sha256(request.to_json().encode("ascii")).hexdigest(),
        hashlib.sha256(pinset.to_json().encode("ascii")).hexdigest(),
        source_id, hashlib.sha256(source_key).hexdigest(),
        sequence, valid_from_unix, valid_until_unix, "0" * 64,
    )
    _shape(permit)
    return replace(permit, mac_sha256=hmac.digest(
        operator_key, _mac_bytes(permit), "sha256",
    ).hex())


def verify_runtime_head_permit(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
    targets: tuple[RuntimeObservationTarget, ...],
    request: RuntimeObservationRequest,
    resolved_ipv4: tuple[tuple[str, ...], ...],
    resolved_ipv6: tuple[tuple[str, ...], ...],
    pinset: RuntimeDNSPinset,
    permit: RuntimeHEADPermit,
    *,
    allowed_ipv4: tuple[tuple[str, ...], ...],
    allowed_ipv6: tuple[tuple[str, ...], ...],
    source_id: str,
    source_key: bytes,
    operator_key: bytes,
    sequence: int,
    now_unix: int,
) -> bool:
    """Verify exact proposal and caller policy without network or key custody.

    A successful MAC only proves possession of operator_key. Caller must
    authenticate operator/collector, secure keys and clock, atomically enforce
    the sequence and independently approve the endpoint before live use.
    """
    _keys(source_id, source_key, operator_key)
    _preflight(handoff, artifact, approval, receipt, plan, targets, request,
               resolved_ipv4, resolved_ipv6, pinset, allowed_ipv4, allowed_ipv6)
    _shape(permit)
    if (type(sequence) is not int or type(now_unix) is not int
            or not 1 <= sequence <= _MAX_UNIX
            or not 0 <= now_unix <= _MAX_UNIX
            or not permit.valid_from_unix <= now_unix <= permit.valid_until_unix
            or permit.sequence != sequence
            or permit.source_id != source_id
            or not hmac.compare_digest(
                permit.runtime_request_sha256,
                hashlib.sha256(request.to_json().encode("ascii")).hexdigest(),
            )
            or not hmac.compare_digest(
                permit.pinset_sha256,
                hashlib.sha256(pinset.to_json().encode("ascii")).hexdigest(),
            )
            or not hmac.compare_digest(
                permit.source_key_sha256, hashlib.sha256(source_key).hexdigest(),
            )
            or not hmac.compare_digest(
                permit.mac_sha256,
                hmac.digest(operator_key, _mac_bytes(permit), "sha256").hex(),
            )):
        raise ValueError("runtime HEAD permit expired or differs from exact policy")
    return True
