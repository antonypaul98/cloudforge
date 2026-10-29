"""Opt-in real first-party application process observation and restart demo.

The launched application is a fixed CloudForge-owned reference service, NOT
the caller's manifest application. This uses a child process, not an OS sandbox.
It never runs manifest scripts or contacts external infrastructure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import select
import subprocess
import sys
import tempfile

from .application_demo import _load_selected_manifests, review_application_manifests
from .deployment import DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request
from .iac import render_iac_proposal
from .inspector import inspect_application
from .local_adapter import LocalExecutionApproval, authorize_local_execution, prepare_local_execution_request
from .observation_http import LoopbackHTTPProbeTarget, collect_loopback_http_samples
from .observation_plan import ObservationProbe, prepare_observation_plan
from .planner import derive_requirements


def _reference_sha256() -> str:
    path = Path(__file__).with_name("demo_owned_app_service.py")
    if path.is_symlink() or not path.is_file():
        raise ValueError("first-party reference application source is unavailable")
    raw = path.read_bytes()
    if not raw or len(raw) > 65_536:
        raise ValueError("first-party reference application source size is invalid")
    return hashlib.sha256(raw).hexdigest()


def _stop_owned_app(process: subprocess.Popen[str]) -> None:
    try:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            raise RuntimeError("reference app did not terminate gracefully")
    finally:
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()


def _start_owned_app(cwd: str) -> tuple[subprocess.Popen[str], int]:
    # No caller-controlled executable, module, host, port, arguments, or
    # inherited environment secrets. No external network or provider calls.
    process = subprocess.Popen(
        [sys.executable, "-m", "cloudforge.demo_owned_app_service"],
        cwd=cwd,
        env={
            "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
            "PYTHONUNBUFFERED": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, close_fds=True,
    )
    try:
        if process.stdout is None or not select.select([process.stdout], [], [], 5)[0]:
            raise RuntimeError("owned reference app did not become ready")
        port_text = process.stdout.readline().strip()
        if not port_text.isascii() or not port_text.isdecimal():
            raise RuntimeError("owned reference app emitted an invalid port")
        port = int(port_text)
        if not 1 <= port <= 65535 or process.poll() is not None:
            raise RuntimeError("owned reference app did not start safely")
        return process, port
    except Exception:
        _stop_owned_app(process)
        raise


def run_owned_reference_process_demo(
    name: str, manifests: dict[str, str], target_id: str, *,
    allow_owned_reference_app: bool = False,
) -> dict[str, object]:
    """Measure real HEAD pass -> process-down -> restarted pass.

    Synthetic fixture approvals are not human authentication. This is a
    reference app subprocess, not the reviewed application or isolated Docker.
    """
    if allow_owned_reference_app is not True:
        raise ValueError("explicit owned reference app opt-in is required")
    review = review_application_manifests(name, manifests, target_id)
    source_sha = _reference_sha256()
    inspected = inspect_application(name, manifests)
    plan = derive_requirements(inspected.profile)
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, target_id)
    if request.digest != review["handoff_request"]["request_digest"]:
        raise ValueError("review and handoff provenance differ")

    # This is a review packet for the fixed reference service, not executable
    # bytes from the caller's selected manifest.
    artifact = json.dumps({
        "source_review_binding_digest": review["source_review_binding"]["digest"],
        "reference_service_sha256": source_sha,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    handoff = authorize_deployment_handoff(
        plan, proposal, request,
        DeploymentApproval(request.digest, "synthetic-owned-demo-reviewer"),
    )
    local_request = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(
        local_request.digest, "synthetic-owned-demo-reviewer",
    )
    receipt = authorize_local_execution(handoff, artifact, local_request, approval)
    observation_plan = prepare_observation_plan(
        handoff, artifact, approval, receipt,
        (ObservationProbe("readiness", 5, 2, 1),
         ObservationProbe("liveness", 5, 2, 1)),
    )

    def observe(port: int, phase: str, expected: str) -> dict[str, object]:
        targets = (
            LoopbackHTTPProbeTarget("readiness", "127.0.0.1", port, "/health"),
            LoopbackHTTPProbeTarget("liveness", "127.0.0.1", port, "/health"),
        )
        samples = collect_loopback_http_samples(
            handoff, artifact, approval, receipt, observation_plan,
            targets, allowed_targets=targets,
        )
        if len(samples) != 2 or any(sample.outcome != expected for sample in samples):
            raise RuntimeError("reference app did not exhibit expected process health")
        return {
            "phase": phase,
            "samples": [
                {"kind": sample.kind, "outcome": sample.outcome}
                for sample in samples
            ],
        }

    # The reference module is rehashed before and after process execution.
    # This detects changes across this demo, not atomic source execution or
    # independent provenance authentication.
    trace: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="cloudforge-owned-app-") as cwd:
        if _reference_sha256() != source_sha:
            raise RuntimeError("reference application source changed")
        first, first_port = _start_owned_app(cwd)
        try:
            trace.append(observe(first_port, "running", "pass"))
        finally:
            _stop_owned_app(first)
        trace.append(observe(first_port, "process-stopped", "unknown"))
        if _reference_sha256() != source_sha:
            raise RuntimeError("reference application source changed")
        second, second_port = _start_owned_app(cwd)
        try:
            trace.append(observe(second_port, "process-restarted", "pass"))
        finally:
            _stop_owned_app(second)
    if _reference_sha256() != source_sha:
        raise RuntimeError("reference application source changed")

    return {
        "demo_only": True,
        "application": name,
        "target_id": target_id,
        "source_review_binding_digest": review["source_review_binding"]["digest"],
        "handoff_request_digest": request.digest,
        "reference_service_sha256": source_sha,
        "reference_process_observation": trace,
        "reference_process_stopped": True,
        "reference_process_restarted": True,
        "reference_application_executed": True,
        "reviewed_application_executed": False,
        "authenticated_review": False,
        "isolated_sandbox": False,
        "deployment_observed": False,
        "infrastructure_recovery_performed": False,
        "infrastructure_mutated": False,
        "limitations": [
            "Executed only the fixed first-party reference app, not the reviewed manifest application.",
            "A child process is not an isolated sandbox; no untrusted code may be supplied.",
            "Synthetic fixture approvals are not authenticated human authorization.",
            "Process restart is not infrastructure deployment, rollback, or production recovery.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Observe and restart an owned reference application process",
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument("--allow-owned-reference-app", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = run_owned_reference_process_demo(
            args.name, _load_selected_manifests(args.manifest), args.target,
            allow_owned_reference_app=args.allow_owned_reference_app,
        )
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        parser.error(str(exc))
    sys.stdout.write(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
