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
