"""Bounded local execution authorization regression checks."""
import json
from dataclasses import replace
import pytest
from cloudforge.approval import ApprovalRequiredError
from cloudforge.deployment import DeploymentApproval, prepare_deployment_request, authorize_deployment_handoff
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import LocalExecutionApproval, prepare_local_execution_request, authorize_local_execution
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements

def sample():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    handoff = authorize_deployment_handoff(plan, proposal, request, DeploymentApproval(request.digest, "reviewer"))
    artifact = b"exact artifact"
    execution = prepare_local_execution_request(handoff, artifact)
    return handoff, artifact, execution

def test_deterministic_local_receipt():
    handoff, artifact, execution = sample()
    approval = LocalExecutionApproval(execution.digest, "reviewer")
    receipt = authorize_local_execution(handoff, artifact, execution, approval)
    assert receipt.infrastructure_mutated is False
    assert json.loads(receipt.to_json())["status"] == "authorized-local-only"

@pytest.mark.parametrize("changed", [b"new artifact", b"exact artifact "])
def test_artifact_mutation_requires_fresh_request(changed):
    handoff, _, execution = sample()
    with pytest.raises(ValueError):
        authorize_local_execution(handoff, changed, execution, LocalExecutionApproval(execution.digest, "reviewer"))

@pytest.mark.parametrize("field,value", [("target_id", "production"), ("operation", "deploy"), ("format_version", True)])
def test_request_mutation_rejected(field, value):
    handoff, artifact, execution = sample()
    with pytest.raises(ValueError):
        authorize_local_execution(handoff, artifact, replace(execution, **{field: value}), LocalExecutionApproval(execution.digest, "reviewer"))

@pytest.mark.parametrize("invalid", [None, True, "yes"])
def test_approval_bypass_rejected(invalid):
    handoff, artifact, execution = sample()
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(handoff, artifact, execution, invalid)


from dataclasses import FrozenInstanceError

@pytest.mark.parametrize("name", ["", " ", " bad", "bad ", "bad\nname", None, 42])
def test_invalid_execution_approver_rejected(name):
    handoff, artifact, request = sample()
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(handoff, artifact, request, LocalExecutionApproval(request.digest, name))

def test_stale_approval_rejected():
    handoff, artifact, request = sample()
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(handoff, artifact, request, LocalExecutionApproval("0" * 64, "reviewer"))

def test_changed_target_requires_fresh_execution_approval():
    handoff, artifact, request = sample()
    new_request = replace(handoff.request, target_id="production")
    new_handoff = replace(handoff, request=new_request, request_digest=new_request.digest)
    new_execution = prepare_local_execution_request(new_handoff, artifact)
    assert new_execution.digest != request.digest
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(new_handoff, artifact, new_execution, LocalExecutionApproval(request.digest, "reviewer"))

@pytest.mark.parametrize("target", ["", " ", " bad", "bad\n", "a\x00b", None, 42])
def test_malformed_target_rejected(target):
    handoff, artifact, _ = sample()
    request = replace(handoff.request, target_id=target)
    changed = replace(handoff, request=request, request_digest=request.digest)
    with pytest.raises(ValueError):
        prepare_local_execution_request(changed, artifact)

def test_request_approval_and_receipt_are_immutable():
    handoff, artifact, request = sample()
    approval = LocalExecutionApproval(request.digest, "reviewer")
    receipt = authorize_local_execution(handoff, artifact, request, approval)
    with pytest.raises(FrozenInstanceError):
        request.target_id = "other"
    with pytest.raises(FrozenInstanceError):
        approval.approved_by = "other"
    with pytest.raises(FrozenInstanceError):
        receipt.infrastructure_mutated = True

