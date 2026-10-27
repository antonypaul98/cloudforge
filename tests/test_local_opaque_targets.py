"""Synthetic opaque target identities must never be interpreted as runtime instructions."""
import builtins
import os
from pathlib import Path
import socket
import subprocess

import pytest

from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution, prepare_local_execution_request,
)
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


@pytest.mark.parametrize("opaque_target", [
    "https://example.invalid/never-contact",
    "/synthetic/never-write",
    "provider://synthetic-target",
    "$(id)",
])
def test_opaque_target_is_not_resolved_or_executed(monkeypatch, opaque_target):
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    handoff_request = prepare_deployment_request(plan, proposal, opaque_target)
    handoff = authorize_deployment_handoff(
        plan, proposal, handoff_request,
        DeploymentApproval(handoff_request.digest, "synthetic-reviewer"),
    )
    artifact = b"synthetic-artifact"
    execution_request = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(execution_request.digest, "synthetic-execution-reviewer")

    def forbidden(*args, **kwargs):
        raise AssertionError("opaque target triggered an external operation")

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(Path, "open", forbidden)
        guard.setattr(Path, "write_bytes", forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(os, "system", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        receipt = authorize_local_execution(handoff, artifact, execution_request, approval)

    assert receipt.request.target_id == opaque_target
    assert receipt.status == "authorized-local-only"
    assert receipt.infrastructure_mutated is False
