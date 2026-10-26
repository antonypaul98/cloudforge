"""End-to-end synthetic acceptance without a provider, credentials or hardware."""
import json
import os
import socket
import subprocess

from cloudforge.synthetic_demo import run_synthetic_local_authorization_demo


def test_synthetic_demo_is_deterministic_redacted_and_fail_closed():
    first = run_synthetic_local_authorization_demo()
    assert first == run_synthetic_local_authorization_demo()
    assert first["demo_only"] is True
    assert first["authenticated_review"] is False
    assert first["infrastructure_mutated"] is False
    assert first["deployment_observed"] is False
    assert first["recovery_performed"] is False
    assert first["synthetic_rejections"] == {
        "forged_recovery_status": True,
        "changed_artifact": True,
    }
    event = first["redacted_audit_event"]
    assert event["status"] == "authorized-local-only"
    assert event["infrastructure_mutated"] is False
    assert len(event["receipt_sha256"]) == 64
    assert len(event["request_digest"]) == 64
    text = json.dumps(first, sort_keys=True)
    for secret_or_identity in (
        "synthetic-handoff-reviewer",
        "synthetic-execution-reviewer",
        "synthetic-target",
        "cloudforge-synthetic-artifact-v1",
        "ready-for-adapter-review",
    ):
        assert secret_or_identity not in text


def test_synthetic_demo_does_not_use_network_or_shell(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("synthetic authorization must not use network or shell")

    with monkeypatch.context() as guard:
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(subprocess, "run", forbidden)
        guard.setattr(os, "system", forbidden)
        result = run_synthetic_local_authorization_demo()
    assert result["infrastructure_mutated"] is False
