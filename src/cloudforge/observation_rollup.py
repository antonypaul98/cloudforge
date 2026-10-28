"""Deterministic rollup of verified observation *samples*, not service health.

This is a pure read-only interpretation of caller-supplied evidence. HMAC
verification proves key possession, not an authenticated collector or live probe.
"""
from __future__ import annotations

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_evidence import ObservationEvidence, verify_observation_evidence
from .observation_plan import ObservationPlan
from .observation_source_pin import ObservationSourcePin, verify_observation_source_pin
from .observation_source_policy import verify_observation_source_policy


def classify_verified_observation_samples(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
    evidence: ObservationEvidence,
    *,
    expected_source_id: str,
    source_key: bytes,
    now_unix: int,
    max_age_seconds: int,
    last_sequence: int,
    source_pin: ObservationSourcePin | None = None,
    require_source_pin: bool = False,
    revoked_key_sha256: tuple[str, ...] = (),
) -> str:
    """Return fail, unknown or pass only after exact evidence verification.

    A known failed probe dominates an unknown probe; unknown dominates pass.
    This result is not a deployment, readiness, health or recovery attestation.
    The caller still owns trusted collector identity, time and durable replay.
    """
    verify_observation_evidence(
        handoff, artifact, approval, receipt, plan, evidence,
        expected_source_id=expected_source_id, source_key=source_key,
        now_unix=now_unix, max_age_seconds=max_age_seconds,
        last_sequence=last_sequence,
    )
    # A verified MAC alone does not establish that this key is still trusted.
    # Reuse the fixture's opt-in caller-managed policy before classification.
    verify_observation_source_policy(
        source_key, source_pin, require_source_pin=require_source_pin,
        revoked_key_sha256=revoked_key_sha256,
    )
    if source_pin is not None:
        verify_observation_source_pin(
            plan, source_pin, source_id=expected_source_id, source_key=source_key,
            observed_at_unix=evidence.observed_at_unix, now_unix=now_unix,
        )
    outcomes = {sample.outcome for sample in evidence.samples}
    if "fail" in outcomes:
        return "fail"
    if "unknown" in outcomes:
        return "unknown"
    return "pass"
