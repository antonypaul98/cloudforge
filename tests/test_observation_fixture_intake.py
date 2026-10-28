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


def test_duplicate_sequence_fails_closed_before_head(fixture_server, tmp_path):
    context = _context()
    targets = _targets(fixture_server)
    path = tmp_path / "replay.sqlite3"
    _collect(context, targets, path)
    with pytest.raises(ValueError, match="already accepted"):
        _collect(context, targets, path)
    assert len(Handler.calls) == 2  # Known duplicate skips HTTP.
    assert _collect(context, targets, path, sequence=2).sequence == 2
    assert len(Handler.calls) == 4  # New sequence still probes.
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


def test_strict_source_pin_policy_allows_valid_fixture(fixture_server, tmp_path):
    context = _context()
    ledger = tmp_path / "strict.db"
    evidence = _collect(
        context, _targets(fixture_server), ledger,
        source_pin=_source_pin(context), require_source_pin=True,
        revoked_key_sha256=("0" * 64,),
    )
    assert evidence.sequence == 1
    assert len(Handler.calls) == 2
    assert ledger.exists()


@pytest.mark.parametrize("policy", [
    {"require_source_pin": True},
    {"revoked_key_sha256": (hashlib.sha256(_KEY).hexdigest(),)},
])
def test_policy_cannot_be_enabled_without_pin_before_io(
    monkeypatch, tmp_path, policy,
):
    import cloudforge.observation_http as http_module
    monkeypatch.setattr(
        http_module.http.client, "HTTPConnection",
        lambda *_a, **_kw: pytest.fail("network before policy"),
    )
    ledger = tmp_path / "no-pin.db"
    with pytest.raises(ValueError, match="pin required"):
        _collect(_context(), _targets(12345), ledger, **policy)
    assert not ledger.exists()


def test_revoked_key_rejected_before_network_or_ledger(monkeypatch, tmp_path):
    import cloudforge.observation_http as http_module
    monkeypatch.setattr(
        http_module.http.client, "HTTPConnection",
        lambda *_a, **_kw: pytest.fail("network before revocation check"),
    )
    context = _context()
    ledger = tmp_path / "revoked.db"
    with pytest.raises(ValueError, match="key is revoked"):
        _collect(
            context, _targets(12345), ledger,
            source_pin=_source_pin(context), require_source_pin=True,
            revoked_key_sha256=(hashlib.sha256(_KEY).hexdigest(),),
        )
    assert not ledger.exists()


@pytest.mark.parametrize("policy", [
    {"require_source_pin": 1},
    {"require_source_pin": None},
    {"revoked_key_sha256": ["0" * 64]},
    {"revoked_key_sha256": ("A" * 64,)},
    {"revoked_key_sha256": ("g" * 64,)},
    {"revoked_key_sha256": (None,)},
    {"revoked_key_sha256": ("0" * 64, "0" * 64)},
    {"revoked_key_sha256": ("0" * 64,) * 65},
])
def test_malformed_source_policy_fails_before_io(monkeypatch, tmp_path, policy):
    import cloudforge.observation_http as http_module
    monkeypatch.setattr(
        http_module.http.client, "HTTPConnection",
        lambda *_a, **_kw: pytest.fail("network before policy validation"),
    )
    context = _context()
    ledger = tmp_path / "bad-policy.db"
    with pytest.raises(ValueError, match="invalid observation source trust policy"):
        _collect(
            context, _targets(12345), ledger,
            source_pin=_source_pin(context), **policy,
        )
    assert not ledger.exists()


def test_revoked_old_key_rotation_preserves_sequence(fixture_server, tmp_path):
    context = _context()
    targets = _targets(fixture_server)
    ledger = tmp_path / "revocation-rotation.db"
    assert _collect(
        context, targets, ledger, source_pin=_source_pin(context),
        require_source_pin=True,
    ).sequence == 1
    old_digest = hashlib.sha256(_KEY).hexdigest()
    with pytest.raises(ValueError, match="key is revoked"):
        _collect(
            context, targets, ledger, source_pin=_source_pin(context),
            require_source_pin=True, revoked_key_sha256=(old_digest,),
            sequence=2,
        )
    new_key = bytes(range(1, 33))
    evidence = _collect(
        context, targets, ledger, source_pin=_source_pin(context, new_key),
        source_key=new_key, require_source_pin=True,
        revoked_key_sha256=(old_digest,), sequence=2,
    )
    assert evidence.sequence == 2
    assert old_digest not in evidence.to_json()
    with sqlite3.connect(ledger) as db:
        assert db.execute(
            "SELECT last_sequence FROM observation_replay"
        ).fetchone() == (2,)


