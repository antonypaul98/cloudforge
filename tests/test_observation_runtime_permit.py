"""No-network permit policy tests for proposed pinned HTTPS HEAD targets."""
from dataclasses import replace
import hashlib
import json
import socket
import subprocess
import time

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
from cloudforge.observation_runtime_dns import prepare_runtime_dns_pinset
from cloudforge.observation_runtime_permit import (
    issue_runtime_head_permit, verify_runtime_head_permit,
)
from cloudforge.observation_runtime_request import (
    RuntimeObservationTarget, prepare_runtime_observation_request,
)
from cloudforge.planner import derive_requirements

_SOURCE_KEY = bytes(range(32))
_OPERATOR_KEY = bytes(range(32, 64))
_NOW = 1_800_000_020


def _context():
    deployment = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(deployment)
    request = prepare_deployment_request(deployment, proposal, "fixture")
    handoff = authorize_deployment_handoff(
        deployment, proposal, request, DeploymentApproval(request.digest, "reviewer"),
    )
    artifact = b"synthetic-runtime-permit"
    local_request = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(local_request.digest, "reviewer")
    receipt = authorize_local_execution(handoff, artifact, local_request, approval)
    plan = prepare_observation_plan(
        handoff, artifact, approval, receipt,
        (ObservationProbe("readiness", 10, 2, 3),
         ObservationProbe("liveness", 10, 2, 3)),
    )
    targets = (
        RuntimeObservationTarget("readiness", "https", "api.example.com", 443, "/ready"),
        RuntimeObservationTarget("liveness", "https", "api.example.com", 8443, "/live"),
    )
    runtime_request = prepare_runtime_observation_request(
        handoff, artifact, approval, receipt, plan, targets,
    )
    a = (("1.1.1.1",), ())
    aaaa = ((), ("2606:4700:4700::1111",))
    pinset = prepare_runtime_dns_pinset(
        handoff, artifact, approval, receipt, plan, targets, runtime_request,
        a, aaaa, allowed_ipv4=a, allowed_ipv6=aaaa,
    )
    args = (handoff, artifact, approval, receipt, plan, targets,
            runtime_request, a, aaaa, pinset)
    kwargs = dict(allowed_ipv4=a, allowed_ipv6=aaaa,
                  source_id="collector-1", source_key=_SOURCE_KEY,
                  operator_key=_OPERATOR_KEY, sequence=7,
                  valid_from_unix=_NOW - 10, valid_until_unix=_NOW + 20)
    return args, kwargs


def _issued():
    args, kwargs = _context()
    return args, kwargs, issue_runtime_head_permit(*args, **kwargs)


def _verify(args, kwargs, permit, **changes):
    policy = {k: v for k, v in kwargs.items()
              if k not in ("valid_from_unix", "valid_until_unix")}
    policy["now_unix"] = _NOW
    policy.update(changes)
    return verify_runtime_head_permit(*args, permit, **policy)


def test_exact_permit_deterministic_and_valid():
    args, kwargs, permit = _issued()
    assert permit == issue_runtime_head_permit(*args, **kwargs)
    assert _verify(args, kwargs, permit) is True
    assert permit.format_version == 1
    assert permit.sequence == 7
    assert permit.runtime_request_sha256 == hashlib.sha256(
        args[6].to_json().encode("ascii")).hexdigest()
    assert permit.pinset_sha256 == hashlib.sha256(
        args[9].to_json().encode("ascii")).hexdigest()
    assert "example.com" not in json.dumps(permit.__dict__)
    assert "synthetic-runtime-permit" not in json.dumps(permit.__dict__)


@pytest.mark.parametrize("change", [
    {"sequence": 8},
    {"now_unix": _NOW - 11},
    {"now_unix": _NOW + 21},
    {"source_id": "collector-2"},
    {"source_key": bytes(range(1, 33))},
    {"operator_key": bytes(range(64, 96))},
    {"sequence": True},
    {"now_unix": True},
])
def test_wrong_identity_key_sequence_or_clock_fails(change):
    args, kwargs, permit = _issued()
    with pytest.raises(ValueError):
        _verify(args, kwargs, permit, **change)


@pytest.mark.parametrize("field,value", [
    ("mac_sha256", "0" * 64),
    ("runtime_request_sha256", "0" * 64),
    ("pinset_sha256", "0" * 64),
    ("source_key_sha256", "0" * 64),
    ("sequence", 8),
    ("valid_until_unix", _NOW + 30),
    ("format_version", 2),
    ("sequence", True),
    ("source_id", "COLLECTOR"),
])
def test_forged_permit_fields_fail(field, value):
    args, kwargs, permit = _issued()
    with pytest.raises(ValueError):
        _verify(args, kwargs, replace(permit, **{field: value}))


@pytest.mark.parametrize("change", [
    {"operator_key": _SOURCE_KEY},
    {"operator_key": b"short"},
    {"operator_key": bytearray(_OPERATOR_KEY)},
    {"sequence": 0},
    {"sequence": True},
    {"valid_from_unix": _NOW},
    {"valid_until_unix": _NOW + 301},
    {"valid_until_unix": True},
])
def test_issuer_rejects_invalid_policy(change):
    args, kwargs = _context()
    with pytest.raises(ValueError):
        issue_runtime_head_permit(*args, **dict(kwargs, **change))


@pytest.mark.parametrize("mutation", [
    "artifact", "target", "request", "pinset", "allowlist",
])
def test_exact_preflight_rejects_mutation_before_signing(mutation):
    args, kwargs = _context()
    args = list(args)
    if mutation == "artifact":
        args[1] = b"changed"
    elif mutation == "target":
        args[5] = (replace(args[5][0], path="/other"), args[5][1])
    elif mutation == "request":
        args[6] = replace(args[6], ordered_targets_sha256="0" * 64)
    elif mutation == "pinset":
        args[9] = replace(args[9], ordered_address_sets_sha256="0" * 64)
    else:
        kwargs["allowed_ipv4"] = (("8.8.8.8",), ())
    with pytest.raises((ValueError, PermissionError)):
        issue_runtime_head_permit(*args, **kwargs)


def test_permit_is_pure_no_network_shell_or_clock(monkeypatch):
    args, kwargs = _context()
    def forbidden(*_args, **_kwargs):
        pytest.fail("permit unexpectedly performed external I/O")
    with monkeypatch.context() as guard:
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(subprocess, "run", forbidden)
        guard.setattr(time, "time", forbidden)
        permit = issue_runtime_head_permit(*args, **kwargs)
        assert _verify(args, kwargs, permit)
