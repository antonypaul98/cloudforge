"""Revalidate local-only receipts against exact inputs without runtime side effects."""
from dataclasses import replace

import pytest

from cloudforge.approval import ApprovalRequiredError
from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution, prepare_local_execution_request,
    verify_local_execution_receipt,
)
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def _sample():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    handoff = authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "handoff-reviewer")
    )
    artifact = b"exact artifact"
    execution = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(execution.digest, "execution-reviewer")
    receipt = authorize_local_execution(handoff, artifact, execution, approval)
    return handoff, artifact, approval, receipt


def test_valid_receipt_is_revalidated_without_claiming_deployment():
    handoff, artifact, approval, receipt = _sample()
    assert verify_local_execution_receipt(handoff, artifact, approval, receipt) is True
    assert receipt.infrastructure_mutated is False
    assert receipt.status == "authorized-local-only"


@pytest.mark.parametrize("field,value", [
    ("status", "deployed"),
    ("status", 0),
    ("infrastructure_mutated", True),
    ("infrastructure_mutated", 0),
    ("approved_by", "different-reviewer"),
    ("approved_by", 42),
    ("request_digest", "0" * 64),
    ("request_digest", 42),
    ("request", {"target_id": "staging"}),
    ("request", None),
])
def test_tampered_receipt_fails_closed(field, value):
    handoff, artifact, approval, receipt = _sample()
    with pytest.raises(ValueError):
        verify_local_execution_receipt(
            handoff, artifact, approval, replace(receipt, **{field: value})
        )


def test_bool_format_version_cannot_pass_int_equality():
    handoff, artifact, approval, receipt = _sample()
    forged_request = replace(receipt.request, format_version=True)
    with pytest.raises(ValueError, match="malformed local execution receipt"):
        verify_local_execution_receipt(
            handoff, artifact, approval, replace(receipt, request=forged_request)
        )


def test_changed_operation_rejected():
    handoff, artifact, approval, receipt = _sample()
    with pytest.raises(ValueError):
        verify_local_execution_receipt(
            handoff, artifact, approval,
            replace(receipt, request=replace(receipt.request, operation="deploy")),
        )


def test_changed_artifact_rejected():
    handoff, _, approval, receipt = _sample()
    with pytest.raises(ValueError):
        verify_local_execution_receipt(handoff, b"changed artifact", approval, receipt)


def test_stale_approval_rejected():
    handoff, artifact, _, receipt = _sample()
    with pytest.raises(ApprovalRequiredError):
        verify_local_execution_receipt(
            handoff, artifact, LocalExecutionApproval("0" * 64, "reviewer"), receipt
        )


def test_missing_approval_rejected():
    handoff, artifact, _, receipt = _sample()
    with pytest.raises(ApprovalRequiredError):
        verify_local_execution_receipt(handoff, artifact, None, receipt)


def test_non_receipt_object_rejected():
    handoff, artifact, approval, _ = _sample()
    with pytest.raises(ValueError, match="expected a local execution receipt"):
        verify_local_execution_receipt(handoff, artifact, approval, {})


@pytest.mark.parametrize("field,value", [
    ("status", "deployed"),
    ("status", "healthy"),
    ("status", None),
    ("status", 0),
    ("infrastructure_mutated", True),
    ("infrastructure_mutated", 0),
    ("infrastructure_mutated", None),
])
def test_local_receipt_json_export_cannot_claim_deployment(field, value):
    handoff, artifact, approval, receipt = _sample()
    with pytest.raises(ValueError, match="local-only receipt"):
        replace(receipt, **{field: value}).to_json()
    assert receipt.infrastructure_mutated is False
    assert '"authorized-local-only"' in receipt.to_json()


@pytest.mark.parametrize("field,value", [
    ("request_digest", "0" * 64),
    ("request_digest", 0),
    ("request_digest", None),
    ("approved_by", " reviewer"),
    ("approved_by", "reviewer "),
    ("approved_by", "reviewer\u202e"),
    ("approved_by", 0),
    ("request", {"target_id": "staging"}),
    ("request", None),
])
def test_local_receipt_json_export_rejects_malformed_outer_bindings(field, value):
    _, _, _, receipt = _sample()
    with pytest.raises(ValueError, match="local-only receipt"):
        replace(receipt, **{field: value}).to_json()


