# Real-manifest review demo (first demo-first milestone)

## What it proves

Run a credential-free, read-only flow on actual caller-selected Python or Node manifest text:

1. Read only the explicitly named root `requirements.txt`, `pyproject.toml`, or `package.json` (bounded to 65,536 bytes each; combined 131,072 bytes).
2. Reuse the existing non-executing application inspector, provider-neutral requirements planner, deterministic JSON proposal renderer and exact-target deployment handoff request.
3. Emit canonical, repeatable JSON containing source SHA-256 fingerprints, limited manifest evidence, proposed resources, plan digest, exact-target handoff request digest, a separate source-bound review digest, and explicit `approval-required` status.
4. Refuse unsupported or malformed inputs, mixed Python/Node manifests, symlink-selected manifest files, duplicate manifest basenames and oversized files.

From a checkout with Python 3.11 and the package installed:

```sh
python -m cloudforge.application_demo --name my-api --target review-staging --manifest ./requirements.txt
python -m cloudforge.application_demo --name my-node-api --target review-staging --manifest ./package.json
```

These commands **read the selected manifest and print review-only JSON**. They do not execute application code, deploy, connect to a service, authenticate a reviewer, issue an execution approval, observe health or perform recovery. The proposal is not executable Terraform, OpenTofu or Pulumi code. An explicit target is only an opaque review identifier.

## Demo acceptance and remaining product gap

| Milestone | Evidence / status |
| --- | --- |
| Existing synthetic authorization/replay demo | `python -m cloudforge.synthetic_demo` already exists; uses fixed fake inputs |
| Real manifest -> inspection -> requirements -> review-only JSON -> target-bound handoff request | This checkpoint; exact-head CI and merged-main CI required before acceptance |
| Independently authenticated operator and collector, signed runtime observations | Not implemented or verified |
| Real sandbox deployment with approved IaC, actual service health, rollback/recovery | Not implemented or verified; requires exact artifact and human approval |
| End-to-end original CloudForge product demo | Not ready |

**DEMO READINESS:** Partial review-only flow; do not call this a production or full product demo.
**FULL PRODUCT COMPLETION:** Unverified; no percentage or delivery date inferred from test counts.

## Bounded reuse-first competitor check

