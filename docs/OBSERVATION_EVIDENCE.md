# Bounded observation evidence intake (in-memory only)

This checkpoint adds an HMAC-SHA256 envelope for externally supplied probe samples.
It does **not** run probes, contact a provider, deploy, read a live target, claim
service health, perform recovery or authenticate a human reviewer.

## Contract

`sign_observation_evidence` constructs a deterministic envelope from an existing
`ObservationPlan`, an opaque collector alias, a caller-supplied Unix timestamp,
a positive sequence number and one sample per planned probe. Each sample has a
`startup`, `readiness` or `liveness` kind, an outcome `pass`, `fail` or
`unknown`, and bounded elapsed milliseconds. The HMAC covers the exact plan's
canonical SHA-256 digest, collector alias, timestamp, sequence and ordered samples.

`verify_observation_evidence` first revalidates the original handoff, exact
artifact, local execution approval and receipt against the observation plan.
It then validates the envelope shape, ordered probe kinds, configured collector
alias, HMAC using `hmac.compare_digest`, bounded age and strictly increasing
sequence. The caller supplies `now_unix`, `max_age_seconds` (1–300),
`last_sequence`, and a separately provisioned 32–128-byte key. No wall-clock
or network call is made. Boolean outcomes are rejected; `unknown` is distinct
from success. A successful verifier return means only that this envelope passed
its configured checks, not that any probe actually ran or a service is healthy.

The integrating application must provision and protect the source key, establish
the collector's real identity, trust its measurement process and clock, and
**atomically persist** a monotonic `last_sequence` per (plan, source). This
module is stateless and cannot prevent cross-process replay without that external
state. A stolen key, dishonest collector, compromised clock, missing durable
counter or key reuse can invalidate the evidence's real-world meaning. Never
log keys or treat synthetic fixtures as production observations.

## Reuse-first and provenance

- Reuses CloudForge's `verify_observation_plan`, canonical `to_json` format,
  exact-artifact receipt binding and existing provider-neutral probe types.
- Uses Python 3.11 standard-library `hmac.digest(..., "sha256")` and
  `hmac.compare_digest`; see
  https://docs.python.org/3.11/library/hmac.html (accessed 2026-10-27).
  No third-party source code or algorithms were pasted or translated.
- Considered OpenTelemetry and Kubernetes runtime libraries, but neither can
  establish the current repository's missing collector identity or safe target
  configuration. Adding them now would add dependencies and scope without
  solving the trust boundary. This slice has no new dependency, service cost,
  runtime permissions or license burden beyond the Python standard library.
- Python 3.11 is the CI target. MAC fields use exact lower-case hex and
  canonical ASCII JSON; sample ordering is bound to the existing proposal.

## Acceptance and explicit non-acceptance

Tests cover deterministic signing, altered fields, wrong source/key, changed
artifact/target/approval, stale/future timestamps, replay counters, invalid
types, duplicate/out-of-order probes, redacted output and forbidden network,
subprocess and clock calls. Exact-head PR CI and merged-main CI are required
before this checkpoint is accepted.

This is an evidence **intake boundary**, not a live read-only observation
runtime. No real infrastructure, endpoint, secret store, alerting, rollback,
authenticated collector or physical hardware was accessed or validated.
