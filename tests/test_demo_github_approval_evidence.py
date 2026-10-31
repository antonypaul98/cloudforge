"""Offline regression tests for read-only GitHub environment review evidence."""
from copy import deepcopy
import socket
import subprocess

import pytest

from cloudforge import demo_github_approval_evidence as gate


HEAD = "a" * 64
ARTIFACT = "b" * 64
REPO = "antonypaul98/cloudforge"
RUN = 17
REVIEWER = 200
ENV = "cloudforge-selected-application"
KW = dict(repository_full_name=REPO, run_id=RUN, expected_head_sha=HEAD,
          expected_artifact_sha256=ARTIFACT, trusted_reviewer_id=REVIEWER)


def snapshots():
    run = {
        "id": RUN, "head_sha": HEAD, "event": "workflow_dispatch",
        "head_branch": "main", "path": ".github/workflows/selected-user-app.yml",
        "run_attempt": 1, "repository": {"full_name": REPO},
        "actor": {"id": 100},
    }
    environment = {
        "id": 300, "name": ENV,
        "deployment_branch_policy": {
            "protected_branches": True, "custom_branch_policies": False,
        },
        "protection_rules": [{
            "type": "required_reviewers", "prevent_self_review": True,
            "reviewers": [{"type": "User", "reviewer": {
                "id": REVIEWER, "type": "User", "login": "independent-reviewer",
            }}],
        }],
    }
    reviews = [{
        "state": "approved",
        "comment": "cloudforge-artifact-sha256:" + ARTIFACT,
        "user": {"id": REVIEWER, "type": "User"},
        "environments": [{"id": 300, "name": ENV}],
    }]
    return [run, environment, reviews]


def install(monkeypatch, values):
    def read(path):
        if path.endswith("/approvals"):
            return deepcopy(values[2])
        if "/environments/" in path:
            return deepcopy(values[1])
        return deepcopy(values[0])
    monkeypatch.setattr(gate, "_get_json", read)


def test_exact_independent_account_review_is_evidence_only(monkeypatch):
    install(monkeypatch, snapshots())
    receipt = gate.verify_selected_github_approval_evidence(**KW)
    assert receipt["github_account_review_evidence_verified"] is True
    assert receipt["execution_permitted"] is False
    assert receipt["human_identity_verified"] is False
    assert receipt["application_executed"] is False
    assert receipt["head_sha"] == HEAD
    assert receipt["artifact_sha256"] == ARTIFACT
    assert "independent-reviewer" not in repr(receipt)


@pytest.mark.parametrize("change", [
    {"run_id": True}, {"run_id": 0}, {"trusted_reviewer_id": True},
    {"trusted_reviewer_id": -1}, {"repository_full_name": "owner/repo/extra"},
    {"repository_full_name": "owner/%2f"}, {"expected_head_sha": "A" * 64},
    {"expected_artifact_sha256": "b" * 63},
])
def test_invalid_pins_fail_before_any_fetch(monkeypatch, change):
    def forbidden(_path):
        pytest.fail("invalid inputs must fail before network")
    monkeypatch.setattr(gate, "_get_json", forbidden)
    with pytest.raises(ValueError, match="invalid pinned"):
        gate.verify_selected_github_approval_evidence(**{**KW, **change})


@pytest.mark.parametrize("path,value", [
    (("id",), 18), (("head_sha",), "c" * 64),
    (("event",), "pull_request"), (("head_branch",), "feature"),
    (("path",), ".github/workflows/other.yml"),
    (("run_attempt",), 2), (("run_attempt",), True),
    (("repository", "full_name"), "other/repo"),
    (("actor", "id"), REVIEWER),
])
def test_changed_run_or_self_review_rejected(monkeypatch, path, value):
    data = snapshots()
    item = data[0]
    for key in path[:-1]:
        item = item[key]
    item[path[-1]] = value
    install(monkeypatch, data)
    with pytest.raises(ValueError):
        gate.verify_selected_github_approval_evidence(**KW)


@pytest.mark.parametrize("path,value", [
    (("id",), 301), (("name",), "unsafe"),
    (("deployment_branch_policy", "protected_branches"), False),
    (("deployment_branch_policy", "custom_branch_policies"), True),
    (("protection_rules", 0, "prevent_self_review"), False),
    (("protection_rules", 0, "reviewers", 0, "reviewer", "id"), 201),
    (("protection_rules", 0, "reviewers", 0, "type"), "Team"),
])
def test_unprotected_or_different_reviewer_rejected(monkeypatch, path, value):
    data = snapshots()
    item = data[1]
    for key in path[:-1]:
        item = item[key]
    item[path[-1]] = value
    install(monkeypatch, data)
    with pytest.raises(ValueError):
        gate.verify_selected_github_approval_evidence(**KW)


@pytest.mark.parametrize("change", [
    {"state": "pending"}, {"state": "rejected"},
    {"comment": "approved"}, {"comment": "cloudforge-artifact-sha256:" + "c" * 64},
    {"user": {"id": 100, "type": "User"}},
    {"user": {"id": REVIEWER, "type": "Bot"}},
    {"environments": [{"id": 999, "name": ENV}]},
])
def test_review_changes_fail_closed(monkeypatch, change):
    data = snapshots()
    data[2][0].update(change)
    install(monkeypatch, data)
    with pytest.raises(ValueError):
        gate.verify_selected_github_approval_evidence(**KW)


def test_later_review_overrides_earlier_approval(monkeypatch):
    data = snapshots()
    later = deepcopy(data[2][0])
    later["comment"] = "not artifact scoped"
    data[2].append(later)
    install(monkeypatch, data)
    with pytest.raises(ValueError, match="exact independent"):
        gate.verify_selected_github_approval_evidence(**KW)


def test_rejection_anywhere_in_history_blocks(monkeypatch):
    data = snapshots()
    earlier = deepcopy(data[2][0])
    earlier["state"] = "rejected"
    data[2].insert(0, earlier)
    install(monkeypatch, data)
    with pytest.raises(ValueError, match="not approved"):
        gate.verify_selected_github_approval_evidence(**KW)


def test_no_reviews_or_fetch_error_fail_closed(monkeypatch):
    data = snapshots()
    data[2] = []
    install(monkeypatch, data)
    with pytest.raises(ValueError, match="no GitHub"):
        gate.verify_selected_github_approval_evidence(**KW)
    def unavailable(_path):
        raise ValueError("GitHub unavailable")
    monkeypatch.setattr(gate, "_get_json", unavailable)
    with pytest.raises(ValueError, match="unavailable"):
        gate.verify_selected_github_approval_evidence(**KW)


def test_verification_never_executes_or_opens_socket(monkeypatch):
    install(monkeypatch, snapshots())
    def forbidden(*args, **kwargs):
        pytest.fail("verification must not execute or contact runtime")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    assert gate.verify_selected_github_approval_evidence(**KW)["execution_permitted"] is False
