"""Synthetic one-time admission of source-bound selected sandbox permits."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import os
import sqlite3

import pytest

from cloudforge.demo_selected_artifact import prepare_selected_artifact
from cloudforge.demo_source_package import package_selected_source
from cloudforge.demo_selected_execution_permit import issue_selected_sandbox_permit
from cloudforge.demo_selected_permit_replay import consume_selected_sandbox_permit


KEY = b"independent-operator-key-32bytes-minimum"
IMAGE = "docker.io/library/python@sha256:" + "a" * 64


def _case(*, source=b"print('private-source')\n", target="isolated-demo"):
    manifests = {"requirements.txt": "redis>=5\n# private-manifest\n"}
    raw = package_selected_source("fixture", manifests, target, "app.py", source)
    review = prepare_selected_artifact(
        "fixture", manifests, target, "app.py", source,
    )
    return {
        "package_bytes": raw,
        "expected_package_sha256": hashlib.sha256(raw).hexdigest(),
        "expected_review_binding_digest": review["selected_source_binding"]["digest"],
        "expected_target_id": target,
        "image_ref": IMAGE,
        "operator_key": KEY,
        "trusted_operator_key_sha256": hashlib.sha256(KEY).hexdigest(),
    }


def _permit(case, sequence=7):
    return issue_selected_sandbox_permit(
        **case, sequence=sequence, valid_from_unix=1000,
        valid_until_unix=1200,
    )


def _consume(case, permit, path, sequence=7):
    return consume_selected_sandbox_permit(
        **case, permit=permit, sequence=sequence, now_unix=1100,
        ledger_path=str(path),
    )


def test_first_use_succeeds_and_same_permit_replay_fails(tmp_path):
    case = _case()
    permit = _permit(case)
    path = tmp_path / "sandbox-permits.sqlite"
    assert _consume(case, permit, path)
    with pytest.raises(ValueError, match="already consumed"):
        _consume(case, permit, path)


def test_strictly_increasing_sequence_and_stale_rejection(tmp_path):
    case = _case()
    path = tmp_path / "sandbox-permits.sqlite"
    assert _consume(case, _permit(case, 7), path, 7)
    assert _consume(case, _permit(case, 8), path, 8)
    with pytest.raises(ValueError, match="already consumed"):
        _consume(case, _permit(case, 7), path, 7)


def test_different_exact_source_has_separate_proposal_scope(tmp_path):
    path = tmp_path / "sandbox-permits.sqlite"
    first = _case()
    changed = _case(source=b"print('changed')\n")
    assert _consume(first, _permit(first), path)
    assert _consume(changed, _permit(changed), path)
    with pytest.raises(ValueError, match="already consumed"):
        _consume(first, _permit(first), path)


def test_invalid_mac_rejected_before_ledger_file_created(tmp_path):
    case = _case()
    path = tmp_path / "never-created.sqlite"
    bad = replace(_permit(case), mac_sha256="f" * 64)
    with pytest.raises(ValueError, match="differs from exact policy"):
        _consume(case, bad, path)
    assert not path.exists()


def test_stale_source_rejected_before_ledger_file_created(tmp_path):
    case = _case()
    path = tmp_path / "never-created.sqlite"
    with pytest.raises(ValueError, match="differs from exact policy"):
        _consume(_case(source=b"print('changed')\n"), _permit(case), path)
    assert not path.exists()


def test_concurrent_same_permit_only_one_wins(tmp_path):
    case = _case()
    permit = _permit(case)
    path = tmp_path / "sandbox-permits.sqlite"

    def attempt(_):
        try:
            return _consume(case, permit, path)
        except ValueError as exc:
            assert "already consumed" in str(exc)
            return False

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(attempt, range(6)))
    assert results.count(True) == 1
    assert results.count(False) == 5


def test_malformed_existing_schema_fails_closed(tmp_path):
    case = _case()
    path = tmp_path / "sandbox-permits.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE selected_sandbox_permit_use (bad TEXT)")
    with pytest.raises(ValueError, match="schema mismatch"):
        _consume(case, _permit(case), path)


def test_unexpected_ledger_trigger_fails_closed(tmp_path):
    case = _case()
    path = tmp_path / "sandbox-permits.sqlite"
    assert _consume(case, _permit(case), path)
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TRIGGER unexpected AFTER UPDATE ON selected_sandbox_permit_use "
            "BEGIN SELECT 1; END"
        )
    with pytest.raises(ValueError, match="schema mismatch"):
        _consume(case, _permit(case, 8), path, 8)


def test_symlinked_ledger_path_is_rejected(tmp_path):
    case = _case()
    real = tmp_path / "real.sqlite"
    alias = tmp_path / "alias.sqlite"
    real.touch()
    os.symlink(real, alias)
    with pytest.raises(ValueError, match="regular file"):
        _consume(case, _permit(case), alias)


def test_invalid_ledger_path_rejected(tmp_path):
    case = _case()
    with pytest.raises(ValueError, match="absolute local file path"):
        _consume(case, _permit(case), "relative.sqlite")
