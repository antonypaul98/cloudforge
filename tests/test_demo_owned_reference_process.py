"""Real first-party reference process checks; no user app or infrastructure."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import cloudforge.demo_owned_reference_process as module
from cloudforge.demo_owned_reference_process import run_owned_reference_process_demo


MANIFEST = {"requirements.txt": "redis>=5\n# PRIVATE=do-not-print\n"}


def _trace():
    return [
        {"phase": "running", "samples": [
            {"kind": "readiness", "outcome": "pass"},
            {"kind": "liveness", "outcome": "pass"},
        ]},
        {"phase": "process-stopped", "samples": [
            {"kind": "readiness", "outcome": "unknown"},
            {"kind": "liveness", "outcome": "unknown"},
        ]},
        {"phase": "process-restarted", "samples": [
            {"kind": "readiness", "outcome": "pass"},
            {"kind": "liveness", "outcome": "pass"},
        ]},
    ]


def test_real_owned_reference_process_failure_and_restart():
    payload = run_owned_reference_process_demo(
        "app", MANIFEST, "local-demo", allow_owned_reference_app=True,
    )
    assert payload["reference_process_observation"] == _trace()
    assert payload["reference_application_executed"] is True
    assert payload["reference_process_restarted"] is True
    assert payload["reference_process_stopped"] is True
    for key in ("reviewed_application_executed", "authenticated_review",
                "isolated_sandbox", "deployment_observed",
                "infrastructure_recovery_performed", "infrastructure_mutated"):
        assert payload[key] is False
    assert "do-not-print" not in json.dumps(payload)
    path = Path(module.__file__).with_name("demo_owned_app_service.py")
    assert payload["reference_service_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_repeatable_output_and_exact_manifest_binding():
    first = run_owned_reference_process_demo(
        "app", MANIFEST, "local-demo", allow_owned_reference_app=True,
    )
    again = run_owned_reference_process_demo(
        "app", MANIFEST, "local-demo", allow_owned_reference_app=True,
    )
    changed = run_owned_reference_process_demo(
        "app", {"requirements.txt": MANIFEST["requirements.txt"] + "# changed\n"},
        "local-demo", allow_owned_reference_app=True,
    )
    assert first == again
    assert first["reference_process_observation"] == changed["reference_process_observation"]
    assert first["source_review_binding_digest"] != changed["source_review_binding_digest"]


def test_explicit_opt_in_required_before_process(monkeypatch):
    monkeypatch.setattr(module.subprocess, "Popen",
                        lambda *_a, **_kw: pytest.fail("must not spawn"))
    with pytest.raises(ValueError, match="opt-in"):
        run_owned_reference_process_demo("app", MANIFEST, "local-demo")


@pytest.mark.parametrize("bad", [
    {}, {"Dockerfile": "FROM python:3.11"},
    {"package.json": '{"dependencies":'},
    {"requirements.txt": "\ud800"},
])
def test_bad_manifest_fails_before_process(monkeypatch, bad):
    monkeypatch.setattr(module.subprocess, "Popen",
                        lambda *_a, **_kw: pytest.fail("must not spawn"))
    with pytest.raises(ValueError):
        run_owned_reference_process_demo(
            "app", bad, "local-demo", allow_owned_reference_app=True,
        )


def test_reference_source_preflight_before_process(monkeypatch):
    monkeypatch.setattr(module, "_reference_sha256",
                        lambda: (_ for _ in ()).throw(ValueError("source unavailable")))
    monkeypatch.setattr(module.subprocess, "Popen",
                        lambda *_a, **_kw: pytest.fail("must not spawn"))
    with pytest.raises(ValueError, match="source unavailable"):
        run_owned_reference_process_demo(
            "app", MANIFEST, "local-demo", allow_owned_reference_app=True,
        )


def test_child_is_fixed_module_with_minimal_environment(monkeypatch):
    real_popen = subprocess.Popen
    seen = []

    def checked(args, **kwargs):
        assert args == [sys.executable, "-m", "cloudforge.demo_owned_app_service"]
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert kwargs["close_fds"] is True
        assert set(kwargs["env"]) == {
            "PYTHONPATH", "PYTHONUNBUFFERED", "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE",
        }
        seen.append(True)
        return real_popen(args, **kwargs)

    monkeypatch.setattr(module.subprocess, "Popen", checked)
    result = run_owned_reference_process_demo(
        "app", MANIFEST, "local-demo", allow_owned_reference_app=True,
    )
    assert result["reference_process_stopped"] is True
    assert len(seen) == 2


def test_only_numeric_loopback_head_connections(monkeypatch):
    import cloudforge.observation_http as http_module
    original = http_module.http.client.HTTPConnection
    seen = []

    def checked(host, port, *args, **kwargs):
        assert host == "127.0.0.1"
        assert type(port) is int and 1 <= port <= 65535
        seen.append((host, port))
        return original(host, port, *args, **kwargs)

    monkeypatch.setattr(http_module.http.client, "HTTPConnection", checked)
    run_owned_reference_process_demo(
        "app", MANIFEST, "local-demo", allow_owned_reference_app=True,
    )
    assert len(seen) == 6


def test_cli_opt_in_and_redacted_observation(tmp_path):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text(MANIFEST["requirements.txt"], encoding="utf-8")
    args = [
        sys.executable, "-m", "cloudforge.demo_owned_reference_process",
        "--name", "app", "--target", "local-demo", "--manifest", str(manifest),
    ]
    denied = subprocess.run(args, capture_output=True, text=True, timeout=20)
    assert denied.returncode != 0
    assert denied.stdout == ""
    assert "opt-in" in denied.stderr
    accepted = subprocess.run(
        args + ["--allow-owned-reference-app"],
        capture_output=True, text=True, timeout=25, check=True,
    )
    assert accepted.stderr == ""
    payload = json.loads(accepted.stdout)
    assert payload["reference_process_observation"] == _trace()
    assert "do-not-print" not in accepted.stdout
