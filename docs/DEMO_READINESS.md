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


## Exact selected application source review (read-only, 2026-10-29)

A real caller-selected **single source file** can now be fingerprinted and
bound to the already-reviewed manifest, application, opaque target, and handoff
request. Supported roots are `app.py` with Python manifests and `server.js`
with Node `package.json`. This is a necessary input-provenance step toward
the original real-app sandbox demo, not a substitute for execution.

```sh
python -m cloudforge.demo_selected_artifact --name my-api --target sandbox-review --manifest ./requirements.txt --source ./app.py
```

The source is read at most 131,072 bytes using Python 3.11 standard-library
`os.open` with `O_NOFOLLOW`, bounded reads and `fstat` regular-file and
single-hardlink checks. If no-follow is unavailable, this tool fails closed.
It rejects invalid UTF-8, NUL, empty or oversized files, and mismatched
runtime/entrypoint. It prints only a versioned canonical SHA-256 binding,
source length, opaque identifiers and explicit non-execution flags; never
prints source or manifest text. Changed source, manifest or target invalidates
the binding. The review itself still uses the existing manifest inspector,
planner and handoff.

**Not a security sandbox:** Symlinked parent directories, filesystem races,
hardlink replacement, concurrent file writes, and untrusted privileged path
selection are not fully solved. A hash is not an authenticated signature,
immutable stored artifact, or execution permission. This step **does not**
execute the user's application, start a container, install dependencies,
contact an endpoint, mutate infrastructure, prove deployment, sign monitoring
evidence, or perform recovery. Do not pass the selected file to the existing
subprocess reference-app demo.

**Reuse/provenance:** Existing CloudForge `review_application_manifests`,
Python 3.11 `hashlib`, `json`, `os.open`, `os.fstat`, and `stat.S_ISREG`;
official semantics: https://docs.python.org/3.11/library/os.html.
No third-party code copied or translated, no new dependency, license, cloud
account, API cost, or provider permission. Compared adding an arbitrary-code
subprocess runner (unsafe without isolation) versus binding selected bytes
before execution; chose the fail-closed read-only bridge. Revert the feature
merge to roll back; no schema or external resource change.

**Next:** Materialize an immutable exact-source artifact and independently
authorize its use in a genuinely OS-isolated sandbox. Verify the selected
application's own health and controlled rollback with signed evidence. The
demo remains **partial**; full-product completion and dates remain unverified.


## Owned exact-byte first-party source in Linux namespaces — 2026-10-29 ET

