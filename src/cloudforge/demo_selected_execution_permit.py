"""Keyed, exact-source sandbox proposal permit. This does not execute code.

The operator key and its expected fingerprint MUST be provisioned independently
of the source package. This is key possession, not human authentication. An
executor must separately verify a trusted clock, atomically consume a sequence,
attest its sandbox and obtain explicit approval before any execution.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import hmac
import json

from .demo_selected_sandbox_plan import prepare_selected_sandbox_review
from .observation_operator_policy import verify_observation_operator_key_pin

_MAX_UNIX = (1 << 63) - 1


@dataclass(frozen=True)
class SelectedSandboxPermit:
    format_version: int
    proposal_sha256: str
    operator_key_sha256: str
    sequence: int
    valid_from_unix: int
    valid_until_unix: int
    mac_sha256: str


def _digest(value: object) -> bool:
    return (type(value) is str and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _shape(permit: SelectedSandboxPermit) -> None:
    if (type(permit) is not SelectedSandboxPermit
            or type(permit.format_version) is not int or permit.format_version != 1
            or not all(_digest(value) for value in (
                permit.proposal_sha256, permit.operator_key_sha256, permit.mac_sha256,
            ))
            or type(permit.sequence) is not int
            or not 1 <= permit.sequence <= _MAX_UNIX
            or type(permit.valid_from_unix) is not int
            or type(permit.valid_until_unix) is not int
            or not 0 <= permit.valid_from_unix < permit.valid_until_unix <= _MAX_UNIX
            or permit.valid_until_unix - permit.valid_from_unix > 300):
        raise ValueError("invalid selected sandbox permit")


def _mac_bytes(permit: SelectedSandboxPermit) -> bytes:
    body = asdict(permit)
    del body["mac_sha256"]
    body["operation"] = "selected-sandbox-proposal-permit-only-v1"
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _review(package_bytes: bytes, expected_package_sha256: str,
            expected_review_binding_digest: str, expected_target_id: str,
            image_ref: str, operator_key: bytes,
            trusted_operator_key_sha256: str) -> dict[str, object]:
    verify_observation_operator_key_pin(
        operator_key, operator_key_sha256=trusted_operator_key_sha256,
        require_operator_pin=True,
    )
    return prepare_selected_sandbox_review(
        package_bytes, expected_package_sha256=expected_package_sha256,
        expected_review_binding_digest=expected_review_binding_digest,
        expected_target_id=expected_target_id, image_ref=image_ref,
    )


def issue_selected_sandbox_permit(
    package_bytes: bytes, *, expected_package_sha256: str,
    expected_review_binding_digest: str, expected_target_id: str,
    image_ref: str, operator_key: bytes, trusted_operator_key_sha256: str,
    sequence: int, valid_from_unix: int, valid_until_unix: int,
) -> SelectedSandboxPermit:
    """MAC-bind a reviewed source/target/image to a short-lived policy token."""
    proposal = _review(
        package_bytes, expected_package_sha256, expected_review_binding_digest,
        expected_target_id, image_ref, operator_key, trusted_operator_key_sha256,
    )
    permit = SelectedSandboxPermit(
        1, proposal["proposal_sha256"], hashlib.sha256(operator_key).hexdigest(),
        sequence, valid_from_unix, valid_until_unix, "0" * 64,
    )
    _shape(permit)
    return replace(permit, mac_sha256=hmac.digest(
        operator_key, _mac_bytes(permit), "sha256",
    ).hex())


def verify_selected_sandbox_permit(
    package_bytes: bytes, permit: SelectedSandboxPermit, *,
    expected_package_sha256: str, expected_review_binding_digest: str,
    expected_target_id: str, image_ref: str, operator_key: bytes,
    trusted_operator_key_sha256: str, sequence: int, now_unix: int,
) -> bool:
    """Validate exact pinned review and operator MAC, without side effects.

    The caller MUST enforce durable one-time sequence consumption before
    any future execution. Successful verification alone permits NO execution.
    """
    proposal = _review(
        package_bytes, expected_package_sha256, expected_review_binding_digest,
        expected_target_id, image_ref, operator_key, trusted_operator_key_sha256,
    )
    _shape(permit)
    if (type(sequence) is not int or type(now_unix) is not int
            or not 1 <= sequence <= _MAX_UNIX or not 0 <= now_unix <= _MAX_UNIX
            or sequence != permit.sequence
            or not permit.valid_from_unix <= now_unix <= permit.valid_until_unix
            or not hmac.compare_digest(permit.proposal_sha256, proposal["proposal_sha256"])
            or not hmac.compare_digest(
                permit.operator_key_sha256, hashlib.sha256(operator_key).hexdigest(),
            )
            or not hmac.compare_digest(
                permit.mac_sha256,
                hmac.digest(operator_key, _mac_bytes(permit), "sha256").hex(),
            )):
        raise ValueError("selected sandbox permit expired or differs from exact policy")
    return True
