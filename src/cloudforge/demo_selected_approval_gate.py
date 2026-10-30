"""Synthetic separate-key approval preflight. No human identity or execution."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import hmac
import json

from .demo_selected_execution_permit import SelectedSandboxPermit, _shape
from .demo_selected_permit_replay import consume_selected_sandbox_permit
from .observation_operator_policy import verify_observation_operator_key_pin


@dataclass(frozen=True)
class SelectedSandboxApproval:
    format_version: int
    permit_mac_sha256: str
    reviewer_key_sha256: str
    valid_from_unix: int
    valid_until_unix: int
    mac_sha256: str


def _valid_digest(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(
        ch in "0123456789abcdef" for ch in value
    )


def _validate(approval: SelectedSandboxApproval, permit: SelectedSandboxPermit) -> None:
    if (type(approval) is not SelectedSandboxApproval
            or type(approval.format_version) is not int
            or approval.format_version != 1
            or not all(_valid_digest(v) for v in (
                approval.permit_mac_sha256, approval.reviewer_key_sha256,
                approval.mac_sha256))
            or type(approval.valid_from_unix) is not int
            or type(approval.valid_until_unix) is not int
            or not permit.valid_from_unix <= approval.valid_from_unix
            < approval.valid_until_unix <= permit.valid_until_unix
            or approval.valid_until_unix - approval.valid_from_unix > 300):
        raise ValueError("invalid selected sandbox approval")


def _mac_body(approval: SelectedSandboxApproval) -> bytes:
    body = asdict(approval)
    del body["mac_sha256"]
    body["operation"] = "selected-sandbox-separate-key-preflight-only-v1"
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _check_reviewer(permit: SelectedSandboxPermit, reviewer_key: bytes,
                    trusted_reviewer_key_sha256: str) -> None:
    _shape(permit)
    verify_observation_operator_key_pin(
        reviewer_key, operator_key_sha256=trusted_reviewer_key_sha256,
        require_operator_pin=True)
    if hmac.compare_digest(permit.operator_key_sha256, trusted_reviewer_key_sha256):
        raise ValueError("reviewer and operator keys must be separate")


def issue_selected_sandbox_approval(
    permit: SelectedSandboxPermit, *, reviewer_key: bytes,
    trusted_reviewer_key_sha256: str, valid_from_unix: int,
    valid_until_unix: int,
) -> SelectedSandboxApproval:
    """Bind one exact operator permit to a distinct reviewer key."""
    _check_reviewer(permit, reviewer_key, trusted_reviewer_key_sha256)
    approval = SelectedSandboxApproval(
        1, permit.mac_sha256, hashlib.sha256(reviewer_key).hexdigest(),
        valid_from_unix, valid_until_unix, "0" * 64)
    _validate(approval, permit)
    return replace(approval, mac_sha256=hmac.digest(
        reviewer_key, _mac_body(approval), "sha256").hex())


def verify_selected_sandbox_approval(
    permit: SelectedSandboxPermit, approval: SelectedSandboxApproval, *,
    reviewer_key: bytes, trusted_reviewer_key_sha256: str,
    now_unix: int,
) -> bool:
    """Verify reviewer-key possession, not a real human approval decision."""
    _check_reviewer(permit, reviewer_key, trusted_reviewer_key_sha256)
    _validate(approval, permit)
    if (type(now_unix) is not int or not 0 <= now_unix < (1 << 63)
            or not approval.valid_from_unix <= now_unix <= approval.valid_until_unix
            or not hmac.compare_digest(approval.permit_mac_sha256, permit.mac_sha256)
            or not hmac.compare_digest(
                approval.reviewer_key_sha256, hashlib.sha256(reviewer_key).hexdigest())
            or not hmac.compare_digest(
                approval.mac_sha256,
                hmac.digest(reviewer_key, _mac_body(approval), "sha256").hex())):
        raise ValueError("selected sandbox approval expired or differs")
    return True


def consume_approved_selected_sandbox_permit(
    package_bytes: bytes, permit: SelectedSandboxPermit,
    approval: SelectedSandboxApproval, *,
    expected_package_sha256: str, expected_review_binding_digest: str,
    expected_target_id: str, image_ref: str, operator_key: bytes,
    trusted_operator_key_sha256: str, reviewer_key: bytes,
    trusted_reviewer_key_sha256: str, sequence: int, now_unix: int,
    ledger_path: str,
) -> bool:
    """Opt-in synthetic dual-key check before the existing replay ledger."""
    verify_selected_sandbox_approval(
        permit, approval, reviewer_key=reviewer_key,
        trusted_reviewer_key_sha256=trusted_reviewer_key_sha256,
        now_unix=now_unix)
    return consume_selected_sandbox_permit(
        package_bytes, permit, expected_package_sha256=expected_package_sha256,
        expected_review_binding_digest=expected_review_binding_digest,
        expected_target_id=expected_target_id, image_ref=image_ref,
        operator_key=operator_key,
        trusted_operator_key_sha256=trusted_operator_key_sha256,
        sequence=sequence, now_unix=now_unix, ledger_path=ledger_path)
