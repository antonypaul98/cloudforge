"""Pure, provider-neutral MAC verification of externally supplied probe samples.

No probes, clocks, networks, providers or infrastructure actions are invoked.
A verified MAC proves possession of a configured source key, not service health,
deployment, reviewer identity or a trusted collector's physical execution.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import asdict, dataclass, replace

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_plan import ObservationPlan, verify_observation_plan


_SOURCE_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z", re.ASCII)
_OUTCOMES = frozenset({"pass", "fail", "unknown"})
_MAX_SEQUENCE = (1 << 63) - 1


@dataclass(frozen=True)
class ObservationSample:
    kind: str
    outcome: str
    elapsed_ms: int


@dataclass(frozen=True)
class ObservationEvidence:
    format_version: int
    plan_sha256: str
    source_id: str
    observed_at_unix: int
    sequence: int
    samples: tuple[ObservationSample, ...]
    mac_sha256: str

    def to_json(self) -> str:
        """Serialize a bounded evidence envelope, not a service-health claim."""
        _validate_shape(self)
        return json.dumps(asdict(self), sort_keys=True, indent=2,
                          ensure_ascii=True, allow_nan=False) + "\n"


def _hex_digest(value: object) -> bool:
    return (type(value) is str and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _validate_source(source_id: object, source_key: object) -> None:
    if (type(source_id) is not str
            or _SOURCE_RE.fullmatch(source_id) is None):
        raise ValueError("invalid opaque observation source identifier")
    if type(source_key) is not bytes or not 32 <= len(source_key) <= 128:
        raise ValueError("observation source key must be 32-128 exact bytes")


def _validate_shape(evidence: object, plan: ObservationPlan | None = None) -> None:
    if (type(evidence) is not ObservationEvidence
            or type(evidence.format_version) is not int
            or evidence.format_version != 1
            or not _hex_digest(evidence.plan_sha256)
            or not _hex_digest(evidence.mac_sha256)
            or type(evidence.source_id) is not str
            or _SOURCE_RE.fullmatch(evidence.source_id) is None
            or type(evidence.observed_at_unix) is not int
            or not 0 <= evidence.observed_at_unix <= _MAX_SEQUENCE
            or type(evidence.sequence) is not int
            or not 1 <= evidence.sequence <= _MAX_SEQUENCE
            or type(evidence.samples) is not tuple
            or not 2 <= len(evidence.samples) <= 3):
        raise ValueError("malformed observation evidence envelope")
    for sample in evidence.samples:
        if (type(sample) is not ObservationSample
                or type(sample.kind) is not str
                or sample.kind not in {"startup", "readiness", "liveness"}
                or type(sample.outcome) is not str
                or sample.outcome not in _OUTCOMES
                or type(sample.elapsed_ms) is not int
                or not 0 <= sample.elapsed_ms <= 300_000):
            raise ValueError("malformed observation probe sample")
    kinds = tuple(sample.kind for sample in evidence.samples)
    if len(set(kinds)) != len(kinds):
        raise ValueError("duplicate observation probe sample")
    if plan is not None:
        expected = hashlib.sha256(plan.to_json().encode("ascii")).hexdigest()
        if (evidence.plan_sha256 != expected
                or kinds != tuple(probe.kind for probe in plan.probes)):
            raise ValueError("observation samples differ from the exact proposal")


def _body_bytes(evidence: ObservationEvidence) -> bytes:
    body = asdict(evidence)
    del body["mac_sha256"]
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def sign_observation_evidence(
    plan: ObservationPlan,
    samples: tuple[ObservationSample, ...],
    source_id: str,
    observed_at_unix: int,
    sequence: int,
    source_key: bytes,
) -> ObservationEvidence:
    """Sign an in-memory sample fixture using an externally provisioned key.

    Only a trusted, separately authenticated collector should hold the key in
    production. This function itself does not collect or authenticate probes.
    """
    _validate_source(source_id, source_key)
    evidence = ObservationEvidence(
        1, hashlib.sha256(plan.to_json().encode("ascii")).hexdigest(),
        source_id, observed_at_unix, sequence, samples, "0" * 64,
    )
    _validate_shape(evidence, plan)
    mac = hmac.digest(source_key, _body_bytes(evidence), "sha256").hex()
    return replace(evidence, mac_sha256=mac)


def verify_observation_evidence(
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
) -> bool:
    """Verify exact plan, source MAC, bounded age and caller-held replay state.

    A True result is *only* sample-envelope acceptance. The caller must manage
    source-key provenance and atomically persist last_sequence per plan/source.
    The caller's clock is not independently authenticated. No service is probed.
    """
    _validate_source(expected_source_id, source_key)
    if (type(now_unix) is not int or not 0 <= now_unix <= _MAX_SEQUENCE
            or type(max_age_seconds) is not int
            or not 1 <= max_age_seconds <= 300
            or type(last_sequence) is not int
            or not 0 <= last_sequence <= _MAX_SEQUENCE):
        raise ValueError("invalid freshness or replay verification context")
    verify_observation_plan(handoff, artifact, approval, receipt, plan)
    _validate_shape(evidence, plan)
    if evidence.source_id != expected_source_id:
        raise ValueError("observation source differs from configured identity")
    age = now_unix - evidence.observed_at_unix
    if age < 0 or age > max_age_seconds:
        raise ValueError("observation sample is stale or future-dated")
    if evidence.sequence <= last_sequence:
        raise ValueError("observation sample sequence is replayed")
    expected_mac = hmac.digest(source_key, _body_bytes(evidence), "sha256").hex()
    if not hmac.compare_digest(expected_mac, evidence.mac_sha256):
        raise ValueError("observation sample MAC is invalid")
    return True
