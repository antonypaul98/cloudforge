"""Read-only, provider-neutral observation *planning* for an exact local receipt.

No probes are executed. A proposed check is not evidence of a healthy service,
a deployment, or authenticated approval.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from .deployment import DeploymentHandoff
from .local_adapter import (
    LocalExecutionApproval,
    LocalExecutionReceipt,
    verify_local_execution_receipt,
)


_ALLOWED_KINDS = frozenset({"startup", "readiness", "liveness"})


@dataclass(frozen=True)
class ObservationProbe:
    kind: str
    interval_seconds: int
    timeout_seconds: int
    failure_threshold: int


@dataclass(frozen=True)
class ObservationPlan:
    format_version: int
    authorization_request_digest: str
    authorization_receipt_sha256: str
    probes: tuple[ObservationProbe, ...]
    status: str = "proposed-only"
    infrastructure_mutated: bool = False
    deployment_observed: bool = False
    recovery_performed: bool = False

    def to_json(self) -> str:
        """Export a bounded canonical proposal, never an observation receipt."""
        _validate_plan_shape(self)
        return json.dumps(asdict(self), sort_keys=True, indent=2,
                          ensure_ascii=True, allow_nan=False) + "\n"


def _valid_digest(value: object) -> bool:
    return (type(value) is str and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _validate_probes(probes: object) -> None:
    if type(probes) is not tuple or not 2 <= len(probes) <= 3:
        raise ValueError("observation probes must be a bounded tuple")
    kinds: set[str] = set()
    for probe in probes:
        if type(probe) is not ObservationProbe or type(probe.kind) is not str:
            raise ValueError("malformed observation probe")
        if probe.kind not in _ALLOWED_KINDS or probe.kind in kinds:
            raise ValueError("unsupported or duplicate observation probe kind")
        kinds.add(probe.kind)
        if (type(probe.interval_seconds) is not int
                or not 5 <= probe.interval_seconds <= 300
                or type(probe.timeout_seconds) is not int
                or not 1 <= probe.timeout_seconds <= probe.interval_seconds
                or type(probe.failure_threshold) is not int
                or not 1 <= probe.failure_threshold <= 10):
            raise ValueError("invalid observation probe timing")
    if not {"readiness", "liveness"}.issubset(kinds):
        raise ValueError("readiness and liveness probes are required")


def _validate_plan_shape(plan: object) -> None:
    if (type(plan) is not ObservationPlan
            or type(plan.format_version) is not int
            or plan.format_version != 1
            or not _valid_digest(plan.authorization_request_digest)
            or not _valid_digest(plan.authorization_receipt_sha256)
            or type(plan.status) is not str
            or plan.status != "proposed-only"
            or plan.infrastructure_mutated is not False
            or plan.deployment_observed is not False
            or plan.recovery_performed is not False):
        raise ValueError("observation plan cannot claim execution or health")
    _validate_probes(plan.probes)


def prepare_observation_plan(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    probes: tuple[ObservationProbe, ...],
) -> ObservationPlan:
    """Bind proposed probes to reverified exact local authorization inputs.

    This does not authenticate a reviewer or check any live service. It does not
    accept endpoint URLs, shell commands, provider credentials or host addresses.
    """
    _validate_probes(probes)
    verify_local_execution_receipt(handoff, artifact, approval, receipt)
    return ObservationPlan(
        format_version=1,
        authorization_request_digest=receipt.request_digest,
        authorization_receipt_sha256=hashlib.sha256(
            receipt.to_json().encode("ascii")
        ).hexdigest(),
        probes=probes,
    )


def verify_observation_plan(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
) -> bool:
    """Compare a proposal with exact revalidated local-only inputs, no I/O."""
    _validate_plan_shape(plan)
    expected = prepare_observation_plan(
        handoff, artifact, approval, receipt, plan.probes,
    )
    if plan != expected:
        raise ValueError("observation proposal differs from exact local authorization")
    return True