- [Backstage software templates](https://backstage.io/docs/features/software-templates/) already support template-driven creation and review, so CloudForge must not claim novelty for scaffolding.
- [OpenTofu plan](https://opentofu.org/docs/v1.9/cli/commands/plan/) already previews real infrastructure changes, so CloudForge's provider-neutral JSON proposal is **not** a replacement for a real execution plan.
- [Pulumi policy-as-code](https://www.pulumi.com/docs/discovery-governance/concepts/policy-as-code/) already enforces policies before deployments, so policy gates alone are not a unique advantage.

The differentiated acceptance target is a verifiable, provenance-linked **real application -> plan -> approved sandbox deployment -> observed behavior -> controlled recovery** journey, with no fabricated identity, evidence or infrastructure outcomes. The present checkpoint only exercises the first read-only portion. Reuses CloudForge's existing Python 3.11 standard-library parser, planner, IaC renderer and handoff; no external code, new dependency, license, API charge or provider permission is added.

## Trust, provenance, and rollback

Only selected manifest text is read. The raw contents are not printed; hashes are linkable metadata. Dependency inference recognizes only PostgreSQL/Redis and can omit other infrastructure needs. Selected paths may still be user-controlled; this is **not** a filesystem sandbox, and symlink checks on selected files do not protect against every path race or symlinked parent. Do not run this tool on untrusted paths with elevated privileges. Existing approval contracts are unchanged. Roll back by reverting the feature merge; no schema migration, external resource or infrastructure mutation.

## Exact source-byte provenance in review packets

The inferred infrastructure plan and existing deployment handoff request can be
identical for different manifest bytes (for example, a changed dependency
version or comment that does not change recognized PostgreSQL/Redis resources).
The `source_review_binding` field closes that *review-demo provenance* gap:
it canonically SHA-256 binds the application and opaque target, the exact
selected manifest-byte SHA-256 map, and the original deployment request digest.
Its versioned operation and digest are reproducible without secrets; changing
manifest bytes, target, or handoff request invalidates the binding. Manifest
insertion order does not affect it.

This is **not an authenticated approval or a signature**. A caller can recompute
or forge this unkeyed digest. Existing deployment approval/authorization APIs
are unchanged and **do not yet enforce** this source binding. A future isolated
sandbox adapter must re-read the exact manifest bytes, rederive this binding,
validate independent operator approval and target, and refuse stale artifacts
before any real execution. Do not treat this digest as permission to deploy.
No third-party code was copied; reused in-repo review contracts and Python 3.11
`hashlib`/`json`. No new dependency, network, credentials, provider costs or
infrastructure changes. Rollback: revert feature merge; no migration.

## Opt-in actual loopback HTTP fixture observation (2026-10-29)

A separate credential-free demo exercises the already-reviewed real Python/Node
manifest pipeline and the existing local-only handoff/observation contracts
against an **owned, ephemeral HTTP fixture**, not the reviewed application:

```sh
python -m cloudforge.demo_loopback_observation --name my-api --target fixture-target --manifest ./requirements.txt --allow-loopback-fixture
```

The opt-in flag is mandatory. The module binds only `127.0.0.1` on an OS-assigned
ephemeral port and runs actual `HEAD /health` requests. It observes a controlled
fixture response sequence: HTTP 204 (readiness/liveness pass), HTTP 503 (both
fail), HTTP 204 (both pass after fixture restoration). The fixture is shut down
and its thread joined before returning. Output omits the port, elapsed timing,
raw manifest text and reviewer names; it includes the review's exact-source
binding and handoff request digests, and explicit false claims for authenticated
review, application execution, deployment, infrastructure mutation and recovery.

This is **measured fixture behavior**, not an authenticated operator, executed
user application, sandbox deployment, live service monitoring or controlled
production recovery. The demo synthesizes in-process reviewer approvals with
a plainly labeled fixture identity; those approvals are **not** independent
authorization. The source-bound artifact is a canonical fingerprint packet,
not runnable application bytes. Never use this demo's synthetic approvals to
authorize a real endpoint or infrastructure action.

**Reuse-first:** existing `review_application_manifests`, inspector/planner/IaC,
deployment handoff, local receipt, observation plan, and loopback HTTP collector;
Python 3.11 standard-library `http.server` and `threading`. No third-party
code/model copied or translated, new dependency, provider API, credential or
cloud cost. Compared existing fixture HTTP tests with a dedicated demo module:
the gap was an observable, reproducible composition starting from real selected
manifest bytes, not another HTTP transport implementation. Real app deployment
still needs an independently authorized isolated runtime with exact-source
revalidation, signed evidence and controlled rollback. Roll back this demo by
reverting its feature merge; it creates no persistent infrastructure or schema.

## Owned first-party application process demo (opt-in; not a sandbox)

The next demo-first step runs an **actual, fixed CloudForge-owned Python
application process** on an ephemeral 127.0.0.1 port. It reuses the real
manifest inspection -> provider-neutral review -> exact-target handoff and
local-only observation contracts. It measures real HEAD pass -> stopped
process/unknown -> restarted process/pass, then cleans up both child processes.

Run with a supported manifest from a Python 3.11 checkout:

`python -m cloudforge.demo_owned_reference_process --name my-api --target local-demo --manifest ./requirements.txt --allow-owned-reference-app`

This **does not execute the caller's application**. It starts only the fixed
first-party reference service, with a minimal child environment and temporary
working directory. A subprocess is **not an OS/container sandbox**; do not
pass untrusted code. The module source is SHA-256 checked across the demo,
but this is not an authenticated or atomic runtime attestation. The selected
manifest's source-review digest is preserved in the output. The local reviewer
identities are synthetic, not authenticated human approval.

Process termination/restart demonstrates actual observed failure and process
restoration, **not** deployment, infrastructure rollback, signed monitoring,
independently approved execution, or recovery of the user's application.
No external endpoint, cloud provider, credentials, infrastructure mutation,
Docker, or physical Mac is involved. This is a bounded stepping stone to
the independently approved isolated real-application sandbox demo.

**Reuse-first:** existing manifest review, planner, handoff, local receipt,
observation plan, loopback HTTP collector and Python 3.11 standard library.
No third-party code, dependencies, new license, provider cost or API key.
Rollback is reverting the feature merge; no persistent infrastructure or
database migration. The next gate is exact-source-bound, independently
authorized **user application** execution inside an OS-isolated sandbox with
signed evidence and controlled rollback. Demo readiness remains partial;
full product completion remains unverified.
