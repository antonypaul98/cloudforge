"""Reject forged handoff provenance before local execution authorization."""

from dataclasses import replace
import json

import pytest

from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import prepare_local_execution_request
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def _handoff():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    return authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "reviewer"),
    )


@pytest.mark.parametrize(("field", "value"), [
    ("plan_digest", None),
    ("plan_digest", True),
    ("plan_digest", ""),
    ("plan_digest", "0" * 63),
    ("plan_digest", "G" * 64),
    ("document", None),
    ("document", True),
    ("document", []),
    ("document", ""),
    ("document", "   "),
])
def test_recomputed_handoff_digest_does_not_launder_invalid_provenance(field, value):
    handoff = _handoff()
    forged_request = replace(handoff.request, **{field: value})
    forged_handoff = replace(
        handoff, request=forged_request, request_digest=forged_request.digest,
    )
    with pytest.raises(ValueError, match="malformed handoff provenance or document"):
        prepare_local_execution_request(forged_handoff, b"synthetic-artifact")


def test_valid_canonical_handoff_still_prepares_exact_artifact_request():
    handoff = _handoff()
    request = prepare_local_execution_request(handoff, b"synthetic-artifact")
    assert request.target_id == "staging"
    assert request.handoff_digest == handoff.request_digest

@pytest.mark.parametrize("document", [
    "not-json",
    '{"application": "api"}',
    '{"application": "api", "requires_approval": false, "resources": []}',
    '{"application": "api", "requires_approval": true, "resources": []}',
    '{"application": "api", "requires_approval": true, "resources": [1]}',
])
def test_recomputed_handoff_digest_cannot_launder_noncanonical_document(document):
    handoff = _handoff()
    forged_request = replace(handoff.request, document=document)
    forged_handoff = replace(
        handoff, request=forged_request, request_digest=forged_request.digest,
    )
    with pytest.raises(ValueError, match="malformed handoff provenance or document"):
        prepare_local_execution_request(forged_handoff, b"synthetic-artifact")

@pytest.mark.parametrize("resources", [
    [{"kind": "compute", "reason": "synthetic", "properties": {"runtime": ""}}],
    [{"kind": "compute", "reason": "synthetic",
      "properties": {"runtime": "python", "provider": "unsupported"}}],
    [{"kind": "network", "reason": "synthetic", "properties": {"port": 0}}],
    [{"kind": "database", "reason": "synthetic", "properties": {"engine": "mysql"}}],
    [{"kind": "compute", "reason": "synthetic", "properties": {"runtime": "python"}},
     {"kind": "compute", "reason": "duplicate", "properties": {"runtime": "python"}}],
])
def test_canonical_json_cannot_launder_invalid_resource_semantics(resources):
    handoff = _handoff()
    payload = json.loads(handoff.request.document)
    payload["resources"] = resources
    document = json.dumps(payload, sort_keys=True, indent=2,
                          ensure_ascii=True, allow_nan=False) + "\n"
    forged_request = replace(handoff.request, document=document)
    forged_handoff = replace(
        handoff, request=forged_request, request_digest=forged_request.digest,
    )
    with pytest.raises(ValueError, match="malformed handoff provenance or document"):
        prepare_local_execution_request(forged_handoff, b"synthetic-artifact")


@pytest.mark.parametrize("forged_digest", ["0" * 64, "f" * 64])
def test_canonical_document_rejects_unrelated_well_formed_plan_digest(forged_digest):
    handoff = _handoff()
    forged_request = replace(handoff.request, plan_digest=forged_digest)
    forged_handoff = replace(
        handoff, request=forged_request, request_digest=forged_request.digest,
    )
    with pytest.raises(ValueError, match="malformed handoff provenance or document"):
        prepare_local_execution_request(forged_handoff, b"synthetic-artifact")


def test_valid_original_resource_order_remains_accepted_after_document_sort():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    reversed_plan = replace(plan, resources=tuple(reversed(plan.resources)))
    proposal = render_iac_proposal(reversed_plan)
    request = prepare_deployment_request(reversed_plan, proposal, "staging")
    handoff = authorize_deployment_handoff(
        reversed_plan, proposal, request,
        DeploymentApproval(request.digest, "reviewer"),
    )
    assert prepare_local_execution_request(handoff, b"synthetic-artifact").handoff_digest == request.digest
