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
        "forged_receipt_reviewer": True,
        "cross_target_authorization": True,
        "forged_mutation_evidence": True,
        "forged_observation_evidence": True,
        "forged_recovery_evidence": True,
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
        "forged-reviewer",
        "synthetic-other-target",
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

def test_synthetic_demo_cli_entrypoint_emits_canonical_redacted_json():
    """Verify the documented python -m entry point, not only its Python API."""
    import sys

    completed = subprocess.run(
        [sys.executable, "-m", "cloudforge.synthetic_demo"],
        check=True, capture_output=True, text=True, timeout=20,
    )
    assert completed.stderr == ""
    expected = json.dumps(
        run_synthetic_local_authorization_demo(), sort_keys=True, indent=2
    ) + "\n"
    assert completed.stdout == expected
    payload = json.loads(completed.stdout)
    assert payload["demo_only"] is True
    assert payload["authenticated_review"] is False
    assert payload["infrastructure_mutated"] is False
    assert payload["deployment_observed"] is False
    assert payload["recovery_performed"] is False


def test_synthetic_demo_rejects_forged_infrastructure_mutation_claim():
    """A redacted local authorization audit cannot be upgraded to deployment proof."""
    result = run_synthetic_local_authorization_demo()
    assert result["synthetic_rejections"]["forged_mutation_evidence"] is True
    assert result["redacted_audit_event"]["infrastructure_mutated"] is False
    assert result["deployment_observed"] is False
    assert result["recovery_performed"] is False



def test_synthetic_demo_rejects_forged_observation_and_recovery_claims():
    """Local authorization audit evidence cannot claim observed or recovered."""
    result = run_synthetic_local_authorization_demo()
    assert result["synthetic_rejections"]["forged_observation_evidence"] is True
    assert result["synthetic_rejections"]["forged_recovery_evidence"] is True
    event = result["redacted_audit_event"]
    assert "deployment_observed" not in event
    assert "recovery_performed" not in event
    assert result["deployment_observed"] is False
    assert result["recovery_performed"] is False