@pytest.mark.parametrize("unsafe_kind", [
    "file_symlink", "parent_symlink", "hardlink", "noncanonical", "missing_parent",
])
def test_unsafe_ledger_rejected_before_head_or_sqlite(
    monkeypatch, tmp_path, unsafe_kind,
):
    """Known unsafe ledger paths must not trigger a probe request."""
    import os
    import cloudforge.observation_http as http_module

    monkeypatch.setattr(
        http_module.http.client, "HTTPConnection",
        lambda *_a, **_kw: pytest.fail("HEAD attempted before ledger path preflight"),
    )
    target = tmp_path / "original.db"
    target.write_bytes(b"sentinel-not-a-database")
    if unsafe_kind == "file_symlink":
        ledger = tmp_path / "alias.db"
        ledger.symlink_to(target)
    elif unsafe_kind == "parent_symlink":
        real_parent = tmp_path / "real-parent"
        real_parent.mkdir()
        alias_parent = tmp_path / "alias-parent"
        alias_parent.symlink_to(real_parent, target_is_directory=True)
        ledger = alias_parent / "ledger.db"
    elif unsafe_kind == "hardlink":
        ledger = tmp_path / "hardlink.db"
        os.link(target, ledger)
    elif unsafe_kind == "noncanonical":
        ledger = str(tmp_path / "unused" / ".." / "ledger.db")
    else:
        ledger = tmp_path / "missing-parent" / "ledger.db"
    with pytest.raises(ValueError, match="replay ledger"):
        _collect(_context(), _targets(12345), tmp_path / "unused.db",
                 ledger_path=str(ledger))
    assert target.read_bytes() == b"sentinel-not-a-database"
    assert not (tmp_path / "unused.db").exists()

def test_corrupt_existing_ledger_rejected_before_head(monkeypatch, tmp_path):
    import cloudforge.observation_http as http_module
    monkeypatch.setattr(http_module.http.client, "HTTPConnection",
                        lambda *_a, **_kw: pytest.fail("HEAD before corrupt DB check"))
    ledger = tmp_path / "corrupt.db"
    ledger.write_bytes(b"not-a-sqlite-database")
    with pytest.raises(ValueError, match="durable replay ledger unavailable"):
        _collect(_context(), _targets(12345), ledger)
    assert ledger.read_bytes() == b"not-a-sqlite-database"


def test_corrupt_counter_rejected_before_head(monkeypatch, fixture_server, tmp_path):
    context, ledger = _context(), tmp_path / "counter.db"
    targets = _targets(fixture_server)
    _collect(context, targets, ledger)
    with sqlite3.connect(ledger) as db:
        db.execute("PRAGMA ignore_check_constraints = ON")
        db.execute("UPDATE observation_replay SET last_sequence = 'bad-counter'")
    import cloudforge.observation_http as http_module
    monkeypatch.setattr(http_module.http.client, "HTTPConnection",
                        lambda *_a, **_kw: pytest.fail("HEAD before counter check"))
    with pytest.raises(ValueError, match="counter invalid"):
        _collect(context, targets, ledger, sequence=2)
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT last_sequence FROM observation_replay").fetchone() == ("bad-counter",)


def test_altered_schema_rejected_before_head(monkeypatch, tmp_path):
    import cloudforge.observation_http as http_module
    monkeypatch.setattr(http_module.http.client, "HTTPConnection",
                        lambda *_a, **_kw: pytest.fail("HEAD before schema check"))
    ledger = tmp_path / "wrong-schema.db"
    with sqlite3.connect(ledger) as db:
        db.execute("CREATE TABLE observation_replay (last_sequence TEXT)")
    with pytest.raises(ValueError, match="schema mismatch"):
        _collect(_context(), _targets(12345), ledger)


def test_existing_empty_sqlite_ledger_initializes(fixture_server, tmp_path):
    ledger = tmp_path / "empty.db"
    with sqlite3.connect(ledger):
        pass
    assert _collect(_context(), _targets(fixture_server), ledger).sequence == 1
    assert len(Handler.calls) == 2
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT last_sequence FROM observation_replay").fetchone() == (1,)


