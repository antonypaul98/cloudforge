"""Read-only recovery review proposal from verified synthetic observation windows.

This is not a remediation executor, trusted alert, health proof or approval.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_evidence import ObservationEvidence
from .observation_plan import ObservationPlan
from .observation_source_pin import ObservationSourcePin
from .observation_thresholds import evaluate_verified_observation_thresholds


_KINDS = frozenset({"startup", "readiness", "liveness"})
_STATUSES = frozenset({
    "manual-review-recommended", "insufficient-evidence", "no-trigger-in-window",
})
_MAX_SEQUENCE = (1 << 63) - 1


def _digest_shape(value: object) -> bool:
    return (type(value) is str and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _kinds_shape(value: object) -> bool:
    return (type(value) is tuple and len(value) <= 3
            and all(type(kind) is str and kind in _KINDS for kind in value)
            and len(set(value)) == len(value))


@dataclass(frozen=True)
class RecoveryReviewProposal:
    format_version: int
    plan_sha256: str
    evidence_window_sha256: str
    last_sequence: int
    status: str
    threshold_kinds: tuple[str, ...]
    unknown_kinds: tuple[str, ...]
    action: str = "none"
    infrastructure_mutated: bool = False
    recovery_performed: bool = False
    deployment_observed: bool = False

    def to_json(self) -> str:
        """Canonical review-only export, never an executable recovery command."""
        if (type(self.format_version) is not int or self.format_version != 1
                or not _digest_shape(self.plan_sha256)
                or not _digest_shape(self.evidence_window_sha256)
                or type(self.last_sequence) is not int
                or not 1 <= self.last_sequence <= _MAX_SEQUENCE
                or type(self.status) is not str or self.status not in _STATUSES
                or not _kinds_shape(self.threshold_kinds)
                or not _kinds_shape(self.unknown_kinds)
                or set(self.threshold_kinds) & set(self.unknown_kinds)
                or type(self.action) is not str
                or self.action != (
                    "manual-investigation-only" if self.threshold_kinds else "none"
                )
                or self.status != (
                    "manual-review-recommended" if self.threshold_kinds
                    else "insufficient-evidence" if self.unknown_kinds
                    else "no-trigger-in-window"
                )
                or self.infrastructure_mutated is not False
                or self.recovery_performed is not False
                or self.deployment_observed is not False):
            raise ValueError("invalid non-executing recovery review proposal")
        return json.dumps(asdict(self), sort_keys=True, indent=2,
                          ensure_ascii=True, allow_nan=False) + "\n"


def propose_recovery_review(
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
) -> RecoveryReviewProposal:
    """Review-only summary of a bounded, fully reverified evidence window.

    Unknown is never treated as pass. Thresholds recommend investigation,
    not automatic restart, rollback, notification, provider access or recovery.
    Caller-controlled signed samples do not prove real-world service health.
    """
    results = evaluate_verified_observation_thresholds(
        handoff, artifact, approval, receipt, plan, evidence_window,
        expected_source_id=expected_source_id, source_key=source_key,
        now_unix=now_unix, max_age_seconds=max_age_seconds,
        last_sequence=last_sequence, source_pin=source_pin,
        require_source_pin=require_source_pin,
        revoked_key_sha256=revoked_key_sha256,
    )
    # Canonical array framing avoids ambiguous concatenation of envelopes.
    # The underlying evidence verifier above has already validated every item.
    canonical_window = json.dumps(
        [json.loads(evidence.to_json()) for evidence in evidence_window],
        sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
    ).encode("ascii")
    threshold_kinds = tuple(item.kind for item in results if item.threshold_reached)
    unknown_kinds = tuple(item.kind for item in results if item.latest_outcome == "unknown")
    status = (
        "manual-review-recommended" if threshold_kinds
        else "insufficient-evidence" if unknown_kinds
        else "no-trigger-in-window"
    )
    proposal = RecoveryReviewProposal(
        1, hashlib.sha256(plan.to_json().encode("ascii")).hexdigest(),
        hashlib.sha256(canonical_window).hexdigest(),
        evidence_window[-1].sequence, status, threshold_kinds, unknown_kinds,
        "manual-investigation-only" if threshold_kinds else "none",
    )
    proposal.to_json()
    return proposal
