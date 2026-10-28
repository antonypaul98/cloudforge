"""Opt-in, bounded HEAD-only observation of an explicitly allowed loopback fixture.

No cloud/provider calls, redirects, credentials, signed evidence or health claims.
Callers must provision trusted allowlists and authorization outside this module.
"""
from __future__ import annotations

import http.client
import re
import time
from dataclasses import dataclass

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_evidence import ObservationSample
from .observation_plan import ObservationPlan, verify_observation_plan

_PATH = re.compile(r"/[A-Za-z0-9/_-]{0,127}\Z", re.ASCII)


@dataclass(frozen=True)
class LoopbackHTTPProbeTarget:
    kind: str
    host: str
    port: int
    path: str


def _validate_targets(
    plan: ObservationPlan,
    targets: tuple[LoopbackHTTPProbeTarget, ...],
    allowed_targets: tuple[LoopbackHTTPProbeTarget, ...],
) -> None:
    # Validate all targets before the first network call, including later targets.
    plan.to_json()
    if (type(targets) is not tuple or type(allowed_targets) is not tuple
            or len(targets) != len(plan.probes)
            or targets != allowed_targets):
        raise ValueError("probe targets differ from explicit trusted allowlist")
    for probe, target in zip(plan.probes, targets):
        if (type(target) is not LoopbackHTTPProbeTarget
                or type(target.kind) is not str or target.kind != probe.kind
                or type(target.host) is not str or target.host != "127.0.0.1"
                or type(target.port) is not int or not 1 <= target.port <= 65535
                or type(target.path) is not str
                or _PATH.fullmatch(target.path) is None
                or "//" in target.path
                or type(probe.timeout_seconds) is not int
                or not 1 <= probe.timeout_seconds <= 10):
            raise ValueError("unsafe or unsupported loopback HEAD probe target")


def collect_loopback_http_samples(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
    targets: tuple[LoopbackHTTPProbeTarget, ...],
    *,
    allowed_targets: tuple[LoopbackHTTPProbeTarget, ...],
) -> tuple[ObservationSample, ...]:
    """Perform HEAD-only checks on explicit numeric loopback endpoints.

    Each result is an unsigned raw HTTP sample, not verified evidence or a
    declaration that a service is healthy. This function does not sign or store
    samples. Only synthetic fixture endpoints are exercised in CI.
    """
    verify_observation_plan(handoff, artifact, approval, receipt, plan)
    _validate_targets(plan, targets, allowed_targets)
    samples = []
    for probe, target in zip(plan.probes, targets):
        started = time.monotonic()
        connection = None
        try:
            connection = http.client.HTTPConnection(
                "127.0.0.1", target.port, timeout=probe.timeout_seconds,
            )
            connection.request("HEAD", target.path, headers={"Connection": "close"})
            response = connection.getresponse()
            outcome = "pass" if 200 <= response.status <= 299 else "fail"
        except (OSError, http.client.HTTPException):
            outcome = "unknown"
        finally:
            if connection is not None:
                try:
                    connection.close()
                except (OSError, http.client.HTTPException):
                    # Failed cleanup invalidates even a successful HEAD status.
                    outcome = "unknown"
        # Socket timeouts bound individual blocking operations, not necessarily
        # the complete HEAD transaction and cleanup. Never count a response
        # that exceeded the configured probe budget as a verified pass/fail.
        elapsed_seconds = time.monotonic() - started
        if not 0 <= elapsed_seconds <= probe.timeout_seconds:
            outcome = "unknown"
        elapsed_ms = min(300_000, max(0, int(elapsed_seconds * 1000)))
        samples.append(ObservationSample(probe.kind, outcome, elapsed_ms))
    return tuple(samples)
