"""Read-only review demo from caller-selected real application manifests.

This is an inspection/plan/handoff-request demo, not deployable IaC,
authenticated approval, service monitoring, or infrastructure execution.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import sys

from .deployment import prepare_deployment_request
from .iac import render_iac_proposal
from .inspector import inspect_application
from .planner import derive_requirements


_ALLOWED = frozenset({"pyproject.toml", "requirements.txt", "package.json"})
_MAX_MANIFEST_BYTES = 65_536
_MAX_TOTAL_BYTES = 131_072
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


def review_application_manifests(
    name: str, manifests: dict[str, str], target_id: str,
) -> dict[str, object]:
    """Turn bounded, supplied manifest text into a reviewable proposal.

    No manifest scripts are executed, no provider-specific configuration is
    generated, and no approval or deployment is asserted.
    """
    if type(name) is not str or _ID.fullmatch(name) is None:
        raise ValueError("application name must be a 1-64 character identifier")
    if type(target_id) is not str or _ID.fullmatch(target_id) is None:
        raise ValueError("target must be a 1-64 character opaque identifier")
    if type(manifests) is not dict or not 1 <= len(manifests) <= 3:
        raise ValueError("supply one to three supported manifests")
    if "package.json" in manifests and (
        "pyproject.toml" in manifests or "requirements.txt" in manifests
    ):
        raise ValueError("mixed Python and Node manifests are ambiguous")

    checked: dict[str, str] = {}
    fingerprints: dict[str, str] = {}
    total = 0
    for path, content in sorted(manifests.items()):
        if type(path) is not str or path not in _ALLOWED:
            raise ValueError("only root pyproject.toml, requirements.txt and package.json are supported")
        if type(content) is not str or not content.strip():
            raise ValueError("manifest contents must be nonblank UTF-8 text")
        try:
            raw = content.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise ValueError("manifest contents must be valid UTF-8 text") from exc
        if len(raw) > _MAX_MANIFEST_BYTES:
            raise ValueError("manifest exceeds the 65536-byte read limit")
        total += len(raw)
        if total > _MAX_TOTAL_BYTES:
            raise ValueError("combined manifests exceed the read limit")
        checked[path] = content
        fingerprints[path] = hashlib.sha256(raw).hexdigest()

    inspected = inspect_application(name, checked)
    if inspected.profile.runtime not in {"python", "node"}:
        raise ValueError("unsupported or unknown runtime")
    if any(warning.startswith("could not parse dependencies") for warning in inspected.warnings):
        raise ValueError("malformed manifest dependencies cannot be used for a proposal")

    plan = derive_requirements(inspected.profile)
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, target_id)
    return {
        "demo_only": True,
        "inspection": {
            "application": inspected.profile.name,
            "runtime": inspected.profile.runtime,
            "manifest_sha256": fingerprints,
            "evidence": [asdict(item) for item in inspected.evidence],
            "warnings": list(inspected.warnings),
        },
        "provider_neutral_proposal": json.loads(proposal.document),
        "plan_digest": proposal.plan_digest,
        "handoff_request": {
            "target_id": request.target_id,
            "request_digest": request.digest,
            "status": "approval-required",
        },
        "authenticated_review": False,
        "infrastructure_mutated": False,
        "deployment_observed": False,
        "recovery_performed": False,
        "limitations": [
            "Manifest inference supports only Python/Node and declared PostgreSQL/Redis.",
            "The JSON proposal is not deployable Terraform, OpenTofu, or Pulumi code.",
            "No operator authentication, execution approval, deployment, monitoring, or recovery.",
        ],
    }


def _load_selected_manifests(paths: list[str]) -> dict[str, str]:
    manifests: dict[str, str] = {}
    for selected in paths:
        path = Path(selected)
        if path.name not in _ALLOWED:
            raise ValueError("selected file must be a supported manifest")
        if path.name in manifests:
            raise ValueError("duplicate manifest basename")
        if path.is_symlink():
            raise ValueError("symlink manifest files are not accepted")
        try:
            with path.open("rb") as stream:
                raw = stream.read(_MAX_MANIFEST_BYTES + 1)
        except OSError as exc:
            raise ValueError("could not read selected manifest") from exc
        if len(raw) > _MAX_MANIFEST_BYTES:
            raise ValueError("manifest exceeds the 65536-byte read limit")
        try:
            manifests[path.name] = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise ValueError("manifest must be valid UTF-8") from exc
    return manifests


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review real app manifests without executing or deploying")
    parser.add_argument("--name", required=True, help="Opaque application identifier")
    parser.add_argument("--target", required=True, help="Opaque review target identifier")
    parser.add_argument("--manifest", action="append", required=True, metavar="PATH",
                        help="Selected requirements.txt, pyproject.toml or package.json (repeatable)")
    args = parser.parse_args(argv)
    try:
        payload = review_application_manifests(
            args.name, _load_selected_manifests(args.manifest), args.target
        )
    except ValueError as exc:
        parser.error(str(exc))
    sys.stdout.write(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
