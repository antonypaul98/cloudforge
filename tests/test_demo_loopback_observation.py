"""Real HEAD/fixture-failure/restore integration, not real application deployment."""
import json
import os
import socket
import subprocess
import sys

import pytest

from cloudforge.application_demo import review_application_manifests
from cloudforge.demo_loopback_observation import run_loopback_observation_demo


PYTHON = {"requirements.txt": "postgresql>=16\nredis>=5\n# PRIVATE=never-print\n"}
NODE = {"package.json": '{"dependencies":{"redis":"^5","express":"^4"}}'}


def _expected_trace():
    return [
        {"phase": "initial", "samples": [
            {"kind": "readiness", "outcome": "pass"},
            {"kind": "liveness", "outcome": "pass"},
        ]},
        {"phase": "fixture-failure", "samples": [
            {"kind": "readiness", "outcome": "fail"},
            {"kind": "liveness", "outcome": "fail"},
        ]},
        {"phase": "fixture-restored", "samples": [
            {"kind": "readiness", "outcome": "pass"},
            {"kind": "liveness", "outcome": "pass"},
        ]},
    ]


@pytest.mark.parametrize("manifests", [PYTHON, NODE])
def test_real_manifest_review_to_real_owned_loopback_head(manifests):
    payload = run_loopback_observation_demo(
        "app", manifests, "fixture-target", allow_fixture=True,
    )
    review = review_application_manifests("app", manifests, "fixture-target")
    assert payload["source_review_binding_digest"] == review["source_review_binding"]["digest"]
    assert payload["handoff_request_digest"] == review["handoff_request"]["request_digest"]
    assert payload["fixture_observation"] == _expected_trace()
    assert payload["fixture_server_stopped"] is True
    assert payload["fixture_behavior_observed"] is True
    assert payload["fixture_fault_injected"] is True
    for key in ("authenticated_review", "application_executed", "deployment_observed",
                "recovery_performed", "infrastructure_mutated"):
        assert payload[key] is False
    assert "never-print" not in json.dumps(payload)


def test_repeatable_output_and_source_byte_binding():
    first = run_loopback_observation_demo("app", PYTHON, "fixture-target", allow_fixture=True)
    second = run_loopback_observation_demo("app", PYTHON, "fixture-target", allow_fixture=True)
    altered = run_loopback_observation_demo(
        "app", {"requirements.txt": PYTHON["requirements.txt"] + "# changed\n"},
        "fixture-target", allow_fixture=True,
    )
    assert first == second
    assert first["fixture_observation"] == altered["fixture_observation"]
    assert first["source_review_binding_digest"] != altered["source_review_binding_digest"]
    assert first["handoff_request_digest"] == altered["handoff_request_digest"]


def test_requires_explicit_opt_in_before_socket(monkeypatch):
    import cloudforge.demo_loopback_observation as module
    monkeypatch.setattr(module, "ThreadingHTTPServer",
                        lambda *_a, **_kw: pytest.fail("must not open socket"))
    with pytest.raises(ValueError, match="opt-in"):
        run_loopback_observation_demo("app", PYTHON, "fixture-target")


@pytest.mark.parametrize("manifests", [
    {}, {"Dockerfile": "FROM python:3.11"},
    {"requirements.txt": "\ud800"},
    {"package.json": '{"dependencies":'},
])
def test_invalid_real_manifest_fails_before_socket(monkeypatch, manifests):
    import cloudforge.demo_loopback_observation as module
    monkeypatch.setattr(module, "ThreadingHTTPServer",
                        lambda *_a, **_kw: pytest.fail("must not open socket"))
    with pytest.raises(ValueError):
        run_loopback_observation_demo(
            "app", manifests, "fixture-target", allow_fixture=True,
        )


def test_owned_fixture_only_uses_numeric_loopback_http(monkeypatch):
    import cloudforge.observation_http as module
    original = module.http.client.HTTPConnection
    destinations = []

    def restricted(host, port, *args, **kwargs):
        destinations.append((host, port))
        assert host == "127.0.0.1"
        assert type(port) is int and 1 <= port <= 65535
        return original(host, port, *args, **kwargs)

    monkeypatch.setattr(module.http.client, "HTTPConnection", restricted)
    run_loopback_observation_demo("app", PYTHON, "fixture-target", allow_fixture=True)
    assert len(destinations) == 6


def test_no_shell_or_child_process_for_fixture(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("no process execution is permitted")
    with monkeypatch.context() as patch:
        patch.setattr(subprocess, "Popen", forbidden)
        patch.setattr(os, "system", forbidden)
        result = run_loopback_observation_demo(
            "app", PYTHON, "fixture-target", allow_fixture=True,
        )
    assert result["fixture_server_stopped"] is True


def test_cli_requires_opt_in_and_outputs_actual_observations(tmp_path):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text(PYTHON["requirements.txt"], encoding="utf-8")
    args = [
        sys.executable, "-m", "cloudforge.demo_loopback_observation",
        "--name", "app", "--target", "fixture-target", "--manifest", str(manifest),
    ]
    refused = subprocess.run(args, capture_output=True, text=True, timeout=20)
    assert refused.returncode != 0
    assert refused.stdout == ""
    assert "opt-in" in refused.stderr
    accepted = subprocess.run(
        args + ["--allow-loopback-fixture"], capture_output=True,
        text=True, timeout=20, check=True,
    )
    assert accepted.stderr == ""
    payload = json.loads(accepted.stdout)
    assert payload["fixture_observation"] == _expected_trace()
    assert "never-print" not in accepted.stdout
