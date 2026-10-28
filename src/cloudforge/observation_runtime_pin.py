"""Pure, IPv4-only pinset preflight for proposed HTTPS observation targets.

Caller-provided resolution is not authenticated DNS evidence. This module never
resolves, connects, authorizes a service, or claims runtime health. The future
transport must connect to the validated IP without a second DNS lookup.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
from dataclasses import asdict, dataclass

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_plan import ObservationPlan
from .observation_runtime_request import (
    RuntimeObservationRequest,
    RuntimeObservationTarget,
    verify_runtime_observation_request,
)


@dataclass(frozen=True)
class RuntimeIPv4Pinset:
    format_version: int
    runtime_request_sha256: str
    ordered_ipv4_sets_sha256: str
    status: str = "pending-independent-approval"
    infrastructure_mutated: bool = False
    deployment_observed: bool = False
    recovery_performed: bool = False

    def to_json(self) -> str:
        _validate_pinset(self)
        return json.dumps(asdict(self), sort_keys=True, indent=2,
                          ensure_ascii=True, allow_nan=False) + "\n"


def _validate_pinset(pinset: RuntimeIPv4Pinset) -> None:
    def digest(value: object) -> bool:
        return (type(value) is str and len(value) == 64
                and all(c in "0123456789abcdef" for c in value))

    if (type(pinset) is not RuntimeIPv4Pinset
            or type(pinset.format_version) is not int
            or pinset.format_version != 1
            or not digest(pinset.runtime_request_sha256)
            or not digest(pinset.ordered_ipv4_sets_sha256)
            or pinset.status != "pending-independent-approval"
            or pinset.infrastructure_mutated is not False
            or pinset.deployment_observed is not False
            or pinset.recovery_performed is not False):
        raise ValueError("IPv4 pinset cannot claim authorization or execution")


def _validate_ipv4_sets(
    targets: tuple[RuntimeObservationTarget, ...],
    sets: tuple[tuple[str, ...], ...],
) -> None:
    if type(sets) is not tuple or len(sets) != len(targets):
        raise ValueError("IPv4 pinset must match ordered targets")
    for values in sets:
        if type(values) is not tuple or not 1 <= len(values) <= 4:
            raise ValueError("IPv4 pinset requires 1-4 addresses per target")
        previous = -1
        for value in values:
            if type(value) is not str or not 7 <= len(value) <= 15:
                raise ValueError("invalid IPv4 pin address")
            try:
                ip = ipaddress.IPv4Address(value)
            except ipaddress.AddressValueError as exc:
                raise ValueError("invalid IPv4 pin address") from exc
            if (str(ip) != value or not ip.is_global or ip.is_reserved
                    or ip.is_multicast or ip.is_unspecified or ip.is_loopback
                    or ip.is_link_local or int(ip) <= previous):
                raise ValueError("unsafe, duplicated or unsorted IPv4 pin address")
            previous = int(ip)


def prepare_runtime_ipv4_pinset(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
    targets: tuple[RuntimeObservationTarget, ...],
    request: RuntimeObservationRequest,
    resolved_ipv4: tuple[tuple[str, ...], ...],
    *,
    allowed_ipv4: tuple[tuple[str, ...], ...],
) -> RuntimeIPv4Pinset:
    """Compare caller-supplied IPv4 answers with exact separately supplied pins.

    This does not prove resolver identity, DNS completeness, approval or TLS.
    It MUST NOT be used alone to permit any outbound network operation.
    """
    verify_runtime_observation_request(
        handoff, artifact, approval, receipt, plan, targets, request,
    )
    _validate_ipv4_sets(targets, resolved_ipv4)
    _validate_ipv4_sets(targets, allowed_ipv4)
    if resolved_ipv4 != allowed_ipv4:
        raise ValueError("resolved IPv4 addresses differ from trusted pin policy")
    body = json.dumps(resolved_ipv4, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")
    return RuntimeIPv4Pinset(
        1,
        hashlib.sha256(request.to_json().encode("ascii")).hexdigest(),
        hashlib.sha256(body).hexdigest(),
    )


def verify_runtime_ipv4_pinset(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
    targets: tuple[RuntimeObservationTarget, ...],
    request: RuntimeObservationRequest,
    resolved_ipv4: tuple[tuple[str, ...], ...],
    pinset: RuntimeIPv4Pinset,
    *,
    allowed_ipv4: tuple[tuple[str, ...], ...],
) -> bool:
    """Recompute a digest-only pinset; verification is not network approval."""
    _validate_pinset(pinset)
    expected = prepare_runtime_ipv4_pinset(
        handoff, artifact, approval, receipt, plan, targets, request,
        resolved_ipv4, allowed_ipv4=allowed_ipv4,
    )
    if pinset != expected:
        raise ValueError("IPv4 pinset differs from exact inputs")
    return True
