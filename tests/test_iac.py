import json
from dataclasses import replace

from cloudforge.iac import render_iac_proposal
from cloudforge.models import ApplicationProfile
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
