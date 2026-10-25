"""Reject untrusted handoff documents with excessive JSON nesting, without executing anything."""
from dataclasses import replace

import pytest

from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import prepare_local_execution_request
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def test_excessively_nested_handoff_document_fails_closed():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    handoff = authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "reviewer")
    )
    depth = 20000
    forged_request = replace(request, document="[" * depth + "0" + "]" * depth)
    forged_handoff = replace(
        handoff, request=forged_request, request_digest=forged_request.digest
    )
    with pytest.raises(ValueError, match="malformed handoff provenance or document"):
        prepare_local_execution_request(forged_handoff, b"synthetic-artifact")


def test_oversized_handoff_document_fails_before_json_parsing(monkeypatch):
    """A huge caller-supplied review document must be rejected before parsing."""
    handoff = _handoff()
    oversized = '{"application":"api","padding":"' + ("x" * 65536) + '"}'
    forged_request = replace(handoff.request, document=oversized)
    forged_handoff = replace(
        handoff, request=forged_request, request_digest=forged_request.digest
    )

    def unexpected_parse(*args, **kwargs):
        raise AssertionError("oversized handoff must fail before JSON parsing")

    monkeypatch.setattr("cloudforge.local_adapter.json.loads", unexpected_parse)
    with pytest.raises(ValueError, match="malformed handoff provenance or document"):
        prepare_local_execution_request(forged_handoff, b"synthetic-artifact")
