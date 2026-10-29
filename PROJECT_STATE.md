# CloudForge checkpoint state

Starting main: `1c85712ede05caca6d825cbbd0e5edf37e3316d6`.
Provider-neutral foundation was integrated through PR #1. The historical
`build/provider-neutral-core` branch is superseded and must not be remerged.

Current integration branch: `build/application-inspection`.
Inspection reads supplied text without application execution or infrastructure
access. It preserves provider-neutral profiles and the existing mandatory approval
boundary. Declared dependency parsing avoids comments/scripts as false evidence,
retains exact source paths, rejects conflicting aliases and reports malformed
manifests. Unsupported runtimes remain explicitly unknown; inspection is limited
to root Python/Node manifests and recognized PostgreSQL/Redis dependency names.

Full local validation: 20 tests passed. Exact-head CI and merged-main verification succeeded (receipt below). Subsequent deployment, observation, bounded simulation
and recovery gates are not claimed by this checkpoint. No infrastructure deployed.

## Verified integration — 2026-09-30

Checkpoint **application inspection accepted on main** through PR #2.

- Exact PR head: `477cfb119086cfb516eb658b1100705011d3e1bf`; CI run `36669376449` succeeded.
- Merge: `a3ea6a5a8eec968092ee69f7641479d2cf68f7c8`, fetched and verified locally.
- Merged-main CI run `36669485006` succeeded.
- Local reviewed/tested source tree equals the merged implementation tree.
- This follow-up records the completed integration; it changes documentation only.

## Deterministic IaC — current checkpoint (2026-10-03)

Canonical branch `build/deterministic-iac`, PR #4. Implementation and 48 local
Python 3.11 tests pass; exact final-head CI and merged-main verification pending.
The original 27 tests passed, but new regressions reproduced 19 validation/order
failures. The renderer now rejects nonliteral approval, invalid ports, missing
provenance, unsupported properties/engines and duplicate or conflicting kinds.
The foundation supports at most one compute, network, PostgreSQL and Redis
requirement, with an optional textual source. Unsupported shapes fail closed.

The document normalizes resource ordering (compute, network, database, cache)
and JSON keys; the existing plan digest intentionally binds the exact input
plan including resource order. Reordering a plan therefore requires renewed
approval even when its normalized document is unchanged. Provenance is retained.
No provider calls or infrastructure deployment occur. Later deployment,
observation and recovery checkpoints are not started.

Deterministic IaC COMPLETE: PR #4 exact head `2851d44f2877dd27010a596bb2f8fc763f8c35fc` passed
CI `37155407573`, merged as `96eb078366b0dfd8f377cac2a9e5c6d69152c0e3`, and merged-main CI
`37155522025` succeeded. All 48 local tests passed on merged main. No deployment.

## Deployment handoff foundation — 2026-10-04

Deterministic IaC remains complete. Current branch `build/deployment-handoff`
implements the next deployment prerequisite: reviewable target/artifact-bound
request and explicit approval receipt. See `docs/DEPLOYMENT_HANDOFF.md`.
No infrastructure execution or deployment acceptance is claimed. Local tests and
exact-head/merged-main CI receipts are recorded in CHECKPOINT_STATE.json.

Deployment handoff foundation COMPLETE through PR #5. Exact head
`a5663fbe9cdb39cd2f3f2af01e62314ca812057f` passed PR CI `37216846708`.
Merged main `79abcd9782ecfc3c235072886666940d1319824c` passed CI `37216883981`
and 80 local tests (zero skipped). This is review-only software acceptance;
actual deployment, observation, simulation and recovery remain unimplemented.

## Bounded local deployment adapter — in progress (2026-10-26)

PR #6 on `build/local-deployment-adapter` provides local-only authorization,
receipt verification and redacted audit evidence. Current changes add early
rejection of forged embedded receipt-request digests with two synthetic
regressions. Exact-head CI, independent approval, guarded merge and merged-main
CI remain separate gates. No provider, network, subprocess, container or
infrastructure mutation is authorized or claimed; runtime, observation and
recovery acceptance remain pending.

## Synthetic local authorization smoke acceptance — 2026-10-26

The credential-free, in-memory demo `python -m cloudforge.synthetic_demo`
exercises the full synthetic plan → handoff → exact-artifact authorization →
receipt verification → redacted audit path. It rejects a changed artifact and
a forged recovery status; two integration regressions cover deterministic,
redacted output and forbidden network/shell entry points. Synthetic reviewer
names are NOT authenticated human approvals. No provider, deployment, runtime,
observability or recovery acceptance is claimed.