def test_uri_reserved_characters_in_ledger_filename(fixture_server, tmp_path):
    ledger = tmp_path / "replay ?#%.sqlite3"
    context, targets = _context(), _targets(fixture_server)
    assert _collect(context, targets, ledger).sequence == 1
    with pytest.raises(ValueError, match="already accepted"):
        _collect(context, targets, ledger)
    assert len(Handler.calls) == 2
    assert _collect(context, targets, ledger, sequence=2).sequence == 2
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT last_sequence FROM observation_replay").fetchone() == (2,)


def test_over_budget_head_is_signed_as_unknown_not_pass(monkeypatch, tmp_path):
    """The integrated HMAC/SQLite path must not preserve an overdue 204 pass."""
    import cloudforge.observation_http as module

    class Slow204:
        def __init__(self, *_args, **_kwargs):
            pass
        def request(self, method, path, headers):
            assert method == "HEAD" and path == "/ok"
        def getresponse(self):
            return type("Response", (), {"status": 204})()
        def close(self):
            pass

    context = _context()
    ledger = tmp_path / "slow-head.db"
    times = iter((100.0, 103.0, 200.0, 203.0))
    with monkeypatch.context() as patch:
        patch.setattr(module.http.client, "HTTPConnection", Slow204)
        patch.setattr(module.time, "monotonic", lambda: next(times))
        evidence = _collect(context, _targets(12345), ledger)
    assert [sample.outcome for sample in evidence.samples] == ["unknown", "unknown"]
    assert verify_observation_evidence(
        *context, evidence, expected_source_id="fixture-collector",
        source_key=_KEY, now_unix=_NOW, max_age_seconds=30, last_sequence=0,
    )
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT last_sequence FROM observation_replay").fetchone() == (1,)


# A distinct, short-lived operator permit binds the exact loopback HEAD targets
# before any HTTP or SQLite activity. These tests do not authenticate a person.
from cloudforge.observation_operator_permit import (
    issue_loopback_operator_permit, verify_loopback_operator_permit,
)
from cloudforge.observation_fixture_intake import (
    collect_and_accept_operator_permitted_loopback_fixture_evidence,
)

_OPERATOR_KEY = bytes(range(32, 64))


def _operator_permit(context, targets):
    return issue_loopback_operator_permit(
        context[-1], targets, source_id="fixture-collector",
        source_key=_KEY, operator_key=_OPERATOR_KEY,
        valid_from_unix=_NOW - 30, valid_until_unix=_NOW + 30,
    )


def _permitted_collect(context, targets, ledger, permit, **changes):
    settings = dict(
        allowed_targets=targets, operator_permit=permit,
        operator_key=_OPERATOR_KEY, source_id="fixture-collector",
        source_key=_KEY, observed_at_unix=1_800_000_000,
        now_unix=_NOW, sequence=1, max_age_seconds=30,
        ledger_path=str(ledger),
    )
    settings.update(changes)
    return collect_and_accept_operator_permitted_loopback_fixture_evidence(
        *context, targets, **settings,
    )


def test_distinct_operator_permit_allows_exact_fixture_only(fixture_server, tmp_path):
    context = _context()
    targets = _targets(fixture_server)
    permit = _operator_permit(context, targets)
    ledger = tmp_path / "operator.db"
    evidence = _permitted_collect(context, targets, ledger, permit)
    assert evidence.sequence == 1
    assert [s.outcome for s in evidence.samples] == ["pass", "pass"]
    assert Handler.calls == [("HEAD", "/ok"), ("HEAD", "/ok")]
    assert ledger.exists()
    assert _OPERATOR_KEY.hex() not in evidence.to_json()
    assert verify_loopback_operator_permit(
        context[-1], targets, permit, source_id="fixture-collector",
        source_key=_KEY, operator_key=_OPERATOR_KEY,
        observed_at_unix=1_800_000_000, now_unix=_NOW,
    )


