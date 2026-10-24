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

## Reserved Unicode noncharacters

The local authorization boundary rejects Unicode noncharacters (U+FDD0–U+FDEF and
all plane-ending U+FFFE/U+FFFF code points) in application, target and reviewer
identities. These code points are reserved for internal use and can be invisible
or inconsistently rendered. This does not reject ordinary Unicode letters or
internal ASCII spaces in application display names. It performs no execution.

## Review-visible resource metadata

Local execution authorization also rejects invisible controls, bidirectional
formatting, non-ASCII space separators and Unicode noncharacters in reviewed
resource reasons and string-valued properties (such as runtime and source).
Ordinary internal ASCII spaces and Unicode letters remain valid. This is an
additional local integrity check; it does not change the accepted handoff
renderer, authenticate an approver or authorize any infrastructure execution.

## Local-only receipt revalidation

`verify_local_execution_receipt(handoff, artifact, approval, receipt)` rechecks a
previously produced receipt against the exact handoff, artifact bytes and local
execution approval. It rejects altered status, target, digest, approver, format,
operation and nonliteral mutation flags. This is an in-process integrity check,
not proof of approver identity or an authenticated signature. It never runs a
provider, observes infrastructure or reports a deployment.


## Review metadata boundary whitespace

Local authorization rejects leading or trailing ASCII whitespace in resource
reasons, runtimes and source-provenance text. The earlier review-only handoff
can contain such values, but a local execution authorization must not treat
visually ambiguous field boundaries as accepted. Ordinary internal ASCII spaces
remain valid. This does not authenticate reviewers or execute infrastructure.

## Invisible variation marks in reviewed fields

The local-only execution authorization boundary also rejects the invisible
combining grapheme joiner (U+034F), Mongolian free variation selectors
(U+180B–U+180F), and Unicode variation selectors (U+FE00–U+FE0F and
U+E0100–U+E01EF) in application names, resource metadata, target IDs and
reviewer identities. These default-ignorable marks can make visually similar
reviewed values carry different approval digests. Ordinary Unicode letters,
internal ASCII spaces and combining accents remain permitted. This validation
is not Unicode confusable detection or authentication, and it performs no
runtime or infrastructure action.
