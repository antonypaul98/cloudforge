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


@pytest.mark.parametrize("field,value", [
    ("target_id", "t" * 16384),
    ("approved_by", "r" * 16384),
    ("approved_by", "\u00e9" * 3000),
])
def test_receipt_export_rejects_json_larger_than_verifier_accepts(field, value):
    _, _, _, receipt = _sample()
    if field == "target_id":
        request = replace(receipt.request, target_id=value)
        receipt = replace(receipt, request=request, request_digest=request.digest)
    else:
        receipt = replace(receipt, approved_by=value)
    with pytest.raises(ValueError, match="canonical JSON size limit"):
        receipt.to_json()


def test_large_but_bounded_receipt_still_roundtrips():
    handoff, artifact, _, receipt = _sample()
    approval = LocalExecutionApproval(receipt.request.digest, "r" * 10000)
    issued = authorize_local_execution(handoff, artifact, receipt.request, approval)
    assert verify_local_execution_receipt_json(
        handoff, artifact, approval, issued.to_json()
    ) is True

@pytest.mark.parametrize("field", ["target_id", "approved_by"])
def test_oversized_receipt_identity_fails_before_request_digest(monkeypatch, field):
    _, _, _, receipt = _sample()
    if field == "target_id":
        request = replace(receipt.request, target_id="t" * 16385)
        receipt = replace(receipt, request=request, request_digest=request.digest)
    else:
        receipt = replace(receipt, approved_by="r" * 16385)

    def unexpected_digest(*args, **kwargs):
        raise AssertionError("oversized receipt must fail before hashing")

    monkeypatch.setattr("cloudforge.local_adapter._digest", unexpected_digest)
    with pytest.raises(ValueError, match="canonical JSON size limit"):
        receipt.to_json()


# Redacted audit evidence never exports reviewed target, reviewer or artifact bytes.
import hashlib
import json
from cloudforge.local_adapter import export_local_execution_audit_event


def test_local_audit_event_is_canonical_deterministic_and_redacted():
    handoff, artifact, approval, receipt = _sample()
    exported = export_local_execution_audit_event(handoff, artifact, approval, receipt)
    assert exported == export_local_execution_audit_event(handoff, artifact, approval, receipt)
    payload = json.loads(exported)
    assert set(payload) == {
        "format_version", "request_digest", "receipt_sha256", "status",
        "infrastructure_mutated",
    }
    assert payload["format_version"] == 1
    assert payload["request_digest"] == receipt.request_digest
    assert payload["receipt_sha256"] == hashlib.sha256(
        receipt.to_json().encode("ascii")
    ).hexdigest()
    assert payload["status"] == "authorized-local-only"
    assert payload["infrastructure_mutated"] is False
    assert exported == json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    for sensitive in ("staging", "execution-reviewer", "handoff-reviewer", "exact artifact"):
        assert sensitive not in exported


@pytest.mark.parametrize("field,value", [
    ("status", "deployed"),
    ("infrastructure_mutated", True),
    ("approved_by", "different-reviewer"),
    ("request_digest", "0" * 64),
])
def test_local_audit_event_rejects_tampered_receipts(field, value):
    handoff, artifact, approval, receipt = _sample()
    with pytest.raises(ValueError):
        export_local_execution_audit_event(
            handoff, artifact, approval, replace(receipt, **{field: value})
        )


def test_local_audit_event_rejects_changed_artifact():
    handoff, _, approval, receipt = _sample()
    with pytest.raises(ValueError):
        export_local_execution_audit_event(handoff, b"changed", approval, receipt)


def test_local_audit_event_requires_exact_fresh_approval():
    handoff, artifact, _, receipt = _sample()
    with pytest.raises(ApprovalRequiredError):
        export_local_execution_audit_event(
            handoff, artifact, LocalExecutionApproval("0" * 64, "reviewer"), receipt
        )


def test_local_authorization_rejects_oversized_receipt_before_audit_export():
    handoff, artifact, _, receipt = _sample()
    approval = LocalExecutionApproval(receipt.request.digest, "r" * 16385)
    with pytest.raises(ValueError, match="canonical JSON size limit"):
        authorize_local_execution(handoff, artifact, receipt.request, approval)


