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

A receipt whose embedded execution request no longer hashes to its claimed
request digest is rejected before artifact hashing when the supplied approval
names that claim. This is a bounded integrity check, not identity authentication.

No boolean approval bypass is permitted. Approval identity authentication belongs
to the integrating application and must not be inferred from caller-controlled
text.

Malformed caller-supplied execution-request fields (format, operation, digest
shapes and target identity) are rejected before parsing the reviewed handoff.
This preflight limits unnecessary work; exact input binding and fresh execution
approval remain mandatory. It does not authenticate the reviewer.

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

## Blank Unicode filler safeguards

The local review boundary also rejects U+115F (Hangul choseong filler),
U+1160 (Hangul jungseong filler), U+2800 (Braille pattern blank), U+3164
(Hangul filler), and U+FFA0 (halfwidth Hangul filler). These characters can
appear blank while changing exact reviewed application, resource, target, or
reviewer values. This narrow check preserves ordinary Korean text, combining
accents and other legitimate Unicode identifiers; it does not claim complete
visual-confusable detection or authenticated reviewer identity.


## Local receipt JSON export is fail-closed for deployment claims

LocalExecutionReceipt.to_json() rejects altered status values and any
infrastructure_mutated value other than literal False (including integer
zero). A local-only receipt cannot be serialized as deployed, healthy or
mutated. This narrow output invariant is **not** an authenticated signature:
consumers must still call verify_local_execution_receipt with the original
handoff, exact artifact bytes and local approval before trusting a receipt.
No provider or infrastructure is contacted.

## Receipt export internal consistency

Before JSON export, a local-only receipt now checks its nested request type,
supported format and operation, literal reviewer and target text, lowercase
SHA-256 field shapes, and the receipt digest against its own request. This
prevents obviously malformed or internally inconsistent receipts from being
exported even when their status still says `authorized-local-only`.
It cannot prove that a self-consistent receipt was issued by a trusted actor:
consumers must still revalidate the exact handoff, artifact bytes and approval.
No infrastructure execution or authenticated identity is implied.


## Canonical receipt JSON revalidation

The function verify_local_execution_receipt_json(handoff, artifact, approval,
receipt_json) accepts only bounded (at most 16,384 characters), exact canonical
JSON exported by LocalExecutionReceipt.to_json(). It rejects duplicate/extra
fields, noncanonical whitespace, malformed types, altered status and mutation
flags, then rechecks the reconstructed receipt against the original handoff,
exact artifact bytes and separate execution approval. No parser output is trusted
solely because its JSON is internally consistent. This is deterministic,
in-process verification, **not** a signature, reviewer authentication,
deployment, observation, or recovery mechanism.

## Export/verification size consistency

The local-only receipt exporter and canonical JSON verifier share a 16,384-
character maximum for the serialized ASCII JSON representation. Export rejects
otherwise self-consistent receipts whose target or reviewer identity expands the
JSON beyond this limit, including Unicode escape expansion. A receipt produced
by the exporter must not be too large for its own verifier. This is a bounded
serialization safeguard, not a runtime or infrastructure deployment capability.

## Early rejection of obviously oversized receipt identities

The receipt exporter rejects target and reviewer strings longer than the
16,384-character canonical ASCII JSON ceiling **before** calculating a request
digest. This avoids unnecessary hashing of oversized caller-supplied identities.
The existing serialized-size check remains authoritative for escaped Unicode
and JSON overhead. This is an in-process resource bound, not authentication or
infrastructure execution.

## Redacted local-only authorization audit event

`export_local_execution_audit_event(handoff, artifact, approval, receipt)`
revalidates the receipt against the exact original handoff, artifact bytes and
separate execution approval before producing deterministic canonical ASCII JSON.
The event contains only format version, request digest, SHA-256 of the canonical
full receipt, the fixed `authorized-local-only` status, and literal
`infrastructure_mutated: false`. It deliberately omits the raw target ID,
reviewer names, artifact bytes and handoff document. The request digest remains
linkable metadata, so audit events should still receive appropriate access
controls. Receipt hashing detects changes only when compared against trusted
reference evidence; it is **not** a signature, authenticated approval, actual
infrastructure observation, deployment, or recovery. No filesystem, network,
provider, subprocess or infrastructure operation is performed.

## Canonical redacted audit event verification

