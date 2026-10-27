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
        "stale_approval_replay": True,
        "stale_plan_approval_replay": True,
        "forged_receipt_reviewer": True,
        "cross_target_authorization": True,
        "forged_mutation_evidence": True,
        "forged_observation_evidence": True,
        "forged_recovery_evidence": True,
        "forged_request_digest": True,
        "forged_receipt_digest": True,
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


def test_synthetic_demo_rejects_replayed_approval_for_new_artifact_request():
    """Changed bytes with a fresh request still require fresh approval."""
    result = run_synthetic_local_authorization_demo()
    assert result["synthetic_rejections"]["stale_approval_replay"] is True
    assert result["authenticated_review"] is False
    assert result["infrastructure_mutated"] is False


def test_synthetic_demo_rejects_replayed_approval_for_changed_plan():
    """Fresh plan/handoff for the same artifact still requires new approval."""
    result = run_synthetic_local_authorization_demo()
    assert result["synthetic_rejections"]["stale_plan_approval_replay"] is True
    assert result["authenticated_review"] is False
    assert result["infrastructure_mutated"] is False


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



def test_synthetic_demo_rejects_forged_provenance_digests():
    """A local audit must not accept another request or receipt fingerprint."""
    result = run_synthetic_local_authorization_demo()
    assert result["synthetic_rejections"]["forged_request_digest"] is True
    assert result["synthetic_rejections"]["forged_receipt_digest"] is True
    event = result["redacted_audit_event"]
    assert len(event["request_digest"]) == 64
    assert len(event["receipt_sha256"]) == 64
    assert event["infrastructure_mutated"] is False
    assert result["deployment_observed"] is False
    assert result["recovery_performed"] is False

def test_synthetic_demo_does_not_mutate_local_files(monkeypatch):
    """A credential-free authorization demonstration must remain read-only."""
    import builtins
    import io
    from pathlib import Path

    def forbidden(*args, **kwargs):
        raise AssertionError("synthetic authorization must not mutate local files")

    def guarded_open(opener):
        def check(file, mode="r", *args, **kwargs):
            if any(flag in mode for flag in ("w", "a", "x", "+")):
                forbidden()
            return opener(file, mode, *args, **kwargs)
        return check

    original_os_open = os.open

    def guarded_os_open(path, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            forbidden()
        return original_os_open(path, flags, *args, **kwargs)

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", guarded_open(builtins.open))
        guard.setattr(io, "open", guarded_open(io.open))
        guard.setattr(os, "open", guarded_os_open)
        for name in ("remove", "unlink", "rename", "replace", "mkdir", "makedirs", "rmdir"):
            guard.setattr(os, name, forbidden)
        for name in ("write_text", "write_bytes", "touch", "unlink", "mkdir", "rename", "replace"):
            guard.setattr(Path, name, forbidden)
        result = run_synthetic_local_authorization_demo()
    assert result["demo_only"] is True
    assert result["infrastructure_mutated"] is False

def test_synthetic_demo_does_not_launch_direct_os_processes(monkeypatch):
    """Guard os-level process launches not covered by subprocess entry points."""
    def forbidden(*args, **kwargs):
        raise AssertionError("synthetic authorization must not launch processes")

    with monkeypatch.context() as guard:
        for name in (
            "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp",
            "spawnl", "spawnle", "spawnlp", "spawnlpe",
            "spawnv", "spawnve", "spawnvp", "spawnvpe",
            "execl", "execle", "execlp", "execlpe",
            "execv", "execve", "execvp", "execvpe",
        ):
            if hasattr(os, name):
                guard.setattr(os, name, forbidden)
        result = run_synthetic_local_authorization_demo()
    assert result["demo_only"] is True
    assert result["infrastructure_mutated"] is False


def test_synthetic_demo_cli_is_independent_of_synthetic_provider_credentials():
    """Provider-like environment settings must not change or leak into the demo."""
    import sys

    synthetic_secrets = {
        "AWS_ACCESS_KEY_ID": "cloudforge-test-access-id-not-real",
        "AWS_SECRET_ACCESS_KEY": "cloudforge-test-secret-key-not-real",
        "OPENAI_API_KEY": "cloudforge-test-openai-key-not-real",
        "CLOUDFORGE_TARGET": "cloudforge-test-external-target-not-real",
    }
    environment = dict(os.environ)
    environment.update(synthetic_secrets)
    completed = subprocess.run(
        [sys.executable, "-m", "cloudforge.synthetic_demo"],
        check=True, capture_output=True, text=True, timeout=20,
        env=environment,
    )
    expected = json.dumps(
        run_synthetic_local_authorization_demo(), sort_keys=True, indent=2
    ) + "\n"
    assert completed.stderr == ""
    assert completed.stdout == expected
    assert all(value not in completed.stdout for value in synthetic_secrets.values())
