"""Compose existing local HEAD fixture, HMAC envelope and SQLite replay guard.

This is an opt-in fixture adapter, not an authenticated collector or live monitor.
The caller owns trusted allowlists, key/identity, clock, sequence and ledger.
"""
from __future__ import annotations

import os

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_evidence import (
    ObservationEvidence, ObservationSample, sign_observation_evidence,
    verify_observation_evidence,
)
from .observation_http import (
    LoopbackHTTPProbeTarget, _validate_targets, collect_loopback_http_samples,
)
from .observation_plan import ObservationPlan
from .observation_replay import (
    _preflight_replay_sequence, accept_observation_evidence_durably,
)
from .observation_source_pin import ObservationSourcePin, verify_observation_source_pin
from .observation_source_policy import verify_observation_source_policy


def collect_and_accept_loopback_fixture_evidence(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
    targets: tuple[LoopbackHTTPProbeTarget, ...],
    *,
    allowed_targets: tuple[LoopbackHTTPProbeTarget, ...],
    source_id: str,
    source_key: bytes,
    observed_at_unix: int,
    now_unix: int,
    sequence: int,
    max_age_seconds: int,
    ledger_path: str,
    source_pin: ObservationSourcePin | None = None,
    require_source_pin: bool = False,
    revoked_key_sha256: tuple[str, ...] = (),
) -> ObservationEvidence:
    """Return signed fixture samples only after durable replay acceptance.

    Validate supplied trust context before sending any HEAD request. A temporary
    all-unknown envelope is used solely to reuse the public source/MAC/freshness
    verifier for preflight; it is never exported or persisted. A read-only preflight rejects known duplicates before HEAD; the later SQLite
    transaction remains authoritative against concurrent replay races.
    """
    if (type(ledger_path) is not str or not ledger_path
            or not os.path.isabs(ledger_path) or "\x00" in ledger_path):
        raise ValueError("replay ledger requires an absolute local file path")
    verify_observation_source_policy(
        source_key, source_pin, require_source_pin=require_source_pin,
        revoked_key_sha256=revoked_key_sha256,
    )
    if source_pin is not None:
        verify_observation_source_pin(
            plan, source_pin, source_id=source_id, source_key=source_key,
            observed_at_unix=observed_at_unix, now_unix=now_unix,
        )
    _validate_targets(plan, targets, allowed_targets)
    preflight = sign_observation_evidence(
        plan,
        tuple(ObservationSample(probe.kind, "unknown", 0) for probe in plan.probes),
        source_id, observed_at_unix, sequence, source_key,
    )
    verify_observation_evidence(
        handoff, artifact, approval, receipt, plan, preflight,
        expected_source_id=source_id, source_key=source_key,
        now_unix=now_unix, max_age_seconds=max_age_seconds, last_sequence=0,
    )
    # Reject unsafe ledger aliases before issuing even read-only HEAD requests.
    # Revalidate inside the durable writer because metadata can change meanwhile.
    _preflight_replay_sequence(ledger_path, preflight)
    samples = collect_loopback_http_samples(
        handoff, artifact, approval, receipt, plan, targets,
        allowed_targets=allowed_targets,
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


def collect_and_accept_operator_permitted_loopback_fixture_evidence(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
    targets: tuple[LoopbackHTTPProbeTarget, ...],
    *,
    allowed_targets: tuple[LoopbackHTTPProbeTarget, ...],
    operator_permit: "LoopbackOperatorPermit",
    operator_key: bytes,
    source_id: str,
    source_key: bytes,
    observed_at_unix: int,
    now_unix: int,
    sequence: int,
    max_age_seconds: int,
    ledger_path: str,
    source_pin: ObservationSourcePin | None = None,
    require_source_pin: bool = False,
    revoked_key_sha256: tuple[str, ...] = (),
    require_one_shot_permit: bool = False,
) -> ObservationEvidence:
    """Require a distinct operator-key MAC before fixture HEAD or SQLite I/O.

    This opt-in wrapper does not authenticate a real operator or collector.
    The operator key, trusted allowlist and time must come from outside the
    collector's control. The original fixture entrypoint remains available.
    """
    from .observation_operator_permit import verify_loopback_operator_permit

    _validate_targets(plan, targets, allowed_targets)
    verify_loopback_operator_permit(
        plan, targets, operator_permit, source_id=source_id,
        source_key=source_key, operator_key=operator_key,
        observed_at_unix=observed_at_unix, now_unix=now_unix,
        ledger_path=ledger_path, sequence=sequence,
        require_one_shot=require_one_shot_permit,
    )
    return collect_and_accept_loopback_fixture_evidence(
        handoff, artifact, approval, receipt, plan, targets,
        allowed_targets=allowed_targets, source_id=source_id,
        source_key=source_key, observed_at_unix=observed_at_unix,
        now_unix=now_unix, sequence=sequence,
        max_age_seconds=max_age_seconds, ledger_path=ledger_path,
        source_pin=source_pin, require_source_pin=require_source_pin,
        revoked_key_sha256=revoked_key_sha256,
    )
