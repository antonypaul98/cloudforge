"""Bind a selected application source file to a manifest review, without executing it.

This is a read-only bridge toward an independently authorized OS-isolated demo.
No selected code, package install, network request, or provider operation runs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

from .application_demo import _load_selected_manifests, review_application_manifests

_MAX_SOURCE_BYTES = 131_072
_ENTRYPOINTS = {"python": "app.py", "node": "server.js"}


def prepare_selected_artifact(
    name: str, manifests: dict[str, str], target_id: str,
    entrypoint_name: str, source_bytes: bytes,
) -> dict[str, object]:
    """Produce a deterministic exact-source review binding, not an execution permit."""
    review = review_application_manifests(name, manifests, target_id)
    runtime = review["inspection"]["runtime"]
    if type(entrypoint_name) is not str or entrypoint_name != _ENTRYPOINTS.get(runtime):
        raise ValueError("entrypoint must be the supported runtime's fixed root filename")
    if type(source_bytes) is not bytes or not 0 < len(source_bytes) <= _MAX_SOURCE_BYTES:
        raise ValueError("source must be 1 to 131072 bytes")
    try:
        source = source_bytes.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise ValueError("source must be UTF-8") from exc
    if "\x00" in source:
        raise ValueError("source must not contain NUL bytes")
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    binding = {
        "format_version": 1,
        "operation": "bind-selected-source-to-review",
        "application": name,
        "target_id": target_id,
        "runtime": runtime,
        "entrypoint": entrypoint_name,
        "source_sha256": source_sha,
        "source_size_bytes": len(source_bytes),
        "manifest_review_digest": review["source_review_binding"]["digest"],
        "handoff_request_digest": review["handoff_request"]["request_digest"],
    }
    binding_digest = hashlib.sha256(json.dumps(
        binding, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("utf-8")).hexdigest()
    return {
        "demo_only": True,
        "selected_source_binding": {**binding, "digest": binding_digest,
                                    "status": "review-only-not-approved"},
        "selected_application_executed": False,
        "isolated_sandbox": False,
        "authenticated_review": False,
        "infrastructure_mutated": False,
        "limitations": [
            "Only one bounded root app.py or server.js source file is supported.",
            "A source hash is not a signature, immutable artifact, or authenticated approval.",
            "No application was executed, isolated, deployed, observed, or recovered.",
        ],
    }


def _read_selected_source(selected: str) -> tuple[str, bytes]:
    path = Path(selected)
    if path.name not in _ENTRYPOINTS.values():
        raise ValueError("unsupported selected source filename")
    # Fail closed if the OS cannot enforce no-follow on the final component.
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("no-follow source opening is unavailable")
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError("source must be a single-link regular file")
            if info.st_size <= 0 or info.st_size > _MAX_SOURCE_BYTES:
                raise ValueError("source size is outside the bounded limit")
            data = stream.read(_MAX_SOURCE_BYTES + 1)
    except OSError as exc:
        raise ValueError("selected source could not be safely read") from exc
    if not 0 < len(data) <= _MAX_SOURCE_BYTES:
        raise ValueError("source size is outside the bounded limit")
    return path.name, data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bind real selected source to review without executing it")
    parser.add_argument("--name", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument("--source", required=True, help="Selected root app.py or server.js")
    args = parser.parse_args(argv)
    try:
        entrypoint, data = _read_selected_source(args.source)
        payload = prepare_selected_artifact(
            args.name, _load_selected_manifests(args.manifest), args.target,
            entrypoint, data,
        )
    except ValueError as exc:
        parser.error(str(exc))
    sys.stdout.write(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
