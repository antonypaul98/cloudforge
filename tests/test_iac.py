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


@pytest.mark.parametrize("value", [True, 0, 65536, "8080", None])
def test_iac_rejects_malformed_ports(value):
    plan = replace(_plan(), resources=(ResourceRequirement("network", "declared port", {"port": value}),))
    with pytest.raises(ValueError):
        render_iac_proposal(plan)


@pytest.mark.parametrize("value", [1, "true", None])
def test_iac_requires_literal_approval_flag(value):
    with pytest.raises(ValueError):
        render_iac_proposal(replace(_plan(), requires_approval=value))


@pytest.mark.parametrize("second_port", [8080, 9090])
def test_iac_rejects_ambiguous_or_conflicting_duplicate_resources(second_port):
    resources = (
        ResourceRequirement("network", "first source", {"port": 8080}),
        ResourceRequirement("network", "second source", {"port": second_port}),
    )
    with pytest.raises(ValueError, match="duplicate"):
        render_iac_proposal(replace(_plan(), resources=resources))


@pytest.mark.parametrize("resource", [
    ResourceRequirement("compute", "", {"runtime": "python"}),
    ResourceRequirement("compute", "runtime", {"runtime": ""}),
    ResourceRequirement("compute", "runtime", {"runtime": "python", "source": " "}),
    ResourceRequirement("compute", "runtime", {"runtime": "python", "aws_region": "us-east-1"}),
    ResourceRequirement("database", "database", {"engine": "unknown"}),
    ResourceRequirement("cache", "cache", {"engine": "postgresql"}),
    ResourceRequirement("network", "port", {}),
    ResourceRequirement("compute", "runtime", {"runtime": float("nan")}),
    ResourceRequirement("compute", "runtime", {"runtime": {"nested": "ambiguous"}}),
])
def test_iac_rejects_missing_provenance_or_unsupported_properties(resource):
    with pytest.raises(ValueError):
        render_iac_proposal(replace(_plan(), resources=(resource,)))


def test_resource_order_is_normalized_but_approval_binds_exact_input_plan():
    plan = _plan()
    reordered = replace(plan, resources=tuple(reversed(plan.resources)))
    first, second = render_iac_proposal(plan), render_iac_proposal(reordered)
    assert first.document == second.document
    # A normalization must never silently reuse approval of a different input plan.
    assert first.plan_digest != second.plan_digest
    with pytest.raises(ApprovalRequiredError):
        require_plan_approval(reordered, PlanApproval(first.plan_digest, "reviewer"))


def test_property_key_order_does_not_change_document_or_digest():
    a = ResourceRequirement("compute", "runtime source", {"source": "pyproject.toml", "runtime": "python"})
    b = replace(a, properties={"runtime": "python", "source": "pyproject.toml"})
    assert render_iac_proposal(replace(_plan(), resources=(a,))) == render_iac_proposal(replace(_plan(), resources=(b,)))
