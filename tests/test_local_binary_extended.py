"""Nonduplicative binary-artifact authorization boundary regressions."""

from dataclasses import replace
import hashlib

import pytest

from cloudforge.approval import ApprovalRequiredError
from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution, prepare_local_execution_request,
)
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def _handoff():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    return authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "reviewer")
    )

def test_forged_binary_digest_cannot_reuse_approval():
    handoff = _handoff()
    artifact = b"\x00\xff"
    request = prepare_local_execution_request(handoff, artifact)
    forged = replace(request, artifact_sha256="0" * 64)
    with pytest.raises(ValueError):
        authorize_local_execution(
            handoff, artifact, forged,
            LocalExecutionApproval(request.digest, "execution-reviewer"),
        )

def test_visually_identical_unicode_artifacts_remain_byte_distinct():
    """Never normalize artifact bytes behind the approver's back."""
    handoff = _handoff()
    composed = "caf\u00e9".encode("utf-8")
    decomposed = "cafe\u0301".encode("utf-8")
    assert composed != decomposed
    original = prepare_local_execution_request(handoff, composed)
    changed = prepare_local_execution_request(handoff, decomposed)
    assert original.artifact_sha256 != changed.artifact_sha256
    assert original.digest != changed.digest
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(
            handoff, decomposed, changed,
            LocalExecutionApproval(original.digest, "execution-reviewer"),
        )

def test_binary_artifact_authorization_has_no_external_side_effects(monkeypatch):
    """Authorization remains read-only even for nontextual binary input."""
    import builtins
    import os
    import pathlib
    import socket
    import subprocess

    handoff = _handoff()
    artifact = b"\x00\xff\x80\x00"
    request = prepare_local_execution_request(handoff, artifact)

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected external side effect")

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(os, "system", forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(pathlib.Path, "open", forbidden)
        guard.setattr(pathlib.Path, "write_bytes", forbidden)
        receipt = authorize_local_execution(
            handoff, artifact, request,
            LocalExecutionApproval(request.digest, "execution-reviewer"),
        )
    assert receipt.infrastructure_mutated is False

def test_bytes_subclass_is_rejected_instead_of_implicitly_trusted():
    """The integrity boundary requires canonical built-in bytes, not a custom subclass."""
    class DerivedBytes(bytes):
        pass

    with pytest.raises(ValueError, match="exact bytes"):
        prepare_local_execution_request(_handoff(), DerivedBytes(b"artifact"))

def test_approval_subclass_cannot_impersonate_canonical_approval():
    """A caller-defined approval subtype must not bypass the exact approval type."""
    class DerivedApproval(LocalExecutionApproval):
        pass

    handoff = _handoff()
    artifact = b"\x00\xff"
    request = prepare_local_execution_request(handoff, artifact)
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(
            handoff, artifact, request,
            DerivedApproval(request.digest, "execution-reviewer"),
        )

def test_receipt_does_not_expose_artifact_bytes_or_raw_canary():
    """A deterministic authorization receipt records digests, not the artifact itself."""
    handoff = _handoff()
    artifact = b"SYNTHETIC-CANARY-DO-NOT-EMIT"
    request = prepare_local_execution_request(handoff, artifact)
    receipt = authorize_local_execution(
        handoff, artifact, request,
        LocalExecutionApproval(request.digest, "execution-reviewer"),
    )
    serialized = receipt.to_json()
    assert "SYNTHETIC-CANARY-DO-NOT-EMIT" not in serialized
    assert hashlib.sha256(artifact).hexdigest() in serialized
    assert receipt.infrastructure_mutated is False
