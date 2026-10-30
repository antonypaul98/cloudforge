"""Owned first-party source package -> Linux namespace -> real HEAD health.

The namespace integration tests run only on Linux environments supporting
unprivileged user namespaces; unsupported CI runners report an explicit skip.
No caller-selected source or external endpoint is ever executed.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

import cloudforge.demo_owned_namespace_source as demo


MANIFEST = {"requirements.txt": "redis>=5\n# SECRET=never-print\n"}
TRACE = [
    {"phase": "running", "outcome": "pass"},
    {"phase": "process-stopped", "outcome": "unknown"},
    {"phase": "process-restarted", "outcome": "pass"},
]


def _requires_linux_namespaces():
    if sys.platform != "linux" or not Path("/usr/bin/unshare").is_file():
        pytest.skip("Linux unshare is unavailable")
    preflight = subprocess.run(
        ["/usr/bin/unshare", "--user", "--map-root-user", "--net",
         "--mount", "--pid", "--fork", "/bin/true"],
        capture_output=True, timeout=10,
    )
    if preflight.returncode:
        pytest.skip("unprivileged Linux namespaces are unavailable")


def test_real_namespaced_owned_source_health_and_cleanup():
    _requires_linux_namespaces()
    result = demo.run_owned_namespace_source_demo(
        "app", MANIFEST, "fixture-target", allow_owned_namespace=True,
    )
    assert result["observed_health"] == TRACE
    assert result["owned_first_party_source_executed"] is True
    assert result["owned_namespace_fixture_completed"] is True
    for field in (
        "caller_selected_application_executed", "independent_operator_approval",
        "signed_runtime_evidence", "production_sandbox_attested",
        "real_infrastructure_mutated", "real_deployment_or_recovery",
    ):
        assert result[field] is False
    assert "never-print" not in json.dumps(result)


def test_real_namespaced_source_review_changes_without_health_change():
    _requires_linux_namespaces()
    original = demo.run_owned_namespace_source_demo(
        "app", MANIFEST, "fixture-target", allow_owned_namespace=True,
    )
    changed = demo.run_owned_namespace_source_demo(
        "app", {"requirements.txt": MANIFEST["requirements.txt"] + "# changed\n"},
        "fixture-target", allow_owned_namespace=True,
    )
    assert original["package_sha256"] != changed["package_sha256"]
    assert original["selected_source_binding_digest"] != changed["selected_source_binding_digest"]
    assert original["observed_health"] == changed["observed_health"] == TRACE


def test_opt_in_rejected_before_any_process(monkeypatch):
    monkeypatch.setattr(demo.subprocess, "run", lambda *_a, **_k: pytest.fail("must not spawn"))
    with pytest.raises(ValueError, match="opt-in"):
        demo.run_owned_namespace_source_demo("app", MANIFEST, "fixture-target")


@pytest.mark.parametrize("bad", [
    {}, {"package.json": '{"dependencies":'},
    {"requirements.txt": "\ud800"}, {"Dockerfile": "FROM python"},
])
def test_invalid_manifests_fail_before_process(monkeypatch, bad):
    monkeypatch.setattr(demo.subprocess, "run", lambda *_a, **_k: pytest.fail("must not spawn"))
    with pytest.raises(ValueError):
        demo.run_owned_namespace_source_demo(
            "app", bad, "fixture-target", allow_owned_namespace=True,
        )


def test_package_verification_failure_fails_closed(monkeypatch):
    def invalid(*_args, **_kwargs):
        raise ValueError("package verification rejected")
    monkeypatch.setattr(demo, "verify_selected_source_package", invalid)
    monkeypatch.setattr(demo.subprocess, "run", lambda *_a, **_k: pytest.fail("must not spawn"))
    with pytest.raises(ValueError, match="package verification rejected"):
        demo.run_owned_namespace_source_demo(
            "app", MANIFEST, "fixture-target", allow_owned_namespace=True,
        )


def test_fixed_unshare_command_and_restricted_environment(monkeypatch):
    observed = {}
    def fake_run(argv, **kwargs):
        observed["argv"] = argv
        observed["kwargs"] = kwargs
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"trace": TRACE}), stderr="")
    monkeypatch.setattr(demo.subprocess, "run", fake_run)
    result = demo.run_owned_namespace_source_demo(
        "app", MANIFEST, "fixture-target", allow_owned_namespace=True,
    )
    assert result["observed_health"] == TRACE
    assert observed["argv"][:8] == [
        "/usr/bin/unshare", "--user", "--map-root-user", "--net",
        "--mount", "--pid", "--fork", "--kill-child",
    ]
    assert observed["argv"][8] == "/bin/sh"
    assert len(observed["argv"]) == 14
    assert observed["argv"][12] == result["first_party_source_sha256"]
    assert observed["argv"][13] == hashlib.sha256(demo._owned_file(
        Path(demo.__file__).with_name("demo_namespace_observer.py")
    )).hexdigest()
    assert observed["kwargs"]["env"] == {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"}
    assert observed["kwargs"]["timeout"] == 40
    assert observed["kwargs"]["stdin"] == subprocess.DEVNULL
    assert "SECRET" not in str(observed["argv"])


@pytest.mark.parametrize("status,output", [
    (1, ""), (0, "not-json"), (0, json.dumps({"trace": []})),
    (0, json.dumps({"trace": TRACE, "secret": "unexpected"})),
])
def test_fail_closed_on_bad_namespace_result(monkeypatch, status, output):
    monkeypatch.setattr(demo.subprocess, "run", lambda argv, **kwargs:
                        subprocess.CompletedProcess(argv, status, stdout=output, stderr="SECRET"))
    with pytest.raises(RuntimeError) as error:
        demo.run_owned_namespace_source_demo(
            "app", MANIFEST, "fixture-target", allow_owned_namespace=True,
        )
    assert "SECRET" not in str(error.value)


def test_no_arbitrary_source_execution_api():
    import inspect
    signature = inspect.signature(demo.run_owned_namespace_source_demo)
    assert "source" not in signature.parameters
    assert "command" not in signature.parameters
    assert "endpoint" not in signature.parameters


@pytest.mark.parametrize("changed", ["app.py", "observer.py"])
def test_stage_hash_mismatch_rejected_before_mount(tmp_path, changed):
    """Real shell preflight refuses swapped bytes without invoking mount."""
    if sys.platform != "linux":
        pytest.skip("fixed Linux namespace fixture requires Linux")
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "app.py").write_bytes(b"original app\\n")
    (stage / "observer.py").write_bytes(b"original observer\\n")
    hashes = [hashlib.sha256((stage / name).read_bytes()).hexdigest()
              for name in ("app.py", "observer.py")]
    (stage / changed).write_bytes(b"tampered source\\n")
    script = Path(demo.__file__).resolve().parents[2] / "scripts" / "owned_namespace_fixture.sh"
    result = subprocess.run(
        ["/bin/sh", str(script), str(tmp_path / "root"), str(stage), *hashes],
        capture_output=True, text=True, timeout=5,
        env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"},
    )
    assert result.returncode != 0
    assert result.stdout == ""
    assert not (tmp_path / "root").exists()