`verify_local_execution_audit_event(handoff, artifact, approval, receipt,
audit_json)` checks an at-most-1,024-character audit string against a freshly
regenerated canonical redacted event. The original handoff, exact artifact
bytes, execution approval and receipt are revalidated first. Modified,
duplicate-key, extra-field, noncanonical or oversized event strings fail closed;
non-string inputs are rejected before revalidation. A valid event is only
evidence that matches these caller-supplied inputs. It does **not** authenticate
an approver, sign evidence, attest to external storage, or prove any actual
deployment, observation or recovery. No provider, filesystem, network or
subprocess action is performed.

## Bounded local handoff document parsing

Before parsing a caller-supplied deployment handoff document, the local-only
adapter rejects documents longer than 65,536 Python string characters. This
prevents unnecessarily parsing oversized reviewed text, including documents
whose JSON would ultimately fail canonical IaC validation. It is a separate
local execution-authorization safeguard: it does not change the previously
accepted review-only handoff, authenticate an approver, or execute infrastructure.

## Authorization and canonical export consistency

A successful `authorize_local_execution()` now checks that its newly issued
receipt can be exported as bounded canonical JSON before returning it. This
prevents the authorization API from reporting success for oversized target or
reviewer identities (including Unicode escape expansion) that the canonical
receipt verifier could never accept. Oversized requests fail closed without
any provider, filesystem, network, subprocess or infrastructure operation.
This is an in-process representation guarantee, not identity authentication,
cryptographic signing, deployment, observation or recovery.

## Preflight resource bound for oversized authorization identities

Before parsing the handoff document or calculating a new local request digest,
authorization rejects target IDs and execution reviewer strings whose Python
character length exceeds the 16,384-character canonical receipt ceiling.
This avoids unnecessary parsing and hashing for values that cannot be exported.
The canonical serialized-size check still handles JSON overhead and escaped
Unicode; shorter malformed values follow the existing validation paths.
This is not reviewer authentication, deployment, observation or recovery.

## Early rejection of structurally invalid execution approvals

Local authorization rejects a missing/wrong approval object, malformed reviewer
identity, or non-lowercase-hex/non-64-character approval digest before parsing
the handoff document. A correctly shaped digest still must match the exact
execution request after full handoff and artifact revalidation. This avoids
unnecessary processing for obviously invalid approvals; it neither authenticates
a reviewer nor relaxes approval, infrastructure or runtime restrictions.

## Early handoff identity preflight

Before parsing a potentially large handoff document, local request preparation
rejects invalid or over-16,384-character target and handoff-reviewer identities.
This prevents avoidable JSON parsing of inputs that cannot pass local review.
The original handoff digest, exact artifact, plan provenance and separate fresh
execution approval remain mandatory. This does not authenticate a reviewer,
execute infrastructure, observe deployment or perform recovery.

## Exact binary input preflight

The local request preparation and authorization boundaries reject non-`bytes`
artifacts before parsing or revalidating the reviewed handoff. Mutable
`bytearray`, `memoryview`, text, booleans and missing artifacts cannot enter
the digest/approval path. This is a local resource and input-integrity guard,
not a size limit on legitimate artifact bytes or infrastructure execution.

## Early rejection of ineligible handoff outcomes

Local request preparation rejects a handoff whose status is not exactly
`ready-for-adapter-review` or whose `infrastructure_mutated` flag is not
literal `False` **before** parsing its reviewed JSON document. Seven
parameterized regressions cover altered status and forged mutation flags,
including integer zero (which compares equal to `False` in Python).
This is a deterministic fail-closed preflight, not authenticated approval,
execution, observation, or recovery.

## Early exact-handoff digest rejection

Before parsing reviewed IaC JSON, local request preparation rejects a malformed
handoff request digest (wrong type, noncanonical lowercase SHA-256 shape) or a
digest that differs from the exact bounded handoff request. This avoids parsing
untrusted document text for an already-invalid handoff. It does not authenticate
reviewers, authorize provider actions, mutate infrastructure, observe or recover
anything. Nine synthetic pytest parameter cases cover malformed and stale digests.

## Early cross-input binding preflight

Local authorization now rejects a caller-supplied execution request whose opaque
`target_id` or exact `handoff_digest` differs from the supplied handoff before
parsing the reviewed IaC document. Two parameterized synthetic regressions
assert this early rejection. Structural request validation still runs first;
full handoff provenance, artifact-byte equality and fresh execution approval
remain mandatory. This is not reviewer authentication or infrastructure execution.

