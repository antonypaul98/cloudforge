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
    {"valid_from_unix": _NOW + 21},
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


# Opt-in synthetic fixture seam: permit preflight must precede any factory call.
from unittest.mock import Mock

from cloudforge.observation_permitted_https_fixture import (
    collect_permitted_pinned_https_fixture_samples,
)


def _permitted_fixture(args, kwargs, permit, factory, **changes):
    policy = {key: kwargs[key] for key in (
        "allowed_ipv4", "allowed_ipv6", "source_id", "source_key",
        "operator_key", "sequence",
    )}
    policy.update(now_unix=_NOW, connection_factory=factory)
    policy.update(changes)
    return collect_permitted_pinned_https_fixture_samples(
        *args, permit, **policy,
    )


def test_permitted_synthetic_head_uses_exact_targets_after_mac_preflight(monkeypatch):
    args, kwargs, permit = _issued()
    def forbidden(*_args, **_kwargs):
        pytest.fail("unexpected real socket in permitted fixture")
    monkeypatch.setattr(socket, "socket", forbidden)
    connection = Mock()
    connection.getresponse.return_value.status = 204
    factory = Mock(return_value=connection)

    samples = _permitted_fixture(args, kwargs, permit, factory)
    assert [(sample.kind, sample.outcome) for sample in samples] == [
        ("readiness", "pass"), ("liveness", "pass"),
    ]
    assert factory.call_count == 2
    assert [call.args[1] for call in factory.call_args_list] == [
        "1.1.1.1", "2606:4700:4700::1111",
    ]
    assert [call.args for call in connection.request.call_args_list] == [
        ("HEAD", "/ready"), ("HEAD", "/live"),
    ]


@pytest.mark.parametrize("mutation", [
    "mac", "expired", "early", "source", "operator_key",
    "sequence", "artifact", "target", "pinset", "allowlist",
])
def test_permitted_fixture_rejects_invalid_policy_before_factory(mutation):
    args, kwargs, permit = _issued()
    args = list(args)
    changes = {}
    if mutation == "mac":
        permit = replace(permit, mac_sha256="0" * 64)
    elif mutation == "expired":
        changes["now_unix"] = _NOW + 21
    elif mutation == "early":
        changes["now_unix"] = _NOW - 11
    elif mutation == "source":
        changes["source_id"] = "collector-other"
    elif mutation == "operator_key":
        changes["operator_key"] = bytes(range(64, 96))
    elif mutation == "sequence":
        changes["sequence"] = 8
    elif mutation == "artifact":
        args[1] = b"changed"
    elif mutation == "target":
        args[5] = (replace(args[5][0], path="/other"), args[5][1])
    elif mutation == "pinset":
        args[9] = replace(args[9], ordered_address_sets_sha256="0" * 64)
    else:
        changes["allowed_ipv4"] = (("8.8.8.8",), ())
    factory = Mock(side_effect=AssertionError("factory invoked before permit check"))
    with pytest.raises((ValueError, PermissionError)):
        _permitted_fixture(tuple(args), kwargs, permit, factory, **changes)
    factory.assert_not_called()


@pytest.mark.parametrize("remaining,accepted", [
    (0, False), (3, False), (4, True), (5, True),
])
def test_synthetic_fixture_requires_permit_window_for_all_probe_timeouts(
    remaining, accepted,
):
    args, kwargs = _context()
    permit = issue_runtime_head_permit(
        *args, **dict(kwargs, valid_until_unix=_NOW + remaining),
    )
    connection = Mock()
    connection.getresponse.return_value.status = 204
    factory = Mock(return_value=connection)
    if accepted:
        samples = _permitted_fixture(args, kwargs, permit, factory)
        assert len(samples) == 2
        assert factory.call_count == 2
    else:
        with pytest.raises(ValueError, match="expires before synthetic probe budget"):
            _permitted_fixture(args, kwargs, permit, factory)
        factory.assert_not_called()


def test_synthetic_fixture_rechecks_remaining_window_at_call_time():
    args, kwargs, permit = _issued()
    factory = Mock(side_effect=AssertionError("expired permit budget reached factory"))
    with pytest.raises(ValueError, match="expires before synthetic probe budget"):
        _permitted_fixture(args, kwargs, permit, factory, now_unix=_NOW + 18)
    factory.assert_not_called()


# Opt-in durable synthetic permit sequence gate: no production trust claims.
import sqlite3
from concurrent.futures import ThreadPoolExecutor


def _consume_fixture(args, kwargs, permit, ledger_path, factory=None):
    connection = Mock()
    connection.getresponse.return_value.status = 204
    if factory is None:
        factory = Mock(return_value=connection)
    samples = _permitted_fixture(
        args, kwargs, permit, factory, permit_ledger_path=str(ledger_path),
    )
    return samples, factory


