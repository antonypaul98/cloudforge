"""Durable local replay guard for verified, externally supplied observation evidence.

SQLite serializes monotonic sequence acceptance across processes. This module
does not collect probes, authenticate a collector, or claim service health.
The caller owns the database directory, key provisioning and trusted clock.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing

from .deployment import DeploymentHandoff
from .local_adapter import LocalExecutionApproval, LocalExecutionReceipt
from .observation_evidence import ObservationEvidence, verify_observation_evidence
from .observation_plan import ObservationPlan


_SCHEMA = """
CREATE TABLE IF NOT EXISTS observation_replay (
    plan_sha256 TEXT NOT NULL,
    source_id TEXT NOT NULL,
    last_sequence INTEGER NOT NULL
        CHECK (last_sequence BETWEEN 1 AND 9223372036854775807),
    PRIMARY KEY (plan_sha256, source_id)
) WITHOUT ROWID
"""
_ADVANCE = """
INSERT INTO observation_replay (plan_sha256, source_id, last_sequence)
VALUES (?, ?, ?)
ON CONFLICT (plan_sha256, source_id) DO UPDATE
SET last_sequence = excluded.last_sequence
WHERE typeof(observation_replay.last_sequence) = 'integer'
  AND observation_replay.last_sequence BETWEEN 1 AND 9223372036854775807
  AND excluded.last_sequence > observation_replay.last_sequence
"""

# SQLite normalizes CREATE TABLE IF NOT EXISTS to CREATE TABLE in sqlite_master.
# A modified ledger schema is rejected rather than automatically migrated.
_CANONICAL_SCHEMA_SQL = _SCHEMA.strip().replace(
    "CREATE TABLE IF NOT EXISTS ", "CREATE TABLE ", 1,
)


def _verify_replay_schema(db: sqlite3.Connection) -> None:
    row = db.execute(
        "SELECT sql FROM sqlite_master "
        "WHERE type = 'table' AND name = 'observation_replay'"
    ).fetchone()
    if (row is None or type(row[0]) is not str
            or row[0].strip() != _CANONICAL_SCHEMA_SQL):
        raise ValueError("durable replay ledger schema mismatch")
    if db.execute(
        "SELECT 1 FROM sqlite_master "
        "WHERE type = 'trigger' AND tbl_name = 'observation_replay' LIMIT 1"
    ).fetchone() is not None:
        raise ValueError("durable replay ledger schema mismatch")


def accept_observation_evidence_durably(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    plan: ObservationPlan,
    evidence: ObservationEvidence,
    *,
    expected_source_id: str,
    source_key: bytes,
    now_unix: int,
    max_age_seconds: int,
    ledger_path: str,
) -> bool:
    """Verify evidence and atomically advance its persistent replay sequence.

    The ledger path must be an explicit absolute local filename in a trusted,
    operator-owned directory. Keys, artifacts, samples and reviewer identities
    are never stored. A verified MAC does not establish actual probe execution.
    """
    if (type(ledger_path) is not str or not ledger_path
            or not os.path.isabs(ledger_path)
            or "\x00" in ledger_path):
        raise ValueError("replay ledger requires an absolute local file path")

    # Validate exact authorization, MAC, source and freshness before any file I/O.
    # The durable sequence comparison is intentionally performed below, inside
    # a SQLite write transaction; an in-memory last_sequence is not sufficient.
    verify_observation_evidence(
        handoff, artifact, approval, receipt, plan, evidence,
        expected_source_id=expected_source_id,
        source_key=source_key,
        now_unix=now_unix,
        max_age_seconds=max_age_seconds,
        last_sequence=0,
    )

    try:
        with closing(sqlite3.connect(ledger_path, timeout=5, uri=False)) as db:
            with db:
                db.execute("BEGIN IMMEDIATE")
                db.execute(_SCHEMA)
                _verify_replay_schema(db)
                changed = db.execute(
                    _ADVANCE,
                    (evidence.plan_sha256, evidence.source_id, evidence.sequence),
                ).rowcount
                if changed != 1:
                    raise ValueError("observation sequence already accepted")
    except sqlite3.Error as exc:
        raise ValueError("durable replay ledger unavailable") from exc
    return True
