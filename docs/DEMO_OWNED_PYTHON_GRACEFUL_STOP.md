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

## Verified feature evidence (2026-10-31)

[Feature PR #153](https://github.com/antonypaul98/cloudforge/pull/153)
merged at `6acfce08887dcbec61f64c57e5496adf28f69e65`. Exact feature
head `113b64ac0841c08d4d9d338997b0ebbff619db56` passed
[push CI #41175176877](https://github.com/antonypaul98/cloudforge/actions/runs/41175176877),
[PR product CI #41175180693](https://github.com/antonypaul98/cloudforge/actions/runs/41175180693),
and [real OCI PR CI #41175180735](https://github.com/antonypaul98/cloudforge/actions/runs/41175180735).
[Merged-main CI #41175273874](https://github.com/antonypaul98/cloudforge/actions/runs/41175273874)
passed at the feature merge SHA. Python 3.11.17: 1,515 pytest passed,
2 existing skips; 38 infrastructure tests run, 1 skipped.

The real disposable rootless OCI job emitted
`graceful_stop=pass` after checking `podman stop -t 3` stopped the
fixed first-party Python process with exit code **0**, before restart.
It independently retained deliberate SIGKILL exit code **137**,
post-crash HTTP health and cleanup. The first feature push CI failed
because an older static test found the new normal-stop exit-code marker
before the deliberate crash marker; the assertion was corrected to
search after the SIGKILL step, and all final-head checks passed.

**Feature evidence is verified; canonical acceptance is pending this
documentation/state PR's exact-head CI, guarded merge and merged-main CI.**
This remains synthetic fixed first-party code, not authenticated human
approval, external selected application execution, signed independent
observation or real infrastructure rollback.

## Canonical acceptance evidence (2026-10-31)

[Documentation/state PR #154](https://github.com/antonypaul98/cloudforge/pull/154)
passed exact head `4be3e79316d4a51cb3b1cb4195d0906183d2d0d1`
[PR CI #41175387411](https://github.com/antonypaul98/cloudforge/actions/runs/41175387411),
merged as `4f1d591ddcef4af9d7b0a3cccae63b8b8eeee4ad`, and passed
[merged-main CI #41175444841](https://github.com/antonypaul98/cloudforge/actions/runs/41175444841).
The **fixed first-party OCI clean-stop checkpoint** is canonically accepted
subject to this final state publication's own exact-head and merged-main CI.
No external selected-app, independent human authorization, signed external
health or production rollback acceptance follows from this result.
