"""Read-only synthetic replay-gap diagnostics; no network or live services."""
import hashlib
import socket
import sqlite3

import pytest

from cloudforge.observation_permit_replay import _SCHEMA as PERMIT_SCHEMA
from cloudforge.observation_replay import _SCHEMA as EVIDENCE_SCHEMA
from cloudforge.observation_replay_diagnostics import inspect_synthetic_https_replay_gap

_SOURCE = "collector-1"
_REQUEST = "a" * 64
_PLAN = "b" * 64


def _inspect(path, **overrides):
    values = dict(source_id=_SOURCE, runtime_request_sha256=_REQUEST,
                  plan_sha256=_PLAN)
    values.update(overrides)
    return inspect_synthetic_https_replay_gap(str(path), **values)


def _ledger(path, *, permit=None, evidence=None, permit_table=True, evidence_table=True):
    with sqlite3.connect(path) as db:
        if permit_table:
            db.execute(PERMIT_SCHEMA)
        if evidence_table:
            db.execute(EVIDENCE_SCHEMA)
        if permit is not None:
            db.execute("INSERT INTO runtime_permit_use VALUES (?, ?, ?)",
                       (_SOURCE, _REQUEST, permit))
        if evidence is not None:
            db.execute("INSERT INTO observation_replay VALUES (?, ?, ?)",
                       (_PLAN, _SOURCE, evidence))


@pytest.mark.parametrize("permit,evidence,expected", [
    (7, None, True), (7, 6, True), (7, 7, False),
    (7, 8, False), (None, 8, False),
])
def test_read_only_gap_signal_is_conservative(tmp_path, permit, evidence, expected):
    path = tmp_path / "ledger.db"
    _ledger(path, permit=permit, evidence=evidence)
    original = hashlib.sha256(path.read_bytes()).digest()
    result = _inspect(path)
    assert result.permit_sequence == (permit or 0)
    assert result.evidence_sequence == (evidence or 0)
    assert result.permit_ahead is expected
    assert hashlib.sha256(path.read_bytes()).digest() == original


def test_crash_after_permit_before_evidence_table_is_detected(tmp_path):
    path = tmp_path / "ledger.db"
    _ledger(path, permit=7, evidence_table=False)
    assert _inspect(path).permit_ahead is True
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name = 'observation_replay'").fetchone() is None


def test_missing_or_empty_ledger_is_not_misreported_as_healthy(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(ValueError, match="unavailable"):
        _inspect(missing)
    assert not missing.exists()
    empty = tmp_path / "empty.db"
    with sqlite3.connect(empty):
        pass
    with pytest.raises(ValueError, match="no recognized tables"):
        _inspect(empty)


@pytest.mark.parametrize("changed", ["source_id", "runtime_request_sha256", "plan_sha256"])
def test_invalid_identity_rejected_before_file_access(tmp_path, changed):
    path = tmp_path / "missing.db"
    with pytest.raises(ValueError, match="identity"):
        _inspect(path, **{changed: "INVALID!"})
    assert not path.exists()


@pytest.mark.parametrize("table", ["permit", "evidence"])
def test_altered_schema_rejected_without_write(tmp_path, table):
    path = tmp_path / "ledger.db"
    _ledger(path, permit=(7 if table != "permit" else None),
            evidence=(7 if table != "evidence" else None),
            permit_table=(table != "permit"), evidence_table=(table != "evidence"))
    with sqlite3.connect(path) as db:
        if table == "permit":
            db.execute("CREATE TABLE runtime_permit_use (source_id TEXT, runtime_request_sha256 TEXT, last_sequence TEXT)")
        else:
            db.execute("CREATE TABLE observation_replay (plan_sha256 TEXT, source_id TEXT, last_sequence TEXT)")
    with pytest.raises(ValueError, match="schema mismatch"):
        _inspect(path)


def test_unexpected_trigger_rejected(tmp_path):
    path = tmp_path / "ledger.db"
    _ledger(path, permit=7, evidence=7)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TRIGGER t AFTER INSERT ON runtime_permit_use BEGIN SELECT 1; END")
    with pytest.raises(ValueError, match="schema mismatch"):
        _inspect(path)


def test_corrupt_counter_rejected(tmp_path):
    path = tmp_path / "ledger.db"
    _ledger(path, evidence=6)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA ignore_check_constraints = ON")
        db.execute("INSERT INTO runtime_permit_use VALUES (?, ?, ?)",
                   (_SOURCE, _REQUEST, "corrupt"))
    with pytest.raises(ValueError, match="counter invalid"):
        _inspect(path)


def test_symlink_alias_rejected_without_modifying_target(tmp_path):
    path = tmp_path / "ledger.db"
    _ledger(path, permit=7)
    alias = tmp_path / "alias.db"
    alias.symlink_to(path)
    with pytest.raises(ValueError, match="regular file"):
        _inspect(alias)
    assert _inspect(path).permit_sequence == 7


def test_no_network_access_during_diagnosis(tmp_path, monkeypatch):
    path = tmp_path / "ledger.db"
    _ledger(path, permit=7)
    monkeypatch.setattr(socket, "socket", lambda *_a, **_kw: pytest.fail("network used"))
    assert _inspect(path).permit_ahead
