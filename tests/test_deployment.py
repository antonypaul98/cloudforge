from dataclasses import FrozenInstanceError, replace
import json

import pytest

from cloudforge.approval import ApprovalRequiredError, PlanApproval, plan_digest
from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def fixture():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "team-a/staging")
    approval = DeploymentApproval(request.digest, "human@example.test")
    return plan, proposal, request, approval


def test_deterministic_end_to_end_handoff_preserves_provenance():
    p, i, r, a = fixture()
    receipt = authorize_deployment_handoff(p, i, r, a)
    assert receipt.to_json() == authorize_deployment_handoff(p, i, r, a).to_json()
    data = json.loads(receipt.to_json())
    assert data["status"] == "ready-for-adapter-review"
    assert data["infrastructure_mutated"] is False
    assert json.loads(data["request"]["document"])["resources"][0]["reason"]
    assert data["request_digest"] == r.digest
    assert data["request"]["plan_digest"] == plan_digest(p)


@pytest.mark.parametrize("target", [None, "", " ", " target", "target\n", "a\x00b", 42])
def test_invalid_target_fails_closed(target):
    p, i, _, _ = fixture()
    with pytest.raises(ValueError):
        prepare_deployment_request(p, i, target)


@pytest.mark.parametrize("field,value", [
    ("document", "{}\n"), ("plan_digest", "0" * 64),
    ("format_version", 2), ("format_version", True),
])
def test_tampered_proposal_rejected(field, value):
    p, i, r, a = fixture()
    with pytest.raises(ValueError):
        authorize_deployment_handoff(p, replace(i, **{field: value}), r, a)


@pytest.mark.parametrize("field,value", [
    ("document", "{}\n"), ("plan_digest", "0" * 64),
    ("operation", "deploy"), ("format_version", 2), ("format_version", True),
])
def test_forged_request_cannot_self_approve(field, value):
    p, i, r, _ = fixture()
    forged = replace(r, **{field: value})
    with pytest.raises(ValueError):
        authorize_deployment_handoff(p, i, forged, DeploymentApproval(forged.digest, "human"))


def test_target_change_requires_renewed_approval():
    p, i, r, a = fixture()
    changed = prepare_deployment_request(p, i, "team-a/production")
    assert changed.digest != r.digest
    with pytest.raises(ApprovalRequiredError):
        authorize_deployment_handoff(p, i, changed, a)


def test_plan_mutation_after_review_cannot_use_old_approval():
    p, i, r, a = fixture()
    snapshot = r.document
    p.resources[0].properties["runtime"] = "node"
    assert r.document == snapshot
    with pytest.raises(ValueError):
        authorize_deployment_handoff(p, i, r, a)
    new_i = render_iac_proposal(p)
    new_r = prepare_deployment_request(p, new_i, r.target_id)
    with pytest.raises(ApprovalRequiredError):
        authorize_deployment_handoff(p, new_i, new_r, a)


def test_resource_reordering_requires_new_approval_even_if_document_same():
    p, i, r, a = fixture()
    changed = replace(p, resources=tuple(reversed(p.resources)))
    new_i = render_iac_proposal(changed)
    assert i.document == new_i.document
    new_r = prepare_deployment_request(changed, new_i, r.target_id)
    assert new_r.digest != r.digest
    with pytest.raises(ApprovalRequiredError):
        authorize_deployment_handoff(changed, new_i, new_r, a)


@pytest.mark.parametrize("name", [None, "", "  ", "human\n", 3])
def test_invalid_approver_rejected(name):
    p, i, r, _ = fixture()
    with pytest.raises(ApprovalRequiredError):
        authorize_deployment_handoff(p, i, r, DeploymentApproval(r.digest, name))


def test_plan_approval_cannot_authorize_deployment_handoff():
    p, i, r, _ = fixture()
    for invalid in (None, True, PlanApproval(plan_digest(p), "human")):
        with pytest.raises(ApprovalRequiredError):
            authorize_deployment_handoff(p, i, r, invalid)


@pytest.mark.parametrize("value", [False, 0, 1, "true", None])
def test_approval_bypass_on_plan_rejected(value):
    p, i, r, a = fixture()
    with pytest.raises(ValueError):
        authorize_deployment_handoff(replace(p, requires_approval=value), i, r, a)


def test_request_and_receipt_are_immutable():
    p, i, r, a = fixture()
    with pytest.raises(FrozenInstanceError):
        r.target_id = "other"
    with pytest.raises(FrozenInstanceError):
        authorize_deployment_handoff(p, i, r, a).infrastructure_mutated = True
