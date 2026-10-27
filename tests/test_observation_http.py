"""Bounded fixture-only HTTP HEAD collector regression tests."""
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution, prepare_local_execution_request,
)
from cloudforge.models import ApplicationProfile
from cloudforge.observation_http import (
    LoopbackHTTPProbeTarget, collect_loopback_http_samples,
)
from cloudforge.observation_plan import ObservationProbe, prepare_observation_plan
from cloudforge.planner import derive_requirements


def _context():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "fixture")
    handoff = authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "reviewer"),
    )
    artifact = b"fixture-http-artifact"
    local_request = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(local_request.digest, "reviewer")
    receipt = authorize_local_execution(handoff, artifact, local_request, approval)
    observation_plan = prepare_observation_plan(
        handoff, artifact, approval, receipt,
        (ObservationProbe("readiness", 10, 2, 3),
         ObservationProbe("liveness", 10, 2, 3)),
    )
    return handoff, artifact, approval, receipt, observation_plan


class FixtureHandler(BaseHTTPRequestHandler):
    calls = []

    def do_HEAD(self):
        type(self).calls.append((self.command, self.path))
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
        elif self.path == "/health":
            self.send_response(204)
        else:
            self.send_response(404)
        self.end_headers()

    def do_GET(self):
        raise AssertionError("collector must not send GET")

    def log_message(self, *_args):
        pass


@pytest.fixture
def fixture_server():
    FixtureHandler.calls = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _targets(port, path="/health"):
    return (
        LoopbackHTTPProbeTarget("readiness", "127.0.0.1", port, path),
        LoopbackHTTPProbeTarget("liveness", "127.0.0.1", port, path),
    )


def _collect(context, targets, *, allowed=None):
    return collect_loopback_http_samples(
        *context, targets, allowed_targets=targets if allowed is None else allowed,
    )


def test_fixture_head_only_and_bounded_samples(fixture_server):
    context = _context()
    targets = _targets(fixture_server)
    samples = _collect(context, targets)
    assert [(s.kind, s.outcome) for s in samples] == [
        ("readiness", "pass"), ("liveness", "pass"),
    ]
    assert all(type(s.elapsed_ms) is int and 0 <= s.elapsed_ms <= 300_000
               for s in samples)
    assert FixtureHandler.calls == [("HEAD", "/health"), ("HEAD", "/health")]


def test_redirect_not_followed_and_not_healthy(fixture_server):
    targets = _targets(fixture_server, "/redirect")
    assert [s.outcome for s in _collect(_context(), targets)] == ["fail", "fail"]
    assert FixtureHandler.calls == [("HEAD", "/redirect"), ("HEAD", "/redirect")]


def test_missing_endpoint_not_healthy(fixture_server):
    assert [s.outcome for s in _collect(_context(), _targets(fixture_server, "/missing"))] == ["fail", "fail"]


@pytest.mark.parametrize("host", [
    "localhost", "127.1", "127.0.0.2", "::1", "0.0.0.0", "169.254.169.254",
    "http://127.0.0.1", "127.0.0.1.evil.test", "2130706433", "[::1]", True,
])
def test_rejects_ambiguous_or_nonloopback_host_before_io(monkeypatch, host):
    import cloudforge.observation_http as module
    monkeypatch.setattr(module.http.client, "HTTPConnection", lambda *_a, **_kw: pytest.fail("unexpected network"))
    targets = _targets(12345)
    bad = (replace(targets[0], host=host), targets[1])
    with pytest.raises(ValueError):
        _collect(_context(), bad)


@pytest.mark.parametrize("path", [
    "http://127.0.0.1/health", "//host/health", "/../health", "/health?token=x",
    "/health#fragment", "/%2e%2e/", "/health\\x", "/héalth", "", "health",
    "/" + "a" * 129, "/health\r\nHost:evil", True,
])
def test_rejects_unsafe_path_before_io(monkeypatch, path):
    import cloudforge.observation_http as module
    monkeypatch.setattr(module.http.client, "HTTPConnection", lambda *_a, **_kw: pytest.fail("unexpected network"))
    targets = _targets(12345)
    bad = (replace(targets[0], path=path), targets[1])
    with pytest.raises(ValueError):
        _collect(_context(), bad)


@pytest.mark.parametrize("port", [0, 65536, -1, True, 1.0, "8080"])
def test_rejects_invalid_port_before_io(monkeypatch, port):
    import cloudforge.observation_http as module
    monkeypatch.setattr(module.http.client, "HTTPConnection", lambda *_a, **_kw: pytest.fail("unexpected network"))
    targets = _targets(12345)
    bad = (replace(targets[0], port=port), targets[1])
    with pytest.raises(ValueError):
        _collect(_context(), bad)


def test_explicit_allowlist_and_exact_probe_order_before_io(monkeypatch):
    import cloudforge.observation_http as module
    monkeypatch.setattr(module.http.client, "HTTPConnection", lambda *_a, **_kw: pytest.fail("unexpected network"))
    context = _context()
    targets = _targets(12345)
    for bad, allowed in (
        (targets, _targets(12346)),
        (targets[::-1], targets[::-1]),
        (targets[:1], targets[:1]),
        (targets + targets[:1], targets + targets[:1]),
        (list(targets), targets),
    ):
        with pytest.raises(ValueError):
            _collect(context, bad, allowed=allowed)


def test_rejects_stale_exact_artifact_before_io(monkeypatch):
    import cloudforge.observation_http as module
    monkeypatch.setattr(module.http.client, "HTTPConnection", lambda *_a, **_kw: pytest.fail("unexpected network"))
    context = _context()
    bad_context = (context[0], b"changed", *context[2:])
    with pytest.raises(ValueError):
        _collect(bad_context, _targets(12345))


def test_connection_refusal_is_unknown_not_pass(monkeypatch):
    import cloudforge.observation_http as module

    class Refuse:
        def __init__(self, *_a, **_kw):
            pass
        def request(self, *_a, **_kw):
            raise ConnectionRefusedError("fixture refusal")
        def close(self):
            pass

    monkeypatch.setattr(module.http.client, "HTTPConnection", Refuse)
    assert [s.outcome for s in _collect(_context(), _targets(12345))] == ["unknown", "unknown"]


def test_rejects_long_probe_timeout_before_io(monkeypatch):
    import cloudforge.observation_http as module
    monkeypatch.setattr(module.http.client, "HTTPConnection", lambda *_a, **_kw: pytest.fail("unexpected network"))
    context = _context()
    long_probe = replace(context[-1].probes[0], timeout_seconds=11, interval_seconds=15)
    long_plan = replace(context[-1], probes=(long_probe, context[-1].probes[1]))
    with pytest.raises(ValueError):
        _collect((*context[:-1], long_plan), _targets(12345))
