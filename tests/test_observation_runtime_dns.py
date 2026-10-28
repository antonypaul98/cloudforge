"""Synthetic, no-network A/AAAA pinset regression tests."""
from dataclasses import replace
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
from cloudforge.observation_runtime_dns import (
    prepare_runtime_dns_pinset, verify_runtime_dns_pinset,
)
from cloudforge.planner import derive_requirements


def _context():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "fixture")
    handoff = authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "reviewer"),
    )
    artifact = b"dns-pin-fixture"
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


def _answers():
    return (("1.1.1.1",), ()), (("2606:4700:4700::1111",), ("2001:4860:4860::8888",))


def _prepare(args, a, aaaa, **overrides):
    return prepare_runtime_dns_pinset(
        *args, a, aaaa, allowed_ipv4=overrides.get("allowed_ipv4", a),
        allowed_ipv6=overrides.get("allowed_ipv6", aaaa),
    )


def test_mixed_and_ipv6_only_answers_are_deterministic_and_redacted():
    args, (a, aaaa) = _context(), _answers()
    result = _prepare(args, a, aaaa)
    assert result == _prepare(args, a, aaaa)
    assert verify_runtime_dns_pinset(
        *args, a, aaaa, result, allowed_ipv4=a, allowed_ipv6=aaaa,
    )
    exported = result.to_json()
    assert json.loads(exported)["status"] == "pending-independent-approval"
    assert json.loads(exported)["format_version"] == 1
    for forbidden in ("api.example.com", "1.1.1.1", "2606:4700", "2001:4860",
                      "reviewer", "/ready", "dns-pin-fixture"):
        assert forbidden not in exported
    assert json.loads(exported)["infrastructure_mutated"] is False
    assert json.loads(exported)["deployment_observed"] is False
    assert json.loads(exported)["recovery_performed"] is False


def test_ipv4_only_and_ipv6_only_targets_are_valid():
    args = _context()
    a = (("1.1.1.1",), ())
    aaaa = ((), ("2606:4700:4700::1111",))
    assert _prepare(args, a, aaaa).status == "pending-independent-approval"
    a = ((), ())
    aaaa = (("2606:4700:4700::1111",), ("2001:4860:4860::8888",))
    assert _prepare(args, a, aaaa).status == "pending-independent-approval"


@pytest.mark.parametrize("bad", [
    "::1", "fe80::1", "fc00::1", "2001:db8::1", "ff02::1",
    "::", "::ffff:8.8.8.8", "2002:c000:201::", "2001::1",
    "64:ff9b::808:808", "64:ff9b:1::808:808",
    "2606:4700:4700:0000::1111", "2606:4700:4700::1111%eth0",
    "[2606:4700:4700::1111]", "2606:4700:4700::1111/128",
    "2606:4700:4700::1111::443", "", True, 123, None,
])
def test_rejects_unsafe_noncanonical_or_malformed_ipv6(bad):
    args = _context()
    a, aaaa = _answers()
    aaaa = ((bad,), aaaa[1])
    with pytest.raises(ValueError):
        _prepare(args, a, aaaa)


@pytest.mark.parametrize("bad", [
    (((), ()), (("2606:4700:4700::1111",), ())),
    ((("1.1.1.1",), ()), ((), ())),
    ((("1.1.1.1",), ()), (("2606:4700:4700::1111",) * 5, ())),
    ((("1.1.1.1",), ("9.9.9.9",)), (("2606:4700:4700::1111",) * 2, ())),
    ((("1.1.1.1",), ("9.9.9.9",)), (("2606:4700:4700::1111", "2001:4860:4860::8888"), ())),
    ((("1.1.1.1",), ("9.9.9.9",)), (("2001:4860:4860::8888", "2606:4700:4700::1111"), ())),
    (((), ()), (("2606:4700:4700::1111",),)),
    (((), ()), (["2606:4700:4700::1111"], ("2001:4860:4860::8888",))),
    (((), ()), (("2606:4700:4700::1111",), ["2001:4860:4860::8888"])),
])
def test_rejects_empty_unsorted_duplicate_or_malformed_sets(bad):
    a, aaaa = bad
    with pytest.raises(ValueError):
        _prepare(_context(), a, aaaa)


def test_rejects_unapproved_a_or_aaaa_change_and_tampered_receipt():
    args, (a, aaaa) = _context(), _answers()
    result = _prepare(args, a, aaaa)
    with pytest.raises(ValueError, match="trusted pin policy"):
        _prepare(args, a, aaaa, allowed_ipv4=(("8.8.8.8",), ()))
    with pytest.raises(ValueError, match="trusted pin policy"):
        _prepare(args, a, aaaa, allowed_ipv6=(aaaa[0], ("2606:4700:4700::1111",)))
    changed = ((), ()), aaaa
    with pytest.raises(ValueError, match="differs"):
        verify_runtime_dns_pinset(
            *args, *changed, result, allowed_ipv4=changed[0], allowed_ipv6=changed[1],
        )
    with pytest.raises((ValueError, PermissionError)):
        _prepare((args[0], b"tampered", *args[2:]), a, aaaa)


@pytest.mark.parametrize("field,value", [
    ("format_version", True), ("format_version", 2),
    ("runtime_request_sha256", "0" * 64),
    ("ordered_address_sets_sha256", "0" * 64),
    ("status", "approved"), ("infrastructure_mutated", True),
    ("deployment_observed", True), ("recovery_performed", True),
])
def test_rejects_forged_pinset(field, value):
    args, (a, aaaa) = _context(), _answers()
    result = replace(_prepare(args, a, aaaa), **{field: value})
    with pytest.raises(ValueError):
        verify_runtime_dns_pinset(
            *args, a, aaaa, result, allowed_ipv4=a, allowed_ipv6=aaaa,
        )


def test_no_dns_network_or_process_io(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("DNS pinset attempted network or process I/O")
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    args, (a, aaaa) = _context(), _answers()
    result = _prepare(args, a, aaaa)
    assert verify_runtime_dns_pinset(
        *args, a, aaaa, result, allowed_ipv4=a, allowed_ipv6=aaaa,
    )
