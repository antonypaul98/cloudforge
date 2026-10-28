"""Fixture-only integration regressions for HEAD -> HMAC -> durable replay."""
from dataclasses import replace
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import sqlite3
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
from cloudforge.observation_evidence import verify_observation_evidence
from cloudforge.observation_fixture_intake import collect_and_accept_loopback_fixture_evidence
from cloudforge.observation_http import LoopbackHTTPProbeTarget
from cloudforge.observation_plan import ObservationProbe, prepare_observation_plan
from cloudforge.observation_source_pin import ObservationSourcePin
from cloudforge.planner import derive_requirements

_KEY = bytes(range(32))
_NOW = 1_800_000_015


def _context():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "fixture")
    handoff = authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "reviewer"),
    )
    artifact = b"fixture-intake-artifact"
    local_request = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(local_request.digest, "reviewer")
    receipt = authorize_local_execution(handoff, artifact, local_request, approval)
    observation_plan = prepare_observation_plan(
        handoff, artifact, approval, receipt,
        (ObservationProbe("readiness", 10, 2, 3),
         ObservationProbe("liveness", 10, 2, 3)),
    )
    return handoff, artifact, approval, receipt, observation_plan


class Handler(BaseHTTPRequestHandler):
    calls = []

    def do_HEAD(self):
        type(self).calls.append((self.command, self.path))
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/")
        elif self.path == "/ok":
            self.send_response(204)
        else:
            self.send_response(503)
        self.end_headers()

    def do_GET(self):
        raise AssertionError("GET must never be used")

    def log_message(self, *_args):
        pass


@pytest.fixture
def fixture_server():
    Handler.calls = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _targets(port, path="/ok"):
    return (LoopbackHTTPProbeTarget("readiness", "127.0.0.1", port, path),
            LoopbackHTTPProbeTarget("liveness", "127.0.0.1", port, path))


def _collect(context, targets, ledger, **overrides):
    settings = dict(
        allowed_targets=targets, source_id="fixture-collector", source_key=_KEY,
        observed_at_unix=1_800_000_000, now_unix=_NOW, sequence=1,
        max_age_seconds=30, ledger_path=str(ledger),
    )
    settings.update(overrides)
    return collect_and_accept_loopback_fixture_evidence(
        *context, targets, **settings,
    )


def test_head_samples_are_signed_and_durably_accepted(fixture_server, tmp_path):
    context = _context()
    path = tmp_path / "replay.sqlite3"
    evidence = _collect(context, _targets(fixture_server), path)
    assert [(s.kind, s.outcome) for s in evidence.samples] == [
        ("readiness", "pass"), ("liveness", "pass"),
    ]
    assert Handler.calls == [("HEAD", "/ok"), ("HEAD", "/ok")]
    assert verify_observation_evidence(
        *context, evidence, expected_source_id="fixture-collector",
        source_key=_KEY, now_unix=_NOW, max_age_seconds=30,
        last_sequence=0,
    )
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT source_id, last_sequence FROM observation_replay").fetchall() == [
            ("fixture-collector", 1),
        ]
    exported = evidence.to_json()
    assert "fixture-intake-artifact" not in exported
    assert "reviewer" not in exported
    assert str(path) not in exported
    assert _KEY.hex() not in exported
    assert "healthy" not in exported


def test_duplicate_sequence_fails_closed_after_head(fixture_server, tmp_path):
    context = _context()
    targets = _targets(fixture_server)
    path = tmp_path / "replay.sqlite3"
    _collect(context, targets, path)
    with pytest.raises(ValueError, match="already accepted"):
        _collect(context, targets, path)
    assert len(Handler.calls) == 4  # preflight does not reserve a sequence
    assert _collect(context, targets, path, sequence=2).sequence == 2
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT last_sequence FROM observation_replay").fetchone() == (2,)


@pytest.mark.parametrize("path,outcome", [("/down", "fail"), ("/redirect", "fail")])
def test_non_2xx_or_redirect_never_becomes_health_claim(fixture_server, tmp_path, path, outcome):
    evidence = _collect(_context(), _targets(fixture_server, path), tmp_path / "replay.db")
    assert [s.outcome for s in evidence.samples] == [outcome, outcome]
    assert Handler.calls == [("HEAD", path), ("HEAD", path)]
    assert "healthy" not in evidence.to_json()


@pytest.mark.parametrize("override", [
    {"source_key": b"short"},
    {"source_id": "wrong source"},
    {"sequence": 0},
    {"sequence": True},
    {"observed_at_unix": True},
    {"now_unix": 1_799_999_999},
    {"now_unix": 1_800_000_500},
    {"max_age_seconds": 0},
    {"ledger_path": "relative.db"},
    {"ledger_path": None},
])
def test_invalid_trust_context_rejected_before_network(monkeypatch, tmp_path, override):
    import cloudforge.observation_http as http_module
    monkeypatch.setattr(http_module.http.client, "HTTPConnection", lambda *_a, **_kw: pytest.fail("network before preflight"))
    path = tmp_path / "ledger.db"
    with pytest.raises(ValueError):
        _collect(_context(), _targets(12345), path, **override)
    assert not path.exists()


def test_changed_artifact_rejected_before_network(monkeypatch, tmp_path):
    import cloudforge.observation_http as http_module
    monkeypatch.setattr(http_module.http.client, "HTTPConnection", lambda *_a, **_kw: pytest.fail("network before auth"))
    context = _context()
    with pytest.raises((ValueError, PermissionError)):
        _collect((context[0], b"changed", *context[2:]), _targets(12345), tmp_path / "ledger.db")


