# Bounded local deployment adapter specification

This checkpoint follows the accepted deployment-handoff foundation. It defines
the safety and acceptance contract for a future local adapter. It does **not**
authorize cloud, provider, network, subprocess, container, shell, or filesystem
mutation and does not claim a deployment occurred.

## Required inputs

The adapter may consume only an accepted `DeploymentHandoff` whose exact request
digest still matches its embedded request. Before any runtime action, it must
derive a separate immutable execution request binding:

- the exact deployment-handoff request digest;
- the opaque target identity;
- the exact artifact bytes by SHA-256 digest;
- the adapter operation and format version.

A separately authenticated human must approve that exact execution-request
digest. The earlier plan approval and deployment-handoff approval are
insufficient. Changing target, artifact bytes, plan ordering, operation, format,
or handoff requires fresh execution approval.

## Fail-closed rules

The adapter must reject malformed or hand-constructed input types, mismatched
handoff/request digests, blank or control-character identities, unsupported
format versions, nonliteral approval values, stale approvals, and any request
whose exact artifact differs after review.

No boolean approval bypass is permitted. Approval identity authentication belongs
to the integrating application and must not be inferred from caller-controlled
text.

## Initial runtime boundary

The first implementation must remain local-only and deterministic. It must not
resolve opaque target IDs as URLs, paths, credentials, commands, provider names,
or executable configuration. It must not call providers, networks, shells,
subprocesses, containers, package managers, or cloud SDKs.

Until a later checkpoint has a legitimate runtime plus measured acceptance
evidence, successful authorization may mean only that the exact local execution
request passed the integrity boundary. It must keep
`infrastructure_mutated = false` and must never report deployed, healthy, ready,
observed, recovered, or equivalent infrastructure state.

## Regression acceptance

Tests must prove deterministic request/receipt serialization, immutable snapshots,
exact artifact binding, target isolation, operation/version isolation, fresh
approval after any mutation, rejection of prior plan/handoff approvals, rejection
of malformed identities and approval bypasses, and zero external side effects.

The suite must run without credentials, Docker, a cloud account, external
network, or provider tooling. Exact-head CI is required before merge; merged-main
CI must also pass. Runtime mutation, observation, failure simulation, recovery,
and real deployment acceptance remain later checkpoints.
