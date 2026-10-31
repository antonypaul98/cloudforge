# GitHub environment approval evidence preflight (read-only)

This demo-first checkpoint adds a bounded verifier for an **independently fetched
GitHub Actions deployment review**. It is an alternative to treating CloudForge's
synthetic HMAC reviewer key as a human identity. It does **not** execute selected
code or confer permission to do so.

The verifier uses only GitHub's public REST API over TLS, with redirects refused,
a 5-second request timeout and a 128 KiB response bound. No API token, cloud
credential, subprocess, source file, secret, or external application is read or
executed. Public GitHub repositories only; unavailable or malformed evidence
fails closed. Tests replace the private fetch function with offline GitHub-shaped
responses. A passing offline test is **not** evidence that a real reviewer acted.

## Exact evidence contract

The caller independently pins the repository, workflow run ID, exact 40-character
commit SHA, exact selected-source package SHA-256 and trusted GitHub reviewer
account ID. The run must be a first-attempt manual workflow_dispatch on
protected main, for .github/workflows/selected-user-app.yml, at the exact
commit. The configured cloudforge-selected-application environment must require
a different named GitHub User reviewer, prevent self-review and allow only
protected branches. Exactly one relevant GitHub deployment review must be
approved by that reviewer with the **entire comment** exactly:

    cloudforge-artifact-sha256:<64 lowercase hexadecimal characters>

Any rejection or ambiguous multiple reviews in the run's environment history blocks the receipt.
Missing approvals, a different artifact, changed run SHA, wrong reviewer, a
re-run, a different workflow, disabled protection or self-review fail closed.
The result explicitly sets execution_permitted=false and
human_identity_verified=false. No raw application source or credentials
appear in the receipt.

This is a **GitHub-account evidence check**, not a proof of a human's identity:
accounts can be compromised or automated; the environment may have changed
since the review; a review comment is not a cryptographic signature over the
source. A later executor must obtain and enforce a fresh, independently
authenticated artifact-specific decision and validate the exact source bytes,
environment/run provenance, isolated runtime, health evidence and rollback.
Do not treat a caller-supplied expected SHA or the return value as authority.

## Integration boundary and limitations

There is deliberately **no selected-user-app workflow** or configured
deployment environment in this checkpoint. No GitHub environment is created
automatically, because an unprotected environment could silently allow a job
to run. The verifier has not observed a real approved workflow run and is not
wired into any executor. An independent reviewer and protected environment
must be explicitly configured and verified before real use. This is not a
request for the repository owner to do routine testing.

Reuse-first: GitHub's existing environment required-reviewer and deployment
review-history REST APIs, and Python 3.11 standard-library JSON/urllib. No
third-party code copied or translated, new dependency, provider account,
API charge, or production infrastructure. The source and tests are isolated
on a feature branch before exact-head CI. Revert the feature merge for
software rollback; no migration or persistent state.

Official references:
- https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- https://docs.github.com/en/rest/actions/workflow-runs#get-the-review-history-for-a-workflow-run
- https://docs.github.com/en/rest/deployments/environments#get-an-environment

**Demo readiness:** Partial. The prior two first-party OCI fixtures remain
the only verified application executions. This preflight is only a read-only
identity/evidence prerequisite, not the differentiated end-to-end demo.

**Full product completion:** Unverified. No evidence-based percentage or date.

## Verified feature-head and merged-main evidence (2026-10-31)

[Feature PR #169](https://github.com/antonypaul98/cloudforge/pull/169) merged as
`a54d8dfa60a18ee2dedd77d56338b334b37642ec` after exact head
`f4c381809dd0ad8efc25ae09686d663491c129bb` passed
[push CI #41195313134](https://github.com/antonypaul98/cloudforge/actions/runs/41195313134),
[PR CI #41195328388](https://github.com/antonypaul98/cloudforge/actions/runs/41195328388),
and [merged-main CI #41195404277](https://github.com/antonypaul98/cloudforge/actions/runs/41195404277).
Python 3.11.17: **1,554 passed, 2 skipped**; infrastructure: **43 tests run, 1 skipped**.
The 36 new pytest cases used offline GitHub-shaped snapshots; no live protected
environment approval was exercised. The feature is a non-executing evidence
preflight only. This acceptance-documentation PR requires its own exact-head
and merged-main CI before publication is complete.
