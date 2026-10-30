"""Synthetic fail-closed checks for the local rootless OCI preflight."""
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from cloudforge import demo_rootless_runtime_preflight as preflight


def _probe(monkeypatch, *, info=None, returncode=0, stdout=None):
    calls = []
    monkeypatch.setattr(preflight.sys, "platform", "linux")
    monkeypatch.setattr(preflight.os, "geteuid", lambda: 1001)
    monkeypatch.setattr(preflight.shutil, "which", lambda *a, **k: "/usr/bin/podman")
    monkeypatch.setenv("CONTAINER_HOST", "ssh://untrusted.example")
    monkeypatch.setenv("CONTAINER_CONNECTION", "remote")
    monkeypatch.setenv("FAKE_PRIVATE_CREDENTIAL", "must-not-leak")
    if info is None:
        info = {"host": {"security": {"rootless": True, "seccompEnabled": True},
                         "cgroupVersion": "v2"}}
    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=returncode,
                               stdout=json.dumps(info) if stdout is None else stdout,
                               stderr="FAKE_PRIVATE_CREDENTIAL=must-not-leak")
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    return calls


def test_valid_local_rootless_candidate_is_only_preflight(monkeypatch):
    calls = _probe(monkeypatch)
    result = preflight.inspect_rootless_oci_candidate()
    assert result["candidate_for_isolated_fixture_trial"] is True
    assert result["isolation_attested"] is False
    assert result["selected_application_executed"] is False
    assert result["authenticated_operator_approval"] is False
    assert result["infrastructure_mutated"] is False
    assert calls[0][0] == ["/usr/bin/podman", "--remote=false", "info", "--format=json"]
    kwargs = calls[0][1]
    assert kwargs["timeout"] == 6
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["check"] is False
    assert "CONTAINER_HOST" not in kwargs["env"]
    assert "CONTAINER_CONNECTION" not in kwargs["env"]
    assert "FAKE_PRIVATE_CREDENTIAL" not in kwargs["env"]
    assert "must-not-leak" not in str(result)


@pytest.mark.parametrize("field,value", [
    ("rootless", False),
    ("rootless", "true"),
    ("seccompEnabled", False),
    ("seccompEnabled", "true"),
])
def test_security_fields_must_be_literal_true(monkeypatch, field, value):
    info = {"host": {"security": {"rootless": True, "seccompEnabled": True},
                     "cgroupVersion": "v2"}}
    info["host"]["security"][field] = value
    _probe(monkeypatch, info=info)
    result = preflight.inspect_rootless_oci_candidate()
    assert result["candidate_for_isolated_fixture_trial"] is False


def test_cgroup_v1_rejected(monkeypatch):
    _probe(monkeypatch, info={"host": {
        "security": {"rootless": True, "seccompEnabled": True},
        "cgroupVersion": "v1",
    }})
    assert not preflight.inspect_rootless_oci_candidate()["candidate_for_isolated_fixture_trial"]


@pytest.mark.parametrize("payload", ["not json", "[]", "{}", '{"host":{}}'])
def test_malformed_info_rejected(monkeypatch, payload):
    _probe(monkeypatch, stdout=payload)
    assert not preflight.inspect_rootless_oci_candidate()["candidate_for_isolated_fixture_trial"]


def test_nonzero_exit_rejected_without_stderr(monkeypatch):
    _probe(monkeypatch, returncode=1)
    result = preflight.inspect_rootless_oci_candidate()
    assert result["reason"] == "local-podman-probe-unavailable"
    assert "must-not-leak" not in str(result)


def test_probe_timeout_rejected(monkeypatch):
    _probe(monkeypatch)
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("podman", 6)
    monkeypatch.setattr(preflight.subprocess, "run", timeout)
    assert not preflight.inspect_rootless_oci_candidate()["candidate_for_isolated_fixture_trial"]


def test_missing_binary_does_not_launch(monkeypatch):
    calls = _probe(monkeypatch)
    monkeypatch.setattr(preflight.shutil, "which", lambda *a, **k: None)
    assert preflight.inspect_rootless_oci_candidate()["reason"] == "local-podman-unavailable"
    assert calls == []


def test_root_or_nonlinux_does_not_launch(monkeypatch):
    calls = _probe(monkeypatch)
    monkeypatch.setattr(preflight.os, "geteuid", lambda: 0)
    assert preflight.inspect_rootless_oci_candidate()["reason"] == "nonroot-linux-required"
    monkeypatch.setattr(preflight.os, "geteuid", lambda: 1001)
    monkeypatch.setattr(preflight.sys, "platform", "darwin")
    assert preflight.inspect_rootless_oci_candidate()["reason"] == "nonroot-linux-required"
    assert calls == []
