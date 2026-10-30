"""Source staging is exact-byte, ephemeral and non-executing."""
import hashlib
import os
import socket
import stat
import subprocess

import pytest

from cloudforge.demo_selected_artifact import prepare_selected_artifact
from cloudforge.demo_source_package import package_selected_source
from cloudforge.demo_selected_oci_stage import stage_verified_selected_source


def _inputs(source=b"print('owned fixture')\n", manifests=None, target="fixture-review", entrypoint="app.py"):
    if manifests is None:
        manifests = {"requirements.txt": "redis>=5\n"}
    raw = package_selected_source("fixture", manifests, target, entrypoint, source)
    digest = prepare_selected_artifact("fixture", manifests, target, entrypoint, source)["selected_source_binding"]["digest"]
    return raw, dict(expected_package_sha256=hashlib.sha256(raw).hexdigest(),
                     expected_review_binding_digest=digest, expected_target_id=target)


def test_exact_source_and_manifest_bytes_are_staged_privately_and_cleaned():
    source = b"# confidential comment\nprint('ok')\n"
    raw, kwargs = _inputs(source=source)
    with stage_verified_selected_source(raw, **kwargs) as staged:
        path = staged.directory
        assert path.is_dir()
        assert stat.S_IMODE(path.stat().st_mode) == 0o700
        assert (path / "app.py").read_bytes() == source
        assert (path / "requirements.txt").read_bytes() == b"redis>=5\n"
        assert stat.S_IMODE((path / "app.py").stat().st_mode) == 0o600
        assert staged.source_sha256 == hashlib.sha256(source).hexdigest()
        assert staged.package_sha256 == kwargs["expected_package_sha256"]
        assert "confidential" not in repr(staged)
    assert not path.exists()


def test_node_manifest_is_staged_without_execution():
    source = b"console.log('hello')\n"
    raw, kwargs = _inputs(source=source, manifests={"package.json": '{"dependencies":{"express":"^4"}}'}, entrypoint="server.js")
    with stage_verified_selected_source(raw, **kwargs) as staged:
        assert staged.entrypoint == "server.js"
        assert (staged.directory / "server.js").read_bytes() == source
        assert (staged.directory / "package.json").is_file()
        assert not (staged.directory / "app.py").exists()


def test_modified_source_and_wrong_target_fail_before_staging(monkeypatch):
    import cloudforge.demo_selected_oci_stage as module
    raw, kwargs = _inputs()
    def forbidden(*args, **kw):
        raise AssertionError("staging must not start before verification")
    monkeypatch.setattr(module.tempfile, "TemporaryDirectory", forbidden)
    with pytest.raises(ValueError):
        with stage_verified_selected_source(raw + b" ", **kwargs):
            pass
    with pytest.raises(ValueError):
        with stage_verified_selected_source(raw, **{**kwargs, "expected_target_id": "wrong"}):
            pass


def test_context_exception_cleans_staged_sensitive_bytes():
    raw, kwargs = _inputs()
    with pytest.raises(RuntimeError, match="stop"):
        with stage_verified_selected_source(raw, **kwargs) as staged:
            path = staged.directory
            raise RuntimeError("stop")
    assert not path.exists()


def test_no_selected_source_process_or_network(monkeypatch):
    raw, kwargs = _inputs()
    def forbidden(*args, **kw):
        raise AssertionError("staging must not execute code or access network")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    with stage_verified_selected_source(raw, **kwargs) as staged:
        assert (staged.directory / "app.py").exists()


def test_staging_write_failure_removes_private_directory(monkeypatch):
    import cloudforge.demo_selected_oci_stage as module
    raw, kwargs = _inputs()
    original = module._write_exact
    captured = []
    def fail_manifest(directory, filename, content):
        captured.append(directory)
        if filename == "requirements.txt":
            raise OSError("synthetic disk error")
        return original(directory, filename, content)
    monkeypatch.setattr(module, "_write_exact", fail_manifest)
    with pytest.raises(OSError, match="synthetic disk error"):
        with stage_verified_selected_source(raw, **kwargs):
            pass
    assert captured and not captured[0].exists()
