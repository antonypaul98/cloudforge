"""Synthetic, no-network IPv4 pinset boundary regressions."""
from dataclasses import replace
import hashlib
import json
import socket
import subprocess

import pytest

from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution, prepare_local_execution_request,
)
from cloudforge.models import ApplicationProfile
from cloudforge.observation_plan import ObservationProbe, prepare_observation_plan
from cloudforge.observation_runtime_request import (
    RuntimeObservationTarget, prepare_runtime_observation_request,
)
from cloudforge.observation_runtime_pin import (
    prepare_runtime_ipv4_pinset, verify_runtime_ipv4_pinset,
)
from cloudforge.planner import derive_requirements


def _context():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "fixture")
    handoff = authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "reviewer"),
    )
    artifact = b"runtime-pin-fixture"
    local_request = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(local_request.digest, "reviewer")
    receipt = authorize_local_execution(handoff, artifact, local_request, approval)
    observation = prepare_observation_plan(
        handoff, artifact, approval, receipt,
        (ObservationProbe("readiness", 10, 2, 3),
         ObservationProbe("liveness", 20, 2, 3)),
    )
    targets = (
        RuntimeObservationTarget("readiness", "https", "api.example.com", 443, "/ready"),
        RuntimeObservationTarget("liveness", "https", "api.example.com", 443, "/live"),
    )
    runtime_request = prepare_runtime_observation_request(
        handoff, artifact, approval, receipt, observation, targets,
    )
    return (handoff, artifact, approval, receipt, observation, targets,
            runtime_request)


def _pins():
    return (("1.1.1.1", "8.8.8.8"), ("9.9.9.9",))


def test_exact_pinset_is_deterministic_redacted_and_not_approval():
    args, pins = _context(), _pins()
    result = prepare_runtime_ipv4_pinset(*args, pins, allowed_ipv4=pins)
    assert result == prepare_runtime_ipv4_pinset(*args, pins, allowed_ipv4=pins)
    assert verify_runtime_ipv4_pinset(*args, pins, result, allowed_ipv4=pins)
    exported = result.to_json()
    assert json.loads(exported)["status"] == "pending-independent-approval"
    assert exported == json.dumps(json.loads(exported), sort_keys=True, indent=2) + "\n"
    assert result.runtime_request_sha256 == hashlib.sha256(
        args[-1].to_json().encode("ascii")
    ).hexdigest()
    for forbidden in ("api.example.com", "1.1.1.1", "8.8.8.8", "9.9.9.9",
                      "/ready", "reviewer", "runtime-pin-fixture"):
        assert forbidden not in exported
    assert '"infrastructure_mutated": false' in exported
    assert '"deployment_observed": false' in exported
    assert '"recovery_performed": false' in exported


@pytest.mark.parametrize("bad", [
    "127.0.0.1", "169.254.169.254", "10.0.0.1", "172.16.0.1",
    "192.168.1.1", "100.64.0.1", "192.0.2.1", "198.51.100.1",
    "203.0.113.1", "0.0.0.0", "255.255.255.255", "224.0.0.1",
    "8.8.8.08", "0x08080808", "134744072", "8.8.8.8/32",
    "::ffff:8.8.8.8", "2606:4700:4700::1111", "8.8.8.8%eth0",
    "8.8.8.8:443", "", True, 0, None,
])
def test_rejects_unsafe_or_noncanonical_address(bad):
    pins = ((bad,), ("9.9.9.9",))
    with pytest.raises(ValueError):
        prepare_runtime_ipv4_pinset(*_context(), pins, allowed_ipv4=pins)


@pytest.mark.parametrize("mutation", [
    lambda p: list(p),
    lambda p: p[:1],
    lambda p: p + p[:1],
    lambda p: ((), p[1]),
    lambda p: (("1.1.1.1",) * 5, p[1]),
    lambda p: (("8.8.8.8", "1.1.1.1"), p[1]),
    lambda p: (("1.1.1.1", "1.1.1.1"), p[1]),
    lambda p: (["1.1.1.1"], p[1]),
    lambda p: (("1.1.1.1", "8.8.8.8"), ["9.9.9.9"]),
])
def test_rejects_malformed_or_unsorted_sets(mutation):
    pins = mutation(_pins())
    with pytest.raises(ValueError):
        prepare_runtime_ipv4_pinset(*_context(), pins, allowed_ipv4=pins)


def test_changed_resolution_or_allowlist_rejected():
    args, pins = _context(), _pins()
    changed = (("1.1.1.1", "8.8.8.8"), ("8.8.4.4",))
    with pytest.raises(ValueError, match="trusted pin policy"):
        prepare_runtime_ipv4_pinset(*args, changed, allowed_ipv4=pins)
    with pytest.raises(ValueError, match="trusted pin policy"):
        prepare_runtime_ipv4_pinset(*args, pins, allowed_ipv4=changed)
    first = prepare_runtime_ipv4_pinset(*args, pins, allowed_ipv4=pins)
    with pytest.raises(ValueError, match="differs"):
        verify_runtime_ipv4_pinset(*args, changed, first, allowed_ipv4=changed)


def test_changed_target_and_artifact_fail_closed():
    args, pins = _context(), _pins()
    first = prepare_runtime_ipv4_pinset(*args, pins, allowed_ipv4=pins)
    changed = (*args[:5], (replace(args[5][0], path="/other"), args[5][1]), args[6])
    with pytest.raises(ValueError):
        verify_runtime_ipv4_pinset(*changed, pins, first, allowed_ipv4=pins)
    with pytest.raises((ValueError, PermissionError)):
        prepare_runtime_ipv4_pinset(
            args[0], b"changed", *args[2:], pins, allowed_ipv4=pins,
        )


@pytest.mark.parametrize("mutation", [
    lambda p: replace(p, format_version=True),
    lambda p: replace(p, format_version=2),
    lambda p: replace(p, runtime_request_sha256="0" * 64),
    lambda p: replace(p, ordered_ipv4_sets_sha256="0" * 64),
    lambda p: replace(p, status="approved"),
    lambda p: replace(p, infrastructure_mutated=True),
    lambda p: replace(p, deployment_observed=True),
    lambda p: replace(p, recovery_performed=True),
])
def test_tampered_pinset_rejected(mutation):
    args, pins = _context(), _pins()
    pinset = mutation(prepare_runtime_ipv4_pinset(*args, pins, allowed_ipv4=pins))
    with pytest.raises(ValueError):
        verify_runtime_ipv4_pinset(*args, pins, pinset, allowed_ipv4=pins)


def test_pinset_never_resolves_or_connects(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("pinset attempted DNS, network or process I/O")
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    args, pins = _context(), _pins()
    pinset = prepare_runtime_ipv4_pinset(*args, pins, allowed_ipv4=pins)
    assert verify_runtime_ipv4_pinset(*args, pins, pinset, allowed_ipv4=pins)
