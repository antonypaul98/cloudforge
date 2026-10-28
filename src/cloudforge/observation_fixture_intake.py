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
from .observation_replay import accept_observation_evidence_durably
from .observation_source_pin import ObservationSourcePin, verify_observation_source_pin


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
) -> ObservationEvidence:
    """Return signed fixture samples only after durable replay acceptance.

    Validate supplied trust context before sending any HEAD request. A temporary
    all-unknown envelope is used solely to reuse the public source/MAC/freshness
    verifier for preflight; it is never exported or persisted. A duplicate
    sequence can still trigger HEAD requests before SQLite rejects its replay.
    """
    if (type(ledger_path) is not str or not ledger_path
            or not os.path.isabs(ledger_path) or "\x00" in ledger_path):
        raise ValueError("replay ledger requires an absolute local file path")
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
