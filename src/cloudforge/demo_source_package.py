"""Exact-byte portable source snapshot for review; never an execution permit.

The returned bytes contain application source and manifests, potentially secrets.
Do not print, upload or execute them without a separate explicit decision.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import hmac
import json

from .demo_selected_artifact import prepare_selected_artifact

_MAX_PACKAGE_BYTES = 400_000
_PACKAGE_FIELDS = frozenset({
    "format_version", "operation", "application", "target_id", "entrypoint",
    "source_base64", "manifests", "review_binding_digest",
})


@dataclass(frozen=True)
class VerifiedSourcePackage:
    """Immutable in-memory bytes, not a trusted or executable artifact."""
    application: str
    target_id: str
    entrypoint: str
    source_bytes: bytes = field(repr=False)
    manifests: tuple[tuple[str, str], ...] = field(repr=False)
    package_sha256: str
    review_binding_digest: str


def _canonical(document: dict[str, object]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _decode_exact_base64(value: object) -> bytes:
    if type(value) is not str or len(value) > 180_000:
        raise ValueError("invalid encoded source component")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("invalid encoded source component") from exc
    if base64.b64encode(raw).decode("ascii") != value:
        raise ValueError("noncanonical encoded source component")
    return raw


def package_selected_source(
    name: str, manifests: dict[str, str], target_id: str,
    entrypoint_name: str, source_bytes: bytes,
) -> bytes:
    """Return a deterministic in-memory byte snapshot; no I/O or execution."""
    review = prepare_selected_artifact(
        name, manifests, target_id, entrypoint_name, source_bytes,
    )
    parts = [
        {"name": filename, "utf8_base64": base64.b64encode(
            content.encode("utf-8", "strict")
        ).decode("ascii")}
        for filename, content in sorted(manifests.items())
    ]
    document = {
        "format_version": 1,
        "operation": "portable-selected-source-review",
        "application": name,
        "target_id": target_id,
        "entrypoint": entrypoint_name,
        "source_base64": base64.b64encode(source_bytes).decode("ascii"),
        "manifests": parts,
        "review_binding_digest": review["selected_source_binding"]["digest"],
    }
    raw = _canonical(document)
    if len(raw) > _MAX_PACKAGE_BYTES:
        raise ValueError("source package exceeds size limit")
    return raw


def verify_selected_source_package(
    package_bytes: bytes, *, expected_package_sha256: str,
    expected_review_binding_digest: str, expected_target_id: str,
) -> VerifiedSourcePackage:
    """Re-derive exact-source review and compare caller-pinned digests.

    The expected digests and target must come from an independently trusted
    approval boundary in any future runtime; this function is NOT that boundary.
    """
    if type(package_bytes) is not bytes or not 0 < len(package_bytes) <= _MAX_PACKAGE_BYTES:
        raise ValueError("invalid source package size or type")
    if type(expected_package_sha256) is not str or len(expected_package_sha256) != 64:
        raise ValueError("expected package digest is invalid")
    if type(expected_review_binding_digest) is not str or len(expected_review_binding_digest) != 64:
        raise ValueError("expected review digest is invalid")
    package_sha = hashlib.sha256(package_bytes).hexdigest()
    if not hmac.compare_digest(package_sha, expected_package_sha256):
        raise ValueError("source package digest differs")
    try:
        document = json.loads(package_bytes.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid source package encoding") from exc
    if type(document) is not dict or set(document) != _PACKAGE_FIELDS:
        raise ValueError("invalid source package schema")
    if _canonical(document) != package_bytes:
        raise ValueError("source package is not canonically encoded")
    if type(document["format_version"]) is not int or document["format_version"] != 1:
        raise ValueError("unsupported source package version")
    if document["operation"] != "portable-selected-source-review":
        raise ValueError("unsupported source package operation")
    if type(expected_target_id) is not str or document["target_id"] != expected_target_id:
        raise ValueError("source package target differs")
    parts = document["manifests"]
    if type(parts) is not list or not 1 <= len(parts) <= 2:
        raise ValueError("invalid source package manifest count")
    manifests: dict[str, str] = {}
    for part in parts:
        if type(part) is not dict or set(part) != {"name", "utf8_base64"}:
            raise ValueError("invalid source package manifest schema")
        filename = part["name"]
        if type(filename) is not str or filename in manifests:
            raise ValueError("duplicate or invalid source package manifest")
        try:
            manifests[filename] = _decode_exact_base64(part["utf8_base64"]).decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise ValueError("source package manifest is not UTF-8") from exc
    if list(manifests) != sorted(manifests):
        raise ValueError("source package manifests are not ordered")
    source = _decode_exact_base64(document["source_base64"])
    review = prepare_selected_artifact(
        document["application"], manifests, document["target_id"],
        document["entrypoint"], source,
    )
    derived = review["selected_source_binding"]["digest"]
    if (type(document["review_binding_digest"]) is not str or
        not hmac.compare_digest(derived, document["review_binding_digest"]) or
        not hmac.compare_digest(derived, expected_review_binding_digest)):
        raise ValueError("source package review binding differs")
    return VerifiedSourcePackage(
        application=document["application"], target_id=document["target_id"],
        entrypoint=document["entrypoint"], source_bytes=source,
        manifests=tuple(manifests.items()), package_sha256=package_sha,
        review_binding_digest=derived,
    )
