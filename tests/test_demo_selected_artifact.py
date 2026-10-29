"""Selected real source review: no application execution or provider access."""
import hashlib
import json
import os
import socket
import subprocess
import sys

import pytest

from cloudforge.demo_selected_artifact import prepare_selected_artifact, _read_selected_source

PYTHON_MANIFEST = {"requirements.txt": "redis>=5\n# TOKEN=private-comment\n"}
NODE_MANIFEST = {"package.json": '{"dependencies":{"express":"^4"}}'}


def test_selected_python_source_bound_to_exact_manifest_and_target():
    first = prepare_selected_artifact("app", PYTHON_MANIFEST, "sandbox", "app.py", b"print('a')\n")
    assert first == prepare_selected_artifact("app", PYTHON_MANIFEST, "sandbox", "app.py", b"print('a')\n")
    assert first["selected_source_binding"]["source_sha256"] == hashlib.sha256(b"print('a')\n").hexdigest()
    assert first["selected_application_executed"] is False
    assert first["isolated_sandbox"] is False
    assert first["authenticated_review"] is False
    assert first["infrastructure_mutated"] is False
    assert "private-comment" not in json.dumps(first)
    assert "print('a')" not in json.dumps(first)


def test_source_change_and_manifest_change_require_distinct_review():
    base = prepare_selected_artifact("app", PYTHON_MANIFEST, "sandbox", "app.py", b"x = 1\n")
    source = prepare_selected_artifact("app", PYTHON_MANIFEST, "sandbox", "app.py", b"x = 2\n")
    manifest = prepare_selected_artifact("app", {"requirements.txt": "redis>=6\n"}, "sandbox", "app.py", b"x = 1\n")
    target = prepare_selected_artifact("app", PYTHON_MANIFEST, "other", "app.py", b"x = 1\n")
    digests = {v["selected_source_binding"]["digest"] for v in (base, source, manifest, target)}
    assert len(digests) == 4


def test_node_runtime_supported_but_mismatched_entrypoint_rejected():
    result = prepare_selected_artifact("node", NODE_MANIFEST, "sandbox", "server.js", b"console.log('hi')\n")
    assert result["selected_source_binding"]["runtime"] == "node"
    with pytest.raises(ValueError, match="entrypoint"):
        prepare_selected_artifact("node", NODE_MANIFEST, "sandbox", "app.py", b"ok")


@pytest.mark.parametrize("entrypoint,data", [
    ("../app.py", b"ok"), ("server.js", b"ok"), ("app.py", b""),
    ("app.py", b"x" * 131073), ("app.py", b"\xff"),
    ("app.py", b"a\x00b"), ("app.py", "unicode"),
])
def test_invalid_selected_source_fails_closed(entrypoint, data):
    with pytest.raises(ValueError):
        prepare_selected_artifact("app", PYTHON_MANIFEST, "sandbox", entrypoint, data)


def test_file_reader_rejects_symlink_hardlink_directory_and_oversize(tmp_path):
    real = tmp_path / "real.py"
    real.write_text("print(1)\n")
    link = tmp_path / "app.py"
    link.symlink_to(real)
    with pytest.raises(ValueError):
        _read_selected_source(str(link))
    link.unlink()
    os.link(real, link)
    with pytest.raises(ValueError, match="single-link"):
        _read_selected_source(str(link))
    link.unlink()
    link.mkdir()
    with pytest.raises(ValueError):
        _read_selected_source(str(link))
    link.rmdir()
    link.write_bytes(b"x" * 131073)
    with pytest.raises(ValueError, match="size"):
        _read_selected_source(str(link))


def test_cli_accepts_selected_file_but_never_prints_source(tmp_path):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text(PYTHON_MANIFEST["requirements.txt"])
    source = tmp_path / "app.py"
    source.write_text("# secret-in-source\nprint(1)\n")
    args = [sys.executable, "-m", "cloudforge.demo_selected_artifact",
            "--name", "app", "--target", "sandbox",
            "--manifest", str(manifest), "--source", str(source)]
    result = subprocess.run(args, capture_output=True, text=True, check=True, timeout=15)
    payload = json.loads(result.stdout)
    assert result.stderr == ""
    assert payload["selected_source_binding"]["entrypoint"] == "app.py"
    assert "secret-in-source" not in result.stdout
    assert "private-comment" not in result.stdout
    assert subprocess.run(args, capture_output=True, text=True, check=True, timeout=15).stdout == result.stdout


def test_no_network_or_process_in_pure_source_review(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("source review must not run code or network")
    with monkeypatch.context() as guard:
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(os, "system", forbidden)
        result = prepare_selected_artifact("app", PYTHON_MANIFEST, "sandbox", "app.py", b"print(1)\n")
    assert result["selected_application_executed"] is False