Source commit `9a356b4002289138e6d7fbd216a8c838bcc8ac51` passed push CI
[40416854601](https://github.com/antonypaul98/cloudforge/actions/runs/40416854601)
and PR CI
[40416862749](https://github.com/antonypaul98/cloudforge/actions/runs/40416862749):
586 pytest passed and 19 infrastructure tests ran (1 inapplicable skip) on
Python 3.11.17. The final checkpoint evidence commit needs its own exact-head CI.
PR #6 is unmerged; main ruleset 25825521 still requires an independent approval.
The repository owner has requested a solo-developer workflow, but that ruleset
change has not been applied. No guarded merge or merged-main CI.

## Synthetic local boundary coverage extension — 2026-10-26

The in-memory smoke demo also tests rejection of a forged receipt reviewer and
cross-target authorization despite a self-consistent caller-supplied approval.
Source commit `b3a05446f9668341203e285a29f87dc58c485f2c` passed push CI
[40424017068](https://github.com/antonypaul98/cloudforge/actions/runs/40424017068)
and PR CI
[40424023059](https://github.com/antonypaul98/cloudforge/actions/runs/40424023059):
586 pytest passed and 19 infrastructure tests ran (1 inapplicable skip) on
Python 3.11.17. The final evidence-state commit requires separate CI.
This is not authenticated reviewer identity, deployment, observation or recovery.

## Runnable synthetic CLI entrypoint — source CI passed (2026-10-26)

The branch README documents a credential-free Python 3.11 quickstart for
`python -m cloudforge.synthetic_demo`. A subprocess regression executes
the exact CLI and compares canonical redacted JSON to the in-process
deterministic result. Source commit `df1cafd07d7a0d62eec5c1018b22bf1b105e8415` passed
[push CI](https://github.com/antonypaul98/cloudforge/actions/runs/40429988623)
and [PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40429994124):
**587 pytest passed**, 19 infrastructure tests (1 inapplicable skip), Python
3.11.17. Final evidence-head CI remains a separate gate. No authenticated
review, infrastructure deployment, external observation, recovery or physical
hardware acceptance is claimed. PR #6 remains unmerged due to the one-review
main ruleset.

## Synthetic forged mutation-evidence regression — source CI passed (2026-10-26)

The local-only synthetic demo now rejects a canonical-shaped audit event falsely
claiming `infrastructure_mutated: true`, with a dedicated regression and redacted
result flag. This is not deployment or recovery evidence. Exact source-head push
and PR CI, protected merge, and merged-main CI must be verified separately.

Source commit `531e5b6ba67bc66b34485cc809f61203fc24f47b` passed
[push CI](https://github.com/antonypaul98/cloudforge/actions/runs/40436195209)
and [PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40436198964):
**588 pytest passed**, 19 infrastructure tests (1 inapplicable skip), Python
3.11.17. Final evidence-head CI is separate; PR #6 remains unmerged due to
main's one-independent-review requirement. No real deployment, observation,
recovery, or physical hardware acceptance.


## Synthetic forged observation/recovery evidence — source CI passed (2026-10-26)

The local-only demo now independently rejects canonical-shaped audit events
with injected `deployment_observed: true` or `recovery_performed: true` claims.
One dedicated regression checks both rejection flags and ensures the redacted
original event contains neither field. This is synthetic schema integrity only,
not real observation or recovery. Source commit `0ad71e8aa5d56a81f1e079c816cad815f2fa5376` passed
[push CI](https://github.com/antonypaul98/cloudforge/actions/runs/40442346284)
and [PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40442352291):
**589 pytest passed**, 19 infrastructure tests (1 inapplicable skip), Python
3.11.17. Final evidence-head CI, protected merge and merged-main CI remain
separate gates; the main ruleset still requires independent approval.


## Synthetic demo local filesystem write guard — source CI passed (2026-10-26 ET)

One new regression blocks write-mode builtins/io/os file opens and common
os/pathlib mutation operations while the in-memory authorization demo runs.
This supplements existing network/shell guards; it is not a universal sandbox
or evidence of authenticated review, cloud deployment, observation or recovery.
Source commit `728c30831edaead22008fea2cd7435bcb1bea394` passed [push CI](https://github.com/antonypaul98/cloudforge/actions/runs/40447174646)
and [PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40447178174):
**590 pytest passed**, 19 infrastructure tests (1 inapplicable skip), Python
3.11.17. Final evidence-head CI, protected merge and merged-main CI remain
pending. Main ruleset 25825521 still requires one independent approval.

## Synthetic demo direct OS process-launch guard — source CI passed (2026-10-27 ET)

One regression forbids direct `os.popen`, `os.fork*`, `os.posix_spawn*`,
`os.spawn*` and `os.exec*` entry points during the credential-free in-memory
authorization demo. This supplements the existing subprocess and shell checks;
it is not a complete process sandbox or evidence of a real deployment.
Source commit `b4f790812b288bc0c703b181ba214a0af2866770` passed
[push CI](https://github.com/antonypaul98/cloudforge/actions/runs/40453387287)
and [PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40453392675):
**591 pytest passed**, 19 infrastructure tests (1 inapplicable skip), Python
3.11.17. Final evidence-head CI, protected merge and merged-main CI remain
separate gates. No authenticated reviewer, provider call, real infrastructure
mutation, observation, recovery or physical Mac acceptance is claimed.

## Synthetic CLI environment independence — source CI passed (2026-10-27 ET)

One regression invokes the documented credential-free CLI with **fake**
AWS, OpenAI and CloudForge environment values, then verifies that its canonical
redacted JSON is unchanged and contains none of those fake values. This is a
bounded synthetic privacy/determinism check, not proof of universal secret
isolation or of authenticated review, deployment, observation or recovery.
Source commit `ad8f17041ae6d68f10f14d9e18c93df5d75d2626` passed [push CI](https://github.com/antonypaul98/cloudforge/actions/runs/40458470056)
and [PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40458472949):
**592 pytest passed**, 19 infrastructure tests (1 inapplicable skip), Python
3.11.17. Final evidence-head CI, independent-review policy, guarded merge
and merged-main CI remain separate gates. No infrastructure mutation.

## Synthetic audit provenance-digest demonstration — 2026-10-27 ET

The credential-free local-only demo now independently rejects a forged
`request_digest` or `receipt_sha256` in a canonical-shaped redacted audit
event. A regression covers both outcomes. Source commit `42ae155b42fb79ccd2658e2909575b2abb670614` passed [push CI](https://github.com/antonypaul98/cloudforge/actions/runs/40470341201)
and [PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40470344578):
**594 pytest passed**, 19 infrastructure tests (1 skip), Python 3.11.17.
Final evidence-head CI remains separate; main's one-independent-review rule
rejected the guarded merge (HTTP 405), and PR #6 remains unmerged.
No provider execution, infrastructure mutation, authenticated reviewer,
external observation or recovery is claimed.

## Synthetic stale-approval replay check — 2026-10-27 ET (source CI passed)

The in-memory demo now exercises a changed artifact with a freshly prepared
execution request and requires the old approval to fail closed. One regression
checks the redacted outcome. Source-head CI, protected merge and merged-main
acceptance remain pending; no infrastructure or physical device was touched.

Source-head verification for the 2026-10-27 stale-approval replay slice:
commit `236d545d9607b010bb8894dc4ce0084bee077213` passed [push CI](https://github.com/antonypaul98/cloudforge/actions/runs/40477790248)
and [PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40477796079)
on Python 3.11.17: **595 pytest passed**, 19 infrastructure tests (1 skip).
Final evidence-head CI, protected merge and merged-main CI remain pending.

## Synthetic changed-plan approval replay — 2026-10-27 ET

The credential-free in-memory demonstration now changes a plan's port from
8080 to 8081 while keeping the same target and artifact bytes. It creates a
fresh synthetic handoff and local request, then requires the previous local
execution approval to fail with `ApprovalRequiredError`. One regression
checks the redacted outcome. This is caller-supplied synthetic identity,
not authenticated review, deployment, observation or recovery.

Source commit `e0d82d585fe0bdcf6d8f1ec60ea9a1007018eef9` passed [push CI](https://github.com/antonypaul98/cloudforge/actions/runs/40485782079)
and [PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40485790877):
**596 pytest passed**, 19 infrastructure tests (1 skipped), Python 3.11.17.
Final evidence-head CI, protected merge and merged-main CI are separate gates.
PR #6 remains unmerged due to the active independent-review rule.

## Synthetic changed-target approval replay — 2026-10-27 ET

A fresh synthetic handoff for a different target, with unchanged plan and
artifact bytes, now requires a fresh local execution approval. One regression
checks fail-closed replay behavior. Source commit `150bc7627228f42ec2a287aa4bee389e78c23eea` passed
[push CI](https://github.com/antonypaul98/cloudforge/actions/runs/40493027663)
and [PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40493033349):
**597 pytest passed**, 19 infrastructure tests (1 skipped), Python 3.11.17.
Final evidence-head CI and protected integration are separate gates. PR #6
remains blocked by one independent approving review. No real deployment,
observation, recovery or authenticated human approval is claimed.

## Synthetic changed-handoff-reviewer replay — 2026-10-27 ET

A changed caller-supplied handoff reviewer with unchanged reviewed request,
target, plan and artifact produces a different full handoff receipt binding.
The synthetic demo requires the old local execution approval to fail closed
against a freshly prepared request. One new integration regression checks
this redacted outcome and absence of the changed reviewer name.
Source commit `c68d6857146cee1d509b8e54e5933023df1b8e32` passed [push CI](https://github.com/antonypaul98/cloudforge/actions/runs/40500596530)
and [PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40500602003):
**598 pytest passed**, 19 infrastructure tests (1 skipped), Python 3.11.17.
Final evidence-head CI and protected integration are separate gates.
This is synthetic digest binding, not reviewer authentication, deployment,
observation or recovery.

## Synthetic forged authenticated-review audit claim — 2026-10-27 ET

The credential-free demo now rejects an added `authenticated_review: true` field
in otherwise canonical local audit JSON. One regression asserts the fail-closed
result and that the original redacted audit contains no authentication claim.
This is synthetic evidence-schema integrity, not identity authentication,
provider deployment, observation or recovery. Published source `489aa6935d63718ccfcd49beb24f60443855d94f`;
exact-head CI, protected merge and merged-main CI remain unverified.

## Synthetic local-file read privacy guard — 2026-10-27 ET

The in-memory authorization demo now has a regression that forbids standard
Python file-reading entry points during its execution. This narrows the chance
of accidentally reading local user files or credentials in the smoke path;
it is not a full OS sandbox or a runtime acceptance test. Source commit
`e16fa50c5eff1c7a77a21b67ca4387ab911d39c9` was published on PR #6. Push CI 40517979671 and PR CI
40517987403 were queued when recorded; success is not yet claimed. Final
state-head CI, protected merge and merged-main CI are separate gates. No real
infrastructure mutation, authenticated review, observation or recovery.

## Synthetic process-environment privacy regression — 2026-10-27

PR #6 now includes `tests/test_synthetic_environment_guard.py`, which blocks common Python environment reads and writes while the credential-free in-memory authorization demonstration executes. This is a bounded regression, not complete process isolation, reviewer authentication or deployment proof. Exact-head CI, protected merge, merged-main CI and checkpoint acceptance remain pending. No real infrastructure was modified.


## Synthetic clock/entropy independence guard — 2026-10-27 ET

One bounded regression asserts that the credential-free in-memory authorization
smoke demo produces identical redacted evidence while common Python clock,
random, secrets, UUID and os.urandom entry points are forbidden. This is a
synthetic determinism guard only, not universal sandboxing, authenticated
human review, deployment, observation or recovery. Exact final-head CI and
protected merge remain separate acceptance gates. PR #6 is still open because
main requires an independent approving review.

## Cross-artifact redacted audit replay regression — 2026-10-27 ET

A new credential-free test constructs two separately authorized synthetic local
artifacts under the same handoff, target and reviewer text. Each produces valid
redacted audit evidence, but replaying either valid event against the other
artifact's fresh authorization must fail. The test also checks that raw artifact
bytes, target and reviewer strings are absent from the redacted audit. This is
an in-process provenance regression, not authenticated human review or a real
provider execution. Source commit `d591a6ee9de37ad7afbfbda40bf61fdcf58a7e67`
passed [PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40546226344):
603 pytest passed and 19 infrastructure tests run (18 passed, 1 skipped),
Python 3.11.17. Push CI has not been independently verified. PR #6 is open;
GitHub rejected the SHA-guarded merge (HTTP 405) because one independent
approving review is still required. Merged-main CI and real deployment,
observation and recovery remain unaccepted.

## Bounded local adapter integration accepted — 2026-10-27 ET

PR [#6](https://github.com/antonypaul98/cloudforge/pull/6) integrated the
provider-neutral, deterministic in-memory authorization, receipt verification,
redacted audit and credential-free synthetic regression suite into `main`.
Exact final PR head `690ba1e052ef08d768f4cfb0e25e0877fa2ef994` passed
[PR CI 40546384064](https://github.com/antonypaul98/cloudforge/actions/runs/40546384064).
The SHA-guarded squash merge produced
[`4f93ab34963a7c038eec63c184dea80aaf073376`](https://github.com/antonypaul98/cloudforge/commit/4f93ab34963a7c038eec63c184dea80aaf073376),
and [merged-main push CI 40549975251](https://github.com/antonypaul98/cloudforge/actions/runs/40549975251)
succeeded. Both CI receipts report Python 3.11.17, **603 pytest passed**, and
19 infrastructure-guard tests run (18 passed, 1 skipped). The active `main`
ruleset retains PR and required `test` checks with zero mandatory reviews.

**Acceptance is strictly synthetic local-only software behavior.** Caller-supplied
reviewer strings are not authenticated approvals; no provider, cloud resource,
filesystem mutation, live deployment, external observation, recovery, or physical
Mac/device acceptance is claimed. Earlier in-progress and review-blocked notes
above are historical snapshots, superseded by this verified integration receipt.
Future real execution requires separately scoped design, exact artifacts,
authenticated authorization, safe rollback and independent acceptance evidence.

## Provider-neutral observation proposal accepted — 2026-10-27 ET

[PR #9](https://github.com/antonypaul98/cloudforge/pull/9) adds an immutable,
deterministic startup/readiness/liveness *proposal* bound to a previously
reverified exact-artifact local authorization receipt. The module reuses the
existing local receipt verifier and standard-library SHA-256 canonical JSON,
rejects malformed, duplicate, stale and forged claims, and performs no network
or subprocess calls. The bounded [design and reuse decision](docs/OBSERVATION_PLAN.md)
records the consulted Kubernetes probe-role concepts; no third-party code,
model, SDK or algorithm was imported.

Exact PR head `7023b0b3b5f20a0ac96c1d8fedacc35f2b693a22` passed
[PR CI 40564999962](https://github.com/antonypaul98/cloudforge/actions/runs/40564999962).
Guarded squash merge `b443133831a4a7111c92535cf93d804527296381`
passed [merged-main push CI 40565157396](https://github.com/antonypaul98/cloudforge/actions/runs/40565157396).
Both runs: Python 3.11.17, **632 pytest passed** (29 new), 19
infrastructure-guard tests run (18 passed, 1 skipped). The source branch is
preserved. No physical Mac test or shell GitHub push was performed.

**Acceptance is planning-only.** Probe execution, trusted external observation,
authenticated reviewer identity, real deployment, recovery, rollback and
hardware acceptance remain unimplemented/unverified. Earlier checkpoint
receipts above remain historical, not proof of these future capabilities.

## Bounded observation evidence intake accepted — 2026-10-27 ET

[PR #11](https://github.com/antonypaul98/cloudforge/pull/11) added a
provider-neutral, in-memory HMAC-SHA256 sample envelope bound to the exact
reverified observation proposal and local authorization inputs. It checks a
configured opaque source alias, ordered probe kinds, bounded timestamps,
caller-maintained monotonic sequence and constant-time MAC comparison.
The [trust contract](docs/OBSERVATION_EVIDENCE.md) records standard-library
reuse, source-key provisioning and replay-state limitations. No third-party
source code, dependency, cloud SDK, live probe or infrastructure action was added.

Exact source head `e44ef4129bab806c1e0e3a38e9159e693b97e580` passed
[PR CI 40575145608](https://github.com/antonypaul98/cloudforge/actions/runs/40575145608).
The guarded squash merge `0fb1f07b3096f5f3b95d61b6a5a48b52fb2989a7`
passed [merged-main push CI 40575241241](https://github.com/antonypaul98/cloudforge/actions/runs/40575241241).
Both runs used Python 3.11.17 and reported **669 pytest passed** (37 new
synthetic tests), with 19 infrastructure-guard tests run (18 passed, 1 skipped).

**Acceptance is synthetic envelope verification only.** MAC possession does not
prove a trusted collector ran a probe, or that a service is healthy. Actual
collector identity/key management, durable atomic replay counters, trusted
clocks, live read-only observation, real deployment, alerting, recovery,
rollback and physical Mac acceptance remain separate unverified checkpoints.
Earlier historical entries above are not evidence of those capabilities.

## Durable observation replay ledger accepted — 2026-10-27 ET

[PR #13](https://github.com/antonypaul98/cloudforge/pull/13) adds an opt-in,
local SQLite replay counter for the existing exact-verified HMAC observation
envelopes. It validates the MAC, source, plan and caller-supplied freshness
before opening the database, then atomically advances the accepted sequence
per (plan SHA-256, source alias) with a transactional conditional UPSERT.
Duplicate, older, corrupt-database and concurrent duplicate attempts fail
closed. The [design and operating contract](docs/OBSERVATION_REPLAY.md) records
local file permissions, trusted-clock assumptions, rollback hazards and
standard-library reuse; no third-party code or dependency was added.

Exact feature head `5d15ec34fcade162d5efa6c00c650f51bf9879cb` passed
[PR CI 40582748697](https://github.com/antonypaul98/cloudforge/actions/runs/40582748697).
Guarded squash merge `e5fbbcc16590248f60ba9240d8a3fc1970afb99d` passed
[merged-main push CI 40582825623](https://github.com/antonypaul98/cloudforge/actions/runs/40582825623).
Both used Python 3.11.17, **681 pytest passed** (12 new cases) and 19
infrastructure-guard tests run (18 passed, 1 skipped). The feature branch is
preserved; external worktree ownership remains unverified.

**Acceptance is local durable replay-state behavior only.** Tests used local
SQLite files and synthetic sample envelopes. No live probe, authenticated
collector, trusted external clock, provider execution, infrastructure
deployment, health claim, distributed ledger, recovery or physical Mac
acceptance is established. Earlier in-memory evidence acceptance remains
valid but does not imply a live monitoring service.

## Bounded loopback HEAD observation fixture accepted — 2026-10-27 ET

[PR #15](https://github.com/antonypaul98/cloudforge/pull/15) adds an opt-in
numeric IPv4 `127.0.0.1` HTTP `HEAD` probe fixture that revalidates the
exact existing handoff/artifact/local approval/receipt and observation plan
before any network call. An explicit operator-supplied `(kind, host, port, path)`
allowlist must match the request exactly; only safe ASCII origin paths,
bounded 1–10s per-probe timeouts and the planned probe order are accepted.
No redirects, proxy discovery, response-body reads, cloud endpoints or
credential use are included. The [scope and reuse contract](docs/OBSERVATION_HTTP.md)
records Python standard-library reuse and OWASP SSRF guidance; no third-party
code, dependency or algorithm was imported.

Exact source head `046c11d8d63ec0ac904dce8101ac7220528f66fe` passed
[PR CI 40592445791](https://github.com/antonypaul98/cloudforge/actions/runs/40592445791).
Guarded squash merge `a4339ba0c1161388df6b92262acfd5a644dd87db` passed
[merged-main push CI 40592539823](https://github.com/antonypaul98/cloudforge/actions/runs/40592539823).
Both used Python 3.11.17 and reported **718 pytest passed** (37 new tests)
and 19 infrastructure tests run (18 passed, 1 skipped). CI tests exercised
only ephemeral loopback fixture servers. The source branch is preserved;
external worktree ownership remains unverified.

**Acceptance is fixture-only unsigned HTTP-status collection.** An explicit
allowlist parameter is not authenticated operator authorization; HTTP 2xx
does not establish trusted service health. No real service, authenticated
collector identity, source key, signed evidence, replay-ledger integration,
deployment, recovery, rollback or physical Mac/device acceptance is claimed.
Earlier observation-plan/evidence/replay acceptance does not imply those
capabilities are connected to this fixture collector.


## Bounded signed fixture intake accepted — 2026-10-27 ET

[PR #17](https://github.com/antonypaul98/cloudforge/pull/17) composes
the existing numeric-loopback HEAD fixture collector, exact-plan HMAC-SHA256
sample envelope and SQLite durable replay guard into one opt-in synchronous
fixture-only path. It validates the allowlist, exact authorization, source/key,
caller-supplied freshness and ledger-path shape before any network call, then
signs the actual HEAD results and returns the envelope only after transactional
replay acceptance. A duplicate sequence may still issue HEAD before the
database rejects it; this is not exactly-once probing.

The [reuse and threat contract](docs/OBSERVATION_FIXTURE_INTAKE.md) documents
the Python 3.11 standard-library and existing-module reuse, unchanged
schemas, no imported third-party code or dependency, and the caller's
responsibility for identity, source key, trusted clock, sequence and ledger.
Tests cover 204/503/302 fixture outcomes, source/clock/target/artifact
fail-closed validation before network, signed samples, durable acceptance,
replay and redacted output.

Exact PR head
`abb58dbb8d48a6427e31505a32bce976b64849b1` passed
[PR CI 40599062565](https://github.com/antonypaul98/cloudforge/actions/runs/40599062565)
and [source push CI 40599034734](https://github.com/antonypaul98/cloudforge/actions/runs/40599034734).
Guarded squash merge
`574cf86ed199e2c50e16777dc977c9fe0d3df630` passed
[merged-main CI 40599169006](https://github.com/antonypaul98/cloudforge/actions/runs/40599169006).
All three used Python 3.11.17, **737 pytest passed** (19 new test cases),
19 infrastructure guards run (18 passed, 1 skipped). The source branch is
preserved; exclusive external worktree ownership remains unverified.

**Acceptance is fixture-only composition.** Signing in a caller-controlled
process is not authenticated collector identity or trustworthy service health.
No production service, independent key/clock provisioning, cloud provider,
real deployment, monitoring scheduler, alerting, recovery, rollback or physical
Mac/device acceptance is established. No real infrastructure was modified.

## Bounded loopback HEAD cleanup safeguard accepted — 2026-10-27 ET

[PR #19](https://github.com/antonypaul98/cloudforge/pull/19)
preserves fail-closed raw observation semantics if Python's
`HTTPConnection.close()` raises an OSError or HTTPException. Even if the
earlier HEAD status was 2xx, the sample becomes `unknown`, not `pass`.
Unexpected cleanup exceptions abort collection before HMAC signing and SQLite
replay acceptance. The [existing transport contract](docs/OBSERVATION_HTTP.md)
now records this behavior. No new external dependencies, model, API, schema,
permissions, network targets or third-party source code were added.

Exact feature head `799931178dda487f2e44486aab14bf4d618fa3b3` passed
[source push CI 40605637354](https://github.com/antonypaul98/cloudforge/actions/runs/40605637354)
and [PR CI 40605683663](https://github.com/antonypaul98/cloudforge/actions/runs/40605683663).
Guarded squash merge `d79d7c13860ad5b3d5e903f0b860a1af25a671a4` passed
[merged-main CI 40605764040](https://github.com/antonypaul98/cloudforge/actions/runs/40605764040).
Python 3.11.17 reported **742 pytest passed** (5 new test cases)
and 19 infrastructure guards run (18 passed, 1 skipped).
The source branch remains preserved; external worktree ownership is unverified.

**Acceptance is a fixture-only transport failure safeguard.** It does not
authenticate collector identity, provision source keys, trust caller clocks,
prove service health, deploy infrastructure, schedule production monitoring,
recover or roll back resources, or validate physical hardware.
No real infrastructure was modified.

## Observation source-key and clock lifecycle regression accepted — 2026-10-27 ET

[PR #21](https://github.com/antonypaul98/cloudforge/pull/21)
adds three fixture-only tests: rotating the configured HMAC key under the same
source alias does not reset the durable SQLite sequence, stale/future or
backwards-clock evidence cannot advance that ledger, and a maximum 63-bit
sequence cannot overflow or restart. The
[reuse and limitations record](docs/OBSERVATION_KEY_CLOCK_LIFECYCLE.md)
documents existing CloudForge/Python/SQLite reuse and the absent trusted
collector, key manager, clock and backup-rollback guarantees.

Exact feature head `17fd69c733cfac9672e570d82a894ecc5bf28898` passed
[source push CI 40612629011](https://github.com/antonypaul98/cloudforge/actions/runs/40612629011)
and [PR CI 40612645312](https://github.com/antonypaul98/cloudforge/actions/runs/40612645312).
Guarded squash merge `2050a1a515e30b1ed62ddb8a56f46a7315cf839a` passed
[merged-main CI 40612705992](https://github.com/antonypaul98/cloudforge/actions/runs/40612705992).
All reported Python 3.11.17, **745 pytest passed** (3 new cases), and
19 infrastructure tests run (18 passed, 1 skipped). The source branch
is preserved; external worktree ownership is unverified.

**Acceptance is regression-only and fixture-only.** The tests do not rotate
or revoke real keys, authenticate collectors, establish trusted time, prevent
ledger-backup rollback, monitor services, deploy infrastructure, recover or
roll back resources, or validate physical Mac/device behavior.
No real infrastructure was modified.


## Canonical observation replay ledger schema guard accepted — 2026-10-27 ET

[PR #23](https://github.com/antonypaul98/cloudforge/pull/23)
rejects lookalike SQLite replay tables with TEXT sequence affinity or missing
constraints, unexpected triggers on the replay table, and noninteger or
out-of-range persisted counters. The canonical schema is checked within the
same BEGIN IMMEDIATE transaction before a conditional sequence UPSERT.
This prevents an altered TEXT counter from accepting sequence 9 after 10
through lexicographic comparison. No new external code or dependencies were
added; Python 3.11 sqlite3 and SQLite's schema catalog are reused.

Exact feature head `93234a57577ff0d474bc7cf0e22f0f2dc01ab3e3`
passed [push CI 40618298894](https://github.com/antonypaul98/cloudforge/actions/runs/40618298894)
and [PR CI 40618312748](https://github.com/antonypaul98/cloudforge/actions/runs/40618312748).
SHA-guarded squash merge `bbd66024e9b2a126655bbb24202f04c51245b086` passed
[merged-main CI 40618385665](https://github.com/antonypaul98/cloudforge/actions/runs/40618385665).
All ran Python 3.11.17 and reported **749 pytest passed** (four new
parametrized cases) and 19 infrastructure guards (18 passed, 1 skipped).
The feature branch is preserved; exclusive external worktree ownership
remains unverified.

**Acceptance is fixture-only local SQLite integrity checking.** A privileged
attacker can replace or roll back the database. Authenticated collector identity,
trusted keys/clocks, real monitoring, deployment, recovery, rollback and physical
Mac/device acceptance are not established. No real infrastructure was modified.

## Observation replay ledger file-type safeguard — 2026-10-27 ET

Fixture-only source change accepted through PR #25. Exact feature head
`29867b4099eb0c759334212242edaa96b8ff8a5e` passed push CI
`40624569759` and PR CI `40624587668`; SHA-guarded squash merge
`7b203daa27d2df559ad1f80c1e68751a07e2201e` passed merged-main CI `40624657198`.
Python 3.11.17 CI: **753 pytest passed**; 19 infrastructure guards run
(18 passed, 1 skipped). Four new regressions verify symlink/special-file
rejection and MAC verification before filesystem metadata access.

Existing CloudForge HMAC and SQLite logic is reused; Python standard-library
`os.lstat`/`stat.S_ISREG` adds best-effort path hygiene, not race-free
file opening. Parent-directory symlinks, untrusted directory writers,
rollback-resistant storage, authenticated collectors, trusted key/clock
provisioning, production monitoring, deployment and recovery remain outside
this acceptance. No physical Mac tests or real infrastructure mutation.
See `docs/OBSERVATION_REPLAY.md` for threat model and limitations.


## Observation replay ledger hard-link safeguard — accepted fixture-only (2026-10-28)

PR [#27](https://github.com/antonypaul98/cloudforge/pull/27) extends the
existing `os.lstat` final-component check to reject existing SQLite replay
ledger files with a hard-link count other than one. Both original and alias
paths are rejected when the inode has multiple names; two new parametrized
tests confirm no replay counter advancement. Reused Python 3.11 standard
library; no third-party dependencies or provider calls.

Source head `275d1693730ec6117e284204adc15036d5075753` passed
[push CI](https://github.com/antonypaul98/cloudforge/actions/runs/40630392569)
and [exact-head PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40630422561).
Guarded squash merge `15ff562ad9b52ac6876228aa7a497df2e8e0c03f`
passed [merged-main CI](https://github.com/antonypaul98/cloudforge/actions/runs/40630475417):
**755 pytest passed**, infrastructure 18 passed and 1 skipped on Python
3.11.17. Local POSIX hard-link smoke check passed separately; no full local
product suite or physical Mac testing was performed.

This remains best-effort pre-open file hygiene, not atomic race prevention,
authenticated collector identity, trusted keys or clocks, production
monitoring, deployment or recovery. No real infrastructure was modified.
External worktree ownership is unverified. Next: bounded collector/source-key
provenance safeguard with independent verification.

## Observation replay parent-path hygiene — accepted fixture-only (2026-10-28)

[PR #29](https://github.com/antonypaul98/cloudforge/pull/29) rejects
noncanonical absolute SQLite replay ledger paths and parent-directory
symlinks (including dangling aliases) before opening the database. All
parent components must already be real directories. Five new fixture
regressions cover existing/dangling parent symlinks, dot traversal,
missing parents and nested real directories. Existing exact-authorization,
HMAC and SQLite sequence semantics are unchanged. Python 3.11 standard
library reused; no external code, dependencies, credentials or provider calls.

Exact feature head `dd59607f93346310b9f12503119116753b293f09` passed
[source push CI 40635120990](https://github.com/antonypaul98/cloudforge/actions/runs/40635120990)
and [PR CI 40635136624](https://github.com/antonypaul98/cloudforge/actions/runs/40635136624).
SHA-guarded squash merge `b4c5666c919dc07b534845c29cc034bb2dfbbecd`
passed [merged-main CI 40635206290](https://github.com/antonypaul98/cloudforge/actions/runs/40635206290).
All three ran Python 3.11.17: **760 pytest passed**, 19 infrastructure
regressions run (18 passed, 1 skipped). Isolated Python 3.13 helper smoke
passed five cases separately; this was not a full local repository suite.

**Acceptance is fixture-only best-effort path hygiene.** A concurrent
attacker may still replace paths after inspection. Ledger rollback, trusted
source identity, key provisioning, clocks, real service monitoring,
deployment, recovery and physical Mac/device acceptance remain unproven.
No real infrastructure was modified; external worktree ownership unverified.
Next: bounded collector/source-key provenance with independent verification.

## Optional observation source/key pin accepted (fixture-only) — 2026-10-28

PR [#31](https://github.com/antonypaul98/cloudforge/pull/31) integrated an
opt-in, independently caller-provisioned source/key/plan/time pin before
local fixture HEAD network I/O and SQLite replay-ledger I/O. It rejects
changed source aliases, key fingerprints, plan digests, invalid validity
windows and key substitution. A rotated key requires a new trusted pin while
the existing per-plan/source replay counter remains monotonic. The original
unpinned fixture interface remains compatible. No external code, dependency,
provider or infrastructure change was introduced. See
[OBSERVATION_SOURCE_PIN.md](docs/OBSERVATION_SOURCE_PIN.md).

Exact source head `5545e393538eb0dbfc5ae6ade98c4b7da54bd1be` passed
[push CI 40641365009](https://github.com/antonypaul98/cloudforge/actions/runs/40641365009)
and [PR CI 40641391039](https://github.com/antonypaul98/cloudforge/actions/runs/40641391039).
The SHA-guarded squash merge produced
`6f15c2d7b9b2064d6695ed14b55c13f8dc937a12`, and
[merged-main CI 40641476831](https://github.com/antonypaul98/cloudforge/actions/runs/40641476831)
passed. Python 3.11.17: **774 pytest passed**, 19 infrastructure tests
(18 passed, 1 skipped). Isolated Python 3.13 compile and 6 smoke checks
are separate, not the pinned suite. The canonical acceptance record is in
CHECKPOINT_STATE.json.

**Not accepted:** authenticated collector identity, trusted configuration
provisioning, key revocation, trusted clock, live service monitoring,
production deployment, recovery, ledger rollback defense, or physical Mac
validation. The pin is optional and cannot attest a caller-controlled key
or clock. External worktree exclusivity remains unverified. Work/Astra was
not invoked; no real infrastructure was modified.


## Fixture source trust policy accepted — 2026-10-28 ET

[PR #33](https://github.com/antonypaul98/cloudforge/pull/33) added an opt-in
strict source-pin requirement and bounded caller-provided revoked-key fingerprint
preflight to the local HEAD → HMAC → SQLite fixture intake. A revoked key or
missing required pin fails before HTTP/ledger I/O; rotation retains the
existing durable sequence. No new dependencies or external source code were
used; see [reuse and trust limitations](docs/OBSERVATION_SOURCE_PIN.md).

Exact feature head 7c28694ea44ec6ead2ae4a1f953317a07c2abb63 passed
[push CI 40647718177](https://github.com/antonypaul98/cloudforge/actions/runs/40647718177)
and [PR CI 40647741775](https://github.com/antonypaul98/cloudforge/actions/runs/40647741775).
The SHA-guarded squash merge a16bfe9c894324a294cc61622fa9f242918ae0d0
passed [merged-main CI 40647818226](https://github.com/antonypaul98/cloudforge/actions/runs/40647818226).
All three runs used Python 3.11.17: **787 pytest passed** (13 new),
19 infrastructure tests (18 passed, 1 skipped). Isolated helper-only Python
3.13 smoke passed 21 tests, but is not full-repository evidence.

**Acceptance is fixture-only.** The policy is optional and caller-provisioned:
no independently authenticated collector, trusted key distribution/revocation,
trusted clocks, rollback-resistant storage, production monitoring, deployment,
recovery or physical Mac/device validation is claimed. No real infrastructure
was modified. External worktree ownership remains unverified.

## Unsafe ledger path preflight before HEAD — accepted fixture-only (2026-10-28)

[PR #35](https://github.com/antonypaul98/cloudforge/pull/35) reuses the
existing SQLite replay ledger path guard in the composed local observation
fixture, after authorization and MAC/freshness verification but before any
HTTP HEAD probe. It rejects known symlinked files and parent directories,
hard-link aliases, noncanonical paths and missing parents without network
traffic. The durable writer repeats the path check before opening SQLite.
Five new synthetic regressions verify rejection before HEAD and sentinel
file preservation. Existing Python 3.11 os/stat logic reused; no third-party
source, dependency, provider permission or infrastructure mutation.

Exact feature head `0333edb9bcb31e7837cb5939c6b3849f10f7afb2` passed
[push CI 40654232366](https://github.com/antonypaul98/cloudforge/actions/runs/40654232366)
and [PR CI 40654276119](https://github.com/antonypaul98/cloudforge/actions/runs/40654276119).
SHA-guarded squash merge `7fb2080e8310bec1f43168eb716300e4de220abb` passed
[merged-main CI 40654407144](https://github.com/antonypaul98/cloudforge/actions/runs/40654407144).
All ran Python 3.11.17: **792 pytest passed** (5 new), 19 infrastructure
tests (18 passed, 1 skipped). No local full-suite or physical Mac tests
were run; GitHub CI supplies the exact-head validation.

**Acceptance is fixture-only.** The checks are not atomic and do not
prevent concurrent path replacement, backup rollback or duplicate-sequence
HEAD requests. Authenticated collector provenance, secure key distribution,
trusted clocks, real runtime monitoring, deployment and recovery remain
unaccepted. External worktree ownership is unverified. Work/Astra was not
invoked and no real infrastructure was modified.


## Verified observation sample rollup — accepted fixture-only (2026-10-28 ET)

[PR #37](https://github.com/antonypaul98/cloudforge/pull/37) adds a pure
read-only decision over already verified observation samples. It reuses the
existing exact-plan/source/HMAC/freshness/replay verifier, then returns
`fail` when any sample failed, `unknown` when none failed but at least one
is unknown, and `pass` only when all verified samples passed. The outcome
is a **raw sample rollup**, not independently authenticated service health.
No third-party source, algorithm, SDK, dependency or provider permission was
introduced; see [reuse and limits](docs/OBSERVATION_ROLLUP.md).

Exact feature head `30d9446edbe2f57213cd778698b40b81a49a1d30` passed
[push CI 40661067939](https://github.com/antonypaul98/cloudforge/actions/runs/40661067939)
and [PR CI 40661089542](https://github.com/antonypaul98/cloudforge/actions/runs/40661089542).
The guarded squash merge `14d127004d26c8d0f156f0018b8f3ca91836ea43`
passed [merged-main CI 40661187846](https://github.com/antonypaul98/cloudforge/actions/runs/40661187846).
All three ran on Python 3.11.17: **803 pytest passed** (11 new
parameterized cases) and 19 infrastructure tests (18 passed, 1 skipped).
The shell container could not resolve github.com, so no separate local full
suite was run. GitHub exact-head CI is the full-suite evidence.

**Not accepted:** authenticated collector identity, trusted key/clock
provisioning, durable sequence acceptance within this pure rollup, actual
service monitoring, deployment, recovery or physical Mac validation. No
real infrastructure was modified; external worktree exclusivity unverified.
No Work/Astra invocation.

## Verified sample rollup source-key trust enforcement — accepted fixture-only (2026-10-28 ET)

[PR #39](https://github.com/antonypaul98/cloudforge/pull/39) composes the
existing opt-in caller-provided source pin and revoked-key policy with the
pure verified sample rollup. A valid MAC under a caller-revoked key cannot
produce a classification; strict mode rejects missing pins. The original
unpinned synthetic API remains compatible. This is read-only policy
enforcement, not a new key registry or authenticated collector.

Feature head `13fb3d3a50c3d326f3671a51250560fe27d1ece9` passed
[push CI 40668633675](https://github.com/antonypaul98/cloudforge/actions/runs/40668633675)
and [exact-head PR CI 40668659085](https://github.com/antonypaul98/cloudforge/actions/runs/40668659085).
Expected-head SHA-guarded squash merge `e92ae9134af35b12440f43808a0e30bb53588d61` passed
[merged-main CI 40668776480](https://github.com/antonypaul98/cloudforge/actions/runs/40668776480).
All three ran Python 3.11.17: **820 pytest passed** (17 new parameterized
cases) and 19 infrastructure tests (18 passed, 1 skipped). No separate local
full suite was run because the shell environment cannot resolve github.com.
No new dependency, third-party code, provider permission or service cost.
Reuse review and trust limitations are in
[docs/OBSERVATION_ROLLUP.md](OBSERVATION_ROLLUP.md).

**Not accepted:** authenticated collector, independently trusted pin/revocation
distribution, secure key lifecycle, trusted clock, atomic replay within pure
rollup, actual service monitoring, deployment, recovery or physical Mac
validation. No real infrastructure was modified. External worktree ownership
remains unverified. Work/Astra was not invoked.

## Read-only SQLite replay preflight before local HEAD — accepted fixture-only (2026-10-28 ET)

[PR #41](https://github.com/antonypaul98/cloudforge/pull/41) adds a best-effort
read-only check of the existing SQLite replay ledger **before** any local
fixture HTTP HEAD probe. A known duplicate sequence, corrupt counter, altered
schema or unreadable database fails before network I/O. The original durable
`BEGIN IMMEDIATE` transaction remains authoritative for concurrent acceptance.
Missing ledgers and valid empty SQLite databases still initialize normally.
Five new synthetic tests cover these cases and reserved URI filename characters.

Feature head `b51298e2aeb9586fb9886cffa52c3d7251eec278` passed
[push CI 40677140018](https://github.com/antonypaul98/cloudforge/actions/runs/40677140018)
and [exact-head PR CI 40677180391](https://github.com/antonypaul98/cloudforge/actions/runs/40677180391).
Expected-head guarded squash merge `d4f83056dfc176f749042df68749da2b869bded0` passed
[merged-main CI 40677299069](https://github.com/antonypaul98/cloudforge/actions/runs/40677299069).
All three ran on Python 3.11.17: **825 pytest passed** (5 new cases) and
19 infrastructure tests (18 passed, 1 skipped). A separate isolated Python
3.13 SQLite URI prototype passed 7 checks, not the repository suite.
No new dependency, third-party code, provider permission or service cost.
See [reuse and limitations](docs/OBSERVATION_FIXTURE_INTAKE.md).

**Not accepted:** race-free replay reservation or filesystem access, authenticated
collector identity, trusted key/clock provisioning, real service monitoring,
deployment, recovery or physical Mac/device validation. No real infrastructure
was modified. External worktree exclusivity remains unverified. Work/Astra
was not invoked.


## Verified observation failure thresholds — accepted fixture-only (2026-10-28 ET)

[Feature PR #43](https://github.com/antonypaul98/cloudforge/pull/43)
adds a bounded, pure read-only evaluator of 1–10 already signed observation
envelopes. Every envelope is reverified against the exact artifact, plan,
source, HMAC, freshness, replay context and optional source pin/revocation
policy. Per-probe consecutive explicit `fail` outcomes are compared with
the plan's existing `failure_threshold`; `pass` or `unknown` breaks the
proven failure streak. Subsequent sequences must be contiguous and
caller-supplied timestamps cannot go backward. A false threshold flag is
**not** evidence of service health, and no polling, alerting or recovery occurs.
See [threshold semantics and reuse review](docs/OBSERVATION_THRESHOLDS.md).

Exact source head `9b35c06b03e631dc450c6fd8bf9a8fc783973958` passed
[push CI 40685231584](https://github.com/antonypaul98/cloudforge/actions/runs/40685231584)
and [exact-head PR CI 40685256016](https://github.com/antonypaul98/cloudforge/actions/runs/40685256016).
Expected-head SHA-guarded squash merge
`55ef3a327f18fe725916a6db758e5a378c1808e1` passed
[merged-main CI 40685395798](https://github.com/antonypaul98/cloudforge/actions/runs/40685395798).
Python 3.11.17: **839 pytest passed** (14 new parameterized cases);
19 infrastructure guards ran (18 passed, 1 skipped). No separate local
full-suite or physical Mac validation. Existing CloudForge verification
and Python standard library reused; no external code, new dependencies,
permissions, credentials or provider costs. No real infrastructure changed.

**Still unaccepted:** independently authenticated collectors, trusted
clock/key provisioning, durable monitoring cadence, live service-health
observation, deployment, rollback and recovery. External worktree
exclusivity remains unverified. Next: design a small independently
verifiable, explicitly authorized read-only runtime observation boundary,
without accessing real services before approval. No Work/Astra invocation.

## Signed observation window cadence safeguard — 2026-10-28

Feature [PR #45](https://github.com/antonypaul98/cloudforge/pull/45) is merged
at `05931222a1df886d43befca43821eee160b2464f`. Exact feature PR head
`044e3d2adb77128963ccd75a777575a5e9eb327e` passed
[PR CI #40693213476](https://github.com/antonypaul98/cloudforge/actions/runs/40693213476),
and [merged-main CI #40693332293](https://github.com/antonypaul98/cloudforge/actions/runs/40693332293)
passed on Python 3.11.17: **842 pytest passed**, 19 infrastructure checks
(18 passed, 1 skipped). Three new regression tests cover equal/too-short
claimed timestamp gaps, exact-interval acceptance and mixed intervals.

The pure failure-streak evaluator now rejects consecutive signed envelopes
whose caller-provided timestamps are closer than the **longest** interval
in the exact observation proposal. Existing plan, MAC, source-key policy,
freshness and replay checks remain in force. This is fixture-only software
acceptance, not verified real scheduling, trusted clocks, authenticated
collectors, production monitoring, alerting, deployment or recovery. No
external source code, new dependencies, real infrastructure actions or
physical Mac validation. External worktree writer exclusivity is unverified.

Next: an independently authenticated, explicitly operator-authorized read-only
collector boundary with trustworthy key/clock provisioning. No live endpoint
access or infrastructure mutation is authorized by this checkpoint.

## Post-hoc loopback HEAD elapsed-budget safeguard — 2026-10-28

Feature [PR #47](https://github.com/antonypaul98/cloudforge/pull/47)
merged as `559b67c7b6f60c4f416c3788abd39857246544f8`. Its exact head
`c5e3da62c71b35e90dc201a5e1f56157ab0abc93` passed
[push CI #40701886612](https://github.com/antonypaul98/cloudforge/actions/runs/40701886612)
and [PR CI #40701927545](https://github.com/antonypaul98/cloudforge/actions/runs/40701927545).
[Feature merged-main CI #40702109730](https://github.com/antonypaul98/cloudforge/actions/runs/40702109730)
passed on Python 3.11.17: **847 pytest passed** (five additional
regressions), 19 infrastructure checks (18 passed, 1 skipped).
An isolated five-case boundary smoke also passed, but no separate local
full-repository suite or physical Mac validation was performed.

The existing numeric-loopback HEAD collector now treats an otherwise
passing/failing response as `unknown` if total monotonic duration including
cleanup exceeds the configured probe timeout. A negative duration fails
closed; an exact-boundary duration remains accepted. The signed and durable
fixture intake also preserves the `unknown` result. Existing standard-library
`http.client` and `time.monotonic` plus CloudForge's sample/HMAC/SQLite
contracts were reused. No third-party code, new dependencies, cloud
credentials, provider access, infrastructure mutation or additional costs.

**Scope limit:** This is post-hoc classification, not an enforced wall-clock
deadline, authenticated collector, trusted timestamp, live service monitoring,
deployment or recovery. A slow socket operation may still block beyond its
timeout budget. The operator-approved, independently authenticated runtime
collector and key/clock lifecycle are still missing. External worktree
exclusivity remains unverified. No Work/Astra invocation.

**Next acceptance boundary:** Define independently trusted collector identity,
key provisioning, exact approved read-only targets and measured runtime
clock/sequence evidence before contacting a real service. Do not interpret
fixture success as service health or authorize infrastructure mutation.

## Separately keyed operator permit for loopback HEAD fixture — 2026-10-28

A new **opt-in**, short-lived (at most 300 seconds) HMAC permit binds the
exact observation plan, ordered numeric-loopback HEAD targets, collector alias,
source-key fingerprint, and an explicit HEAD-only operation domain. A distinct
operator key verifies the permit before the existing fixture HTTP and SQLite
path. Existing callers remain compatible; this is not a universal mandatory
authorization mechanism. The operator and collector keys must be provisioned
independently, and caller-supplied time is not a trusted clock.

Feature [PR #49](https://github.com/antonypaul98/cloudforge/pull/49)
source head `ed358f42e19a7cfe956b5021c9437d4f0821149f` passed
[push CI](https://github.com/antonypaul98/cloudforge/actions/runs/40712699027)
and [exact-head PR CI](https://github.com/antonypaul98/cloudforge/actions/runs/40712762871).
Guarded merge `ec3b6ab1bef914ee78d31d301fb1433ca4a9c832` passed
[merged-main CI](https://github.com/antonypaul98/cloudforge/actions/runs/40712944688):
**869 pytest passed** (22 new synthetic regressions), infrastructure guards
19 run (18 passed, 1 skipped), Python 3.11.17. See
`docs/OBSERVATION_OPERATOR_PERMIT.md` for reuse-first provenance, scope and
limitations. No new dependency or third-party code was added.

This is **fixture-only software acceptance**. A valid MAC proves possession
of a configured operator key, not a human decision or authenticated collector.
No live service, real infrastructure, production deployment, recovery, trusted
clock/key distribution, or physical Mac was tested or accepted. External
worktree exclusivity remains unverified. No Work/Astra invoked.

## Scoped one-ledger/sequence operator permit (v2) — 2026-10-28

Opt-in v2 extends the separately keyed loopback HEAD fixture permit with an
HMAC-bound digest of the exact normalized absolute SQLite replay-ledger path
and one positive 63-bit sequence. Strict mode rejects legacy v1; existing
non-strict v1 callers remain compatible. The scoped permit is verified before
HEAD requests or SQLite access. The ledger path itself is not exported in the
permit. See `docs/OBSERVATION_OPERATOR_PERMIT.md` for the precise contract,
reuse-first provenance and rollback limitations.

Feature [PR #51](https://github.com/antonypaul98/cloudforge/pull/51)
exact head `11792a88859d91d25064818be036af0a74f9a3a1` passed
[push CI #40722564237](https://github.com/antonypaul98/cloudforge/actions/runs/40722564237)
and [PR CI #40722607886](https://github.com/antonypaul98/cloudforge/actions/runs/40722607886).
Guarded merge `0632ce7726f024d911dcfd28ac0caf605729bc6d` passed
[merged-main CI #40722806845](https://github.com/antonypaul98/cloudforge/actions/runs/40722806845):
**888 pytest passed** (19 additional regression cases), 19 infrastructure
checks (18 passed, 1 skipped), Python 3.11.17. No separate local full
repository suite or physical Mac acceptance was performed.

**Boundary:** This is fixture-only software acceptance, not globally
single-use authorization. A copied/rolled-back SQLite ledger is not protected.
A MAC does not authenticate a human operator or collector, and timestamps
remain caller-supplied. No real service was contacted, infrastructure modified,
cloud provider used, deployment performed, or recovery tested. No new
third-party code or dependencies. External worktree exclusivity remains
unverified; Work/Astra were not invoked.

**Next:** Independently authenticated operator/collector provenance and trusted
key/clock provisioning before any separately approved read-only runtime
observation. Do not extend fixture acceptance into production claims.

## Redacted HTTPS runtime observation target proposal — 2026-10-28

A new planning-only API binds ordered, syntactically validated HTTPS HEAD
runtime targets to the exact existing observation plan, handoff, artifact,
approval and local receipt. The exported immutable proposal contains only
plan/target digests and `pending-independent-approval`; no hostnames, paths,
reviewers, artifacts, credentials, deployment or health claims. No DNS, network,
provider call, subprocess, deployment or recovery is performed. This is a
meaningful **runtime-target handoff prerequisite**, not a live collector or
authorization to probe a service.

Feature [PR #53](https://github.com/antonypaul98/cloudforge/pull/53)
exact head `d674d1d56a97e332b3a446d4ee02026dff7257a0` passed
[push CI #40732181839](https://github.com/antonypaul98/cloudforge/actions/runs/40732181839)
and [PR CI #40732231789](https://github.com/antonypaul98/cloudforge/actions/runs/40732231789).
Guarded merge `44e6dd78d5b29145f82bdc2f66c12210d5730e27` passed
[merged-main CI #40732399857](https://github.com/antonypaul98/cloudforge/actions/runs/40732399857):
**920 pytest passed** (32 additional synthetic cases), 19 infrastructure
checks (18 passed, 1 skipped), Python 3.11.17. See
`docs/OBSERVATION_RUNTIME_REQUEST.md` for the exact trust boundary,
reuse-first review, threat limitations and rollback. No external code,
dependencies, credentials or permissions were added. No separate local full
suite or physical Mac acceptance was performed.

**Still required before live monitoring:** Independently authenticated
operator approval and collector identity, trusted key/clock custody, endpoint
allowlist, DNS resolution and IP pinning/revalidation, TLS peer verification,
SSRF and redirect controls, measured runtime evidence and safe rollback.
Even a valid proposed DNS hostname may later resolve to a prohibited address.
No live service, infrastructure or recovery acceptance is claimed. Connected
GitHub integration was the writer; exclusive external worktree ownership is
unverified. Work/Astra were not invoked.

## Runtime IPv4 pinset preflight — 2026-10-28

Feature [PR #55](https://github.com/antonypaul98/cloudforge/pull/55)
merged as `3b9c68865cb1d8caba24b036c12ceb0c48a73813`. Exact feature
head `c66dff25a31d626cf2ca32659333ec2788e93e74` passed
[push CI #40741131775](https://github.com/antonypaul98/cloudforge/actions/runs/40741131775)
and [exact-head PR CI #40741170910](https://github.com/antonypaul98/cloudforge/actions/runs/40741170910).
[Feature merged-main CI #40741305989](https://github.com/antonypaul98/cloudforge/actions/runs/40741305989)
passed on Python 3.11.17: **965 pytest passed** (45 additional regression
cases), 19 infrastructure tests (18 passed, 1 skipped). A separate
isolated Python 3.13 module smoke passed 9 checks, but no separate local
full-repository suite or physical Mac/device validation was performed.

The pure, deterministic `RuntimeIPv4Pinset` checks caller-supplied IPv4
resolution against an exact separately supplied allowlist for each ordered
HTTPS observation target, after revalidating the existing handoff, receipt,
plan and proposal. Canonical public IPv4-only sets reject private, loopback,
metadata, shared, reserved, multicast, malformed, duplicate and misordered
addresses. The exported receipt is digest-only and always pending independent
approval. It does not contact DNS, network or services. See
[reuse-first provenance, tests and rollback](docs/OBSERVATION_RUNTIME_IPV4_PIN.md).
No third-party code, dependencies, credentials, provider costs or
infrastructure mutation were introduced.

**Not accepted:** independently authenticated operator or collector,
trusted DNS/allowlist provenance, AAAA/IPv6 validation, DNS rebinding
protection at connection time, TLS/SNI, trusted keys/clocks, actual runtime
service monitoring, deployment, recovery or physical hardware acceptance.
A caller can forge both supplied sets. External worktree exclusivity remains
unverified. No Work/Astra was invoked.

**Next:** Implement a separately approved, independently authenticated
read-only HTTPS collector with complete DNS/IP and connection-time TLS pinning.
No real endpoint may be contacted before exact human authorization.


## Runtime A/AAAA pinset preflight — 2026-10-28

Feature [PR #57](https://github.com/antonypaul98/cloudforge/pull/57)
merged as `8cd19fe7c069e9bc8f69922f7a50d1ab12f1eee1`. Exact
source head `3c308f8a36cc4fa83c898aacef0e69b0fc1f7d11` passed
[push CI #40750357903](https://github.com/antonypaul98/cloudforge/actions/runs/40750357903)
and [exact-head PR CI #40750368321](https://github.com/antonypaul98/cloudforge/actions/runs/40750368321).
[Feature merged-main CI #40750561795](https://github.com/antonypaul98/cloudforge/actions/runs/40750561795)
also passed: **1005 pytest passed** (40 additional regression cases),
19 infrastructure checks (18 passed, 1 skipped), Python 3.11.17.
Two earlier CI attempts failed because tests incorrectly classified valid
IPv6 input/order as invalid; the test fixtures were corrected and the
final exact head passed. An isolated Python 3.13 stubbed-module smoke
covered valid/verify/redaction and 13 negative IPv6 cases, but is not a
full repository acceptance run.

The optional `RuntimeDNSPinset` revalidates the existing exact
observation proposal and compares both caller-supplied A and AAAA sets
with separately supplied exact allowlists. It permits IPv4-only,
IPv6-only and mixed targets while rejecting unsafe/noncanonical,
duplicate, unsorted and altered addresses. It exports only digests and
pending-independent-approval status. See
[trust boundary, reuse provenance and rollback](docs/OBSERVATION_RUNTIME_DNS_PIN.md).
Existing CloudForge IPv4 validation and Python 3.11 standard library
were reused; no external code, dependencies, provider permissions,
network calls or infrastructure mutations were introduced.

**Not accepted:** Independent DNS resolution or proof of complete
A/AAAA answers; authenticated operator/collector, trusted keys/clocks,
connection-time IP pinning and TLS/SNI verification, live monitoring,
deployment, recovery or physical Mac/device evidence. The caller can
forge both answer and allowlist sets. The connected GitHub integration
was the writer; external worktree exclusivity remains unverified.
Work/Astra were not invoked.

**Next:** Independently authenticated and explicitly approved
read-only HTTPS transport with trusted DNS/allowlist provenance,
connection-time pinned destination IP, original hostname TLS/SNI/Host
verification, bounded retries and no unchecked redirects or DNS.
Do not contact real services before exact human approval.

## Pinned HTTPS socket primitive — 2026-10-28

Feature [PR #59](https://github.com/antonypaul98/cloudforge/pull/59)
merged as `3f88f36f7e82894aac82e8383aac46d936669de4`.
Exact source head `0b46b348526d5c7a6f926f01b200a21d12b83a4b`
passed [push CI #40759914358](https://github.com/antonypaul98/cloudforge/actions/runs/40759914358)
and [PR CI #40759948764](https://github.com/antonypaul98/cloudforge/actions/runs/40759948764).
[Feature merged-main CI #40760050324](https://github.com/antonypaul98/cloudforge/actions/runs/40760050324)
passed on Python 3.11.17: **1033 pytest passed** (28 new synthetic cases),
19 infrastructure tests (18 passed, 1 skipped). An isolated Python 3.13
stubbed-module smoke passed the same 28 cases but does not substitute for
repository CI. No physical Mac validation or real network probe occurred.

The internal `_PinnedHTTPSConnection` reuses existing CloudForge
target and A/AAAA address validators, opens only a numeric IP socket,
and preserves the original DNS hostname for verified TLS SNI/certificate
checks. It rejects HTTP CONNECT tunneling and closes raw sockets on
failed TCP/TLS connections. See
[implementation boundaries and rollback](docs/OBSERVATION_HTTPS_TRANSPORT.md).
Python standard-library primitives were reused; no third-party code,
new dependencies, credentials or infrastructure mutation.

**Software slice accepted only:** This class is deliberately not wired
to a collector or independent approval flow. It does not issue HEAD
requests, prove authenticated operator/collector identity, independently
validate DNS/allowlists, enforce overall transaction deadlines, produce
runtime evidence or monitor/deploy/recover real services. Exact approval,
Host header binding, trusted keys/clocks, safe retries and independently
verified runtime behavior remain mandatory before any real endpoint access.
Connected GitHub integration was the writer; external worktree exclusivity
remains unverified. Work/Astra were not invoked.

**Next:** Add an independently authenticated, exact-endpoint/IP-authorized
HEAD-only collector that uses this primitive with full timeout, Host,
redirection and evidence protections. No real endpoint access until
explicit human authorization.

## Unwired HTTPS HEAD request guard — 2026-10-28

Feature [PR #61](https://github.com/antonypaul98/cloudforge/pull/61)
merged as `04c595088bf4551843f9ea3d1d047a9259311b1d`. Exact source head `5406eef4f3b0e086dd9cf00ec490c128f8f6036d`
passed [push CI #40768144064](https://github.com/antonypaul98/cloudforge/actions/runs/40768144064)
and [PR CI #40768168374](https://github.com/antonypaul98/cloudforge/actions/runs/40768168374).
[Feature merged-main CI #40768333484](https://github.com/antonypaul98/cloudforge/actions/runs/40768333484)
passed on Python 3.11.17: **1051 pytest passed** (18 new fake-socket
regressions), 19 infrastructure checks (18 passed, 1 skipped).
An isolated Python 3.13 stubbed-module smoke passed 18 cases but was
not the full repository suite. Documentation acceptance PR must pass
its own exact-head and final merged-main CI before canonical acceptance.

The unwired `_PinnedHTTPSConnection.request()` now accepts only exact,
bodyless HEAD for the validated path and supplies the original hostname
in `Host`, including a nondefault port, plus `Connection: close`.
It rejects alternate methods, paths, request bodies, caller headers and
chunking before sending bytes. This reuses the existing CloudForge
transport and Python 3.11 `http.client`; official request documentation
was compared. No third-party code, dependencies or new provider costs.
See [contract, provenance and rollback](docs/OBSERVATION_HTTPS_TRANSPORT.md).

**Only the intended request API is guarded.** Inherited lower-level
methods remain callable; this is not a security sandbox or an approved
collector. No independently authenticated operator/collector, trusted
DNS/allowlist/key/clock, exact live approval, full transaction deadline,
signed runtime evidence, service monitoring, deployment, recovery or
physical Mac acceptance is claimed. No real network or infrastructure
was accessed. Connected GitHub integration was the writer; external
worktree exclusivity unverified. No Work/Astra invoked.

**Next:** Build the independently authenticated, exact-endpoint/IP-
approved HEAD-only collector with a complete deadline and evidence
boundary. No live endpoint access before explicit human approval.

## Unwired HTTPS inherited low-level guard — 2026-10-28

Feature [PR #63](https://github.com/antonypaul98/cloudforge/pull/63)
merged as `020a8bd673f8b24e158bf88bee1f5986ab9746e7`. Exact source head `49d6d2022752db9753805ac3b9e596d75d7cd6a0`
passed [push CI #40776427159](https://github.com/antonypaul98/cloudforge/actions/runs/40776427159)
and [PR CI #40776436834](https://github.com/antonypaul98/cloudforge/actions/runs/40776436834).
[Feature merged-main CI #40776555260](https://github.com/antonypaul98/cloudforge/actions/runs/40776555260)
passed on Python 3.11.17: **1059 pytest passed** (8 additional synthetic
regressions), 19 infrastructure tests (18 passed, 1 skipped). An isolated
Python 3.13 standalone prototype passed six low-level rejections and
canonical HEAD wire; it is not repository acceptance. This documentation
checkpoint requires its own exact-head and final merged-main CI.

The private, unwired pinned HTTPS connection now rejects ordinary direct
use of inherited `putrequest`, `putheader`, `endheaders`, `send`,
`_send_request` and `_send_output` outside its exact bodyless HEAD request.
Guard state resets after failed sends. Existing CloudForge code and Python
3.11 standard library were reused; official `http.client` docs were
reviewed. No third-party code, new dependencies, licenses, costs, schema
changes, credentials, live endpoint access or infrastructure mutation.
See [scope, tests and rollback](docs/OBSERVATION_HTTPS_TRANSPORT.md).

**Software-only safeguard, not a security sandbox:** explicit base-class
calls, monkeypatching, mutable attributes or raw sockets remain possible
from arbitrary same-process Python. No independently authenticated operator
or collector, trusted DNS/allowlist/key/clock, exact approved live endpoint,
complete transaction deadline, signed runtime evidence, service monitoring,
deployment, recovery or physical Mac/device acceptance. The GitHub connector
was the writer; external worktree exclusivity unverified. No Work/Astra used.

**Next:** Independently authenticated and operator-approved exact-endpoint/IP
HEAD-only collector with full elapsed deadline, evidence and rollback
boundaries; synthetic testing first. No live endpoint before explicit approval.


## Unwired HTTPS monotonic transaction deadline — 2026-10-28

Feature [PR #65](https://github.com/antonypaul98/cloudforge/pull/65)
merged as `c7872c4be9dff8f270db167baad55b9bb7f6703d`.
Exact source head `6052772248bdd918ac5bd3a3abdc41ba7500237a`
passed [push CI #40784965631](https://github.com/antonypaul98/cloudforge/actions/runs/40784965631)
and [PR CI #40784972134](https://github.com/antonypaul98/cloudforge/actions/runs/40784972134).
[Feature merged-main CI #40785104824](https://github.com/antonypaul98/cloudforge/actions/runs/40785104824)
passed on Python 3.11.17: **1068 pytest passed** (9 new synthetic
regressions), 19 infrastructure checks (18 passed, 1 skipped).
Container GitHub DNS prevented a separate local full-suite run; the
GitHub exact-head and merged-main runs are the full-suite evidence.

The private, still-unwired `_PinnedHTTPSConnection` now applies one
monotonic elapsed-time budget to the exact bodyless HEAD transaction:
numeric-IP connect, original-host TLS, send and response header retrieval.
It sets remaining per-operation socket timeouts, rejects late responses,
closes failed connections and prevents a second request while the first
response is pending. A regression specifically covers `http.client`
automatically closing the socket before the final deadline check.
Existing CloudForge transport and Python 3.11 standard library were reused,
with no third-party code, dependencies, licenses, provider permissions,
service costs, credentials or infrastructure mutation. See
[scope, provenance, limitations and rollback](docs/OBSERVATION_HTTPS_DEADLINE.md).

**Software-only acceptance:** Per-operation socket timeouts plus elapsed
postchecks do not forcibly cancel a single blocking call that overruns
the global budget; cleanup may also block. This is not a security sandbox,
authenticated collector, trusted DNS/allowlist/clock/key service, exact
operator approval, signed runtime evidence, actual service monitoring,
deployment or recovery. No real endpoint, physical Mac or device was
tested. Connected GitHub integration was the writer; external worktree
exclusivity remains unverified. Work/Astra were not invoked.

**Next:** Implement independently authenticated and explicitly authorized
read-only HTTPS HEAD collection with exact approved endpoint/IP, trusted
provenance and signed runtime evidence. No real service access or
infrastructure mutation without exact artifacts/plans and human approval.


## Synthetic pinned HTTPS HEAD fixture orchestration — 2026-10-28 ET

Feature [PR #67](https://github.com/antonypaul98/cloudforge/pull/67) merged
as `1052baa4298f2151c14f421fa98b5c65fd1d3fd6` after exact source head
`b330bab5781da5a7b41fd713681d7fdc5f958ddd` passed
[push CI #40791581678](https://github.com/antonypaul98/cloudforge/actions/runs/40791581678)
and [PR CI #40791605159](https://github.com/antonypaul98/cloudforge/actions/runs/40791605159).
[Merged-main CI #40791681944](https://github.com/antonypaul98/cloudforge/actions/runs/40791681944)
also passed: **1096 pytest passed** (28 new synthetic cases), 19
infrastructure checks (18 passed, 1 skipped), Python 3.11.17.
Container shell could not resolve GitHub, so no independent local full suite
was run; CI receipts are the actual complete-suite evidence.

The new `collect_pinned_https_fixture_samples` requires exact local receipt,
observation plan, runtime target request and full A/AAAA pinset revalidation
before any injected fake connection. It selects the first policy-matched numeric
IP, issues exact HEAD, classifies 2xx/3xx–5xx/invalid statuses and fails closed
on transport errors, cleanup failures and elapsed-budget overruns. The factory
is mandatory and has no network-capable default. This is **synthetic only**;
unsigned samples are not authenticated observations or service-health evidence.
See [contract, provenance and rollback](docs/OBSERVATION_HTTPS_FIXTURE.md).

Reused existing CloudForge validators, sample type and Python standard library.
No third-party code, new dependencies, credentials, cloud costs, provider calls,
real endpoint access, infrastructure mutation or physical Mac testing. Connected
GitHub integration was the writer; external worktree exclusivity unverified.
No Work/Astra invoked. Caller-supplied DNS/allowlists remain untrusted and
an injected factory is not a security boundary.

**Next:** Independently authenticated and explicitly approved read-only HTTPS
collector with trusted exact endpoint/IP, source key and clock, signed evidence,
separate operator authorization and rollback boundary. Do not access a real
service without explicit human approval.


## Proposed HTTPS HEAD operator-key permit — 2026-10-28 ET

Feature [PR #69](https://github.com/antonypaul98/cloudforge/pull/69)
merged as `a7ba9322ac29316d21f5ba56a874f160e234811f` after
exact source head `8f8eeb7634acf9bc2ac8ebb1d27252c992ae98e7` passed
[push CI #40798438798](https://github.com/antonypaul98/cloudforge/actions/runs/40798438798)
and [PR CI #40798444277](https://github.com/antonypaul98/cloudforge/actions/runs/40798444277).
[Feature merged-main CI #40798558609](https://github.com/antonypaul98/cloudforge/actions/runs/40798558609)
passed: **1128 pytest passed** (32 new synthetic tests), 19 infrastructure
checks (18 passed, 1 skipped), Python 3.11.17. The initial CI attempt failed
because a test incorrectly treated `valid_from == now` as invalid; the
expectation was corrected and the new exact head passed before merge.
No separate local full-suite run: container shell GitHub DNS unavailable.

`issue_runtime_head_permit` and `verify_runtime_head_permit` bind the
exact proposed HTTPS HEAD request, caller-supplied dual-stack pinset, source
alias/key fingerprint, one sequence and a maximum five-minute validity window
using a distinct operator-key HMAC. Both revalidate the existing exact
handoff/receipt/plan/target/pinset chain before acceptance. This is a
**no-I/O software-only permit**; it neither authenticates a human/collector
nor grants permission to contact a real endpoint. See
[scope, reuse and rollback](docs/OBSERVATION_RUNTIME_PERMIT.md).

Reused existing CloudForge validators and Python 3.11 standard-library
HMAC; no third-party code, new dependencies, service costs or provider
permissions. No live DNS/network, real infrastructure mutation, signed
runtime evidence, deployment, recovery or physical Mac validation.
Connected GitHub integration was the writer; external worktree exclusivity
remains unverified. Work/Astra were not invoked.

**Next:** Independently authenticate operator and collector, establish
trusted key/clock/DNS/allowlist provenance, atomically enforce one-shot
sequence, and only then wire an explicitly approved exact-endpoint/IP
HEAD-only runtime collector with signed evidence. No real service access
without explicit human approval.


## Permit-gated synthetic pinned HTTPS HEAD fixture — 2026-10-28 ET

Feature [PR #71](https://github.com/antonypaul98/cloudforge/pull/71)
merged as `326adb18fd47534576701136531b823db83c8c50` after exact
source head `65418194ba9e22500705f8fef8935ce4ef0e13a1` passed
[push CI #40804321853](https://github.com/antonypaul98/cloudforge/actions/runs/40804321853)
and [PR CI #40804341077](https://github.com/antonypaul98/cloudforge/actions/runs/40804341077).
[Feature merged-main CI #40804438339](https://github.com/antonypaul98/cloudforge/actions/runs/40804438339)
passed: **1139 pytest passed** (11 new synthetic cases), 19
infrastructure checks (18 passed, 1 skipped), Python 3.11.17.
No independent local full-suite run because the container cannot resolve
GitHub; CI receipts are the actual complete-suite evidence.

The new opt-in `collect_permitted_pinned_https_fixture_samples` verifies
the existing short-lived operator-key MAC and exact receipt/plan/target/A/AAAA
pinset chain **before** invoking any injected fake connection. Regressions
check correct HEAD-only IPv4/IPv6 ordering and fail-closed invalid policy
without factory invocation. Existing fixture APIs are unchanged. See
[reuse, limits and rollback](docs/OBSERVATION_PERMITTED_HTTPS_FIXTURE.md).

**Synthetic-only acceptance:** Caller-supplied operator/source keys, clock,
DNS, allowlists and injected factory are not independently authenticated
or isolated. This is not a security sandbox, signed runtime observation,
real monitoring, deployment or recovery. No third-party code, new
dependencies, credentials, real endpoints, infrastructure mutation or
physical Mac tests. Connected GitHub integration was the writer; external
worktree exclusivity unverified. Work/Astra not invoked.

**Next:** Independently authenticate operator/collector and trust roots,
atomically enforce one-shot sequence, then authorize exact live endpoint
read-only HEAD with signed runtime evidence. Explicit human approval
remains required before any real service access.


## Synthetic HTTPS permit remaining-window guard — accepted (2026-10-28 ET)

Feature [PR #73](https://github.com/antonypaul98/cloudforge/pull/73)
exact source head `8f08a5656acd85938cae42858b261e92cff71039`
passed [push CI #40810075232](https://github.com/antonypaul98/cloudforge/actions/runs/40810075232)
and [PR CI #40810091541](https://github.com/antonypaul98/cloudforge/actions/runs/40810091541).
Guarded squash merge `8f452518ae0dea27a00bc2eb5fc66ce8c2c03ab4`
passed [merged-main CI #40810194926](https://github.com/antonypaul98/cloudforge/actions/runs/40810194926):
**1,144 pytest passed**, infrastructure **18 passed/1 skipped** on Python 3.11.17.
Five new synthetic regressions check exact and insufficient permit-window
boundaries and rechecking caller-supplied time before any injected factory.

Reused existing runtime permit verifier, validated plan timeout fields and
synthetic HEAD seam. No third-party code, new dependency, provider operation,
live endpoint, DNS, real infrastructure change, physical Mac or Work/Astra.
The budget is not an enforceable hard deadline, trusted clock, authenticated
operator/collector, durable replay guard, signed runtime observation, deployment
or recovery. External worktree exclusivity remains unverified. Rollback is a
feature-merge revert; no migration. Canonical documentation acceptance has its
own exact-head and final merged-main CI gates.

Next: independent operator/collector trust and endpoint policy, durable atomic
one-time replay enforcement, then explicitly approved read-only monitoring.


## Optional SQLite permit replay admission — accepted synthetic checkpoint (2026-10-29 ET)

Feature [PR #75](https://github.com/antonypaul98/cloudforge/pull/75) exact head
`a73243ac24664745f92057cac383dea0ebd28ac3` passed [push CI #40815363923](https://github.com/antonypaul98/cloudforge/actions/runs/40815363923)
and [PR CI #40815380768](https://github.com/antonypaul98/cloudforge/actions/runs/40815380768).
Guarded squash merge `f25ebfcac2f4788695c6036cecfcee8dbcc81e0a` passed
[merged-main CI #40815444322](https://github.com/antonypaul98/cloudforge/actions/runs/40815444322)
on Python 3.11.17: **1,155 pytest passed** (11 new synthetic cases);
infrastructure 18 passed, 1 skipped.

An opt-in SQLite `BEGIN IMMEDIATE` ledger now rejects duplicate or lower
operator-key permit sequences per source alias/runtime request **before any
injected fake HEAD connection**. It reuses CloudForge's existing hardened local
ledger path preflight and SQLite conditional UPSERT pattern, plus Python 3.11
stdlib; no third-party code, new dependencies or external services. Tests
exercise persistence, concurrent duplicate attempts, source-key rotation,
invalid MAC before ledger creation, unsafe paths, altered schema, and
failed-probe consumption. See
[scope, provenance and rollback](docs/OBSERVATION_PERMITTED_HTTPS_FIXTURE.md).

**Synthetic-only acceptance:** The caller still controls ledger path, source
alias, keys, clock, DNS/pinset, factory and policy. The optional ledger is
not a privileged, trusted, single-writer execution boundary; backup rollback,
alternate ledgers/aliases or ungated callers bypass it. This is at-most-once
admission within one local ledger, not exactly-once execution, authenticated
operator/collector identity, live monitoring, signed runtime evidence,
deployment or recovery. No real endpoint, infrastructure, physical Mac, Work
or Astra was used. Connected GitHub integration wrote the checkpoint;
external worktree exclusivity remains unverified. Rollback is a feature-merge
revert; no existing schema migration.

**Next:** Independently authenticate operator and collector; establish trusted
key/clock/endpoint policy and one protected ledger before explicitly approved
read-only HEAD collection and signed runtime evidence. Canonical documentation
acceptance requires its own exact-head and final merged-main CI.


## Synthetic permitted HTTPS signed intake — accepted (2026-10-29 ET)

Feature [PR #77](https://github.com/antonypaul98/cloudforge/pull/77) exact
head `daaca840b0e716ebc7d2a70e661450775ce5ffea` passed
[push CI #40821005868](https://github.com/antonypaul98/cloudforge/actions/runs/40821005868)
and [PR CI #40821029491](https://github.com/antonypaul98/cloudforge/actions/runs/40821029491).
Guarded squash merge `6f56078f8d1798c60df8cf7c126d3f2437be874a` passed
[merged-main CI #40821108824](https://github.com/antonypaul98/cloudforge/actions/runs/40821108824)
on Python 3.11.17: **1,166 pytest passed** (11 new synthetic cases);
infrastructure **18 passed, 1 skipped**. GitHub CI is the full-suite
evidence; the container could not resolve GitHub for a separate local suite.

The new opt-in `collect_and_accept_permitted_pinned_https_fixture_evidence`
composes exact permit/pinset and freshness checks, read-only replay preflight,
atomic permit consumption, injected fake HEAD, HMAC signing and durable evidence
acceptance. Both independent SQLite tables live in the same explicit local
file. Tests cover valid signed samples, duplicate and corrupt ledger rejection,
MAC/freshness/budget/path failures before I/O, unknown-on-probe-failure,
concurrent duplicates and increasing sequence. See
[reuse, limitations and rollback](docs/OBSERVATION_PERMITTED_HTTPS_INTAKE.md).

**Synthetic-only acceptance:** Caller-provided identity, keys, clock, DNS,
allowlists, ledger and factory remain untrusted. The two SQLite transactions
are not one atomic transaction and a crash after permit consumption may leave
no evidence. No real endpoint, independently authenticated operator/collector,
protected runtime policy, live monitoring, deployment, recovery, physical Mac
or infrastructure mutation. Existing CloudForge logic and Python standard
library were reused, without third-party code or new dependencies. Connected
GitHub integration wrote the checkpoint; external worktree exclusivity remains
unverified. No Work/Astra invoked. Rollback is feature-merge revert.

**Next:** Establish independently authenticated operator/collector identity,
trusted key/clock/DNS/endpoint policy and protected replay boundary, then
explicitly approve an exact read-only endpoint before real monitoring.
Canonical acceptance documentation has its own exact-head and merged-main CI.


## Read-only synthetic HTTPS replay-gap diagnostic — accepted (2026-10-29 ET)

Feature [PR #79](https://github.com/antonypaul98/cloudforge/pull/79) exact
head `07dc3428c12003690fff981f6844165b18c83efe` passed
[push CI #40827337800](https://github.com/antonypaul98/cloudforge/actions/runs/40827337800)
and [PR CI #40827358657](https://github.com/antonypaul98/cloudforge/actions/runs/40827358657).
Guarded squash merge `0bb46f13f1f0744235af0787c00b4ab2fdc3cf08`
passed [merged-main CI #40827444731](https://github.com/antonypaul98/cloudforge/actions/runs/40827444731)
on Python 3.11.17: **1,182 pytest passed** (16 new synthetic tests);
infrastructure **18 passed, 1 skipped**. Separate isolated Python 3.13
stubbed smoke passed 16 cases; it is not full-repository evidence.

New read-only `inspect_synthetic_https_replay_gap` compares a consumed
permit sequence and accepted evidence sequence from one caller-selected
SQLite ledger, detecting a *possible* interrupted two-transaction intake
without changing either counter, reissuing permits or probing services.
It reuses CloudForge schema/path/source validation and Python standard-library
SQLite read-only mode. No third-party code, new dependencies, cloud cost,
credentials, real endpoint, provider, infrastructure or physical Mac changes.
See [scope, provenance and rollback](docs/OBSERVATION_REPLAY_DIAGNOSTICS.md).

**Synthetic-only acceptance:** Different counter key scopes mean a gap is
only a signal, and equal counters do not prove an individual request ran
or produced signed evidence. Caller-held ledger, keys, identity, clock, DNS
and fake factory are not independently trusted. No production monitoring,
automatic recovery, deployment or real runtime evidence. Work/Astra were
not invoked; connected GitHub integration wrote the checkpoint, and external
worktree exclusivity remains unverified. Revert feature merge for rollback;
no migration. Canonical acceptance documentation requires its own exact-head
and merged-main CI.

**Next:** Prioritize independent operator/collector authentication, protected
keys/clock/endpoint policy and replay boundary, then explicitly approved
read-only monitoring with signed runtime provenance. Never reset consumed
permits automatically.

## Consistent read-only HTTPS replay-gap snapshot — 2026-10-29 ET

Feature [PR #81](https://github.com/antonypaul98/cloudforge/pull/81) exact
source head fc0d7a3265d98364ed0f93b18415a9288cdcf1c5 passed
[push CI #40833371802](https://github.com/antonypaul98/cloudforge/actions/runs/40833371802)
and [exact-head PR CI #40833400206](https://github.com/antonypaul98/cloudforge/actions/runs/40833400206).
Guarded squash merge 96b3ac6459295f7d3ab4dba968bedd3bdecade90
passed [merged-main CI #40833512821](https://github.com/antonypaul98/cloudforge/actions/runs/40833512821):
**1,184 pytest passed** (two new synthetic regressions), infrastructure
**18 passed/1 skipped**, Python 3.11.17. The SQLite Python 3.13 isolated
prototype demonstrated inconsistent counter reads without an explicit
transaction and a stable snapshot with one; it was not the full suite.

The diagnostic now starts one explicit query-only SQLite read transaction
so schema inventory and both replay counters reflect one consistent database
snapshot. Two deterministic WAL-mode tests inject concurrent counter advancement
and table creation between reads, then verify that a later inspection sees
the committed changes. This reuses existing CloudForge contracts and SQLite
standard-library behavior, with no external code, new dependencies, schema
migration or provider cost. See
[provenance, limits and rollback](docs/OBSERVATION_REPLAY_DIAGNOSTICS.md).

**Synthetic-only acceptance:** This does not authenticate an operator or
collector, trust keys/clocks/DNS, prevent ledger replacement/rollback, prove
a specific probe executed, or enable real monitoring, deployment or recovery.
No live endpoints, physical Mac, infrastructure mutation, Work or Astra.
Connected GitHub integration was the writer; external worktree exclusivity
remains unverified. Rollback is revert of the feature merge.

**Next:** Establish independent operator/collector identity, protected trust
roots and execution boundary, and exact human-approved endpoint policy before
live read-only monitoring with signed runtime evidence.


## Strict optional signed HTTPS source policy — accepted feature (2026-10-29 ET)

Feature [PR #83](https://github.com/antonypaul98/cloudforge/pull/83)
source head `e57dd6f8b8205b7d884d4502b0bccb831c995fa0` passed
[push CI #40840265770](https://github.com/antonypaul98/cloudforge/actions/runs/40840265770)
and [exact-head PR CI #40840400974](https://github.com/antonypaul98/cloudforge/actions/runs/40840400974).
Guarded squash merge `326569fe47c51cdd13250ea4ddacdc3b93892961`
passed [merged-main CI #40840599008](https://github.com/antonypaul98/cloudforge/actions/runs/40840599008):
**1,198 pytest passed** (14 new synthetic regression cases), infrastructure
**18 passed, 1 skipped**, Python 3.11.17. The container could not resolve
GitHub for an independent local full-suite run; GitHub CI is the full-suite
evidence. Canonical documentation PR requires its own exact-head and
final merged-main CI.

The signed synthetic pinned HTTPS intake now optionally checks the existing
exact observation-plan/source/key/time pin, strict pin requirement and
revoked-key fingerprints before SQLite replay access or any injected fake
HEAD factory. Tests cover valid strict mode, 12 invalid/malformed/boundary
cases rejected before factory and ledger creation, and key rotation requiring
a new pin without resetting the replay counters. Existing unpinned behavior
remains supported. The code reuses CloudForge's loopback source-policy and
source-pin verifier plus Python standard-library SHA-256/HMAC; no copied
third-party code, dependencies, schema changes or provider costs. See
[provenance, limitations and rollback](docs/OBSERVATION_PERMITTED_HTTPS_INTAKE.md).

**Synthetic-only acceptance:** Caller-supplied source policy, keys, clock,
DNS, ledger and fake connection factory are not independently trusted.
Ungated and unpinned callers can bypass this opt-in safeguard. No real
endpoint, physical Mac, infrastructure mutation, authenticated collector,
production deployment or recovery was used. Work/Astra not invoked.
Connected GitHub integration was the writer; exclusive external worktree
ownership remains unverified. Rollback is revert of feature merge; no migration.

**Next:** Independent operator/collector authentication, protected
key/clock/endpoint policy and durable execution boundary before exact
human-approved real read-only service monitoring with signed runtime evidence.


## Synthetic HTTPS factory preflight — accepted feature (2026-10-29 ET)

Feature [PR #85](https://github.com/antonypaul98/cloudforge/pull/85)
exact source head `2795421670f29124dfd8c38bfa296de733f783d7` passed
[push CI #40846726793](https://github.com/antonypaul98/cloudforge/actions/runs/40846726793)
and [exact-head PR CI #40846772456](https://github.com/antonypaul98/cloudforge/actions/runs/40846772456).
Guarded squash merge `40fdc215c3ccd6a8bd6eeecddd68629f5f8d1af5`
passed [merged-main CI #40846895046](https://github.com/antonypaul98/cloudforge/actions/runs/40846895046):
**1,204 pytest passed** (six new synthetic cases), infrastructure **18
passed/1 skipped**, Python 3.11.17. No independent local full-suite run:
shell GitHub DNS was unavailable and local Python 3.11 was absent.

Both the permitted synthetic HEAD fixture and signed evidence intake now
reject missing/noncallable injected connection factories before consuming
the one-shot permit; the signed path also rejects before read-only evidence
replay preflight. Previously a caller configuration error could burn a valid
permit without running any HEAD fixture. Tests cover three invalid factory
values at both entry points, no premature ledger use and successful reuse
of the same permit with a proper fake factory. Existing CloudForge validation
and Python's built-in `callable` were reused; no third-party code, new
dependency, provider operation, credential, infrastructure mutation, real
endpoint or physical Mac test. See
[scope, provenance and rollback](docs/OBSERVATION_PERMITTED_HTTPS_INTAKE.md).

**Synthetic-only acceptance:** A callable factory can still perform real
network I/O if supplied by an unsafe caller. No independently authenticated
operator/collector, trusted key/clock/DNS/endpoint policy, protected replay
boundary, signed *runtime* service evidence, production deployment or
recovery is established. Connected GitHub integration wrote the feature;
exclusive external worktree ownership remains unverified. Work/Astra were
not invoked. Revert the feature merge for rollback; no migration.
Canonical documentation acceptance requires its own exact-head and final
merged-main CI.

**Next:** Establish independent operator/collector identity and protected
execution trust roots. Only then consider an explicitly human-approved,
read-only endpoint collector with signed runtime evidence; no real endpoint
or infrastructure mutation without exact plans and human approval.


## Signed synthetic HTTPS observation timestamp within permit window — accepted feature (2026-10-29 ET)

Feature [PR #87](https://github.com/antonypaul98/cloudforge/pull/87)
source head `aa80e4f5c6832fcd46cff60599e008fc77bc3b98` passed
[push CI #40853840983](https://github.com/antonypaul98/cloudforge/actions/runs/40853840983)
and [exact-head PR CI #40853864706](https://github.com/antonypaul98/cloudforge/actions/runs/40853864706).
Guarded squash merge `32edfec76da9145c0d91d6e2a8532726f9a0c307` passed
[merged-main CI #40853948547](https://github.com/antonypaul98/cloudforge/actions/runs/40853948547):
**1,208 pytest passed** (four new parameterized no-network cases), infrastructure
**18 passed/1 skipped**, Python 3.11.17. The separate local Python 3.13
prototype checked only the integer/window predicate; it was not the full suite.

The signed synthetic pinned HTTPS intake now requires the claimed observation
time to fall within the verified HEAD permit's validity interval, rejecting a
pre-permit timestamp even when it meets ordinary evidence freshness. Non-integer
and boolean values also fail before replay ledger access or any injected factory.
The lower permit boundary remains inclusive; a rejected attempt does not burn
the one-shot permit. This reuses the existing CloudForge loopback permit rule
and Python built-ins, without third-party code, new dependencies, credentials,
real endpoint access, physical Mac, infrastructure mutation or Work/Astra.
See [contract, provenance, limits and rollback](docs/OBSERVATION_PERMITTED_HTTPS_INTAKE.md).

**Synthetic-only acceptance:** The timestamp, clock, keys, DNS, ledger and
connection factory remain caller-controlled. This does not authenticate an
operator or collector, prove actual probe timing, provide trusted monitoring,
deploy or recover infrastructure. Connected GitHub integration wrote the feature;
exclusive external worktree ownership is unverified. Revert feature merge for
rollback; no migration. Canonical documentation PR requires its own exact-head
and final merged-main CI.

**Next:** Establish independent operator/collector identity and protected
execution trust roots, trusted clock/key/endpoint policy and durable replay
boundary before explicitly human-approved read-only monitoring.


## Synthetic HTTPS monotonic-clock failure guard — accepted feature (2026-10-29 ET)

Feature [PR #89](https://github.com/antonypaul98/cloudforge/pull/89)
source head `49857e1e2366425cc6eee3aa88c19a626c12ecb0` passed
[push CI #40862665715](https://github.com/antonypaul98/cloudforge/actions/runs/40862665715)
and [exact-head PR CI #40862702829](https://github.com/antonypaul98/cloudforge/actions/runs/40862702829).
Guarded squash merge `e095b0be95fa965ba117cad48a6b647f4e80cb2e` passed
[merged-main CI #40862819512](https://github.com/antonypaul98/cloudforge/actions/runs/40862819512):
**1,214 pytest passed** (six new no-network regression cases), infrastructure
**18 passed/1 skipped**, Python 3.11.17. The isolated Python 3.13
arithmetic prototype was not a full repository test; shell GitHub DNS
and Python 3.11 were unavailable locally.

The injected synthetic HTTPS HEAD fixture now maps monotonic start/finish
read failures and nonfinite elapsed deltas to `unknown` with zero
elapsed milliseconds, without forging a successful sample or leaking
a conversion exception. It skips the fake connection if the start clock
fails and closes the connection before handling a finish clock failure.
Huge finite elapsed values are clamped before integer conversion.
Normal elapsed behavior and timeout checks are preserved.
Reused the existing fixture and Python 3.11 standard-library
`math.isfinite`; no copied third-party code, dependencies, real DNS,
endpoint, provider, credentials, infrastructure change, physical Mac,
Work or Astra. See [provenance and rollback](docs/OBSERVATION_HTTPS_FIXTURE.md).

**Synthetic-only acceptance:** The clock, keys, DNS, ledger and injected
factory remain caller-controlled. This does not establish trusted time,
operator/collector identity, a secure runtime boundary, actual monitoring,
deployment or recovery. Connected GitHub integration wrote the feature;
exclusive external worktree ownership is unverified. Revert feature merge
for rollback; no migration. Canonical documentation PR requires its own
exact-head and final merged-main CI.

**Next:** Establish independent operator/collector identity, protected
clock/key/endpoint policy and durable replay execution boundary before
explicitly approved read-only service monitoring.


## Synthetic HTTPS monotonic start-clock preflight — accepted feature (2026-10-29 ET)

Feature [PR #91](https://github.com/antonypaul98/cloudforge/pull/91)
source head `0d0becdb986a9b924b96e050f7569384de644b7f` passed
[push CI #40869852648](https://github.com/antonypaul98/cloudforge/actions/runs/40869852648)
and [exact-head PR CI #40869883510](https://github.com/antonypaul98/cloudforge/actions/runs/40869883510).
Guarded squash merge `c950a6b2ceb71624471d6464b32c3243b9f88462` passed
[merged-main CI #40870007469](https://github.com/antonypaul98/cloudforge/actions/runs/40870007469):
**1,224 pytest passed** (ten new no-network regression cases), infrastructure
**18 passed/1 skipped**, Python 3.11.17. No independent local full suite:
container shell GitHub DNS unavailable and Python 3.11 absent.

Synthetic HTTPS HEAD fixture now rejects nonfinite, malformed, boolean and
unrepresentably huge monotonic **start** values before invoking any injected
fake connection. Invalid finish clocks still close the connection and yield
unknown samples. Existing valid-clock behavior and public signature unchanged.
Reused Python 3.11 standard-library math.isfinite and existing fixture code;
no third-party code, dependencies, provider, credentials, real endpoint,
infrastructure mutation, physical Mac, Work or Astra. See
[reuse, tests, limitations and rollback](docs/OBSERVATION_HTTPS_FIXTURE.md).

**Synthetic-only acceptance:** The clock, keys, DNS, ledger and injected
factory remain caller-controlled. No independent operator/collector identity,
trusted runtime execution, real monitoring, deployment or recovery.
Connected GitHub integration was the writer; external worktree exclusivity
unverified. Rollback: revert feature merge; no schema or infrastructure
change. Canonical documentation PR requires its own exact-head and final
merged-main CI before final canonical acceptance.

**Next:** Establish independent operator/collector authentication, protected
key/clock/endpoint/replay execution boundary, then explicitly approved
read-only monitoring.


## Deterministic recovery review proposal — accepted synthetic feature (2026-10-29 ET)

Feature [PR #93](https://github.com/antonypaul98/cloudforge/pull/93)
source head c87c75601d5aa00bdc795003f217581d8f498f7f passed
[push CI #40879159606](https://github.com/antonypaul98/cloudforge/actions/runs/40879159606)
and [exact-head PR CI #40879184437](https://github.com/antonypaul98/cloudforge/actions/runs/40879184437).
Guarded squash merge 052bf4cffc768fb5be44b14bea9205ec869c4347 passed
[merged-main CI #40879404105](https://github.com/antonypaul98/cloudforge/actions/runs/40879404105):
**1,241 pytest passed** (17 new synthetic cases), infrastructure
**18 passed/1 skipped**, Python 3.11.17. Full suite was verified in
GitHub CI; no independent local full suite because shell GitHub DNS
and Python 3.11 were unavailable.

The new pure provider-neutral recovery review proposal reuses the
existing exact artifact/approval/HMAC/source-policy, contiguous sequence,
claimed cadence and failure-threshold verification. It emits a canonical
non-executing manual-investigation proposal only when a threshold is
reached; unknown is insufficient evidence, and no trigger in a bounded
window does not prove health. Plan and evidence-window SHA-256 digests
bind the review without exporting raw source identities, artifact bytes
or reviewer names. No provider calls, new dependencies, credentials,
real network, infrastructure, physical Mac, Work or Astra. See
[scope, reuse, tests and rollback](docs/RECOVERY_REVIEW.md).

**Synthetic-only acceptance:** The source key, clock, samples and
replay context remain caller-controlled. This is not a trusted collector,
service-health proof, actual alert, automatic rollback, deployment or
recovery. Connected GitHub integration was the writer; external worktree
exclusivity remains unverified. Revert feature merge for rollback; no
schema or infrastructure change. Canonical documentation PR must pass
its own exact-head and final merged-main CI before final acceptance.

**Next:** Independently authenticate operator/collector identities and
establish protected key/clock/endpoint/replay execution boundaries,
then explicitly approve and validate read-only live monitoring.


## Optional operator-key fingerprint preflight — accepted synthetic feature (2026-10-29 ET)

Feature [PR #95](https://github.com/antonypaul98/cloudforge/pull/95)
source head `2486872a89e38f0235f590655ca402e084658a53` passed
[push CI #40898441429](https://github.com/antonypaul98/cloudforge/actions/runs/40898441429)
and [exact-head PR CI #40898503679](https://github.com/antonypaul98/cloudforge/actions/runs/40898503679).
Guarded squash merge `8e3c3bb7136fd0565bab1e7149f1a43dbd354091` passed
[merged-main CI #40898630758](https://github.com/antonypaul98/cloudforge/actions/runs/40898630758):
**1,258 pytest passed** (17 new offline cases), infrastructure
**18 passed/1 skipped**, Python 3.11.17. Local Python 3.13 checked only
six standalone helper assertions; it was not the repository suite.

Signed synthetic HTTPS intake now optionally validates a separately
supplied lowercase SHA-256 operator-key fingerprint, including strict
requirement mode, before SQLite replay reads or fake HEAD calls. It composes
with the existing source pin and operator/source distinct-key permit checks.
Malformed, missing or mismatched pins fail closed; old unpinned callers
remain compatible. Existing CloudForge contracts and Python standard-library
hashlib/hmac were reused without copied third-party code, dependency, API,
provider, credentials, infrastructure, real network, physical Mac, Work or
Astra. See [provenance and rollback](docs/OBSERVATION_PERMITTED_HTTPS_INTAKE.md).

**Synthetic-only limitation:** The caller still controls both the key and
expected digest. This is configuration consistency, **not independently
authenticated operator or collector identity**. No protected key/clock/DNS/
endpoint/replay execution, real monitoring, deployment or recovery is
established. Connected GitHub integration wrote the feature; external
worktree exclusivity is unverified. Revert feature merge for rollback;
no schema migration. Canonical documentation PR must pass its own exact-head
and final merged-main CI before final canonical acceptance.

**Next:** Provision an independent trust root and authenticate operator/
collector workloads, protect runtime key/clock/endpoint/replay boundaries,
then obtain exact human approval for any real read-only endpoint. Do not
replace this milestone with additional optional fixture pins.


## Unwired explicit-root collector mTLS client context — accepted synthetic software (2026-10-29 ET)

Feature [PR #97](https://github.com/antonypaul98/cloudforge/pull/97) exact head
`9c10ba43bec93659ddebf97be8fdd86a5daebce0` passed [push CI #40907336514](https://github.com/antonypaul98/cloudforge/actions/runs/40907336514)
and [PR CI #40907371409](https://github.com/antonypaul98/cloudforge/actions/runs/40907371409).
Guarded squash merge `d03d8a3628321b4680f330172b6fe4c2f95cac8f` passed
[merged-main CI #40907511050](https://github.com/antonypaul98/cloudforge/actions/runs/40907511050):
**1,302 pytest passed**, infrastructure **18 passed/1 skipped**, Python 3.11.17.
The new isolated offline regressions contributed 44 cases; an isolated Python
3.13 smoke also passed 44, but is not independent full-suite acceptance.

The new `build_collector_mtls_client_context` constructs a strict TLS client
context with an explicit CA trust bundle and client certificate/private key,
peer certificate and hostname verification, TLS 1.2 minimum, no default CA
fallback and noninteractive private-key loading. It reuses Python 3.11 `ssl`
without new dependencies, copied third-party code or credentials. It is **not
wired** to the existing HTTPS transport and performs no network I/O.
See [trust boundary, reuse and rollback](docs/OBSERVATION_MTLS_BOUNDARY.md).

**Not production identity acceptance:** No independently provisioned root or
short-lived workload certificate exists in CloudForge; no authenticated operator,
server-side client identity authorization, protected key/clock/DNS/endpoint/replay
execution, SPIFFE URI SAN validation, live collector, deployment or recovery.
No real TLS handshake, provider, infrastructure, physical Mac, Work or Astra.
Connected GitHub integration was the writer; external worktree exclusivity
remains unverified. Rollback: revert feature merge, no migration or deployed
state. Canonical documentation PR requires its own exact-head and final
merged-main CI before final acceptance.

**Next:** Establish independent operator/collector workload identity and
protected runtime enforcement before any explicitly approved live monitoring.

## Real-manifest review-only demo — accepted feature (2026-10-29 ET)

Demo-first transition followed successful mTLS acceptance [PR #98](https://github.com/antonypaul98/cloudforge/pull/98), final merged-main CI [#40907986885](https://github.com/antonypaul98/cloudforge/actions/runs/40907986885). No unfinished PR was abandoned.

Feature [PR #99](https://github.com/antonypaul98/cloudforge/pull/99) source head `091247e6d4e329920b27de48ec875c43e8817c4d` passed [exact-head push CI #40926942716](https://github.com/antonypaul98/cloudforge/actions/runs/40926942716) and [PR CI #40926994207](https://github.com/antonypaul98/cloudforge/actions/runs/40926994207). Guarded squash merge `3f4334b706c5061faed037865251684313ac84dc` passed [merged-main CI #40927135195](https://github.com/antonypaul98/cloudforge/actions/runs/40927135195) on Python 3.11.17: **1,324 pytest passed** (22 new cases), infrastructure **18 passed/1 skipped**. No independent local full suite was run because the container cannot resolve GitHub.

The CLI `python -m cloudforge.application_demo --name my-api --target review-staging --manifest ./requirements.txt` reads only explicitly selected, bounded manifest text and composes existing non-executing inspection, provider-neutral planning, deterministic JSON proposal, and exact-target handoff-request digest. It outputs source SHA-256 fingerprints, limited manifest evidence and `approval-required` status. Tests cover repeatability, changed-target/changed-dependency binding, malformed/oversized/ambiguous inputs, symlinks, UTF-8, redaction, no network/process, and CLI operation. No external source code was copied or translated, no new dependency, credentials, API costs, provider call, real endpoint, infrastructure mutation, physical Mac or Work/Astra. Connected GitHub integration was writer; exclusive external worktree ownership unverified. Revert merge to roll back; no schema migration.

Reuse-first comparison: [Backstage templates](https://backstage.io/docs/features/software-templates/) already scaffold applications; [OpenTofu plan](https://opentofu.org/docs/v1.9/cli/commands/plan/) already previews real infrastructure; [Pulumi policies](https://www.pulumi.com/docs/discovery-governance/concepts/policy-as-code/) already enforce policy gates. CloudForge's intended gap is verified provenance across real input, approval, sandbox deployment, observation and controlled recovery, not a novel scaffold/plan/policy. See [demo readiness](docs/DEMO_READINESS.md).

**DEMO READINESS: PARTIAL.** Real-input review-only chain is repeatable; full original product demo is **NOT READY**. **FULL PRODUCT COMPLETION: UNVERIFIED**, with no justified percentage or date. The JSON is not executable IaC. No authenticated operator/collector, independent key/clock/DNS, actual sandbox deployment, signed real monitoring, chaos, rollback or recovery has been verified. Canonical documentation PR requires its own exact-head and final merged-main CI before final acceptance.

**Next:** Define and test an exact-artifact-approved, isolated sandbox execution/observe/recover path with independent trust and measurable outputs; no real endpoint or infrastructure action without explicit human approval. Do not divert into optional fixture safeguards before demonstrating the original product journey.
