"""Exact selected application -> non-executing rootless sandbox review."""
import hashlib
import json
import os
import socket
import subprocess

import pytest

from cloudforge.demo_selected_artifact import prepare_selected_artifact
from cloudforge.demo_source_package import package_selected_source
from cloudforge.demo_selected_sandbox_plan import prepare_selected_sandbox_review

PY_MANIFEST = {"requirements.txt": "redis>=5\n# PRIVATE=manifest-secret\n"}
PY_SOURCE = b"# PRIVATE=source-secret\nprint('ready')\n"
NODE_MANIFEST = {"package.json": '{"dependencies":{"express":"^4"}}'}
NODE_SOURCE = b"console.log('ready')\n"
PY_IMAGE = "docker.io/library/python@sha256:" + "a" * 64
NODE_IMAGE = "docker.io/library/node@sha256:" + "b" * 64


def _input(manifests=PY_MANIFEST, source=PY_SOURCE, entrypoint="app.py", target="sandbox-review"):
    raw = package_selected_source("example", manifests, target, entrypoint, source)
    digest = prepare_selected_artifact(
        "example", manifests, target, entrypoint, source,
    )["selected_source_binding"]["digest"]
    return raw, hashlib.sha256(raw).hexdigest(), digest


def _plan(manifests=PY_MANIFEST, source=PY_SOURCE, entrypoint="app.py",
          target="sandbox-review", image=PY_IMAGE):
    raw, package_digest, review_digest = _input(manifests, source, entrypoint, target)
    return prepare_selected_sandbox_review(
        raw, expected_package_sha256=package_digest,
        expected_review_binding_digest=review_digest,
        expected_target_id=target, image_ref=image,
    )


@pytest.mark.parametrize("manifests,source,entrypoint,image,runtime", [
    (PY_MANIFEST, PY_SOURCE, "app.py", PY_IMAGE, "python"),
    (NODE_MANIFEST, NODE_SOURCE, "server.js", NODE_IMAGE, "node"),
])
def test_python_and_node_review_are_deterministic_and_nonexecuting(
    manifests, source, entrypoint, image, runtime,
):
    first = _plan(manifests, source, entrypoint, image=image)
    assert first == _plan(manifests, source, entrypoint, image=image)
    assert first["runtime"] == runtime
    assert first["entrypoint"] == entrypoint
    assert first["execution_permitted"] is False
    assert first["runtime_observed"] is False
    assert first["isolation_attested"] is False
    assert first["signed_health_evidence"] is False
    assert first["rollback_performed"] is False
    assert first["approval_status"] == "independent-authorization-required"
    assert first["constraints"]["network"] == "none"
    assert first["constraints"]["root_filesystem"] == "read-only"
    assert first["constraints"]["capabilities"] == "drop-all"
    assert first["constraints"]["pull_policy"] == "never"
    serialized = json.dumps(first)
    assert "source-secret" not in serialized
    assert "manifest-secret" not in serialized
    assert source.decode().strip() not in serialized


def test_plan_digest_changes_for_source_manifest_target_and_image():
    original = _plan()
    variants = [
        _plan(source=b"print('different')\n"),
        _plan(manifests={"requirements.txt": "redis>=6\n"}),
        _plan(target="different-target"),
        _plan(image="docker.io/library/python@sha256:" + "c" * 64),
    ]
    assert len({v["proposal_sha256"] for v in [original, *variants]}) == 5


def test_stale_package_and_source_review_are_rejected():
    raw, package_digest, review_digest = _input()
    changed, changed_digest, _ = _input(source=b"print('changed')\n")
    with pytest.raises(ValueError, match="package digest differs"):
        prepare_selected_sandbox_review(
            changed, expected_package_sha256=package_digest,
            expected_review_binding_digest=review_digest,
            expected_target_id="sandbox-review", image_ref=PY_IMAGE,
        )
    with pytest.raises(ValueError, match="review binding differs"):
        prepare_selected_sandbox_review(
            changed, expected_package_sha256=changed_digest,
            expected_review_binding_digest=review_digest,
            expected_target_id="sandbox-review", image_ref=PY_IMAGE,
        )
    with pytest.raises(ValueError, match="target differs"):
        prepare_selected_sandbox_review(
            raw, expected_package_sha256=package_digest,
            expected_review_binding_digest=review_digest,
            expected_target_id="other-target", image_ref=PY_IMAGE,
        )


@pytest.mark.parametrize("bad", [
    "", "python:3.11", "python@sha256:" + "a" * 64,
    "docker.io/library/python:3.11",
    "docker.io/library/python@sha256:" + "A" * 64,
    "docker.io/library/python@sha256:" + "a" * 63,
    "docker.io/library/../python@sha256:" + "a" * 64,
    "docker.io/library/python@sha256:" + "a" * 64 + " --privileged",
    "docker.io/library/python@sha256:" + "a" * 64 + "\n",
    None, 7, True,
])
def test_invalid_or_unpinned_image_fails_closed(bad):
    raw, package_digest, review_digest = _input()
    with pytest.raises(ValueError, match="digest-pinned"):
        prepare_selected_sandbox_review(
            raw, expected_package_sha256=package_digest,
            expected_review_binding_digest=review_digest,
            expected_target_id="sandbox-review", image_ref=bad,
        )


def test_review_never_launches_process_or_opens_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("review must never execute or access network")
    with monkeypatch.context() as guard:
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(subprocess, "run", forbidden)
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(os, "system", forbidden)
        result = _plan()
    assert result["execution_permitted"] is False


def test_immutable_digest_represents_all_proposal_fields():
    result = _plan()
    digest = result.pop("proposal_sha256")
    canonical = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    assert hashlib.sha256(canonical).hexdigest() == digest
