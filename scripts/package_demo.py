#!/usr/bin/env python3
"""Package and verify CloudForge's accepted review-only/synthetic demos.

No selected application execution, authenticated approval, or deployment.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = (
    "src/cloudforge", "README.md", "docs/DEMO_READINESS.md",
    "pyproject.toml", "scripts/package_demo.py",
)
SAMPLE = "postgresql>=16\nredis>=5\n# DEMO_PRIVATE_MARKER=not-for-output\n"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_extract(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r:*") as stream:
        for member in stream.getmembers():
            path = PurePosixPath(member.name)
            if (path.is_absolute() or ".." in path.parts
                    or not (member.isfile() or member.isdir())):
                raise RuntimeError("unsafe archive member")
        stream.extractall(destination, filter="data")


def smoke(stage: Path, scratch: Path) -> dict[str, object]:
    scratch.mkdir(parents=True, exist_ok=True)
    env_dir = scratch / "venv"
    venv.EnvBuilder(with_pip=False).create(env_dir)
    python = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    env = dict(os.environ, PYTHONPATH=str(stage / "src"),
               PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(python), "-m", *args], cwd=stage,
                              env=env, capture_output=True, text=True,
                              check=False, timeout=30)

    app_args = ("cloudforge.application_demo", "--name", "demo-api",
                "--target", "review-staging", "--manifest",
                str(stage / "sample" / "requirements.txt"))
    a1, a2 = run(*app_args), run(*app_args)
    s1, s2 = run("cloudforge.synthetic_demo"), run("cloudforge.synthetic_demo")
    if any(r.returncode != 0 or r.stderr for r in (a1, a2, s1, s2)):
        raise RuntimeError("demo CLI smoke failed")
    if a1.stdout != a2.stdout or s1.stdout != s2.stdout:
        raise RuntimeError("demo CLI output is not deterministic")
    app, synthetic = json.loads(a1.stdout), json.loads(s1.stdout)
    for payload in (app, synthetic):
        if (payload.get("demo_only") is not True
                or payload.get("authenticated_review") is not False
                or payload.get("infrastructure_mutated") is not False
                or payload.get("deployment_observed") is not False
                or payload.get("recovery_performed") is not False):
            raise RuntimeError("demo claims exceed accepted scope")
    if (app["inspection"]["runtime"] != "python"
            or app["handoff_request"]["status"] != "approval-required"
            or len(app["source_review_binding"]["digest"]) != 64):
        raise RuntimeError("application review contract failed")
    rejections = synthetic.get("synthetic_rejections", {})
    if len(rejections) != 14 or not all(v is True for v in rejections.values()):
        raise RuntimeError("synthetic fail-closed checks failed")
    if "DEMO_PRIVATE_MARKER" in a1.stdout or "not-for-output" in a1.stdout:
        raise RuntimeError("raw manifest content leaked")
    invalid = run("cloudforge.application_demo", "--name", "demo-api",
                  "--target", "review-staging", "--manifest",
                  str(scratch / "missing" / "requirements.txt"))
    if invalid.returncode == 0 or invalid.stdout:
        raise RuntimeError("invalid input was not rejected")
    return {
        "app_sha256": digest(a1.stdout.encode()),
        "synthetic_sha256": digest(s1.stdout.encode()),
        "app_runs": 2, "synthetic_runs": 2,
        "synthetic_rejections": 14, "invalid_input_rejected": True,
        "execution_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="dist")
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                  text=True).strip()
    if len(sha) != 40:
        raise RuntimeError("expected full pinned Git SHA")
    version = "cloudforge-review-demo-" + sha[:12]
    with tempfile.TemporaryDirectory(prefix="cloudforge-release-") as tmp_name:
        tmp = Path(tmp_name)
        source_archive = tmp / "source.tar"
        subprocess.run(["git", "archive", "--format=tar", "-o",
                        str(source_archive), sha, "--", *SOURCE_PATHS],
                       cwd=ROOT, check=True)
        stage = tmp / version
        stage.mkdir()
        safe_extract(source_archive, stage)
        (stage / "sample").mkdir()
        (stage / "sample" / "requirements.txt").write_text(SAMPLE, encoding="utf-8")
        (stage / "RUNTIME_DEPENDENCIES.lock").write_text(
            "Python 3.11; standard library only; no third-party runtime dependencies.\n",
            encoding="utf-8")
        (stage / "BUNDLE_README.md").write_text(
            "# CloudForge bounded demo\n\nSource SHA: " + sha + "\n\n"
            "Python 3.11, stdlib only. From extracted root:\n\n"
            "python3.11 -m venv .venv\n"
            "PYTHONPATH=src .venv/bin/python -m cloudforge.application_demo "
            "--name demo-api --target review-staging --manifest sample/requirements.txt\n"
            "PYTHONPATH=src .venv/bin/python -m cloudforge.synthetic_demo\n\n"
            "Expected: deterministic redacted JSON; review status approval-required, "
            "14 synthetic fail-closed checks, no authenticated approval, "
            "no selected-app execution, no deployment, no real recovery.\n"
            "Run twice and compare outputs. Verify archive using SHA256SUMS. "
            "Rollback to the pinned source SHA.\n", encoding="utf-8")
        receipt = smoke(stage, tmp / "first-smoke")
        receipt.update({"source_sha": sha, "python": sys.version.split()[0],
                        "tested_at_utc": datetime.now(timezone.utc).isoformat()})
        (stage / "SMOKE_RECEIPT.json").write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        files = sorted(p for p in stage.rglob("*") if p.is_file())
        manifest = {
            "version": version, "source_sha": sha, "python_minor": "3.11",
            "runtime_dependencies": [],
            "files": [{"path": p.relative_to(stage).as_posix(),
                       "sha256": digest(p.read_bytes()), "bytes": p.stat().st_size}
                      for p in files],
        }
        (stage / "BUNDLE_MANIFEST.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        archive = output / (version + ".tar.gz")
        with tarfile.open(archive, "w:gz") as stream:
            stream.add(stage, arcname=version)
        checksum = digest(archive.read_bytes())
        (output / "SHA256SUMS").write_text(
            checksum + "  " + archive.name + "\n", encoding="utf-8")
        extracted = tmp / "extracted"
        extracted.mkdir()
        safe_extract(archive, extracted)
        unpacked = extracted / version
        for item in manifest["files"]:
            if digest((unpacked / item["path"]).read_bytes()) != item["sha256"]:
                raise RuntimeError("extracted bundle integrity mismatch")
        verified = smoke(unpacked, tmp / "second-smoke")
        if any(verified[key] != receipt[key] for key in verified):
            raise RuntimeError("clean-room smoke differs from source smoke")
        print(json.dumps({"version": version, "source_sha": sha,
                          "sha256": checksum, "archive": str(archive),
                          "clean_room_smoke": "passed"}, sort_keys=True))


if __name__ == "__main__":
    main()
