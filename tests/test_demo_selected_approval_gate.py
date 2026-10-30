"""Synthetic distinct-key preflight, no real application execution."""
from dataclasses import replace
import hashlib
import os
import socket
import subprocess

import pytest

from cloudforge.demo_selected_artifact import prepare_selected_artifact
from cloudforge.demo_source_package import package_selected_source
from cloudforge.demo_selected_execution_permit import issue_selected_sandbox_permit
from cloudforge.demo_selected_approval_gate import (
    SelectedSandboxApproval, issue_selected_sandbox_approval,
    verify_selected_sandbox_approval, consume_approved_selected_sandbox_permit)

OP = b"operator-policy-key-32bytes-minimum-000"
REVIEW = b"separate-reviewer-key-32bytes-minimum-111"
IMAGE = "docker.io/library/python@sha256:" + "a" * 64


def case(source=b"print('private')\n", target="isolated-demo"):
    manifests = {"requirements.txt": "redis>=5\n"}
    raw = package_selected_source("fixture", manifests, target, "app.py", source)
    review = prepare_selected_artifact("fixture", manifests, target, "app.py", source)
    return dict(
        package_bytes=raw, expected_package_sha256=hashlib.sha256(raw).hexdigest(),
        expected_review_binding_digest=review["selected_source_binding"]["digest"],
        expected_target_id=target, image_ref=IMAGE, operator_key=OP,
        trusted_operator_key_sha256=hashlib.sha256(OP).hexdigest())


def permit(data=None, sequence=7):
    return issue_selected_sandbox_permit(
        **(data or case()), sequence=sequence, valid_from_unix=1000,
        valid_until_unix=1200)


def approval(p=None, key=REVIEW, start=1020, end=1180):
    return issue_selected_sandbox_approval(
        p or permit(), reviewer_key=key,
        trusted_reviewer_key_sha256=hashlib.sha256(key).hexdigest(),
        valid_from_unix=start, valid_until_unix=end)


def consume(path, data=None, p=None, a=None, now=1100, sequence=7,
            key=REVIEW, pin=None):
    data = data or case()
    p = p or permit(data, sequence)
    return consume_approved_selected_sandbox_permit(
        **data, permit=p, approval=a or approval(p), reviewer_key=key,
        trusted_reviewer_key_sha256=pin or hashlib.sha256(REVIEW).hexdigest(),
        sequence=sequence, now_unix=now, ledger_path=str(path))


def test_valid_separate_key_admission_and_replay(tmp_path):
    p = permit()
    a = approval(p)
    assert isinstance(a, SelectedSandboxApproval)
    assert verify_selected_sandbox_approval(
        p, a, reviewer_key=REVIEW,
        trusted_reviewer_key_sha256=hashlib.sha256(REVIEW).hexdigest(),
        now_unix=1100)
    path = tmp_path / "ledger.sqlite"
    assert consume(path, p=p, a=a)
    with pytest.raises(ValueError, match="already consumed"):
        consume(path, p=p, a=a)


@pytest.mark.parametrize("field,value", [
    ("format_version", True), ("permit_mac_sha256", "f" * 64),
    ("reviewer_key_sha256", "f" * 64), ("mac_sha256", "f" * 64),
    ("valid_until_unix", 1300), ("valid_from_unix", True)])
def test_forged_receipt_fails_before_ledger(tmp_path, field, value):
    path = tmp_path / "missing.sqlite"
    with pytest.raises(ValueError, match="approval"):
        consume(path, a=replace(approval(), **{field: value}))
    assert not path.exists()


@pytest.mark.parametrize("now", [1019, 1181, True, -1, 1 << 63])
def test_invalid_or_stale_clock_fails(tmp_path, now):
    path = tmp_path / "missing.sqlite"
    with pytest.raises(ValueError, match="approval"):
        consume(path, now=now)
    assert not path.exists()


def test_other_permit_sequence_fails_before_ledger(tmp_path):
    path = tmp_path / "missing.sqlite"
    with pytest.raises(ValueError, match="approval"):
        consume(path, p=permit(sequence=8), sequence=8, a=approval(permit()))
    assert not path.exists()


def test_source_and_target_changes_fail_before_ledger(tmp_path):
    original = permit()
    for changed in (case(source=b"print('changed')\n"), case(target="other")):
        path = tmp_path / "missing.sqlite"
        with pytest.raises(ValueError, match="differs from exact policy"):
            consume(path, data=changed, p=original, a=approval(original))
        assert not path.exists()


def test_same_key_or_wrong_pin_fails(tmp_path):
    with pytest.raises(ValueError, match="separate"):
        approval(key=OP)
    path = tmp_path / "missing.sqlite"
    with pytest.raises(ValueError, match="separate"):
        consume(path, key=OP, pin=hashlib.sha256(OP).hexdigest())
    with pytest.raises(ValueError, match="pin"):
        consume(path, key=b"wrong-reviewer-key-32bytes-minimum-000")
    assert not path.exists()


@pytest.mark.parametrize("start,end", [
    (999, 1100), (1020, 1201), (1100, 1100),
    (True, 1180), (1020, True)])
def test_invalid_approval_window_rejected(start, end):
    with pytest.raises(ValueError, match="invalid selected sandbox approval"):
        approval(start=start, end=end)


def test_preflight_does_not_execute_or_network(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("preflight must not execute or open network")
    with monkeypatch.context() as guard:
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(subprocess, "run", forbidden)
        guard.setattr(os, "system", forbidden)
        assert consume(tmp_path / "ledger.sqlite")


def test_receipt_redacts_source_and_keys():
    text = repr(approval())
    assert "private" not in text
    assert OP.decode() not in text
    assert REVIEW.decode() not in text
