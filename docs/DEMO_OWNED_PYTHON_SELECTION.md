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
