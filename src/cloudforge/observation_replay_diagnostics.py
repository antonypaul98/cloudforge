"""Read-only diagnosis of synthetic HTTPS permit/evidence replay counters.

This cannot prove an individual request executed, that evidence is authentic,
or that a caller-controlled SQLite ledger is trusted. No retry or recovery is
performed; a consumed permit must never be reset by this diagnostic.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from urllib.parse import quote

from .observation_evidence import _SOURCE_RE, _hex_digest
from .observation_permit_replay import _verify_schema as _verify_permit_schema
from .observation_replay import (
    _verify_replay_ledger_path, _verify_replay_schema,
)

_MAX_SEQUENCE = (1 << 63) - 1


@dataclass(frozen=True)
class SyntheticReplayGap:
    permit_sequence: int
    evidence_sequence: int
    permit_ahead: bool


def _counter(db: sqlite3.Connection, table: str, keys: tuple[str, str]) -> int:
    # Table names are fixed literals, never supplied by the caller.
    if table == "runtime_permit_use":
        query = ("SELECT last_sequence FROM runtime_permit_use "
                 "WHERE source_id = ? AND runtime_request_sha256 = ?")
        _verify = _verify_permit_schema
    else:
        query = ("SELECT last_sequence FROM observation_replay "
                 "WHERE plan_sha256 = ? AND source_id = ?")
        _verify = _verify_replay_schema
    entry = db.execute("SELECT type FROM sqlite_master WHERE name = ?", (table,)).fetchone()
    if entry is None:
        return 0
    if entry[0] != "table":
        raise ValueError("synthetic replay ledger schema mismatch")
    _verify(db)
    row = db.execute(query, keys).fetchone()
    if row is None:
        return 0
    value = row[0]
    if type(value) is not int or not 1 <= value <= _MAX_SEQUENCE:
        raise ValueError("synthetic replay ledger counter invalid")
    return value


def inspect_synthetic_https_replay_gap(
    ledger_path: str,
    *,
    source_id: str,
    runtime_request_sha256: str,
    plan_sha256: str,
) -> SyntheticReplayGap:
    """Inspect two counters without writing, consuming permits or probing.

    permit_ahead is a possible missing-evidence signal, not proof of a
    specific probe or signed evidence. The counters have different key scopes:
    (source, request) versus (plan, source), so even equality is inconclusive.
    Missing ledger, altered schema, unsafe path or corrupt counter fails closed.
    """
    if (type(source_id) is not str or _SOURCE_RE.fullmatch(source_id) is None
            or not _hex_digest(runtime_request_sha256)
            or not _hex_digest(plan_sha256)):
        raise ValueError("invalid synthetic replay diagnostic identity")
    _verify_replay_ledger_path(ledger_path)
    uri = "file:" + quote(ledger_path, safe="/") + "?mode=ro"
    try:
        with closing(sqlite3.connect(uri, timeout=5, uri=True)) as db:
            db.execute("PRAGMA query_only = ON")
            tables = db.execute(
                "SELECT name FROM sqlite_master WHERE name IN "
                "('runtime_permit_use', 'observation_replay')"
            ).fetchall()
            if not tables:
                raise ValueError("synthetic replay ledger has no recognized tables")
            permit_sequence = _counter(
                db, "runtime_permit_use", (source_id, runtime_request_sha256),
            )
            evidence_sequence = _counter(
                db, "observation_replay", (plan_sha256, source_id),
            )
    except sqlite3.Error as exc:
        raise ValueError("synthetic replay ledger unavailable") from exc
    return SyntheticReplayGap(
        permit_sequence, evidence_sequence, permit_sequence > evidence_sequence,
    )
