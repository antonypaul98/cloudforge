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
