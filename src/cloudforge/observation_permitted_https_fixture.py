"""Synthetic-only permit gate for the injected pinned HTTPS HEAD fixture.

This is not an authenticated collector or a network authorization boundary.
Caller-provided keys, clock, endpoint policy and connection factory are untrusted.
"""
from __future__ import annotations

from typing import Callable

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_evidence import ObservationSample
from .observation_https_fixture import collect_pinned_https_fixture_samples
from .observation_plan import ObservationPlan
from .observation_runtime_dns import RuntimeDNSPinset
from .observation_runtime_permit import RuntimeHEADPermit, verify_runtime_head_permit
from .observation_runtime_request import RuntimeObservationRequest, RuntimeObservationTarget


def collect_permitted_pinned_https_fixture_samples(
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
    connection_factory: Callable,
) -> tuple[ObservationSample, ...]:
    """Reject a mismatched caller-held permit before invoking any fake connection.

    This opt-in test seam deliberately has no network-capable default.
    A valid MAC is not independently authenticated human approval; the
    injected factory is not isolated from network access by this function.
    """
    verify_runtime_head_permit(
        handoff, artifact, approval, receipt, plan, targets, request,
        resolved_ipv4, resolved_ipv6, pinset, permit,
        allowed_ipv4=allowed_ipv4, allowed_ipv6=allowed_ipv6,
        source_id=source_id, source_key=source_key, operator_key=operator_key,
        sequence=sequence, now_unix=now_unix,
    )
    # A permit valid only at preflight time must not start a sequence whose
    # configured maximum probe durations extend past its expiry. This is a
    # conservative caller-clock budget, not a hard runtime cancellation.
    if sum(probe.timeout_seconds for probe in plan.probes) > permit.valid_until_unix - now_unix:
        raise ValueError("runtime HEAD permit expires before synthetic probe budget")
    return collect_pinned_https_fixture_samples(
        handoff, artifact, approval, receipt, plan, targets, request,
        resolved_ipv4, resolved_ipv6, pinset,
        allowed_ipv4=allowed_ipv4, allowed_ipv6=allowed_ipv6,
        connection_factory=connection_factory,
    )
