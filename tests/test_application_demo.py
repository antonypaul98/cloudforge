"""Real-input, no-deployment demo acceptance tests."""
import json
import os
import socket
import subprocess
import sys

import pytest

from cloudforge.application_demo import review_application_manifests


PYTHON = {"requirements.txt": "postgresql>=16\nredis>=5\n# PASSWORD=do-not-leak\n"}


def test_real_python_manifest_produces_reviewable_bound_proposal():
    first = review_application_manifests("sample-api", PYTHON, "review-staging")
    assert first == review_application_manifests("sample-api", PYTHON, "review-staging")
    assert first["demo_only"] is True
    assert first["inspection"]["runtime"] == "python"
    assert [x["kind"] for x in first["provider_neutral_proposal"]["resources"]] == [
        "compute", "database", "cache"
    ]
    assert [x["path"] for x in first["inspection"]["evidence"]] == [
        "requirements.txt", "requirements.txt", "requirements.txt"
    ]
    assert len(first["plan_digest"]) == 64
    assert len(first["handoff_request"]["request_digest"]) == 64
    assert first["handoff_request"]["status"] == "approval-required"
    assert first["authenticated_review"] is False
    assert first["infrastructure_mutated"] is False
    assert first["deployment_observed"] is False
    assert first["recovery_performed"] is False
    assert "do-not-leak" not in json.dumps(first)


def test_real_node_manifest_uses_only_supported_declared_resources():
    payload = review_application_manifests(
        "node-api", {"package.json": '{"dependencies":{"redis":"^5","express":"^4"}}'},
        "staging",
    )
    assert payload["inspection"]["runtime"] == "node"
    assert [r["kind"] for r in payload["provider_neutral_proposal"]["resources"]] == [
        "compute", "cache"
    ]
    assert "express" not in json.dumps(payload)


def test_changed_target_requires_new_handoff_request_but_same_plan():
    before = review_application_manifests("sample-api", PYTHON, "target-a")
    after = review_application_manifests("sample-api", PYTHON, "target-b")
    assert before["plan_digest"] == after["plan_digest"]
    assert before["handoff_request"]["request_digest"] != after["handoff_request"]["request_digest"]


def test_changed_declared_dependencies_change_plan_and_handoff():
    before = review_application_manifests("sample-api", PYTHON, "target-a")
    after = review_application_manifests(
        "sample-api", {"requirements.txt": "redis>=5\n"}, "target-a"
    )
    assert before["plan_digest"] != after["plan_digest"]
    assert before["handoff_request"]["request_digest"] != after["handoff_request"]["request_digest"]


@pytest.mark.parametrize("manifests", [
    {}, {"Dockerfile": "FROM python:3.11"},
    {"requirements.txt": ""}, {"requirements.txt": "a" * 65537},
    {"requirements.txt": "\ud800"},
    {"package.json": '{"dependencies":'},
    {"pyproject.toml": "[project\n"},
    {"package.json": "{}","requirements.txt": "redis"},
])
def test_unsafe_or_ambiguous_manifests_fail_closed(manifests):
    with pytest.raises(ValueError):
        review_application_manifests("sample-api", manifests, "target-a")


@pytest.mark.parametrize("name,target", [
    ("", "target"), ("../escape", "target"), ("x" * 65, "target"),
    ("app", ""), ("app", "https://example.com"), ("app", "a\nb"),
])
def test_invalid_opaque_identifiers_fail_closed(name, target):
    with pytest.raises(ValueError):
        review_application_manifests(name, PYTHON, target)


def test_real_manifest_cli_is_repeatable_and_redacts_raw_text(tmp_path):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text(PYTHON["requirements.txt"], encoding="utf-8")
    args = [sys.executable, "-m", "cloudforge.application_demo",
            "--name", "sample-api", "--target", "review-staging",
            "--manifest", str(manifest)]
    first = subprocess.run(args, capture_output=True, text=True, check=True, timeout=20)
    second = subprocess.run(args, capture_output=True, text=True, check=True, timeout=20)
    assert first.stdout == second.stdout
    assert first.stderr == ""
    payload = json.loads(first.stdout)
    assert payload == review_application_manifests("sample-api", PYTHON, "review-staging")
    assert "do-not-leak" not in first.stdout
    assert manifest.read_text(encoding="utf-8") == PYTHON["requirements.txt"]


