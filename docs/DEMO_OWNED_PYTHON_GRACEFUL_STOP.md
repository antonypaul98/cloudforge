# Fixed first-party Python OCI graceful-stop trial

This bounded demo-reliability slice addresses an observed gap: the disposable
rootless Podman Python fixture previously escalated its normal stop from SIGTERM
to SIGKILL. It did demonstrate crash recovery, but not clean shutdown.

## Reuse and scope

Reuse the existing first-party Python HTTP fixture, the pinned source-package
verification, synthetic two-key admission, private staging, rootless Podman,
restricted separate-container observer, and existing CI workflow. The only
runtime change is a Python 3.11 standard-library `signal.SIGTERM` handler
raising `SystemExit(0)` and `HTTPServer.server_close()` in `finally`.
A synchronous `HTTPServer.shutdown()` call from its serving thread would
deadlock, so it is deliberately not used. No third-party source was copied,
new package installed, permission relaxed or external application selected.

The exact fixture source digest is updated alongside its static regression.
The OCI workflow must now verify stopped state **and exit code zero** after
`podman stop -t 3`, before restarting the same container. A forced kill
reports exit code 137 and must fail this clean-stop gate. Deliberate SIGKILL
and post-crash health checks remain separate and unchanged.

## Acceptance and limits

A local process trial with a temporary alternate port observed HTTP health and
SIGTERM exit code zero. The default port 8080 was occupied in that test
environment, so this is not exact-byte OCI acceptance. The real disposable
rootless OCI CI, exact-head product suite and merged-main CI must all succeed
before recording canonical acceptance. A green static check alone is insufficient.

This is only a fixed first-party synthetic-admission fixture, not independently
authenticated human approval, external selected-source execution, independent
signed observation, production deployment, multi-tenant isolation or actual
infrastructure rollback. No physical Mac or production infrastructure needed.
Rollback the software change by reverting its PR; the CI containers and ledger
are ephemeral. No persistent migration is introduced.

**Demo readiness: partial until CI proves the clean-stop behavior. Full product
completion: unverified.** Continue toward independently authenticated,
artifact-specific selected-application execution and trusted health/rollback
after this bounded checkpoint is accepted.
