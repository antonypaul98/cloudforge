from dataclasses import replace

import pytest

from cloudforge.approval import (
    ApprovalRequiredError,
    PlanApproval,
    plan_digest,
    require_plan_approval,
)
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def _plan():
    return derive_requirements(ApplicationProfile("api", "python", port=8080))


def test_digest_is_deterministic_for_same_plan():
    plan = _plan()
    assert plan_digest(plan) == plan_digest(plan)


def test_exact_plan_approval_is_accepted():
    plan = _plan()
    require_plan_approval(plan, PlanApproval(plan_digest(plan), "antony"))


def test_missing_approval_fails_closed():
    with pytest.raises(ApprovalRequiredError, match="explicit approval"):
        require_plan_approval(_plan(), None)


def test_empty_approver_is_rejected():
    plan = _plan()
    with pytest.raises(ApprovalRequiredError, match="identify an approver"):
        require_plan_approval(plan, PlanApproval(plan_digest(plan), "   "))


def test_stale_approval_is_rejected_after_plan_changes():
    plan = _plan()
    approval = PlanApproval(plan_digest(plan), "antony")
    changed = replace(plan, application="different-api")
    with pytest.raises(ApprovalRequiredError, match="does not match"):
        require_plan_approval(changed, approval)
