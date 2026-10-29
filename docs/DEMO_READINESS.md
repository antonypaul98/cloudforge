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
