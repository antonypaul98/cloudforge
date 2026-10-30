"""Run a fixed first-party source package in a private Linux namespace fixture.

This opt-in checkpoint exercises real OS namespace isolation for a *known*
CloudForge reference source. It NEVER executes caller-selected application
code, authenticates an operator, deploys infrastructure, or approves execution.
Linux user namespaces and chroot are not a security guarantee for untrusted code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from .application_demo import _load_selected_manifests
from .demo_selected_artifact import prepare_selected_artifact
from .demo_source_package import package_selected_source, verify_selected_source_package


_EXPECTED_TRACE = [
    {"phase": "running", "outcome": "pass"},
    {"phase": "process-stopped", "outcome": "unknown"},
    {"phase": "process-restarted", "outcome": "pass"},
]


def _owned_file(path: Path, *, limit: int = 131_072) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("fixed first-party fixture is unavailable")
    raw = path.read_bytes()
    if not 0 < len(raw) <= limit:
        raise ValueError("fixed first-party fixture size is invalid")
    return raw


def run_owned_namespace_source_demo(
    name: str, manifests: dict[str, str], target_id: str, *,
    allow_owned_namespace: bool = False,
) -> dict[str, object]:
    """Exercise an exact-byte *owned* source package in a Linux OS namespace.

    The package's expected hashes are self-consistency checks, NOT an
    independently authenticated approval. The API has no caller source input.
    """
    if allow_owned_namespace is not True:
        raise ValueError("explicit owned namespace opt-in is required")
    if sys.platform != "linux":
        raise RuntimeError("owned namespace fixture requires Linux")
    root = Path(__file__).resolve().parents[2]
    source = _owned_file(Path(__file__).with_name("demo_owned_app_service.py"))
    observer = _owned_file(Path(__file__).with_name("demo_namespace_observer.py"))
    observer_sha = hashlib.sha256(observer).hexdigest()
    script = root / "scripts" / "owned_namespace_fixture.sh"
    _owned_file(script, limit=16_384)

    # Reuse the accepted exact-byte selected-source review package.
    review = prepare_selected_artifact(name, manifests, target_id, "app.py", source)
    package = package_selected_source(name, manifests, target_id, "app.py", source)
    expected_package_sha = hashlib.sha256(package).hexdigest()
    expected_review = review["selected_source_binding"]["digest"]
    verified = verify_selected_source_package(
        package,
        expected_package_sha256=expected_package_sha,
        expected_review_binding_digest=expected_review,
        expected_target_id=target_id,
    )
    if verified.entrypoint != "app.py" or verified.source_bytes != source:
        raise RuntimeError("first-party package source differs")

    # Fixed filenames and commands only. No source, manifest or user-supplied
    # path becomes an executable argument or shell expression.
    with tempfile.TemporaryDirectory(prefix="cloudforge-owned-namespace-") as base:
        base_path = Path(base)
        stage = base_path / "stage"
        mount_root = base_path / "root"
        stage.mkdir(mode=0o700)
        mount_root.mkdir(mode=0o700)
        for filename, raw in (("app.py", verified.source_bytes), ("observer.py", observer)):
            path = stage / filename
            with path.open("xb") as stream:
                stream.write(raw)
            path.chmod(0o600)
        try:
            result = subprocess.run(
                [
                    "/usr/bin/unshare", "--user", "--map-root-user",
                    "--net", "--mount", "--pid", "--fork", "--kill-child",
                    "/bin/sh", str(script), str(mount_root), str(stage),
                    hashlib.sha256(verified.source_bytes).hexdigest(), observer_sha,
                ],
                cwd=base,
                env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"},
                stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=40, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("owned Linux namespace fixture unavailable") from exc
    if result.returncode != 0:
        # Never echo process stderr: it may contain raw source or host details.
        raise RuntimeError("owned Linux namespace fixture failed or is unsupported")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("owned namespace observer output is invalid") from exc
    if type(payload) is not dict or set(payload) != {"trace"} or payload["trace"] != _EXPECTED_TRACE:
        raise RuntimeError("owned namespace did not exhibit expected HTTP health")

    return {
        "demo_only": True,
        "owned_first_party_source_executed": True,
        "owned_namespace_fixture_completed": True,
        "observed_health": payload["trace"],
        "package_sha256": expected_package_sha,
        "selected_source_binding_digest": verified.review_binding_digest,
        "first_party_source_sha256": hashlib.sha256(source).hexdigest(),
        "target_id": target_id,
        "caller_selected_application_executed": False,
        "independent_operator_approval": False,
        "signed_runtime_evidence": False,
        "production_sandbox_attested": False,
        "real_infrastructure_mutated": False,
        "real_deployment_or_recovery": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Opt-in fixed first-party Linux namespace demo")
    parser.add_argument("--name", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument("--allow-owned-namespace", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_owned_namespace_source_demo(
            args.name, _load_selected_manifests(args.manifest), args.target,
            allow_owned_namespace=args.allow_owned_namespace,
        )
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