@pytest.mark.parametrize("field,value", [
    ("format_version", True),
    ("format_version", 2),
    ("operation", "deploy"),
    ("handoff_digest", "0" * 63),
    ("artifact_sha256", 0),
    ("handoff_receipt_sha256", "Z" * 64),
    ("target_id", "staging "),
    ("target_id", "sta\u202eging"),
    ("target_id", None),
    ("operation", 0),
])
def test_local_receipt_json_export_rejects_malformed_request_bindings(field, value):
    _, _, _, receipt = _sample()
    with pytest.raises(ValueError, match="local-only receipt"):
        replace(receipt, request=replace(receipt.request, **{field: value})).to_json()


from cloudforge.local_adapter import verify_local_execution_receipt_json


def test_canonical_local_receipt_json_revalidates_exact_inputs():
    handoff, artifact, approval, receipt = _sample()
    assert verify_local_execution_receipt_json(
        handoff, artifact, approval, receipt.to_json()
    ) is True


@pytest.mark.parametrize("alter", [
    pytest.param(lambda s: s.rstrip("\n"), id="missing-newline"),
    pytest.param(lambda s: s.replace('"status": "authorized-local-only"',
                                     '"status": "deployed"'), id="forged-status"),
    pytest.param(lambda s: s.replace('"infrastructure_mutated": false',
                                     '"infrastructure_mutated": 0'), id="numeric-mutation"),
    pytest.param(lambda s: s.replace('"format_version": 1',
                                     '"format_version": true'), id="boolean-version"),
    pytest.param(lambda s: s.replace('"target_id": "staging"',
                                     '"target_id": "production"'), id="changed-target"),
    pytest.param(lambda s: s.replace('"status":', '"extra": true,\n  "status":'),
                 id="extra-outer-field"),
    pytest.param(lambda s: s.replace('"request": {', '"request": {"extra": true,'),
                 id="extra-request-field"),
    pytest.param(lambda s: s.replace('"request_digest":',
                                     '"request_digest": "0", "request_digest":', 1),
                 id="duplicate-key"),
    pytest.param(lambda s: s.replace('"status": "authorized-local-only"',
                                     '"status": NaN'), id="non-json-constant"),
    pytest.param(lambda s: s.replace('"approved_by": "execution-reviewer"',
                                     '"approved_by": "someone-else"'), id="changed-reviewer"),
    pytest.param(lambda s: s + " " * 17000, id="oversized"),
    pytest.param(lambda s: "[]", id="array"),
    pytest.param(lambda s: "null", id="null"),
    pytest.param(lambda s: "", id="empty"),
])
def test_serialized_local_receipt_rejects_tampering_and_noncanonical_json(alter):
    handoff, artifact, approval, receipt = _sample()
    with pytest.raises(ValueError):
        verify_local_execution_receipt_json(
            handoff, artifact, approval, alter(receipt.to_json())
        )


@pytest.mark.parametrize("invalid", [None, b"{}", 0, {}, True])
def test_serialized_local_receipt_rejects_non_text_inputs(invalid):
    handoff, artifact, approval, _ = _sample()
    with pytest.raises(ValueError):
        verify_local_execution_receipt_json(handoff, artifact, approval, invalid)


def test_serialized_local_receipt_rejects_changed_artifact():
    handoff, _, approval, receipt = _sample()
    with pytest.raises(ValueError):
        verify_local_execution_receipt_json(
            handoff, b"different artifact", approval, receipt.to_json()
        )


def test_serialized_local_receipt_requires_fresh_approval():
    handoff, artifact, _, receipt = _sample()
    with pytest.raises(ApprovalRequiredError):
        verify_local_execution_receipt_json(
            handoff, artifact, LocalExecutionApproval("0" * 64, "reviewer"),
            receipt.to_json(),
        )