@pytest.mark.parametrize("mutation", [
    lambda p: replace(p, plan_sha256="0" * 64),
    lambda p: replace(p, targets_sha256="0" * 64),
    lambda p: replace(p, source_key_sha256="0" * 64),
    lambda p: replace(p, source_id="other"),
    lambda p: replace(p, mac_sha256="0" * 64),
    lambda p: replace(p, format_version=True),
    lambda p: replace(p, valid_until_unix=_NOW - 1),
    lambda p: replace(p, valid_until_unix=_NOW + 301),
    lambda p: "forged",
])
def test_operator_permit_tampering_fails_before_network_or_ledger(
    monkeypatch, tmp_path, mutation,
):
    import cloudforge.observation_http as module
    monkeypatch.setattr(
        module.http.client, "HTTPConnection",
        lambda *_a, **_kw: pytest.fail("network before operator permit"),
    )
    context, targets = _context(), _targets(12345)
    ledger = tmp_path / "no-permit.db"
    with pytest.raises(ValueError):
        _permitted_collect(context, targets, ledger,
                           mutation(_operator_permit(context, targets)))
    assert not ledger.exists()


@pytest.mark.parametrize("change", [
    {"operator_key": bytes(range(1, 33))},
    {"source_key": bytes(range(1, 33))},
    {"now_unix": _NOW + 31},
    {"observed_at_unix": _NOW - 31},
    {"operator_key": _KEY},
    {"operator_key": None},
])
def test_operator_permit_context_rejected_before_network_or_ledger(
    monkeypatch, tmp_path, change,
):
    import cloudforge.observation_http as module
    monkeypatch.setattr(
        module.http.client, "HTTPConnection",
        lambda *_a, **_kw: pytest.fail("network before operator context"),
    )
    context, targets = _context(), _targets(12345)
    ledger = tmp_path / "bad-context.db"
    with pytest.raises(ValueError):
        _permitted_collect(context, targets, ledger,
                           _operator_permit(context, targets), **change)
    assert not ledger.exists()


def test_operator_permit_cannot_be_reused_for_another_allowed_target(monkeypatch, tmp_path):
    import cloudforge.observation_http as module
    monkeypatch.setattr(
        module.http.client, "HTTPConnection",
        lambda *_a, **_kw: pytest.fail("network before target binding"),
    )
    context, targets = _context(), _targets(12345)
    different = _targets(12346)
    ledger = tmp_path / "changed-target.db"
    with pytest.raises(ValueError, match="operator permit mismatch"):
        _permitted_collect(context, different, ledger,
                           _operator_permit(context, targets))
    assert not ledger.exists()


@pytest.mark.parametrize("window", [
    (_NOW, _NOW),
    (True, _NOW + 1),
    (_NOW - 1, True),
    (_NOW - 301, _NOW + 1),
])
def test_operator_permit_issuance_rejects_invalid_windows(window):
    context, targets = _context(), _targets(12345)
    with pytest.raises(ValueError, match="validity window"):
        issue_loopback_operator_permit(
            context[-1], targets, source_id="fixture-collector",
            source_key=_KEY, operator_key=_OPERATOR_KEY,
            valid_from_unix=window[0], valid_until_unix=window[1],
        )


def test_operator_permit_issuance_rejects_same_role_key():
    context, targets = _context(), _targets(12345)
    with pytest.raises(ValueError, match="distinct"):
        issue_loopback_operator_permit(
            context[-1], targets, source_id="fixture-collector",
            source_key=_KEY, operator_key=_KEY,
            valid_from_unix=_NOW - 30, valid_until_unix=_NOW + 30,
        )


# V2 permits are opt-in, scoped to one ledger path and sequence.
def _one_shot_permit(context, targets, ledger, sequence=1):
    return issue_loopback_operator_permit(
        context[-1], targets, source_id="fixture-collector",
        source_key=_KEY, operator_key=_OPERATOR_KEY,
        valid_from_unix=_NOW - 30, valid_until_unix=_NOW + 30,
        ledger_path=str(ledger), sequence=sequence,
    )


def test_scoped_operator_permit_exact_fixture(fixture_server, tmp_path):
    context, targets = _context(), _targets(fixture_server)
    ledger = tmp_path / "one-shot.db"
    permit = _one_shot_permit(context, targets, ledger)
    assert permit.format_version == 2
    assert permit.ledger_path_sha256 == hashlib.sha256(str(ledger).encode()).hexdigest()
    assert permit.sequence == 1
    evidence = _permitted_collect(
        context, targets, ledger, permit, require_one_shot_permit=True,
    )
    assert evidence.sequence == 1
    assert len(Handler.calls) == 2
    assert str(ledger) not in str(permit)
    assert _OPERATOR_KEY.hex() not in evidence.to_json()
    with pytest.raises(ValueError, match="already accepted"):
        _permitted_collect(
            context, targets, ledger, permit, require_one_shot_permit=True,
        )
    assert len(Handler.calls) == 2


