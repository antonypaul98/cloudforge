# Provider-neutral observation proposal (planning only)

This checkpoint adds an immutable, deterministic observation *proposal* bound to an
existing exact-artifact local authorization receipt. It never executes a probe,
connects to a provider, deploys infrastructure, or claims a service is healthy.
`status="proposed-only"`, `deployment_observed=false`,
`infrastructure_mutated=false`, and `recovery_performed=false` are mandatory.

`prepare_observation_plan(handoff, artifact, approval, receipt, probes)` reuses
`verify_local_execution_receipt` to recheck the original plan/handoff/target,
artifact bytes and local-only approval before constructing the proposal. The
proposal contains only the request digest, receipt digest, and bounded probe
configuration. It does not export raw artifacts, target IDs, reviewer names,
credentials, endpoints or commands. `verify_observation_plan` rederives it from
the exact inputs; a JSON proposal by itself is not trusted evidence.

The proposed probe kinds are `startup`, `readiness` and `liveness`, with distinct
meanings. Both readiness and liveness are required, and startup is optional.
Each kind appears at most once. Intervals must be 5–300 seconds, timeouts 1 to
interval seconds, and failure thresholds 1–10. Values are integers, not booleans.
The limits are bounded local design choices, not imported Kubernetes defaults.
There is no address, transport or provider-specific check implementation yet.

## Reuse and compatibility decision

- Reused existing CloudForge `LocalExecutionReceipt`, exact-input verifier and
  canonical SHA-256 receipt JSON; no new dependency, network or cloud SDK.
- Consulted Kubernetes' documented startup/readiness/liveness separation:
  https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
  The **conceptual distinctions only** inform this proposal. No Kubernetes code,
  manifest, schema, configuration or third-party algorithm is copied or ported.
- OpenTelemetry and Kubernetes runtime libraries are not integrated: the current
  repository has no authenticated runtime/target, and introducing one would
  exceed this safe planning-only checkpoint. The standard-library-only module
  remains provider-neutral, Python >=3.11 and license-independent.

## Acceptance and remaining gates

Regression tests require deterministic canonical JSON, exact authorization
binding, readiness/liveness distinction, optional startup, bounded timing,
rejection of malformed/duplicate probe kinds and forged status/digest claims,
changed-artifact/target/approval rejection, and no network or subprocess use.
Exact PR-head and merged-main CI must pass before accepting this checkpoint.

**Not accepted:** actual deployment, authenticated human approval, executing
health checks, trusted observation collection, freshness/identity verification,
alerting, rollback or recovery. Those need separate adapters, independently
validated runtime evidence, safe failure behavior and explicit approval for
consequential infrastructure changes.
