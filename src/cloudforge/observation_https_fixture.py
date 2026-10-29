"""Synthetic-only orchestration seam for the unwired pinned HTTPS HEAD transport.

The injected connection factory is a test fixture, not a trusted collector.
This module neither authenticates an operator/collector nor supplies a real
network connection, source key, DNS resolver or execution permission.
"""
from __future__ import annotations

import http.client
import time
from typing import Callable

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_evidence import ObservationSample
from .observation_plan import ObservationPlan
from .observation_runtime_dns import RuntimeDNSPinset, verify_runtime_dns_pinset
from .observation_runtime_request import RuntimeObservationRequest, RuntimeObservationTarget


def collect_pinned_https_fixture_samples(
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
    *,
    allowed_ipv4: tuple[tuple[str, ...], ...],
    allowed_ipv6: tuple[tuple[str, ...], ...],
    connection_factory: Callable,
) -> tuple[ObservationSample, ...]:
    """Exercise injected fake HEAD connections after full no-I/O preflight.

    This intentionally has no default connection factory. Supplying a real
    network-capable factory is outside this synthetic checkpoint and requires
    separate authenticated authorization. Samples are unsigned/untrusted and
    MUST NOT be interpreted as verified service health.
    """
    verify_runtime_dns_pinset(
        handoff, artifact, approval, receipt, plan, targets, request,
        resolved_ipv4, resolved_ipv6, pinset,
        allowed_ipv4=allowed_ipv4, allowed_ipv6=allowed_ipv6,
    )
    if not callable(connection_factory):
        raise ValueError("synthetic HTTPS connection factory is required")
    samples: list[ObservationSample] = []
    for probe, target, a, aaaa in zip(
        plan.probes, targets, resolved_ipv4, resolved_ipv6,
    ):
        # Pinset verification requires nonempty, canonical, policy-equal sets.
        pinned_ip = a[0] if a else aaaa[0]
        started = time.monotonic()
        connection = None
        outcome = "unknown"
        try:
            connection = connection_factory(target, pinned_ip, probe.timeout_seconds)
            connection.request("HEAD", target.path)
            response = connection.getresponse()
            status = response.status
            if type(status) is int:
                if 200 <= status <= 299:
                    outcome = "pass"
                elif 300 <= status <= 599:
                    outcome = "fail"
        except Exception:
            # Transport, TLS, timeout, malformed response and fixture failures
            # all fail closed. No raw exception or target is emitted.
            outcome = "unknown"
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    outcome = "unknown"
        elapsed = time.monotonic() - started
        if not 0 <= elapsed <= probe.timeout_seconds:
            outcome = "unknown"
        samples.append(ObservationSample(
            probe.kind, outcome, min(300_000, max(0, int(elapsed * 1000))),
        ))
    return tuple(samples)
