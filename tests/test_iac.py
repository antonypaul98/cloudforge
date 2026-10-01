import json
from dataclasses import replace

import pytest

from cloudforge.approval import ApprovalRequiredError, PlanApproval, require_plan_approval
from cloudforge.iac import render_iac_proposal
from cloudforge.models import ApplicationProfile, InfrastructurePlan, ResourceRequirement
from cloudforge.planner import derive_requirements


def _plan():
    return derive_requirements(
        ApplicationProfile(
            "api",
            "python",
            port=8080,
            dependencies=("postgres", "redis"),
        )
    )


def test_iac_proposal_is_deterministic_and_review_only():
    plan = _plan()
    first = render_iac_proposal(plan)
    second = render_iac_proposal(plan)
    assert first == second
    assert first.format_version == 1
    assert json.loads(first.document)["application"] == "api"


def test_iac_proposal_binds_to_exact_plan():
    plan = _plan()
    changed = replace(plan, application="other-api")
    assert render_iac_proposal(plan).plan_digest != render_iac_proposal(changed).plan_digest


def test_iac_proposal_preserves_provider_neutral_requirements():
    payload = json.loads(render_iac_proposal(_plan()).document)
    assert [resource["kind"] for resource in payload["resources"]] == [
        "compute",
        "network",
        "database",
        "cache",
    ]
    assert payload["requires_approval"] is True


def test_iac_proposal_document_and_hash_are_stable():
    plan = _plan()
    proposal = render_iac_proposal(plan)
    assert proposal.document == render_iac_proposal(plan).document
    assert proposal.plan_digest == render_iac_proposal(plan).plan_digest


def test_iac_proposal_preserves_requirement_provenance():
    plan = InfrastructurePlan(
        application="api",
        resources=(
            ResourceRequirement(
                kind="compute",
                reason="python runtime detected",
                properties={"runtime": "python", "source": "application-inspection"},
            ),
        ),
    )
    resource = json.loads(render_iac_proposal(plan).document)["resources"][0]
    assert resource["reason"] == "python runtime detected"
    assert resource["properties"]["source"] == "application-inspection"


@pytest.mark.parametrize("application", ["", "   "])
def test_iac_proposal_rejects_missing_application_identity(application):
    with pytest.raises(ValueError, match="application identity"):
        render_iac_proposal(replace(_plan(), application=application))


def test_iac_proposal_rejects_removed_approval_boundary():
    with pytest.raises(ValueError, match="explicit approval"):
        render_iac_proposal(replace(_plan(), requires_approval=False))


def test_iac_proposal_rejects_provider_specific_or_unknown_resource_kind():
    malformed = ResourceRequirement(kind="compute", reason="test")
    object.__setattr__(malformed, "kind", "aws_ec2")
    plan = replace(_plan(), resources=(malformed,))
    with pytest.raises(ValueError, match="unsupported resource kind"):
        render_iac_proposal(plan)


def test_plan_mutation_invalidates_existing_exact_plan_approval():
    plan = _plan()
    proposal = render_iac_proposal(plan)
    approval = PlanApproval(plan_digest=proposal.plan_digest, approved_by="reviewer")
    require_plan_approval(plan, approval)

    mutated = replace(plan, application="other-api")
    with pytest.raises(ApprovalRequiredError, match="does not match"):
        require_plan_approval(mutated, approval)
