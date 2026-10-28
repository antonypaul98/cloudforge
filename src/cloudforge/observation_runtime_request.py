"""Deterministic, no-I/O handoff for proposed HTTPS runtime observation targets.

A proposal is not authorization to contact a service, evidence of collector
identity, or proof of health. A separate authenticated approval and runtime
adapter are required before any request can be sent.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_http import _PATH
from .observation_plan import ObservationPlan, verify_observation_plan

_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z", re.ASCII)
_TLD = re.compile(r"[a-z]{2,63}\Z", re.ASCII)
_HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


@dataclass(frozen=True)
class RuntimeObservationTarget:
    kind: str
    scheme: str
    host: str
    port: int
    path: str


@dataclass(frozen=True)
class RuntimeObservationRequest:
    format_version: int
    observation_plan_sha256: str
    ordered_targets_sha256: str
    operation: str = "propose-read-only-https-head"
    status: str = "pending-independent-approval"
    infrastructure_mutated: bool = False
    deployment_observed: bool = False
    recovery_performed: bool = False

    def to_json(self) -> str:
        _validate_request(self)
        return json.dumps(asdict(self), sort_keys=True, indent=2,
                          ensure_ascii=True, allow_nan=False) + "\n"


def _validate_targets(plan: ObservationPlan,
                      targets: tuple[RuntimeObservationTarget, ...]) -> None:
    plan.to_json()
    if type(targets) is not tuple or len(targets) != len(plan.probes):
        raise ValueError("runtime observation targets must match probe order")
    for probe, target in zip(plan.probes, targets):
        if (type(target) is not RuntimeObservationTarget
                or type(target.kind) is not str or target.kind != probe.kind
                or type(target.scheme) is not str or target.scheme != "https"
                or type(target.host) is not str
                or not 1 <= len(target.host) <= 253
                or target.host != target.host.lower()
                or type(target.port) is not int or not 1 <= target.port <= 65535
                or type(target.path) is not str
                or _PATH.fullmatch(target.path) is None
                or "//" in target.path):
            raise ValueError("invalid proposed HTTPS observation target")
        labels = target.host.split(".")
        if (len(labels) < 2 or not _TLD.fullmatch(labels[-1])
                or any(_LABEL.fullmatch(label) is None for label in labels)):
            raise ValueError("invalid proposed HTTPS observation hostname")


def _validate_request(request: RuntimeObservationRequest) -> None:
    if (type(request) is not RuntimeObservationRequest
            or type(request.format_version) is not int
            or request.format_version != 1
            or type(request.observation_plan_sha256) is not str
            or _HEX.fullmatch(request.observation_plan_sha256) is None
            or type(request.ordered_targets_sha256) is not str
            or _HEX.fullmatch(request.ordered_targets_sha256) is None
            or request.operation != "propose-read-only-https-head"
            or request.status != "pending-independent-approval"
            or request.infrastructure_mutated is not False
            or request.deployment_observed is not False
            or request.recovery_performed is not False):
        raise ValueError("runtime observation request cannot claim authorization or execution")


def prepare_runtime_observation_request(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
    targets: tuple[RuntimeObservationTarget, ...],
) -> RuntimeObservationRequest:
    """Bind exact local receipt, observation plan and ordered target proposal.

    Does not resolve DNS, send HTTP, read credentials, or authorize runtime use.
    """
    verify_observation_plan(handoff, artifact, approval, receipt, plan)
    _validate_targets(plan, targets)
    target_json = json.dumps([asdict(t) for t in targets], sort_keys=True,
                             separators=(",", ":"), ensure_ascii=True)
    return RuntimeObservationRequest(
        1,
        hashlib.sha256(plan.to_json().encode("ascii")).hexdigest(),
        hashlib.sha256(target_json.encode("ascii")).hexdigest(),
    )


def verify_runtime_observation_request(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
    targets: tuple[RuntimeObservationTarget, ...],
    request: RuntimeObservationRequest,
) -> bool:
    """Rebuild the exact proposal; verification grants no network permission."""
    _validate_request(request)
    expected = prepare_runtime_observation_request(
        handoff, artifact, approval, receipt, plan, targets,
    )
    if request != expected:
        raise ValueError("runtime observation request differs from exact inputs")
    return True