def test_cli_rejects_duplicate_basename_and_invalid_utf8(tmp_path):
    first = tmp_path / "requirements.txt"
    first.write_text("redis\n", encoding="utf-8")
    args = [sys.executable, "-m", "cloudforge.application_demo",
            "--name", "app", "--target", "target"]
    repeated = subprocess.run(
        args + ["--manifest", str(first), "--manifest", str(first)],
        capture_output=True, text=True, timeout=20
    )
    assert repeated.returncode != 0
    assert repeated.stdout == ""
    assert "duplicate" in repeated.stderr
    first.write_bytes(b"\xff")
    invalid = subprocess.run(
        args + ["--manifest", str(first)],
        capture_output=True, text=True, timeout=20
    )
    assert invalid.returncode != 0
    assert invalid.stdout == ""
    assert "UTF-8" in invalid.stderr


def test_cli_rejects_symlink_selected_manifest(tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("redis\n", encoding="utf-8")
    selected = tmp_path / "requirements.txt"
    selected.symlink_to(real)
    completed = subprocess.run(
        [sys.executable, "-m", "cloudforge.application_demo",
         "--name", "app", "--target", "target", "--manifest", str(selected)],
        capture_output=True, text=True, timeout=20,
    )
    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "symlink" in completed.stderr


def test_no_network_or_process_execution_in_pure_review(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("demo review must not execute or contact providers")
    with monkeypatch.context() as guard:
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(subprocess, "run", forbidden)
        guard.setattr(os, "system", forbidden)
        payload = review_application_manifests("app", PYTHON, "review-target")
    assert payload["infrastructure_mutated"] is False


def test_source_binding_changes_on_same_requirements_with_changed_source_bytes():
    before = review_application_manifests("sample-api", PYTHON, "review-staging")
    after = review_application_manifests(
        "sample-api", {"requirements.txt": PYTHON["requirements.txt"] + "# edited comment\\n"},
        "review-staging",
    )
    # The inferred resources and legacy deployment request are unchanged.
    assert before["plan_digest"] == after["plan_digest"]
    assert before["handoff_request"]["request_digest"] == after["handoff_request"]["request_digest"]
    # The new provenance packet binds the exact manifest bytes, including comments.
    assert before["source_review_binding"]["digest"] != after["source_review_binding"]["digest"]
    assert before["inspection"]["manifest_sha256"] != after["inspection"]["manifest_sha256"]


def test_source_binding_is_recomputable_without_secret_or_approval():
    result = review_application_manifests("sample-api", PYTHON, "review-staging")
    binding = result["source_review_binding"]
    import hashlib
    payload = {key: value for key, value in binding.items() if key not in {"digest", "status"}}
    expected = hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")).hexdigest()
    assert binding["digest"] == expected
    assert binding["status"] == "review-only-not-approved"
    assert binding["manifest_sha256"] == result["inspection"]["manifest_sha256"]
    assert binding["handoff_request_digest"] == result["handoff_request"]["request_digest"]
    assert result["authenticated_review"] is False
    assert result["infrastructure_mutated"] is False


def test_source_binding_is_independent_of_manifest_insertion_order():
    one = {"requirements.txt": "redis>=5\\n", "pyproject.toml": "[project]\\ndependencies = []\\n"}
    two = dict(reversed(list(one.items())))
    first = review_application_manifests("app", one, "review-target")
    second = review_application_manifests("app", two, "review-target")
    assert first == second
    assert first["source_review_binding"]["digest"] == second["source_review_binding"]["digest"]


def test_source_binding_changes_with_target_even_when_manifest_is_unchanged():
    first = review_application_manifests("app", PYTHON, "review-a")
    second = review_application_manifests("app", PYTHON, "review-b")
    assert first["source_review_binding"]["digest"] != second["source_review_binding"]["digest"]
    assert first["inspection"]["manifest_sha256"] == second["inspection"]["manifest_sha256"]


def test_source_binding_does_not_expose_manifest_comment_text():
    result = review_application_manifests("app", PYTHON, "review-target")
    assert "do-not-leak" not in json.dumps(result["source_review_binding"])
    assert set(result["source_review_binding"]["manifest_sha256"]) == {"requirements.txt"}
