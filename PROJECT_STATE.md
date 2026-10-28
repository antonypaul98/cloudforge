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
