"""Optional local at-most-once gate for verified synthetic HTTPS HEAD permits.

Only the permitted fixture calls this *after* exact MAC, policy and budget
validation. The ledger does not authenticate a caller or authorize live I/O.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing

from .observation_replay import _verify_replay_ledger_path
from .observation_runtime_permit import RuntimeHEADPermit


_SCHEMA = """
CREATE TABLE IF NOT EXISTS runtime_permit_use (
    source_id TEXT NOT NULL,
    runtime_request_sha256 TEXT NOT NULL,
    last_sequence INTEGER NOT NULL
        CHECK (last_sequence BETWEEN 1 AND 9223372036854775807),
    PRIMARY KEY (source_id, runtime_request_sha256)
) WITHOUT ROWID
"""
_CANONICAL_SCHEMA = _SCHEMA.strip().replace(
    "CREATE TABLE IF NOT EXISTS ", "CREATE TABLE ", 1,
)
_ADVANCE = """
INSERT INTO runtime_permit_use (source_id, runtime_request_sha256, last_sequence)
VALUES (?, ?, ?)
ON CONFLICT (source_id, runtime_request_sha256) DO UPDATE
SET last_sequence = excluded.last_sequence
WHERE typeof(runtime_permit_use.last_sequence) = 'integer'
  AND runtime_permit_use.last_sequence BETWEEN 1 AND 9223372036854775807
  AND excluded.last_sequence > runtime_permit_use.last_sequence
"""


def _verify_schema(db: sqlite3.Connection) -> None:
    row = db.execute(
        "SELECT sql FROM sqlite_master "
        "WHERE type = 'table' AND name = 'runtime_permit_use'"
    ).fetchone()
    if (row is None or type(row[0]) is not str
            or row[0].strip() != _CANONICAL_SCHEMA):
        raise ValueError("runtime permit ledger schema mismatch")
    if db.execute(
        "SELECT 1 FROM sqlite_master "
        "WHERE type = 'trigger' AND tbl_name = 'runtime_permit_use' LIMIT 1"
    ).fetchone() is not None:
        raise ValueError("runtime permit ledger schema mismatch")


def _consume_verified_permit(permit: RuntimeHEADPermit, ledger_path: str) -> None:
    """Atomically consume a previously verified permit before fake probes.

    This is at-most-once per (source, request) increasing sequence within one
    operator-owned SQLite file, not exactly-once execution or a trusted runtime.
    A failed probe still consumes the sequence. Never reset/restore this ledger
    while accepting permits.
    """
    _verify_replay_ledger_path(ledger_path)
    try:
        with closing(sqlite3.connect(ledger_path, timeout=5, uri=False)) as db:
            with db:
                db.execute("BEGIN IMMEDIATE")
                db.execute(_SCHEMA)
                _verify_schema(db)
                changed = db.execute(
                    _ADVANCE,
                    (permit.source_id, permit.runtime_request_sha256,
                     permit.sequence),
                ).rowcount
                if changed != 1:
                    raise ValueError("runtime HEAD permit sequence already consumed")
    except sqlite3.Error as exc:
        raise ValueError("runtime HEAD permit ledger unavailable") from exc
