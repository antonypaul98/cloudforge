"""Synthetic admission-to-staging integration; no selected-code execution."""
from dataclasses import replace
import hashlib
import os
import socket
import subprocess

import pytest

from cloudforge.demo_selected_artifact import prepare_selected_artifact
from cloudforge.demo_source_package import package_selected_source
from cloudforge.demo_selected_execution_permit import issue_selected_sandbox_permit
from cloudforge.demo_selected_approval_gate import issue_selected_sandbox_approval
from cloudforge.demo_selected_admission_stage import stage_synthetically_admitted_selected_source

OP = b"operator-policy-key-32bytes-minimum-000"
REVIEW = b"separate-reviewer-key-32bytes-minimum-111"
IMAGE = "docker.io/library/python@sha256:" + "a" * 64
SOURCE = b"# private source\nprint('fixture')\n"


def inputs(tmp_path, source=SOURCE, target="isolated-demo"):
    manifests = {"requirements.txt": "# stdlib only\n"}
    package = package_selected_source("fixture", manifests, target, "app.py", source)
    review = prepare_selected_artifact("fixture", manifests, target, "app.py", source)
    data = dict(
        expected_package_sha256=hashlib.sha256(package).hexdigest(),
        expected_review_binding_digest=review["selected_source_binding"]["digest"],
        expected_target_id=target, image_ref=IMAGE,
        operator_key=OP, trusted_operator_key_sha256=hashlib.sha256(OP).hexdigest(),
    )
    permit = issue_selected_sandbox_permit(
        package, **data, sequence=7, valid_from_unix=1000,
        valid_until_unix=1200,
    )
    approval = issue_selected_sandbox_approval(
        permit, reviewer_key=REVIEW,
        trusted_reviewer_key_sha256=hashlib.sha256(REVIEW).hexdigest(),
        valid_from_unix=1020, valid_until_unix=1180,
    )
    kwargs = dict(
        **data, reviewer_key=REVIEW,
        trusted_reviewer_key_sha256=hashlib.sha256(REVIEW).hexdigest(),
        sequence=7, now_unix=1100, ledger_path=str(tmp_path / "ledger.sqlite"),
    )
    return package, permit, approval, kwargs


def stage(package, permit, approval, kwargs):
    return stage_synthetically_admitted_selected_source(
        package, permit, approval, **kwargs,
    )


def test_valid_staging_then_replay_rejected_and_cleaned(tmp_path):
    package, permit, approval, kwargs = inputs(tmp_path)
    with stage(package, permit, approval, kwargs) as staged:
        directory = staged.directory
        assert (directory / "app.py").read_bytes() == SOURCE
        assert (directory / "requirements.txt").read_bytes() == b"# stdlib only\n"
        assert staged.package_sha256 == kwargs["expected_package_sha256"]
        assert kwargs["ledger_path"] and os.path.isfile(kwargs["ledger_path"])
    assert not directory.exists()
    with pytest.raises(ValueError, match="already consumed"):
        with stage(package, permit, approval, kwargs):
            pytest.fail("replayed permit must not yield staged source")
    assert not directory.exists()


def test_invalid_reviewer_receipt_never_stages_or_opens_ledger(tmp_path, monkeypatch):
    import cloudforge.demo_selected_admission_stage as module
    package, permit, approval, kwargs = inputs(tmp_path)
    def forbidden(*args, **kw):
        pytest.fail("invalid approval must not stage")
    monkeypatch.setattr(module, "stage_verified_selected_source", forbidden)
    with pytest.raises(ValueError, match="approval"):
        with stage(package, permit, replace(approval, mac_sha256="f" * 64), kwargs):
            pass
    assert not os.path.exists(kwargs["ledger_path"])


def test_changed_source_or_image_rejected_before_staging(tmp_path, monkeypatch):
    import cloudforge.demo_selected_admission_stage as module
    package, permit, approval, kwargs = inputs(tmp_path)
    def forbidden(*args, **kw):
        pytest.fail("invalid permit must not stage")
    monkeypatch.setattr(module, "stage_verified_selected_source", forbidden)
    for bad_package, bad_kwargs in (
        (package + b" ", kwargs),
        (package, {**kwargs, "image_ref": "docker.io/library/python@sha256:" + "b" * 64}),
        (package, {**kwargs, "expected_target_id": "changed-target"}),
    ):
        with pytest.raises(ValueError):
            with stage(bad_package, permit, approval, bad_kwargs):
                pass
    assert not os.path.exists(kwargs["ledger_path"])


def test_stage_failure_does_not_consume_permit(tmp_path, monkeypatch):
    import cloudforge.demo_selected_admission_stage as module
    package, permit, approval, kwargs = inputs(tmp_path)
    original = module.stage_verified_selected_source
    def failed(*args, **kw):
        raise OSError("synthetic staging failure")
    monkeypatch.setattr(module, "stage_verified_selected_source", failed)
    with pytest.raises(OSError, match="synthetic staging failure"):
        with stage(package, permit, approval, kwargs):
            pass
    assert not os.path.exists(kwargs["ledger_path"])
    monkeypatch.setattr(module, "stage_verified_selected_source", original)
    with stage(package, permit, approval, kwargs) as staged:
        assert (staged.directory / "app.py").read_bytes() == SOURCE


def test_downstream_failure_cleans_staging_without_refunding_permit(tmp_path):
    package, permit, approval, kwargs = inputs(tmp_path)
    with pytest.raises(RuntimeError, match="downstream"):
        with stage(package, permit, approval, kwargs) as staged:
            directory = staged.directory
            raise RuntimeError("downstream")
    assert not directory.exists()
    with pytest.raises(ValueError, match="already consumed"):
        with stage(package, permit, approval, kwargs):
            pass


def test_no_process_or_network_from_admission_staging(tmp_path, monkeypatch):
    package, permit, approval, kwargs = inputs(tmp_path)
    def forbidden(*args, **kw):
        pytest.fail("admission staging must not execute or network")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    with stage(package, permit, approval, kwargs) as staged:
        assert (staged.directory / "app.py").is_file()