def test_authorization_has_no_external_runtime_side_effects(monkeypatch):
    import builtins
    import os
    import pathlib
    import socket
    import subprocess
    handoff, artifact, request = sample()
    approval = LocalExecutionApproval(request.digest, "reviewer")
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected external runtime side effect")
    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(os, "system", forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(pathlib.Path, "open", forbidden)
        guard.setattr(pathlib.Path, "write_bytes", forbidden)
        receipt = authorize_local_execution(handoff, artifact, request, approval)
    assert receipt.infrastructure_mutated is False


@pytest.mark.parametrize("reviewer", [
    pytest.param("r" * 16385, id="oversized-ascii-reviewer"),
    pytest.param("\u00e9" * 3000, id="unicode-escape-expansion"),
])
def test_authorization_rejects_unexportable_reviewers(reviewer):
    handoff, artifact, execution = sample()
    with pytest.raises(ValueError, match="canonical JSON size limit"):
        authorize_local_execution(
            handoff, artifact, execution,
            LocalExecutionApproval(execution.digest, reviewer),
        )


def test_authorization_rejects_unexportable_target():
    handoff, artifact, execution = sample()
    altered_request = replace(handoff.request, target_id="t" * 16385)
    altered_handoff = replace(
        handoff, request=altered_request, request_digest=altered_request.digest,
    )
    # Preparation now rejects the malformed handoff before JSON parsing.
    with pytest.raises(ValueError, match="local handoff identity exceeds size limit"):
        prepare_local_execution_request(altered_handoff, artifact)
    # Authorization must independently reject the same oversized target.
    with pytest.raises(ValueError, match="canonical JSON size limit"):
        authorize_local_execution(
            altered_handoff, artifact, execution,
            LocalExecutionApproval(execution.digest, "reviewer"),
        )

@pytest.mark.parametrize("oversized", ["target", "reviewer"])
def test_oversized_identity_fails_before_expensive_handoff_revalidation(monkeypatch, oversized):
    handoff, artifact, execution = sample()
    approval = LocalExecutionApproval(execution.digest, "reviewer")
    if oversized == "target":
        request = replace(handoff.request, target_id="t" * 16385)
        handoff = replace(handoff, request=request, request_digest=request.digest)
    else:
        approval = LocalExecutionApproval(execution.digest, "r" * 16385)

    def forbidden(*args, **kwargs):
        raise AssertionError("oversized identity must be rejected before handoff parsing")

    monkeypatch.setattr("cloudforge.local_adapter.prepare_local_execution_request", forbidden)
    with pytest.raises(ValueError, match="canonical JSON size limit"):
        authorize_local_execution(handoff, artifact, execution, approval)

@pytest.mark.parametrize("invalid", [
    None,
    True,
    "yes",
    LocalExecutionApproval("0" * 64, None),
    LocalExecutionApproval("0" * 64, ""),
    LocalExecutionApproval("0" * 64, " bad"),
    LocalExecutionApproval(None, "reviewer"),
    LocalExecutionApproval(True, "reviewer"),
    LocalExecutionApproval("short", "reviewer"),
    LocalExecutionApproval("G" * 64, "reviewer"),
    LocalExecutionApproval("0" * 65, "reviewer"),
])
def test_invalid_execution_approval_fails_before_handoff_parsing(monkeypatch, invalid):
    handoff, artifact, execution = sample()

    def forbidden(*args, **kwargs):
        raise AssertionError("invalid approval must fail before handoff parsing")

    monkeypatch.setattr(
        "cloudforge.local_adapter.prepare_local_execution_request", forbidden
    )
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(handoff, artifact, execution, invalid)

@pytest.mark.parametrize("field,value", [
    ("format_version", True),
    ("format_version", 2),
    ("operation", "deploy"),
    ("operation", None),
    ("handoff_digest", "0" * 63),
    ("handoff_digest", True),
    ("artifact_sha256", "A" * 64),
    ("handoff_receipt_sha256", None),
    ("target_id", ""),
    ("target_id", " bad"),
    ("target_id", "bad\n"),
    ("target_id", None),
    ("target_id", "t" * 16385),
])
def test_malformed_execution_request_fails_before_handoff_parsing(monkeypatch, field, value):
    handoff, artifact, execution = sample()
    approval = LocalExecutionApproval(execution.digest, "reviewer")

    def forbidden(*args, **kwargs):
        raise AssertionError("malformed request must fail before handoff parsing")

    monkeypatch.setattr(
        "cloudforge.local_adapter.prepare_local_execution_request", forbidden
    )
    with pytest.raises(ValueError):
        authorize_local_execution(
            handoff, artifact, replace(execution, **{field: value}), approval
        )


@pytest.mark.parametrize("identity,value", [
    ("target_id", "t" * 16385),
    ("target_id", "bad\n"),
    ("target_id", None),
    ("approved_by", "r" * 16385),
    ("approved_by", "bad\n"),
    ("approved_by", None),
])
def test_invalid_handoff_identity_fails_before_document_parse(monkeypatch, identity, value):
    handoff, artifact, _ = sample()
    if identity == "target_id":
        handoff = replace(handoff, request=replace(handoff.request, target_id=value))
    else:
        handoff = replace(handoff, approved_by=value)

    def forbidden(*args, **kwargs):
        raise AssertionError("invalid identity must fail before document JSON parsing")

    with monkeypatch.context() as guard:
        guard.setattr("cloudforge.local_adapter.json.loads", forbidden)
        with pytest.raises(ValueError):
            prepare_local_execution_request(handoff, artifact)

@pytest.mark.parametrize("invalid", [
    None, True, "artifact text", bytearray(b"artifact"), memoryview(b"artifact"),
])
def test_nonbytes_artifact_fails_before_handoff_document_parse(monkeypatch, invalid):
    handoff, _, _ = sample()

    def forbidden(*args, **kwargs):
        raise AssertionError("nonbytes artifact must fail before document parsing")

    monkeypatch.setattr("cloudforge.local_adapter.json.loads", forbidden)
    with pytest.raises(ValueError, match="artifact must be exact bytes"):
        prepare_local_execution_request(handoff, invalid)


@pytest.mark.parametrize("invalid", [
    None, True, "artifact text", bytearray(b"artifact"), memoryview(b"artifact"),
])
def test_nonbytes_artifact_fails_before_authorization_revalidation(monkeypatch, invalid):
    handoff, _, request = sample()
    approval = LocalExecutionApproval(request.digest, "reviewer")

    def forbidden(*args, **kwargs):
        raise AssertionError("nonbytes artifact must fail before handoff revalidation")

    monkeypatch.setattr(
        "cloudforge.local_adapter.prepare_local_execution_request", forbidden
    )
    with pytest.raises(ValueError, match="artifact must be exact bytes"):
        authorize_local_execution(handoff, invalid, request, approval)

@pytest.mark.parametrize("field,value", [
    ("status", None),
    ("status", True),
    ("status", "deployed"),
    ("status", "ready-for-adapter-review "),
    ("infrastructure_mutated", None),
    ("infrastructure_mutated", 0),
    ("infrastructure_mutated", True),
])
def test_ineligible_handoff_fails_before_document_parse(monkeypatch, field, value):
    handoff, artifact, _ = sample()
    handoff = replace(handoff, **{field: value})

    def forbidden(*args, **kwargs):
        raise AssertionError("ineligible handoff must fail before JSON parsing")

    monkeypatch.setattr("cloudforge.local_adapter.json.loads", forbidden)
    with pytest.raises(ValueError, match="handoff is not eligible"):
        prepare_local_execution_request(handoff, artifact)


@pytest.mark.parametrize("binding", ["target_id", "handoff_digest"])
def test_stale_local_binding_fails_before_handoff_document_parse(monkeypatch, binding):
    handoff, artifact, execution = sample()
    if binding == "target_id":
        forged = replace(execution, target_id="different-target")
    else:
        stale = "0" * 64 if execution.handoff_digest != "0" * 64 else "f" * 64
        forged = replace(execution, handoff_digest=stale)

    def forbidden(*args, **kwargs):
        raise AssertionError("stale binding must fail before handoff JSON parsing")

    monkeypatch.setattr("cloudforge.local_adapter.json.loads", forbidden)
    with pytest.raises(ValueError, match="request differs from exact local execution inputs"):
        authorize_local_execution(
            handoff, artifact, forged, LocalExecutionApproval(forged.digest, "reviewer"),
        )
