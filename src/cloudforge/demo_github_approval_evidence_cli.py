"""Read-only CLI for pinned GitHub account review evidence.

This tool reports evidence only. It never grants execution permission, launches
an application, or mutates GitHub environments or infrastructure.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .demo_github_approval_evidence import verify_selected_github_approval_evidence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect exact GitHub account review evidence; never authorize execution."
    )
    parser.add_argument("--repository", required=True, help="Pinned owner/repo")
    parser.add_argument("--run-id", required=True, type=int, help="Pinned workflow run ID")
    parser.add_argument("--head-sha", required=True, help="Pinned 40-character commit SHA")
    parser.add_argument("--artifact-sha256", required=True, help="Pinned selected-source digest")
    parser.add_argument("--reviewer-account-id", required=True, type=int,
                        help="Independently trusted GitHub account ID")
    args = parser.parse_args(argv)

    try:
        receipt = verify_selected_github_approval_evidence(
            repository_full_name=args.repository,
            run_id=args.run_id,
            expected_head_sha=args.head_sha,
            expected_artifact_sha256=args.artifact_sha256,
            trusted_reviewer_id=args.reviewer_account_id,
        )
    except ValueError:
        # Do not echo untrusted API response bodies or caller-supplied source.
        print(json.dumps({
            "github_account_review_evidence_verified": False,
            "human_identity_verified": False,
            "execution_permitted": False,
            "application_executed": False,
        }, sort_keys=True))
        return 1

    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
