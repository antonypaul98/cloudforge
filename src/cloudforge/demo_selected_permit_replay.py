"""Local at-most-once admission for a verified selected-source policy permit.

This is a synthetic, non-executing gate. The caller owns the ledger directory,
clock, operator key, authenticated approval, and any future isolated runtime.
"""
from __future__ import annotations

from contextlib import closing
import sqlite3

from .demo_selected_execution_permit import (
    SelectedSandboxPermit, verify_selected_sandbox_permit,
)
from .observation_replay import _verify_replay_ledger_path


_SCHEMA = """
CREATE TABLE IF NOT EXISTS selected_sandbox_permit_use (
    operator_key_sha256 TEXT NOT NULL,
    proposal_sha256 TEXT NOT NULL,
    last_sequence INTEGER NOT NULL
        CHECK (last_sequence BETWEEN 1 AND 9223372036854775807),
    PRIMARY KEY (operator_key_sha256, proposal_sha256)
) WITHOUT ROWID
"""
_CANONICAL_SCHEMA = _SCHEMA.strip().replace(
    "CREATE TABLE IF NOT EXISTS ", "CREATE TABLE ", 1,
)
_ADVANCE = """
INSERT INTO selected_sandbox_permit_use
    (operator_key_sha256, proposal_sha256, last_sequence)
VALUES (?, ?, ?)
ON CONFLICT (operator_key_sha256, proposal_sha256) DO UPDATE
SET last_sequence = excluded.last_sequence
WHERE typeof(selected_sandbox_permit_use.last_sequence) = 'integer'
  AND selected_sandbox_permit_use.last_sequence BETWEEN 1 AND 9223372036854775807
  AND excluded.last_sequence > selected_sandbox_permit_use.last_sequence
"""


def _verify_schema(db: sqlite3.Connection) -> None:
    row = db.execute(
        "SELECT sql FROM sqlite_master "
        "WHERE type = 'table' AND name = 'selected_sandbox_permit_use'"
    ).fetchone()
    if (row is None or type(row[0]) is not str
            or row[0].strip() != _CANONICAL_SCHEMA):
        raise ValueError("selected sandbox permit ledger schema mismatch")
    if db.execute(
        "SELECT 1 FROM sqlite_master "
        "WHERE type = 'trigger' AND tbl_name = 'selected_sandbox_permit_use' LIMIT 1"
    ).fetchone() is not None:
        raise ValueError("selected sandbox permit ledger schema mismatch")


def consume_selected_sandbox_permit(
    package_bytes: bytes, permit: SelectedSandboxPermit, *,
    expected_package_sha256: str, expected_review_binding_digest: str,
    expected_target_id: str, image_ref: str, operator_key: bytes,
    trusted_operator_key_sha256: str, sequence: int, now_unix: int,
    ledger_path: str,
) -> bool:
    """Verify first, then atomically admit one increasing sequence per proposal.

    Admission is at-most-once only within this single trusted SQLite ledger.
    It does not run a container, authenticate a human, or grant deployment.
    A failed downstream operation must not restore the consumed sequence.
    """
    verify_selected_sandbox_permit(
        package_bytes, permit,
        expected_package_sha256=expected_package_sha256,
        expected_review_binding_digest=expected_review_binding_digest,
        expected_target_id=expected_target_id, image_ref=image_ref,
        operator_key=operator_key,
        trusted_operator_key_sha256=trusted_operator_key_sha256,
        sequence=sequence, now_unix=now_unix,
    )
    _verify_replay_ledger_path(ledger_path)
    try:
        with closing(sqlite3.connect(ledger_path, timeout=5, uri=False)) as db:
            with db:
                db.execute("BEGIN IMMEDIATE")
                db.execute(_SCHEMA)
                _verify_schema(db)
                changed = db.execute(
                    _ADVANCE,
                    (permit.operator_key_sha256, permit.proposal_sha256,
                     permit.sequence),
                ).rowcount
                if changed != 1:
                    raise ValueError("selected sandbox permit already consumed")
    except sqlite3.Error as exc:
        raise ValueError("selected sandbox permit ledger unavailable") from exc
    return True