## Early exact-artifact binding preflight

Local execution authorization compares the caller-supplied artifact SHA-256
with the actual immutable artifact bytes before parsing the reviewed IaC
handoff document. A changed artifact or a stale request artifact digest fails
closed, even when the caller supplies a matching self-constructed approval
digest. The full handoff and approval revalidation remains mandatory for
matching bytes. This preflight neither authenticates the reviewer nor executes
infrastructure.


## Early stale execution-approval rejection

Local authorization compares the structurally valid execution approval digest
with the bounded caller-supplied local execution request digest **before**
parsing the reviewed IaC handoff document. A stale digest or a request changed
after approval fails closed without unnecessary document parsing. Matching
caller-supplied digests still require complete handoff/artifact verification;
this preflight does not authenticate the claimed approver, execute a provider,
mutate infrastructure, observe a deployment, or perform recovery.


## Early exact handoff receipt binding rejection

Local execution authorization now rejects a stale full-handoff SHA-256 binding
before parsing the reviewed IaC document when the handoff has bounded scalar
fields. Changing the handoff's claimed reviewer without changing its embedded
request, or supplying a stale handoff receipt digest with a matching
caller-constructed execution approval, fails closed. Malformed or oversized
handoffs continue through existing full validation rather than bypassing it.
Two synthetic regressions check early rejection. This is local integrity
validation, not authenticated reviewer proof or infrastructure execution.

## Bounded handoff scalar hashing

Local authorization rejects oversized handoff reviewer, plan digest, operation,
request digest, and status strings before computing the full-handoff receipt
hash. Each is bounded to 16,384 characters; the separately bounded reviewed
IaC document retains its existing 65,536-character limit. Five synthetic
regressions verify that oversized scalar fields cannot reach the handoff hash.
This is a local resource-integrity safeguard, not authenticated approval or
infrastructure execution.

## Early malformed-document rejection before artifact hashing

Local authorization now rejects a non-text or greater-than-65,536-character
handoff document before hashing the exact artifact bytes. Three synthetic
regressions cover oversized text, missing text, and binary document input while
forbidding SHA-256 calls. This is a resource-use guard only: the full canonical
handoff, provenance, artifact and separate approval checks still apply. It does
not read a filesystem, run a provider, mutate infrastructure, or authenticate
a reviewer.

## Early ineligible-handoff rejection before artifact hashing

Local authorization rejects a handoff whose status is not exactly
`ready-for-adapter-review` or whose infrastructure-mutation flag is not
literal `False` before hashing artifact bytes. Six synthetic regression
cases cover forged status and mutation values, including integer zero.
The complete canonical handoff, exact artifact and fresh execution approval
checks remain mandatory for eligible inputs. This is a local resource guard,
not authenticated approval, infrastructure execution, observation or recovery.

## Malformed handoff metadata before artifact hashing

Local authorization rejects unsupported or nonliteral handoff format versions,
operations other than `deployment-handoff`, and malformed 64-character lowercase
SHA-256 plan digests before hashing potentially large artifact bytes. Eight
synthetic regression cases guard this early failure path. Full canonical
provenance validation remains mandatory; this does not authenticate an approver,
execute infrastructure, or prove runtime acceptance.

## Fail-fast canonical audit-event preflight

The redacted audit-event verifier rejects malformed JSON, noncanonical encoding,
wrong format/status/mutation flags, extra or duplicate fields, and malformed
lowercase SHA-256 fields **before** regenerating evidence from the original
handoff, artifact and approval. Ten synthetic regressions assert that invalid
audit strings cannot trigger receipt revalidation. Structurally valid but
forged or stale audit evidence still requires full exact-input verification.
This is not a signature, authenticated approval, deployment or recovery.

## Early stale canonical audit-binding rejection

After canonical audit-event shape validation, the verifier rejects a stale
request digest or receipt SHA-256 before recomputing the full audit event from
the original handoff, artifact and approval. Two parameterized synthetic
regressions forbid original-input revalidation for those stale bindings.
Matching digests are not proof of authenticated approval: full exact-input
revalidation still follows. No provider execution, infrastructure mutation,
observation, recovery or physical acceptance is claimed.

## Early stale handoff-request digest rejection