[Feature PR #111](https://github.com/antonypaul98/cloudforge/pull/111)
reuses the accepted exact-byte package, source review binding and first-party
reference service. It runs only the **fixed CloudForge-owned** `app.py` in
private Linux user/mount/network/PID namespaces with a temporary tmpfs root,
read-only system mounts, chroot and private loopback. Actual HTTP HEAD
observation in a supported local Linux container produced
**running pass -> stopped unknown -> restarted pass**. The local test
reproduced the feature's namespace shell, observer and fixed service; it
was **not** a local full-repository suite.

Exact feature head `6fda3cc74746c58a2eb7fe61fe3eba4f29982a56`
passed [push CI #40983582804](https://github.com/antonypaul98/cloudforge/actions/runs/40983582804)
and [PR CI #40983605895](https://github.com/antonypaul98/cloudforge/actions/runs/40983605895).
Guarded feature merge `75f862594ae50520534e8edfbbffddac06a05f4a`
passed [merged-main CI #40983770702](https://github.com/antonypaul98/cloudforge/actions/runs/40983770702):
**1,392 pytest passed, 2 skipped**, infrastructure **18 passed, 1 skipped**,
Python 3.11.17. **Both real namespace integration tests skipped on GitHub's
runner** because required namespace prerequisites were unavailable; the CI
pass is not proof of real OS isolation there. Separate local Linux namespace
smoke did exercise the actual HEAD stop/restart path. No physical Mac test.

**DEMO READINESS: PARTIAL.** This is not user-selected application execution,
a hardened sandbox for untrusted code, independently authenticated approval,
signed monitoring, a real infrastructure deployment or infrastructure rollback.
The package hashes are self-consistency checks, not signatures. **FULL PRODUCT
COMPLETION: UNVERIFIED**; no percentage or delivery date. No external endpoint,
cloud provider, credentials, persistent infrastructure mutation, Work or Astra.
The connected GitHub integration was the writer; external worktree exclusivity
remains unverified. Reuse was first-party CloudForge code, Python stdlib and
existing Linux namespace tools; no third-party source copied or new dependency.
See [scope, limitations and rollback](DEMO_OWNED_NAMESPACE.md). Revert feature
merge to roll back; no migration.

**Next:** independently authenticated and explicitly approved user-selected
application execution in a hardened exact-source-pinned isolated runtime,
followed by signed real health evidence and controlled rollback. No real
infrastructure or external endpoint without artifact-scoped human approval.

## Selected-source rootless OCI sandbox review (2026-10-29, non-executing)

Feature [PR #115](https://github.com/antonypaul98/cloudforge/pull/115)
merged at `a3c3a36e14fc4f8e61e3dd5eeaad6bae8ed1859b`.
Its exact feature head `d5253730b6fa8e69912276f8fb1ddf942a283945`
passed push [CI #40994596795](https://github.com/antonypaul98/cloudforge/actions/runs/40994596795)
and PR [CI #40994613916](https://github.com/antonypaul98/cloudforge/actions/runs/40994613916).
Merged-main [CI #40994711112](https://github.com/antonypaul98/cloudforge/actions/runs/40994711112)
passed: **1,412 Python tests passed, 2 existing namespace tests skipped**;
infrastructure **18 passed, 1 skipped** (Python 3.11.17).

The new `prepare_selected_sandbox_review` composes exact-byte verified
selected Python/Node packages with a digest-pinned OCI image reference and
fixed rootless isolation requirements. It returns a deterministic
source/target/image-bound proposal digest, with raw source and manifest bytes
omitted. See [scope and limitations](SELECTED_SANDBOX_REVIEW.md).

**No selected application was executed.** The proposal is not an independent
authorization, trusted image, hardened sandbox, signed observation or rollback.
The existing Linux namespace runtime tests remain skipped on GitHub CI;
the earlier local fixed first-party fixture receipt does not prove this new
selected-application runtime. Demo readiness remains **PARTIAL** and full
product completion remains **UNVERIFIED**. Next: independently authenticated
artifact-specific approval, actual rootless sandbox execution of a controlled
selected app, signed measured health and controlled rollback. No real
infrastructure change without explicit approval.

## Selected-source keyed sandbox permit preflight (2026-10-29, non-executing)

Feature [PR #117](https://github.com/antonypaul98/cloudforge/pull/117)
merged at `5bc82ab7d3d84a1d59932c374c81684eb5673ca8`.
Its exact feature head `a197893df36c2d71171640b73a243bab587e9d64`
passed [push CI #41000502656](https://github.com/antonypaul98/cloudforge/actions/runs/41000502656)
and [PR CI #41000524529](https://github.com/antonypaul98/cloudforge/actions/runs/41000524529).
[Feature merged-main CI #41000640475](https://github.com/antonypaul98/cloudforge/actions/runs/41000640475)
also passed: **1,450 Python tests passed, 2 existing Linux namespace tests skipped**;
infrastructure **18 passed, 1 skipped**, Python 3.11.17.

The new short-lived, operator-key HMAC policy envelope is bound to the
reverified exact selected Python/Node source package, manifest, target, image
and sequence. A separately provisioned key fingerprint is mandatory.
Tests cover source/manifest/target/image changes, key mismatch, MAC tampering,
expiry, sequence mismatch, strict shape, redaction and no process/network I/O.
See [trust boundaries](SELECTED_EXECUTION_PERMIT.md). Reuse was first-party
CloudForge plus Python stdlib, with no imported third-party source.

**No selected application executed.** This is a stateless key-possession
check, not authenticated human approval, a one-time replay ledger, trusted
image, sandbox attestation, signed health, real deployment or rollback.
Two namespace integration tests still skip in GitHub CI. Demo readiness
remains **PARTIAL** and full product completion **UNVERIFIED**.
Next: independent artifact-scoped approval, durable one-shot replay gate,
actual isolated selected-app execution, measured signed health and controlled
rollback. No real infrastructure mutation without explicit approval.
