# Pinned first-party source-selection OCI trial (in progress)

This demo-first slice replaces one hardcoded first-party OCI fixture trial with a
two-variant GitHub Actions matrix. Each variant has a separately reviewed
SHA-256-pinned Python source file and a distinct expected HTTP health body.
The selected variant changes the exact source package, source-bound review
digest, staged OCI build input and observed response. The job must pass for
both variants, including graceful shutdown, deliberate SIGKILL recovery and
cleanup, before this feature is accepted.

The matrix is static and checked into the repository. No arbitrary paths,
workflow-dispatch input, fork source, package installation, secrets or cloud
resources are admitted. It is **not a user-selected external application** and
does **not authenticate a human**. Synthetic CI-only keys remain synthetic.
The disposable runner is not a production deployment, independent health
attestation, trusted multi-tenant sandbox or infrastructure rollback.

Reuse: existing first-party package/review/staging/admission, rootless Podman,
separate BusyBox observer, Python 3.11 standard-library fixture and the GitHub
Actions matrix feature. No third-party code copied or translated, no new Python
dependency or provider API cost. GitHub's official matrix contract:
https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax

Acceptance: both exact-head matrix jobs must succeed, as must full Python and
infrastructure suites, protected merge and merged-main CI. Failed jobs must not
be described as passing. Revert the feature merge for software rollback; the
CI containers and staging are disposable. The next genuine demo gate remains
independently authenticated, artifact-specific approval for a user-selected
application in an isolated runtime, then trusted health and controlled rollback.

**Demo readiness:** Partial until the actual selected-application gate.
**Full product completion:** Unverified.

## Verified first-party selection feature, 2026-10-31

[Feature PR #165](https://github.com/antonypaul98/cloudforge/pull/165)
merged as `6109a4e37fa8993cf896c2cfaaf64194d7b05a8c` after exact
head `637244b86841e1badf1666e0eaaf4694a9ceb83a` passed
[push product CI #41191134282](https://github.com/antonypaul98/cloudforge/actions/runs/41191134282),
[PR product CI #41191138189](https://github.com/antonypaul98/cloudforge/actions/runs/41191138189),
and [real rootless OCI PR #41191138091](https://github.com/antonypaul98/cloudforge/actions/runs/41191138091)
(attempt 2). [Merged-main CI #41191293408](https://github.com/antonypaul98/cloudforge/actions/runs/41191293408)
succeeded. Python 3.11.17: **1,518 pytest passed, 2 skipped;
43 infrastructure tests run, 1 skipped**. Both OCI matrix variants
reported their distinct source digests and successful actual HTTP health,
graceful stop, deliberate SIGKILL recovery and cleanup.

The first feature commit failed two static mutation assertions; the test
guard was corrected before final-head validation. The alternate OCI runner
initially failed rootless prerequisite probing
(`local-podman-probe-unavailable`), while the primary succeeded. Retrying
the failed job on the same exact head succeeded; no isolation bypass or
code change was made to suppress the failure. These failed attempts remain
visible in GitHub Actions history.

**Accepted only:** static choice between two CloudForge-owned, SHA-pinned
Python source fixtures, each built and observed in a disposable rootless
OCI job. This does not establish external user-selected application execution,
independent human authorization, signed independent health, hardened
multi-tenant isolation, real provider deployment or infrastructure rollback.
No Mac, Astra/Work or production infrastructure used. Canonical documentation
and state acceptance still require this PR's own exact-head CI, guarded merge
and merged-main CI. Demo readiness remains partial; full completion unverified.

## Canonical documentation acceptance (2026-10-31)

[PR #166](https://github.com/antonypaul98/cloudforge/pull/166) passed
[exact-head PR CI #41191408775](https://github.com/antonypaul98/cloudforge/actions/runs/41191408775),
merged as `cf5b751360e64af7577786668fee4e1b31aba088` and passed
[merged-main CI #41191460316](https://github.com/antonypaul98/cloudforge/actions/runs/41191460316).
The final checkpoint state publication has its own independent exact-head and
merged-main CI gate. This does not change the first-party-only demo boundary.
