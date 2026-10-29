"""No-network fixture integration of exact pinsets with HEAD sample handling."""
from dataclasses import replace
import http.client
import socket
from unittest.mock import Mock

import pytest

from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution, prepare_local_execution_request,
)
from cloudforge.models import ApplicationProfile
from cloudforge.observation_https_fixture import collect_pinned_https_fixture_samples
from cloudforge.observation_plan import ObservationProbe, prepare_observation_plan
from cloudforge.observation_runtime_dns import prepare_runtime_dns_pinset
from cloudforge.observation_runtime_request import (
    RuntimeObservationTarget, prepare_runtime_observation_request,
)
from cloudforge.planner import derive_requirements


def _fixture():
    deployment = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(deployment)
    request = prepare_deployment_request(deployment, proposal, "fixture")
    handoff = authorize_deployment_handoff(
        deployment, proposal, request, DeploymentApproval(request.digest, "reviewer"),
    )
    artifact = b"synthetic-pinned-head"
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
    return args, {"allowed_ipv4": a, "allowed_ipv6": aaaa}


def _run(factory, args=None, kwargs=None):
    if args is None:
        args, kwargs = _fixture()
    return collect_pinned_https_fixture_samples(
        *args, **kwargs, connection_factory=factory,
    )


def _fake(status=204, *, close_error=None, request_error=None):
    connection = Mock()
    connection.getresponse.return_value.status = status
    if close_error is not None:
        connection.close.side_effect = close_error
    if request_error is not None:
        connection.request.side_effect = request_error
    return connection


def test_pinned_ipv4_ipv6_order_and_exact_head_without_real_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("real socket attempted in synthetic fixture")
    monkeypatch.setattr(socket, "socket", forbidden)
    calls = []
    connections = [_fake(204), _fake(404)]

    def factory(target, ip, timeout):
        calls.append((target.kind, target.path, ip, timeout))
        return connections[len(calls) - 1]

    samples = _run(factory)
    assert [(s.kind, s.outcome) for s in samples] == [
        ("readiness", "pass"), ("liveness", "fail"),
    ]
    assert calls == [
        ("readiness", "/ready", "1.1.1.1", 2),
        ("liveness", "/live", "2606:4700:4700::1111", 2),
    ]
    for connection, path in zip(connections, ("/ready", "/live")):
        connection.request.assert_called_once_with("HEAD", path)
        connection.getresponse.assert_called_once_with()
        connection.close.assert_called_once_with()


@pytest.mark.parametrize("status,expected", [
    (200, "pass"), (299, "pass"), (300, "fail"), (302, "fail"),
    (404, "fail"), (599, "fail"), (100, "unknown"), (600, "unknown"),
    (True, "unknown"), ("204", "unknown"), (None, "unknown"),
])
def test_status_is_strict_and_redirect_is_never_followed(status, expected):
    samples = _run(lambda *_: _fake(status))
    assert [s.outcome for s in samples] == [expected, expected]


@pytest.mark.parametrize("failure", [
    TimeoutError("late"), ConnectionError("refused"),
    http.client.HTTPException("malformed"), ValueError("invalid"),
])
def test_transport_failures_are_unknown_and_connections_closed(failure):
    connections = []
    def factory(*_):
        conn = _fake(request_error=failure)
        connections.append(conn)
        return conn
    assert [s.outcome for s in _run(factory)] == ["unknown", "unknown"]
    assert all(conn.close.call_count == 1 for conn in connections)


def test_close_failure_invalidates_success_and_does_not_leak():
    assert [s.outcome for s in _run(
        lambda *_: _fake(close_error=OSError("close failed"))
    )] == ["unknown", "unknown"]


def test_factory_failure_is_unknown_without_leaking_exception():
    def broken(*_):
        raise OSError("private synthetic endpoint")
    assert [s.outcome for s in _run(broken)] == ["unknown", "unknown"]


@pytest.mark.parametrize("mutation", ["artifact", "request", "pinset", "allowlist", "target"])
def test_preflight_rejects_changed_inputs_before_any_connection(mutation):
    args, kwargs = _fixture()
    args = list(args)
    if mutation == "artifact":
        args[1] = b"changed"
    elif mutation == "request":
        args[6] = replace(args[6], ordered_targets_sha256="0" * 64)
    elif mutation == "pinset":
        args[9] = replace(args[9], ordered_address_sets_sha256="0" * 64)
    elif mutation == "allowlist":
        kwargs["allowed_ipv4"] = (("8.8.8.8",), ())
    else:
        args[5] = (replace(args[5][0], path="/other"), args[5][1])
    factory = Mock(side_effect=AssertionError("unexpected fixture connection"))
    with pytest.raises((ValueError, PermissionError)):
        _run(factory, tuple(args), kwargs)
    factory.assert_not_called()


def test_missing_factory_rejected_before_any_connection():
    args, kwargs = _fixture()
    with pytest.raises(ValueError, match="factory"):
        _run(None, args, kwargs)


@pytest.mark.parametrize("elapsed,expected", [
    (1.9, "pass"), (2.0, "pass"), (2.1, "unknown"), (-0.1, "unknown"),
])
def test_total_head_and_cleanup_elapsed_budget(monkeypatch, elapsed, expected):
    import cloudforge.observation_https_fixture as module
    ticks = iter((100.0, 100.0 + elapsed, 200.0, 200.0 + elapsed))
    monkeypatch.setattr(module.time, "monotonic", lambda: next(ticks))
    assert [s.outcome for s in _run(lambda *_: _fake(204))] == [expected, expected]

@pytest.mark.parametrize("elapsed,expected_ms", [
    (float("nan"), 0), (float("inf"), 0), (float("-inf"), 0),
    (1e308, 300_000),
])
def test_nonfinite_or_huge_monotonic_delta_fails_closed(monkeypatch, elapsed, expected_ms):
    import cloudforge.observation_https_fixture as module
    ticks = iter((100.0, 100.0 + elapsed, 200.0, 200.0 + elapsed))
    monkeypatch.setattr(module.time, "monotonic", lambda: next(ticks))
    samples = _run(lambda *_: _fake(204))
    assert [(s.outcome, s.elapsed_ms) for s in samples] == [
        ("unknown", expected_ms), ("unknown", expected_ms),
    ]


@pytest.mark.parametrize("failure_phase", ["start", "finish"])
def test_monotonic_exception_does_not_forge_success(monkeypatch, failure_phase):
    import cloudforge.observation_https_fixture as module
    connection = _fake(204)
    factory = Mock(return_value=connection)
    if failure_phase == "start":
        monkeypatch.setattr(
            module.time, "monotonic", Mock(side_effect=OSError("clock unavailable")),
        )
    else:
        ticks = iter((100.0, OSError("clock unavailable"),
                      200.0, OSError("clock unavailable")))

        def clock():
            tick = next(ticks)
            if isinstance(tick, Exception):
                raise tick
            return tick

        monkeypatch.setattr(module.time, "monotonic", clock)
    samples = _run(factory)
    assert [(s.outcome, s.elapsed_ms) for s in samples] == [
        ("unknown", 0), ("unknown", 0),
    ]
    assert factory.call_count == (0 if failure_phase == "start" else 2)
    assert connection.close.call_count == (0 if failure_phase == "start" else 2)