def test_local_audit_event_has_no_runtime_side_effects(monkeypatch):
    import builtins
    import os
    import pathlib
    import socket
    import subprocess
    handoff, artifact, approval, receipt = _sample()

    def forbidden(*args, **kwargs):
        raise AssertionError("audit event must not access runtime or infrastructure")

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(os, "system", forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(pathlib.Path, "open", forbidden)
        guard.setattr(pathlib.Path, "write_bytes", forbidden)
        exported = export_local_execution_audit_event(handoff, artifact, approval, receipt)
    assert json.loads(exported)["infrastructure_mutated"] is False

from cloudforge.local_adapter import verify_local_execution_audit_event


def test_local_audit_event_verification_roundtrip():
    handoff, artifact, approval, receipt = _sample()
    event = export_local_execution_audit_event(handoff, artifact, approval, receipt)
    assert verify_local_execution_audit_event(
        handoff, artifact, approval, receipt, event
    ) is True


@pytest.mark.parametrize("alter", [
    pytest.param(lambda s: s.rstrip("\n"), id="missing-newline"),
    pytest.param(lambda s: s.replace('"status": "authorized-local-only"',
                                     '"status": "deployed"'), id="forged-status"),
    pytest.param(lambda s: s.replace('"infrastructure_mutated": false',
                                     '"infrastructure_mutated": 0'), id="numeric-mutation"),
    pytest.param(lambda s: s.replace('"format_version": 1',
                                     '"format_version": true'), id="boolean-version"),
    pytest.param(lambda s: s.replace('"receipt_sha256":',
                                     '"receipt_sha256": "0", "receipt_sha256":', 1),
                 id="duplicate-receipt-hash"),
    pytest.param(lambda s: s.replace('"request_digest":',
                                     '"extra": true, "request_digest":', 1),
                 id="extra-field"),
    pytest.param(lambda s: s.replace('"request_digest":',
                                     '"request_digest": "0", "request_digest":', 1),
                 id="duplicate-request-digest"),
    pytest.param(lambda s: s.replace('  "status":', ' "status":'),
                 id="noncanonical-whitespace"),
    pytest.param(lambda s: s + " " * 2048, id="oversized"),
    pytest.param(lambda s: "{}", id="missing-fields"),
])
def test_local_audit_event_verification_rejects_modified_json(alter):
    handoff, artifact, approval, receipt = _sample()
    event = export_local_execution_audit_event(handoff, artifact, approval, receipt)
    with pytest.raises(ValueError):
        verify_local_execution_audit_event(
            handoff, artifact, approval, receipt, alter(event)
        )


@pytest.mark.parametrize("invalid", [None, b"{}", 0, {}, True])
def test_local_audit_event_verification_rejects_non_text(invalid):
    handoff, artifact, approval, receipt = _sample()
    with pytest.raises(ValueError, match="bounded canonical"):
        verify_local_execution_audit_event(
            handoff, artifact, approval, receipt, invalid
        )


def test_local_audit_event_verification_rejects_changed_artifact():
    handoff, artifact, approval, receipt = _sample()
    event = export_local_execution_audit_event(handoff, artifact, approval, receipt)
    with pytest.raises(ValueError):
        verify_local_execution_audit_event(
            handoff, b"different artifact", approval, receipt, event
        )


def test_local_audit_event_verification_requires_fresh_approval():
    handoff, artifact, approval, receipt = _sample()
    event = export_local_execution_audit_event(handoff, artifact, approval, receipt)
    with pytest.raises(ApprovalRequiredError):
        verify_local_execution_audit_event(
            handoff, artifact, LocalExecutionApproval("0" * 64, "reviewer"),
            receipt, event
        )


def test_local_audit_event_verification_rejects_tampered_receipt():
    handoff, artifact, approval, receipt = _sample()
    event = export_local_execution_audit_event(handoff, artifact, approval, receipt)
    with pytest.raises(ValueError):
        verify_local_execution_audit_event(
            handoff, artifact, approval, replace(receipt, status="deployed"), event
        )


def test_oversized_audit_event_fails_before_receipt_revalidation(monkeypatch):
    handoff, artifact, approval, receipt = _sample()
    def unexpected_export(*args, **kwargs):
        raise AssertionError("oversized event must fail before receipt validation")
    monkeypatch.setattr(
        "cloudforge.local_adapter.export_local_execution_audit_event",
        unexpected_export
    )
    with pytest.raises(ValueError, match="bounded canonical"):
        verify_local_execution_audit_event(
            handoff, artifact, approval, receipt, " " * 1025
        )


def test_local_audit_event_verification_has_no_external_side_effects(monkeypatch):
    import builtins
    import os
    import pathlib
    import socket
    import subprocess
    handoff, artifact, approval, receipt = _sample()
    event = export_local_execution_audit_event(handoff, artifact, approval, receipt)

    def forbidden(*args, **kwargs):
        raise AssertionError("audit verification must not access runtime or infrastructure")

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(os, "system", forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(pathlib.Path, "open", forbidden)
        guard.setattr(pathlib.Path, "write_bytes", forbidden)
        assert verify_local_execution_audit_event(
            handoff, artifact, approval, receipt, event
        ) is True
