"""Synthetic dual-key admission followed by exact-byte staging, never execution.

This is a composition of first-party review, key checks, replay and staging.
It does not authenticate a human or grant permission to run selected code.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from .demo_selected_approval_gate import (
    SelectedSandboxApproval, consume_approved_selected_sandbox_permit,
    verify_selected_sandbox_approval,
)
from .demo_selected_execution_permit import (
    SelectedSandboxPermit, verify_selected_sandbox_permit,
)
from .demo_selected_oci_stage import (
    StagedSelectedSource, stage_verified_selected_source,
)


@contextmanager
def stage_synthetically_admitted_selected_source(
    package_bytes: bytes, permit: SelectedSandboxPermit,
    approval: SelectedSandboxApproval, *,
    expected_package_sha256: str, expected_review_binding_digest: str,
    expected_target_id: str, image_ref: str,
    operator_key: bytes, trusted_operator_key_sha256: str,
    reviewer_key: bytes, trusted_reviewer_key_sha256: str,
    sequence: int, now_unix: int, ledger_path: str,
) -> Iterator[StagedSelectedSource]:
    """Yield staged bytes only after both key checks and durable admission.

    Verify both keys and exact source *before* writing temporary source files.
    Stage before consuming the sequence, so a staging failure does not spend it.
    Consume before yielding; an error in downstream use never refunds it.
    The caller owns keys, clock and ledger and MUST NOT execute on this basis.
    """
    verify_selected_sandbox_approval(
        permit, approval, reviewer_key=reviewer_key,
        trusted_reviewer_key_sha256=trusted_reviewer_key_sha256,
        now_unix=now_unix,
    )
    verify_selected_sandbox_permit(
        package_bytes, permit,
        expected_package_sha256=expected_package_sha256,
        expected_review_binding_digest=expected_review_binding_digest,
        expected_target_id=expected_target_id, image_ref=image_ref,
        operator_key=operator_key,
        trusted_operator_key_sha256=trusted_operator_key_sha256,
        sequence=sequence, now_unix=now_unix,
    )
    with stage_verified_selected_source(
        package_bytes, expected_package_sha256=expected_package_sha256,
        expected_review_binding_digest=expected_review_binding_digest,
        expected_target_id=expected_target_id,
    ) as staged:
        consume_approved_selected_sandbox_permit(
            package_bytes, permit, approval,
            expected_package_sha256=expected_package_sha256,
            expected_review_binding_digest=expected_review_binding_digest,
            expected_target_id=expected_target_id, image_ref=image_ref,
            operator_key=operator_key,
            trusted_operator_key_sha256=trusted_operator_key_sha256,
            reviewer_key=reviewer_key,
            trusted_reviewer_key_sha256=trusted_reviewer_key_sha256,
            sequence=sequence, now_unix=now_unix, ledger_path=ledger_path,
        )
        yield staged
