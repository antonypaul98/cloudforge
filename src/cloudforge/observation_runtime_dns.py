"""Pure A/AAAA pinset preflight for proposed HTTPS observations.

Both answer families and both allowlists are supplied by the caller; this
module never performs DNS, socket I/O, approval or live observation.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
from dataclasses import asdict, dataclass

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_plan import ObservationPlan
from .observation_runtime_pin import _validate_ipv4_sets
from .observation_runtime_request import (
    RuntimeObservationRequest,
    RuntimeObservationTarget,
    verify_runtime_observation_request,
)


@dataclass(frozen=True)
class RuntimeDNSPinset:
    format_version: int
    runtime_request_sha256: str
    ordered_address_sets_sha256: str
    status: str = "pending-independent-approval"
    infrastructure_mutated: bool = False
    deployment_observed: bool = False
    recovery_performed: bool = False

    def to_json(self) -> str:
        _validate_pinset(self)
        return json.dumps(asdict(self), sort_keys=True, indent=2,
                          ensure_ascii=True, allow_nan=False) + "\n"


def _validate_pinset(pinset: RuntimeDNSPinset) -> None:
    def digest(value: object) -> bool:
        return (type(value) is str and len(value) == 64
                and all(c in "0123456789abcdef" for c in value))

    if (type(pinset) is not RuntimeDNSPinset
            or type(pinset.format_version) is not int
            or pinset.format_version != 1
            or not digest(pinset.runtime_request_sha256)
            or not digest(pinset.ordered_address_sets_sha256)
            or pinset.status != "pending-independent-approval"
            or pinset.infrastructure_mutated is not False
            or pinset.deployment_observed is not False
            or pinset.recovery_performed is not False):
        raise ValueError("DNS pinset cannot claim authorization or execution")


def _validate_address_sets(
    targets: tuple[RuntimeObservationTarget, ...],
    ipv4_sets: tuple[tuple[str, ...], ...],
    ipv6_sets: tuple[tuple[str, ...], ...],
) -> None:
    if (type(ipv4_sets) is not tuple or type(ipv6_sets) is not tuple
            or len(ipv4_sets) != len(targets)
            or len(ipv6_sets) != len(targets)):
        raise ValueError("A/AAAA answer sets must match ordered targets")
    for target, a, aaaa in zip(targets, ipv4_sets, ipv6_sets):
        if (type(a) is not tuple or type(aaaa) is not tuple
                or len(a) > 4 or len(aaaa) > 4
                or not (a or aaaa)):
            raise ValueError("each target requires 1-4 total A/AAAA addresses per family")
        if a:
            _validate_ipv4_sets((target,), (a,))
        previous = -1
        for value in aaaa:
            if type(value) is not str or not 2 <= len(value) <= 39:
                raise ValueError("invalid IPv6 pin address")
            try:
                ip = ipaddress.IPv6Address(value)
            except ipaddress.AddressValueError as exc:
                raise ValueError("invalid IPv6 pin address") from exc
            if (str(ip) != value or ip.scope_id is not None
                    or not ip.is_global or ip.is_reserved or ip.is_multicast
                    or ip.is_unspecified or ip.is_loopback or ip.is_link_local
                    or ip.is_site_local or ip.ipv4_mapped is not None
                    or ip.sixtofour is not None or ip.teredo is not None
                    or ip in ipaddress.IPv6Network("64:ff9b::/96")
                    or ip in ipaddress.IPv6Network("64:ff9b:1::/48")
                    or int(ip) <= previous):
                raise ValueError("unsafe, duplicated or unsorted IPv6 pin address")
            previous = int(ip)


def prepare_runtime_dns_pinset(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
    targets: tuple[RuntimeObservationTarget, ...],
    request: RuntimeObservationRequest,
    resolved_ipv4: tuple[tuple[str, ...], ...],
    resolved_ipv6: tuple[tuple[str, ...], ...],
    *,
    allowed_ipv4: tuple[tuple[str, ...], ...],
    allowed_ipv6: tuple[tuple[str, ...], ...],
) -> RuntimeDNSPinset:
    """Compare exact caller-supplied A and AAAA sets; never permit network I/O."""
    verify_runtime_observation_request(
        handoff, artifact, approval, receipt, plan, targets, request,
    )
    _validate_address_sets(targets, resolved_ipv4, resolved_ipv6)
    _validate_address_sets(targets, allowed_ipv4, allowed_ipv6)
    if resolved_ipv4 != allowed_ipv4 or resolved_ipv6 != allowed_ipv6:
        raise ValueError("resolved A/AAAA addresses differ from trusted pin policy")
    body = json.dumps({"A": resolved_ipv4, "AAAA": resolved_ipv6},
                      sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")
    return RuntimeDNSPinset(
        1,
        hashlib.sha256(request.to_json().encode("ascii")).hexdigest(),
        hashlib.sha256(body).hexdigest(),
    )


def verify_runtime_dns_pinset(
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
) -> bool:
    """Recompute digest-only evidence; verification grants no approval."""
    _validate_pinset(pinset)
    expected = prepare_runtime_dns_pinset(
        handoff, artifact, approval, receipt, plan, targets, request,
        resolved_ipv4, resolved_ipv6,
        allowed_ipv4=allowed_ipv4, allowed_ipv6=allowed_ipv6,
    )
    if pinset != expected:
        raise ValueError("DNS pinset differs from exact inputs")
    return True