def test_permit_ledger_rejects_repeat_before_any_factory(tmp_path):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "permit.db"
    samples, factory = _consume_fixture(args, kwargs, permit, ledger)
    assert len(samples) == 2
    assert factory.call_count == 2
    denied = Mock(side_effect=AssertionError("replayed permit reached factory"))
    with pytest.raises(ValueError, match="already consumed"):
        _consume_fixture(args, kwargs, permit, ledger, denied)
    denied.assert_not_called()


def test_permit_ledger_survives_reopen_and_requires_increasing_sequence(tmp_path):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "permit.db"
    _consume_fixture(args, kwargs, permit, ledger)
    permit8 = issue_runtime_head_permit(*args, **dict(kwargs, sequence=8))
    _consume_fixture(args, dict(kwargs, sequence=8), permit8, ledger)
    denied = Mock(side_effect=AssertionError("old permit reached factory"))
    with pytest.raises(ValueError, match="already consumed"):
        _consume_fixture(args, kwargs, permit, ledger, denied)
    denied.assert_not_called()


def test_rotating_source_key_does_not_reset_permit_sequence(tmp_path):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "permit.db"
    _consume_fixture(args, kwargs, permit, ledger)
    rotated = dict(kwargs, source_key=bytes(range(33, 65)))
    rotated7 = issue_runtime_head_permit(*args, **rotated)
    denied = Mock(side_effect=AssertionError("rotated duplicate reached factory"))
    with pytest.raises(ValueError, match="already consumed"):
        _consume_fixture(args, rotated, rotated7, ledger, denied)
    denied.assert_not_called()
    rotated8 = issue_runtime_head_permit(*args, **dict(rotated, sequence=8))
    _consume_fixture(args, dict(rotated, sequence=8), rotated8, ledger)


def test_invalid_mac_rejected_before_ledger_creation(tmp_path):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "new.db"
    denied = Mock(side_effect=AssertionError("invalid MAC reached factory"))
    with pytest.raises(ValueError):
        _consume_fixture(args, kwargs, replace(permit, mac_sha256="0" * 64),
                         ledger, denied)
    denied.assert_not_called()
    assert not ledger.exists()


@pytest.mark.parametrize("bad_path", ["relative.db", "", None])
def test_invalid_permit_ledger_path_fails_before_factory(tmp_path, bad_path):
    args, kwargs, permit = _issued()
    if bad_path is None:
        bad_path = str(tmp_path)  # existing directory, not a regular ledger
    denied = Mock(side_effect=AssertionError("bad path reached factory"))
    with pytest.raises(ValueError):
        _consume_fixture(args, kwargs, permit, bad_path, denied)
    denied.assert_not_called()


def test_permit_ledger_rejects_modified_schema_and_triggers(tmp_path):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "permit.db"
    with sqlite3.connect(ledger) as db:
        db.execute(
            "CREATE TABLE runtime_permit_use "
            "(source_id TEXT, runtime_request_sha256 TEXT, last_sequence TEXT)"
        )
    denied = Mock(side_effect=AssertionError("bad schema reached factory"))
    with pytest.raises(ValueError, match="schema mismatch"):
        _consume_fixture(args, kwargs, permit, ledger, denied)
    denied.assert_not_called()


def test_two_concurrent_consumers_accept_at_most_one(tmp_path):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "permit.db"
    def attempt():
        try:
            _consume_fixture(args, kwargs, permit, ledger)
            return True
        except ValueError as exc:
            assert "already consumed" in str(exc)
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results) == [False, True]


def test_failed_fake_probe_still_consumes_permit(tmp_path):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "permit.db"
    failing = Mock(side_effect=OSError("synthetic fixture unavailable"))
    samples, _ = _consume_fixture(args, kwargs, permit, ledger, failing)
    assert [s.outcome for s in samples] == ["unknown", "unknown"]
    denied = Mock(side_effect=AssertionError("reused failed permit"))
    with pytest.raises(ValueError, match="already consumed"):
        _consume_fixture(args, kwargs, permit, ledger, denied)
    denied.assert_not_called()


def test_permit_ledger_rejects_symlink_without_touching_target(tmp_path):
    args, kwargs, permit = _issued()
    target = tmp_path / "target.db"
    link = tmp_path / "alias.db"
    link.symlink_to(target)
    denied = Mock(side_effect=AssertionError("alias reached factory"))
    with pytest.raises(ValueError):
        _consume_fixture(args, kwargs, permit, link, denied)
    denied.assert_not_called()
    assert not target.exists()


# Synthetic permitted HTTPS HEAD -> signed HMAC -> durable evidence replay.
from cloudforge.observation_evidence import verify_observation_evidence
from cloudforge.observation_permitted_https_intake import (
    collect_and_accept_permitted_pinned_https_fixture_evidence,
)


def _signed_https_fixture(args, kwargs, permit, ledger, factory=None, **changes):
    if factory is None:
        conn = Mock()
        conn.getresponse.return_value.status = 204
        factory = Mock(return_value=conn)
    policy = {key: kwargs[key] for key in (
        "allowed_ipv4", "allowed_ipv6", "source_id", "source_key",
        "operator_key", "sequence",
    )}
    policy.update(
        observed_at_unix=_NOW, now_unix=_NOW, max_age_seconds=30,
        ledger_path=str(ledger), connection_factory=factory,
    )
    policy.update(changes)
    return collect_and_accept_permitted_pinned_https_fixture_evidence(
        *args, permit, **policy,
    )