For a structurally bounded local-only handoff, authorization now rejects a
handoff whose stored request digest no longer matches its exact reviewed
request **before hashing the artifact bytes**. Two parameterized synthetic
regressions cover changed plan-digest and document fields while forbidding
artifact hashing. A matching digest is not reviewer authentication or
sufficient authorization: canonical IaC, artifact, receipt and execution
approval revalidation still follow. No infrastructure is executed.

## Early stale authorization rejection before artifact hashing

When a caller-supplied execution-approval digest matches the exact request,
the local-only adapter checks the bounded handoff receipt binding before hashing
potentially large artifact bytes. A changed claimed handoff reviewer or forged
handoff receipt digest fails closed before artifact hashing. Two synthetic
regressions assert this ordering. When approval is stale, artifact mismatches
retain their prior error precedence. Matching metadata still requires exact artifact
SHA-256, canonical handoff validation, and full receipt serialization checks.
This is resource-efficient integrity validation, not authenticated approval,
deployment, infrastructure observation, or recovery.


## Early blank-document and ambiguous-reviewer rejection

Local-only authorization rejects an empty or whitespace-only reviewed handoff
document and malformed claimed handoff reviewer text before hashing artifact
bytes. Nine synthetic regression cases cover blank documents and reviewer
whitespace, invisible controls, and missing identities, including a
self-consistent forged handoff receipt binding. Matching metadata is not
authenticated reviewer proof: exact canonical handoff, artifact and fresh
execution approval validation remain mandatory. No provider or infrastructure
action is performed.

## Early malformed handoff-container rejection

Local-only authorization rejects a caller-supplied handoff or nested request
that is not the exact expected dataclass type before hashing artifact bytes.
Seven synthetic regression cases prohibit artifact hashing on these invalid
container shapes. Valid handoffs still require complete canonical provenance,
exact artifact binding and fresh execution approval. This does not authenticate
a reviewer, access a provider or mutate infrastructure.

## Reject forged receipt outcomes before artifact hashing

Verification now rejects a local-only receipt that claims deployment, an
ineligible status, or infrastructure mutation before hashing artifact bytes or
revalidating the handoff. Four synthetic regressions guard the early failure.
Valid receipts still undergo exact artifact, handoff, approval and provenance
revalidation. This is not reviewer authentication or real deployment evidence.

## Early forged receipt-reviewer rejection

When a supplied execution approval references the same request digest as a
local-only receipt, receipt verification rejects a different claimed reviewer
before hashing artifact bytes. Stale or missing approvals still follow the
ordinary approval-required path. This is a bounded fail-fast integrity check,
not authentication of either caller-supplied reviewer identity; full exact-input
revalidation remains mandatory for matching identities. Three synthetic cases
cover mismatched, whitespace-suffixed and bidirectional-control reviewer names.

## Credential-free synthetic end-to-end demonstration

After installing the package locally (`python -m pip install -e .`), run
`python -m cloudforge.synthetic_demo`. It creates only in-memory synthetic
plan, handoff and execution approvals, checks the exact immutable artifact,
verifies canonical receipt and redacted audit evidence, then asserts that an
altered artifact and a forged `recovered` audit status are rejected. The
output is deterministic JSON with only SHA-256 digests, local-only status and
explicit flags that authenticated review, deployment, observation and recovery
have **not** occurred. Reviewer names, target identity and artifact bytes are
not printed. No credentials, provider, network, shell or physical device are
needed. Two integration tests also fail if this demo attempts network or shell
entry points. This is synthetic integration evidence, not real-world deployment
acceptance or approval authentication.

## Synthetic receipt-reviewer and cross-target rejection demo

The credential-free in-memory smoke demo now also exercises two fail-closed
integrity cases: a canonical receipt with a forged claimed execution reviewer,
and an otherwise self-consistent execution approval for a different opaque
target. Both must be rejected. The demo reports only redacted boolean rejection
outcomes and does not authenticate any human, contact a provider, execute
infrastructure, observe deployment, or perform recovery.

## Synthetic forged infrastructure-mutation audit rejection

The credential-free in-memory demo also changes the canonical audit event's
`infrastructure_mutated` flag from literal `false` to `true` and verifies
that the local-only audit verifier rejects this forged claim. The public demo
reports only a redacted rejection boolean. It does not authenticate an approver,
mutate infrastructure, observe a deployment or perform recovery.
