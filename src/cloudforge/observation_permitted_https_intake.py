"""Synthetic pinned HTTPS HEAD -> signed evidence -> durable intake.

This opt-in composition is fixture-only. Caller-provided keys, clock, DNS,
allowlists, connection factory and SQLite path are not a trusted collector.
No real endpoint or infrastructure action is authorized.
"""
from __future__ import annotations

from typing import Callable

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_evidence import (
    ObservationEvidence, ObservationSample, sign_observation_evidence,
    verify_observation_evidence,
)
from .observation_permitted_https_fixture import (
    collect_permitted_pinned_https_fixture_samples,
)
from .observation_plan import ObservationPlan
from .observation_replay import (
    _preflight_replay_sequence, accept_observation_evidence_durably,
)
from .observation_runtime_dns import RuntimeDNSPinset
from .observation_runtime_permit import RuntimeHEADPermit, verify_runtime_head_permit
from .observation_runtime_request import RuntimeObservationRequest, RuntimeObservationTarget
from .observation_source_pin import ObservationSourcePin, verify_observation_source_pin
from .observation_source_policy import verify_observation_source_policy


def collect_and_accept_permitted_pinned_https_fixture_evidence(
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
    observed_at_unix: int,
    now_unix: int,
    max_age_seconds: int,
    ledger_path: str,
    connection_factory: Callable,
    source_pin: ObservationSourcePin | None = None,
    require_source_pin: bool = False,
    revoked_key_sha256: tuple[str, ...] = (),
) -> ObservationEvidence:
    """Accept signed synthetic samples only after two SQLite replay checks.

    One ledger file holds the independent permit-consumption and evidence
    counters. A failed fixture still burns its permit. The permit is consumed
    before any injected HEAD connection; evidence is committed afterward.
    Neither operation authenticates the caller or makes the factory safe.
    """
    # Verify the exact permit and remaining caller-clock budget before any
    # filesystem access. The delegated fixture repeats both checks immediately
    # before consuming the permit and invoking the fake connection factory.
    verify_runtime_head_permit(
        handoff, artifact, approval, receipt, plan, targets, request,
        resolved_ipv4, resolved_ipv6, pinset, permit,
        allowed_ipv4=allowed_ipv4, allowed_ipv6=allowed_ipv6,
        source_id=source_id, source_key=source_key,
        operator_key=operator_key, sequence=sequence, now_unix=now_unix,
    )
    if sum(p.timeout_seconds for p in plan.probes) > permit.valid_until_unix - now_unix:
        raise ValueError("runtime HEAD permit expires before synthetic probe budget")

    # Reuse the existing optional source-key pin/revocation policy before any
    # ledger access or injected HEAD factory. These caller-provided settings
    # do not establish independent collector identity or trusted key custody.
    verify_observation_source_policy(
        source_key, source_pin, require_source_pin=require_source_pin,
        revoked_key_sha256=revoked_key_sha256,
    )
    if source_pin is not None:
        verify_observation_source_pin(
            plan, source_pin, source_id=source_id, source_key=source_key,
            observed_at_unix=observed_at_unix, now_unix=now_unix,
        )

    # Validate evidence freshness/MAC context and reject known evidence replay
    # before any fake HEAD. The final SQLite transaction is authoritative for
    # races; the preflight is deliberately not claimed to be an atomic lock.
    preflight = sign_observation_evidence(
        plan,
        tuple(ObservationSample(p.kind, "unknown", 0) for p in plan.probes),
        source_id, observed_at_unix, sequence, source_key,
    )
    verify_observation_evidence(
        handoff, artifact, approval, receipt, plan, preflight,
        expected_source_id=source_id, source_key=source_key,
        now_unix=now_unix, max_age_seconds=max_age_seconds,
        last_sequence=0,
    )
    _preflight_replay_sequence(ledger_path, preflight)

    samples = collect_permitted_pinned_https_fixture_samples(
        handoff, artifact, approval, receipt, plan, targets, request,
        resolved_ipv4, resolved_ipv6, pinset, permit,
        allowed_ipv4=allowed_ipv4, allowed_ipv6=allowed_ipv6,
        source_id=source_id, source_key=source_key,
        operator_key=operator_key, sequence=sequence, now_unix=now_unix,
        connection_factory=connection_factory,
        permit_ledger_path=ledger_path,
    )
    evidence = sign_observation_evidence(
        plan, samples, source_id, observed_at_unix, sequence, source_key,
    )
    accept_observation_evidence_durably(
        handoff, artifact, approval, receipt, plan, evidence,
        expected_source_id=source_id, source_key=source_key,
        now_unix=now_unix, max_age_seconds=max_age_seconds,
        ledger_path=ledger_path,
    )
    return evidence
