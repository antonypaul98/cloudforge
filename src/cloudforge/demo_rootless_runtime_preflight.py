"""Non-executing preflight for a *local* rootless Podman trial.

This is a capability hint, not a sandbox attestation, independent approval,
container execution, signed observation, or permission to deploy.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys


def inspect_rootless_oci_candidate() -> dict[str, bool | str]:
    """Fail closed on unsupported hosts without starting or pulling a container.

    Probe only a local Podman installation in fixed system executable paths.
    Never return Podman output, host paths, environment values or credentials.
    Even a positive result MUST NOT authorize running selected application code.
    """
    def result(candidate: bool, reason: str) -> dict[str, bool | str]:
        return {
            "runtime": "podman",
            "candidate_for_isolated_fixture_trial": candidate,
            "reason": reason,
            "isolation_attested": False,
            "selected_application_executed": False,
            "authenticated_operator_approval": False,
            "infrastructure_mutated": False,
        }

    if sys.platform != "linux" or os.geteuid() == 0:
        return result(False, "nonroot-linux-required")
    binary = shutil.which("podman", path="/usr/local/bin:/usr/bin:/bin")
    if binary is None or not os.path.isabs(binary):
        return result(False, "local-podman-unavailable")

    # Never inherit CONTAINER_HOST/CONTAINER_CONNECTION or unrelated secrets.
    # --remote=false is explicit: a remote Podman machine is not local isolation.
    env = {key: os.environ[key] for key in (
        "HOME", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "TMPDIR",
    ) if key in os.environ}
    env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
    try:
        probe = subprocess.run(
            [binary, "--remote=false", "info", "--format=json"],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            check=False, timeout=6, env=env,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return result(False, "local-podman-probe-unavailable")
    if probe.returncode != 0 or len(probe.stdout) > 32768:
        return result(False, "local-podman-probe-unavailable")
    try:
        info = json.loads(probe.stdout)
    except (ValueError, TypeError):
        return result(False, "local-podman-info-invalid")
    if type(info) is not dict or type(info.get("host")) is not dict:
        return result(False, "local-podman-info-invalid")
    host = info["host"]
    security = host.get("security")
    if type(security) is not dict:
        return result(False, "local-podman-info-invalid")
    if (security.get("rootless") is not True
            or security.get("seccompEnabled") is not True
            or host.get("cgroupVersion") != "v2"):
        return result(False, "rootless-security-prerequisites-unverified")
    return result(True, "preflight-only-not-authorization")
