"""Read-only GitHub deployment-review evidence check for a selected-app demo.

This checks independently fetched GitHub account and environment records, not
a person's identity or an execution permission. No selected code is run.
Only public github.com repositories are supported; failures are fail-closed.
"""
from __future__ import annotations

import json
import re
from urllib.request import HTTPRedirectHandler, Request, build_opener


_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_ENVIRONMENT = "cloudforge-selected-application"
_WORKFLOW = ".github/workflows/selected-user-app.yml"
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_MAX_RESPONSE = 131_072


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("GitHub evidence redirect refused")


def _get_json(path: str) -> object:
    """Fetch only fixed-shape GitHub REST paths over TLS; no token or redirects."""
    url = "https://api.github.com" + path
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "cloudforge-read-only-approval-evidence",
    })
    try:
        with build_opener(_NoRedirect).open(request, timeout=5) as response:
            if response.geturl() != url:
                raise ValueError("GitHub evidence redirect refused")
            raw = response.read(_MAX_RESPONSE + 1)
    except (OSError, TimeoutError, ValueError) as exc:
        raise ValueError("GitHub approval evidence unavailable") from exc
    if len(raw) > _MAX_RESPONSE:
        raise ValueError("GitHub approval evidence exceeds size limit")
    try:
        return json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid GitHub approval evidence") from exc


def _account_id(account: object) -> int | None:
    if (type(account) is dict and account.get("type") == "User"
            and type(account.get("id")) is int and account["id"] > 0):
        return account["id"]
    return None


def verify_selected_github_approval_evidence(
    *, repository_full_name: str, run_id: int, expected_head_sha: str,
    expected_artifact_sha256: str, trusted_reviewer_id: int,
) -> dict[str, object]:
    """Check exact run, protected environment, reviewer and artifact comment.

    The expected SHA, artifact and reviewer ID MUST be pinned by an independent
    trusted caller. This is a read-only evidence receipt, not permission to
    execute. The private fetch helper is replaced only in offline tests.
    """
    if (type(repository_full_name) is not str
            or not _REPOSITORY.fullmatch(repository_full_name)
            or type(run_id) is not int or run_id <= 0
            or type(trusted_reviewer_id) is not int or trusted_reviewer_id <= 0
            or type(expected_head_sha) is not str
            or not _COMMIT.fullmatch(expected_head_sha)
            or type(expected_artifact_sha256) is not str
            or not _HEX.fullmatch(expected_artifact_sha256)):
        raise ValueError("invalid pinned GitHub approval inputs")

    root = "/repos/" + repository_full_name
    run = _get_json(root + "/actions/runs/" + str(run_id))
    environment = _get_json(root + "/environments/" + _ENVIRONMENT)
    approvals = _get_json(root + "/actions/runs/" + str(run_id) + "/approvals")

    if (type(run) is not dict or type(run.get("id")) is not int
            or run.get("id") != run_id
            or run.get("head_sha") != expected_head_sha
            or run.get("event") != "workflow_dispatch"
            or run.get("head_branch") != "main"
            or run.get("path") != _WORKFLOW
            or type(run.get("run_attempt")) is not int
            or run["run_attempt"] != 1
            or type(run.get("repository")) is not dict
            or run["repository"].get("full_name") != repository_full_name
            or type(run.get("actor")) is not dict
            or type(run["actor"].get("id")) is not int
            or run["actor"]["id"] <= 0):
        raise ValueError("GitHub run differs from pinned selected-app execution")

    if (type(environment) is not dict
            or environment.get("name") != _ENVIRONMENT
            or type(environment.get("id")) is not int
            or environment["id"] <= 0
            or type(environment.get("deployment_branch_policy")) is not dict
            or environment["deployment_branch_policy"].get("protected_branches") is not True
            or environment["deployment_branch_policy"].get("custom_branch_policies") is not False
            or type(environment.get("protection_rules")) is not list):
        raise ValueError("selected-app environment is not protected")

    reviewer_is_required = False
    for rule in environment["protection_rules"]:
        if type(rule) is not dict or rule.get("type") != "required_reviewers":
            continue
        if rule.get("prevent_self_review") is not True:
            continue
        reviewers = rule.get("reviewers")
        if type(reviewers) is not list:
            continue
        for reviewer in reviewers:
            if (type(reviewer) is dict and reviewer.get("type") == "User"
                    and _account_id(reviewer.get("reviewer")) == trusted_reviewer_id):
                reviewer_is_required = True
    if not reviewer_is_required or run["actor"]["id"] == trusted_reviewer_id:
        raise ValueError("independent required reviewer is not configured")

    if type(approvals) is not list or not approvals:
        raise ValueError("no GitHub deployment approval evidence")
    relevant = []
    for event in approvals:
        if type(event) is not dict or type(event.get("environments")) is not list:
            raise ValueError("malformed GitHub deployment review history")
        if any(type(item) is dict
               and item.get("id") == environment["id"]
               and item.get("name") == _ENVIRONMENT
               for item in event["environments"]):
            relevant.append(event)
    if len(relevant) != 1 or any(event.get("state") == "rejected" for event in relevant):
        raise ValueError("selected-app deployment not approved")
    latest = relevant[0]
    if (latest.get("state") != "approved"
            or _account_id(latest.get("user")) != trusted_reviewer_id
            or latest.get("comment")
            != "cloudforge-artifact-sha256:" + expected_artifact_sha256):
        raise ValueError("GitHub review is not an exact independent artifact approval")

    return {
        "format_version": 1,
        "repository": repository_full_name,
        "run_id": run_id,
        "head_sha": expected_head_sha,
        "artifact_sha256": expected_artifact_sha256,
        "environment": _ENVIRONMENT,
        "reviewer_account_id": trusted_reviewer_id,
        "github_account_review_evidence_verified": True,
        "human_identity_verified": False,
        "execution_permitted": False,
        "application_executed": False,
    }
