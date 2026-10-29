"""Portable selected-source snapshots are review-only, never executable."""
import base64
from dataclasses import FrozenInstanceError
import hashlib
import json
import os
import socket
import subprocess

import pytest

from cloudforge.demo_selected_artifact import prepare_selected_artifact
from cloudforge.demo_source_package import (
    package_selected_source, verify_selected_source_package,
)

MANIFESTS = {"requirements.txt": "redis>=5\n# PRIVATE=manifest-comment\n"}
SOURCE = b"# PRIVATE=source-comment\nprint('ready')\n"


def _package(manifests=MANIFESTS, source=SOURCE, target="local-review"):
    raw = package_selected_source("example", manifests, target, "app.py", source)
    binding = prepare_selected_artifact("example", manifests, target, "app.py", source)["selected_source_binding"]["digest"]
    return raw, binding


def _verify(raw, binding, target="local-review"):
    return verify_selected_source_package(
        raw, expected_package_sha256=hashlib.sha256(raw).hexdigest(),
        expected_review_binding_digest=binding, expected_target_id=target,
    )


def test_exact_snapshot_is_deterministic_and_contains_real_bytes_without_execution():
    raw, binding = _package()
    assert raw == _package()[0]
    result = _verify(raw, binding)
    assert result.source_bytes == SOURCE
    assert result.manifests == tuple(MANIFESTS.items())
    assert result.entrypoint == "app.py"
    assert result.package_sha256 == hashlib.sha256(raw).hexdigest()
    assert result.review_binding_digest == binding
    assert "PRIVATE=source-comment" not in repr(result)
    assert "PRIVATE=manifest-comment" not in repr(result)
    with pytest.raises(FrozenInstanceError):
        result.source_bytes = b"tampered"


def test_changed_source_manifest_and_target_cannot_reuse_expected_digests():
    raw, binding = _package()
    variants = [
        _package(source=b"print('different')\n"),
        _package(manifests={"requirements.txt": "redis>=6\n"}),
        _package(target="other"),
    ]
    assert len({hashlib.sha256(p[0]).hexdigest() for p in variants + [(raw, binding)]}) == 4
    for changed, _ in variants:
        with pytest.raises(ValueError, match="digest differs"):
            verify_selected_source_package(
                changed, expected_package_sha256=hashlib.sha256(raw).hexdigest(),
                expected_review_binding_digest=binding, expected_target_id="local-review",
            )
    with pytest.raises(ValueError, match="target differs"):
        _verify(raw, binding, target="other")


def test_rehashed_tampered_source_still_fails_original_review_binding():
    raw, binding = _package()
    document = json.loads(raw)
    document["source_base64"] = base64.b64encode(b"print('changed')\n").decode()
    tampered = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    with pytest.raises(ValueError, match="review binding differs"):
        _verify(tampered, binding)


@pytest.mark.parametrize("change", [
    lambda d: d.update({"extra": True}),
    lambda d: d.update({"format_version": True}),
    lambda d: d.update({"operation": "execute"}),
    lambda d: d.update({"source_base64": "%%%"}),
    lambda d: d.update({"source_base64": "YQ==="}),
    lambda d: d.update({"manifests": []}),
    lambda d: d.update({"manifests": [d["manifests"][0], d["manifests"][0]]}),
    lambda d: d.update({"manifests": [{"name": "../requirements.txt", "utf8_base64": "YQ=="}]}),
    lambda d: d.update({"manifests": [{"name": "requirements.txt", "utf8_base64": "/w=="}]}),
    lambda d: d.update({"entrypoint": "../../app.py"}),
])
def test_rejects_rehashed_nonconforming_packages(change):
    raw, binding = _package()
    document = json.loads(raw)
    change(document)
    altered = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    with pytest.raises(ValueError):
        _verify(altered, binding)


def test_rejects_noncanonical_bytes_and_invalid_types():
    raw, binding = _package()
    with pytest.raises(ValueError, match="canonically encoded"):
        _verify(json.dumps(json.loads(raw), indent=2).encode(), binding)
    for invalid in (b"", b"{", b"x" * 400001, b"\xff"):
        with pytest.raises(ValueError):
            _verify(invalid, binding)
    with pytest.raises(ValueError):
        verify_selected_source_package("not bytes", expected_package_sha256=hashlib.sha256(raw).hexdigest(),
            expected_review_binding_digest=binding, expected_target_id="local-review")
    with pytest.raises(ValueError):
        verify_selected_source_package(raw, expected_package_sha256="wrong",
            expected_review_binding_digest=binding, expected_target_id="local-review")


def test_node_source_and_manifest_roundtrip():
    manifests = {"package.json": '{"dependencies":{"express":"^4"}}'}
    source = b"console.log('ready')\n"
    raw = package_selected_source("node-app", manifests, "review", "server.js", source)
    digest = prepare_selected_artifact("node-app", manifests, "review", "server.js", source)["selected_source_binding"]["digest"]
    result = _verify(raw, digest, target="review")
    assert result.entrypoint == "server.js"
    assert result.source_bytes == source


def test_packaging_does_not_launch_process_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("review package must not run code or network")
    with monkeypatch.context() as guard:
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(os, "system", forbidden)
        raw, binding = _package()
        assert _verify(raw, binding).source_bytes == SOURCE
