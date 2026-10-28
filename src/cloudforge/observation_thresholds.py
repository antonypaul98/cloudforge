"""Bounded failure streaks from a contiguous window of verified sample envelopes.

This is a pure interpretation of caller-supplied signed evidence, not an
authenticated runtime collector, service-health assertion, alert or recovery.
"""
from __future__ import annotations

from dataclasses import dataclass

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_evidence import ObservationEvidence
from .observation_plan import ObservationPlan
from .observation_rollup import classify_verified_observation_samples
from .observation_source_pin import ObservationSourcePin


@dataclass(frozen=True)
class ObservationFailureThreshold:
    kind: str
    consecutive_failures: int
    failure_threshold: int
    threshold_reached: bool
    latest_outcome: str


def evaluate_verified_observation_thresholds(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
    evidence_window: tuple[ObservationEvidence, ...],
    *,
    expected_source_id: str,
    source_key: bytes,
    now_unix: int,
    max_age_seconds: int,
    last_sequence: int,
    source_pin: ObservationSourcePin | None = None,
    require_source_pin: bool = False,
    revoked_key_sha256: tuple[str, ...] = (),
) -> tuple[ObservationFailureThreshold, ...]:
    """Evaluate only consecutive explicit failures in 1-10 verified envelopes.

    Every envelope is independently verified against the same exact plan,
    artifact, source, key, freshness and optional trust policy. Subsequent
    sequences must be contiguous; timestamps cannot move backward. An unknown
    sample breaks an explicit-failure streak rather than counting as a failure.
    Results cover only this window; no historical, scheduled or runtime state
    is inferred, and no evidence is persisted.
    """
    if type(evidence_window) is not tuple or not 1 <= len(evidence_window) <= 10:
        raise ValueError("observation window must contain 1-10 envelopes")
    streaks: dict[str, int] = {}
    latest: dict[str, str] = {}
    previous_sequence = last_sequence
    previous_time: int | None = None
    for index, evidence in enumerate(evidence_window):
        # Reuse the existing complete verifier, including source-key policy.
        # It rejects malformed envelopes before any sample is interpreted.
        classify_verified_observation_samples(
            handoff, artifact, approval, receipt, plan, evidence,
            expected_source_id=expected_source_id,
            source_key=source_key,
            now_unix=now_unix,
            max_age_seconds=max_age_seconds,
            last_sequence=previous_sequence,
            source_pin=source_pin,
            require_source_pin=require_source_pin,
            revoked_key_sha256=revoked_key_sha256,
        )
        if (index > 0 and evidence.sequence != previous_sequence + 1):
            raise ValueError("observation window has a sequence gap")
        if (previous_time is not None
                and evidence.observed_at_unix < previous_time):
            raise ValueError("observation window clock moved backward")
        for sample in evidence.samples:
            streaks[sample.kind] = (
                streaks.get(sample.kind, 0) + 1 if sample.outcome == "fail" else 0
            )
            latest[sample.kind] = sample.outcome
        previous_sequence = evidence.sequence
        previous_time = evidence.observed_at_unix
    return tuple(
        ObservationFailureThreshold(
            probe.kind, streaks[probe.kind], probe.failure_threshold,
            streaks[probe.kind] >= probe.failure_threshold, latest[probe.kind],
        )
        for probe in plan.probes
    )