def test_signed_https_fixture_persists_permit_and_evidence_in_one_ledger(tmp_path):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "shared.db"
    evidence = _signed_https_fixture(args, kwargs, permit, ledger)
    assert [(s.kind, s.outcome) for s in evidence.samples] == [
        ("readiness", "pass"), ("liveness", "pass"),
    ]
    assert verify_observation_evidence(
        *args[:5], evidence, expected_source_id=kwargs["source_id"],
        source_key=kwargs["source_key"], now_unix=_NOW,
        max_age_seconds=30, last_sequence=0,
    )
    with sqlite3.connect(ledger) as db:
        assert db.execute(
            "SELECT last_sequence FROM runtime_permit_use"
        ).fetchone() == (7,)
        assert db.execute(
            "SELECT last_sequence FROM observation_replay"
        ).fetchone() == (7,)
    exported = evidence.to_json()
    assert str(ledger) not in exported
    assert "synthetic-runtime-permit" not in exported
    assert kwargs["source_key"].hex() not in exported


def test_signed_https_duplicate_rejected_before_any_fake_head(tmp_path):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "shared.db"
    _signed_https_fixture(args, kwargs, permit, ledger)
    denied = Mock(side_effect=AssertionError("replayed HEAD reached factory"))
    with pytest.raises(ValueError, match="already accepted"):
        _signed_https_fixture(args, kwargs, permit, ledger, denied)
    denied.assert_not_called()


@pytest.mark.parametrize("mutation", ["mac", "stale", "future", "budget", "path"])
def test_signed_https_invalid_context_rejected_before_ledger_or_head(
    tmp_path, mutation,
):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "shared.db"
    changes = {}
    if mutation == "mac":
        permit = replace(permit, mac_sha256="0" * 64)
    elif mutation == "stale":
        changes["observed_at_unix"] = _NOW - 31
    elif mutation == "future":
        changes["observed_at_unix"] = _NOW + 1
    elif mutation == "budget":
        changes["now_unix"] = _NOW + 18
    else:
        changes["ledger_path"] = "relative.db"
    denied = Mock(side_effect=AssertionError("invalid context reached factory"))
    with pytest.raises(ValueError):
        _signed_https_fixture(args, kwargs, permit, ledger, denied, **changes)
    denied.assert_not_called()
    assert not ledger.exists()


def test_signed_https_unknown_probe_is_not_forged_as_pass(tmp_path):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "shared.db"
    failed = Mock(side_effect=OSError("fixture transport failure"))
    evidence = _signed_https_fixture(args, kwargs, permit, ledger, failed)
    assert [s.outcome for s in evidence.samples] == ["unknown", "unknown"]
    with sqlite3.connect(ledger) as db:
        assert db.execute(
            "SELECT last_sequence FROM runtime_permit_use"
        ).fetchone() == (7,)
        assert db.execute(
            "SELECT last_sequence FROM observation_replay"
        ).fetchone() == (7,)


def test_signed_https_rejects_corrupt_evidence_schema_before_head(tmp_path):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "shared.db"
    with sqlite3.connect(ledger) as db:
        db.execute("CREATE TABLE observation_replay (last_sequence TEXT)")
    denied = Mock(side_effect=AssertionError("corrupt ledger reached factory"))
    with pytest.raises(ValueError, match="schema mismatch"):
        _signed_https_fixture(args, kwargs, permit, ledger, denied)
    denied.assert_not_called()
    with sqlite3.connect(ledger) as db:
        assert db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='runtime_permit_use'"
        ).fetchone() is None


def test_signed_https_concurrent_duplicate_admits_one_fixture(tmp_path):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "shared.db"
    conn = Mock()
    conn.getresponse.return_value.status = 204
    factory = Mock(return_value=conn)
    def attempt():
        try:
            _signed_https_fixture(args, kwargs, permit, ledger, factory)
            return True
        except ValueError as exc:
            assert "already consumed" in str(exc) or "already accepted" in str(exc)
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results) == [False, True]
    assert factory.call_count == 2


def test_signed_https_next_sequence_reuses_same_ledger(tmp_path):
    args, kwargs, permit = _issued()
    ledger = tmp_path / "shared.db"
    _signed_https_fixture(args, kwargs, permit, ledger)
    next_kwargs = dict(kwargs, sequence=8)
    next_permit = issue_runtime_head_permit(*args, **next_kwargs)
    evidence = _signed_https_fixture(args, next_kwargs, next_permit, ledger)
    assert evidence.sequence == 8
    with sqlite3.connect(ledger) as db:
        assert db.execute(
            "SELECT last_sequence FROM runtime_permit_use"
        ).fetchone() == (8,)
        assert db.execute(
            "SELECT last_sequence FROM observation_replay"
        ).fetchone() == (8,)