@pytest.mark.parametrize("change", [
    {"sequence": 2},
    {"ledger_path": "different"},
    {"sequence": True},
])
def test_scoped_permit_rejects_changed_scope_before_io(monkeypatch, tmp_path, change):
    import cloudforge.observation_http as module
    monkeypatch.setattr(
        module.http.client, "HTTPConnection",
        lambda *_a, **_kw: pytest.fail("HEAD before scope verification"),
    )
    context, targets = _context(), _targets(12345)
    ledger = tmp_path / "original.db"
    permit = _one_shot_permit(context, targets, ledger)
    if change.get("ledger_path") == "different":
        change = {"ledger_path": str(tmp_path / "different.db")}
    with pytest.raises(ValueError):
        _permitted_collect(
            context, targets, ledger, permit,
            require_one_shot_permit=True, **change,
        )
    assert not ledger.exists()
    assert not (tmp_path / "different.db").exists()


@pytest.mark.parametrize("change", [
    {"ledger_path_sha256": "0" * 64},
    {"sequence": 2},
    {"sequence": True},
    {"format_version": 1},
    {"ledger_path_sha256": None},
])
def test_scoped_permit_rejects_tampering_before_io(monkeypatch, tmp_path, change):
    import cloudforge.observation_http as module
    monkeypatch.setattr(
        module.http.client, "HTTPConnection",
        lambda *_a, **_kw: pytest.fail("HEAD before scoped MAC verification"),
    )
    context, targets = _context(), _targets(12345)
    ledger = tmp_path / "tampered.db"
    permit = replace(_one_shot_permit(context, targets, ledger), **change)
    with pytest.raises(ValueError):
        _permitted_collect(
            context, targets, ledger, permit, require_one_shot_permit=True,
        )
    assert not ledger.exists()


def test_strict_scope_rejects_legacy_v1_before_io(monkeypatch, tmp_path):
    import cloudforge.observation_http as module
    monkeypatch.setattr(
        module.http.client, "HTTPConnection",
        lambda *_a, **_kw: pytest.fail("HEAD before strict scope"),
    )
    context, targets = _context(), _targets(12345)
    ledger = tmp_path / "legacy.db"
    with pytest.raises(ValueError, match="scoped operator permit required"):
        _permitted_collect(
            context, targets, ledger, _operator_permit(context, targets),
            require_one_shot_permit=True,
        )
    assert not ledger.exists()


@pytest.mark.parametrize("ledger,seq", [
    ("relative.db", 1),
    ("/tmp/../tmp/ledger.db", 1),
    ("/tmp/ledger.db", 0),
    ("/tmp/ledger.db", True),
    ("/tmp/ledger.db", (1 << 63)),
    ("/tmp/ledger.db", None),
    (None, 1),
    ("/" + "a" * 4097, 1),
])
def test_scoped_issuance_rejects_invalid_scope(ledger, seq):
    context, targets = _context(), _targets(12345)
    with pytest.raises(ValueError, match="scoped operator permit"):
        issue_loopback_operator_permit(
            context[-1], targets, source_id="fixture-collector",
            source_key=_KEY, operator_key=_OPERATOR_KEY,
            valid_from_unix=_NOW - 30, valid_until_unix=_NOW + 30,
            ledger_path=ledger, sequence=seq,
        )


def test_scoped_verification_requires_expected_scope(tmp_path):
    context, targets = _context(), _targets(12345)
    ledger = tmp_path / "verify.db"
    permit = _one_shot_permit(context, targets, ledger)
    kwargs = dict(
        source_id="fixture-collector", source_key=_KEY,
        operator_key=_OPERATOR_KEY, observed_at_unix=1_800_000_000,
        now_unix=_NOW,
    )
    with pytest.raises(ValueError, match="scoped operator permit"):
        verify_loopback_operator_permit(context[-1], targets, permit, **kwargs)
    assert verify_loopback_operator_permit(
        context[-1], targets, permit, ledger_path=str(ledger),
        sequence=1, require_one_shot=True, **kwargs,
    )
