"""Review a source-pinned, rootless OCI sandbox proposal without executing it.

This is a deterministic handoff prerequisite, not a container command, an
independent approval, a security attestation or evidence of deployment.
"""
from __future__ import annotations

import hashlib
import json
import re

from .demo_source_package import verify_selected_source_package

# The image name is a conservative, tag-free subset of OCI references.
# A digest-pinned name does not establish image provenance or trust.
_IMAGE = re.compile(
    r"[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)+"
    r"@sha256:[0-9a-f]{64}\Z"
)

_CONSTRAINTS = {
    "container_engine": "rootless-OCI-required-not-verified",
    "network": "none",
    "root_filesystem": "read-only",
    "privileges": "no-new-privileges",
    "capabilities": "drop-all",
    "host_mounts": "none",
    "host_devices": "none",
    "user": "non-root",
    "pid_limit": 64,
    "memory_limit_mib": 256,
    "cpu_limit": 1,
    "pull_policy": "never",
}


def prepare_selected_sandbox_review(
    package_bytes: bytes, *,
    expected_package_sha256: str,
    expected_review_binding_digest: str,
    expected_target_id: str,
    image_ref: str,
) -> dict[str, object]:
    """Build a review-only proposal bound to exact verified source bytes.

    All expected digests, target and image must originate from a separately
    trusted boundary before any future runtime uses this proposal. No such
    boundary is implemented here.
    """
    verified = verify_selected_source_package(
        package_bytes,
        expected_package_sha256=expected_package_sha256,
        expected_review_binding_digest=expected_review_binding_digest,
        expected_target_id=expected_target_id,
    )
    if type(image_ref) is not str or len(image_ref) > 256 or not _IMAGE.fullmatch(image_ref):
        raise ValueError("a lowercase, digest-pinned OCI image reference is required")
    if verified.entrypoint == "app.py":
        runtime = "python"
    elif verified.entrypoint == "server.js":
        runtime = "node"
    else:
        raise ValueError("unsupported selected application runtime")

    # The source bytes are intentionally excluded from the review result.
    # No host path, shell command, environment variable or credential is
    # accepted, and no container is started by this module.
    proposal = {
        "format_version": 1,
        "operation": "selected-source-sandbox-review-only",
        "application": verified.application,
        "target_id": verified.target_id,
        "entrypoint": verified.entrypoint,
        "runtime": runtime,
        "package_sha256": verified.package_sha256,
        "source_sha256": hashlib.sha256(verified.source_bytes).hexdigest(),
        "source_review_binding_digest": verified.review_binding_digest,
        "image_ref": image_ref,
        "constraints": dict(_CONSTRAINTS),
        "approval_status": "independent-authorization-required",
        "execution_permitted": False,
        "runtime_observed": False,
        "isolation_attested": False,
        "signed_health_evidence": False,
        "rollback_performed": False,
    }
    canonical = json.dumps(
        proposal, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return {**proposal, "proposal_sha256": hashlib.sha256(canonical).hexdigest()}
