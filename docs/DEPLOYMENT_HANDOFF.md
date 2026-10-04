# Deployment handoff foundation

The accepted inspection → deterministic IaC sequence is followed by deployment
in PROJECT_STATE.md. The preserved architecture in
`docs/recovery/CloudForge-source-11d1b93.zip` describes adapters consuming only
approved, validated plans. Archived implementation/acceptance claims are not
adopted. This checkpoint implements that prerequisite against the current core.

`prepare_deployment_request(plan, proposal, target_id)` validates the live plan
and compares the proposal's exact bytes, digest and format with canonical output.
It snapshots the artifact into an immutable request. Its digest binds the exact
plan, source provenance, document bytes, target identity, format and operation.
Target IDs are opaque, caller-supplied scope identifiers; they are never resolved
as URLs, paths, credentials or executable commands.

A human reviews that complete request. The integrating application authenticates
the human and constructs `DeploymentApproval(request.digest, approved_by)`.
`authorize_deployment_handoff` validates the inputs again and returns a
serializable immutable receipt only if approval matches exactly. Existing
PlanApproval does not approve a deployment target. Changing a target, artifact,
plan resource order or operation requires fresh approval. No boolean bypass.

This is an in-process integrity boundary, not authenticated authorization storage
or cryptographic proof of identity. Callers cannot treat a hand-constructed
receipt as trusted. No adapter, subprocess, network, deployment, readiness,
observation or recovery mechanism is included. `ready-for-adapter-review` never
means deployed. Real execution needs a separately scoped adapter checkpoint,
authenticated execution authorization and legitimate runtime acceptance evidence.

Acceptance: deterministic end-to-end receipts preserve provenance; tampered and
unsupported inputs fail closed; approvals cannot cross targets/artifacts/operation
or be reused after plan mutation; request/receipt snapshots are immutable. Tests
require no credentials, Docker, cloud account or external network.

Next checkpoint: design a bounded local deployment adapter with explicit target
configuration, exact artifact execution authorization and measured runtime
acceptance. The historical Docker adapter is reference material only; do not
blindly restore it or report its historical tests as current acceptance.