@pytest.mark.parametrize("mutation", [
    lambda t: (replace(t[0], host="169.254.169.254"), t[1]),
    lambda t: (replace(t[0], path="//bad"), t[1]),
    lambda t: (t[1], t[0]),
])
def test_unsafe_or_misordered_targets_rejected_before_network(monkeypatch, tmp_path, mutation):
    import cloudforge.observation_http as http_module
    monkeypatch.setattr(http_module.http.client, "HTTPConnection", lambda *_a, **_kw: pytest.fail("network before allowlist"))
    targets = _targets(12345)
    with pytest.raises(ValueError):
        _collect(_context(), mutation(targets), tmp_path / "ledger.db", allowed_targets=targets)


def test_transport_refusal_yields_unknown_signed_sample(monkeypatch, tmp_path):
    import cloudforge.observation_http as http_module

    class Refuse:
        def __init__(self, *_args, **_kwargs):
            pass
        def request(self, *_args, **_kwargs):
            raise ConnectionRefusedError("fixture refusal")
        def close(self):
            pass

    monkeypatch.setattr(http_module.http.client, "HTTPConnection", Refuse)
    evidence = _collect(_context(), _targets(12345), tmp_path / "ledger.db")
    assert [s.outcome for s in evidence.samples] == ["unknown", "unknown"]


def test_cleanup_failure_cannot_sign_a_passing_sample(monkeypatch, tmp_path):
    import cloudforge.observation_http as http_module

    class FailingClose:
        def __init__(self, *_args, **_kwargs):
            pass
        def request(self, method, path, headers):
            assert method == "HEAD" and path == "/ok"
        def getresponse(self):
            return type("Response", (), {"status": 204})()
        def close(self):
            raise OSError("fixture close failed")

    monkeypatch.setattr(http_module.http.client, "HTTPConnection", FailingClose)
    ledger = tmp_path / "ledger.db"
    evidence = _collect(_context(), _targets(12345), ledger)
    assert [sample.outcome for sample in evidence.samples] == ["unknown", "unknown"]
    assert evidence.sequence == 1
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT last_sequence FROM observation_replay").fetchone() == (1,)


def test_unexpected_cleanup_exception_never_persists_evidence(monkeypatch, tmp_path):
    import cloudforge.observation_http as http_module

    class UnexpectedClose:
        def __init__(self, *_args, **_kwargs):
            pass
        def request(self, *_args, **_kwargs):
            pass
        def getresponse(self):
            return type("Response", (), {"status": 204})()
        def close(self):
            raise RuntimeError("unexpected fixture failure")

    monkeypatch.setattr(http_module.http.client, "HTTPConnection", UnexpectedClose)
    ledger = tmp_path / "ledger.db"
    with pytest.raises(RuntimeError, match="unexpected fixture failure"):
        _collect(_context(), _targets(12345), ledger)
    assert not ledger.exists()


def _source_pin(context, key=_KEY):
    return ObservationSourcePin(
        "fixture-collector",
        hashlib.sha256(context[-1].to_json().encode("ascii")).hexdigest(),
        hashlib.sha256(key).hexdigest(),
        _NOW - 20, _NOW + 20,
    )


def test_pinned_source_collects_with_exact_plan_and_key(fixture_server, tmp_path):
    context = _context()
    ledger = tmp_path / "pinned.db"
    evidence = _collect(
        context, _targets(fixture_server), ledger, source_pin=_source_pin(context),
    )
    assert evidence.source_id == "fixture-collector"
    assert len(Handler.calls) == 2
    assert ledger.exists()


@pytest.mark.parametrize("change,settings", [
    (lambda p: replace(p, source_id="other-source"), {}),
    (lambda p: replace(p, plan_sha256="0" * 64), {}),
    (lambda p: replace(p, key_sha256="0" * 64), {}),
    (lambda p: replace(p, key_sha256="G" * 64), {}),
    (lambda p: replace(p, valid_from_unix=True), {}),
    (lambda p: replace(p, valid_until_unix=_NOW - 1), {}),
    (lambda p: replace(p, valid_until_unix=_NOW + 86_401), {}),
    (lambda p: replace(p, valid_from_unix=_NOW + 1), {}),
    (lambda p: p, {"source_key": bytes(range(1, 33))}),
    (lambda p: p, {"observed_at_unix": _NOW - 21}),
    (lambda p: p, {"now_unix": _NOW + 21}),
    (lambda p: "untrusted", {}),
])
def test_invalid_source_pin_rejected_before_network_or_ledger(
    monkeypatch, tmp_path, change, settings,
):
    import cloudforge.observation_http as http_module
    monkeypatch.setattr(
        http_module.http.client, "HTTPConnection",
        lambda *_a, **_kw: pytest.fail("network before source pin verification"),
    )
    context = _context()
    ledger = tmp_path / "pinned.db"
    with pytest.raises(ValueError):
        _collect(
            context, _targets(12345), ledger,
            source_pin=change(_source_pin(context)), **settings,
        )
    assert not ledger.exists()


def test_pinned_source_key_rotation_requires_new_operator_pin(fixture_server, tmp_path):
    context = _context()
    targets = _targets(fixture_server)
    ledger = tmp_path / "rotation.db"
    old_pin = _source_pin(context)
    assert _collect(context, targets, ledger, source_pin=old_pin).sequence == 1
    new_key = bytes(range(1, 33))
    with pytest.raises(ValueError, match="pin mismatch"):
        _collect(context, targets, ledger, source_pin=old_pin,
                 source_key=new_key, sequence=2)
    assert _collect(context, targets, ledger, source_pin=_source_pin(context, new_key),
                    source_key=new_key, sequence=2).sequence == 2
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT last_sequence FROM observation_replay").fetchone() == (2,)
