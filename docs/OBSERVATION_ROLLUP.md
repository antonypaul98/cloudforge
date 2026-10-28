# Verified observation sample rollup (synthetic, read-only)

`classify_verified_observation_samples` reuses CloudForge's existing
`verify_observation_evidence` before interpreting the ordered raw samples
from an exact observation plan. It returns only one of `fail`, `unknown`,
or `pass`:

- `fail` if any verified sample explicitly failed, even if another is unknown.
- `unknown` if no sample failed but at least one was unknown.
- `pass` only when every verified sample passed.

Malformed, forged, stale, replayed, wrong-source/key, changed-artifact or
changed-authorization evidence is rejected by the existing verifier before
any rollup result is returned. This function has no network, filesystem,
provider, clock, subprocess, database or infrastructure side effects. It
does not persist sequence counters, schedule observations or perform recovery.

## Reuse-first and provenance

Existing `ObservationEvidence`, `ObservationPlan` and
`verify_observation_evidence` contracts were inspected and reused rather
than introducing a second MAC verifier, schema, database, runtime collector
or monitoring SDK. The precedence rule is a small original in-repository
decision, not third-party copied or translated logic. Python 3.11 built-ins
are sufficient; no new dependencies, permissions, licenses or service costs.
External OpenTelemetry exporters and runtime SDKs would add operational and
identity surfaces without authenticating the current synthetic collector.

## Acceptance boundary

The regressions exercise all three outcomes, both fail/unknown orders,
tampered MAC and sample fields, stale/replayed/wrong-key evidence, changed
artifact and forbidden external I/O. The full Python 3.11 and infrastructure
suites must pass on the exact PR head and merged main before acceptance.

A `pass` result means **only** that the verified caller-supplied sample
outcomes all equal `pass`. The HMAC proves configured key possession, not
real probe execution, trusted time, independently authenticated collector
identity, actual service health, deployment or recovery. There is no live
service monitoring or physical device validation in this checkpoint.

## Optional source-key trust enforcement for rollup (2026-10-28)

The read-only classifier accepts the same optional caller-provided
`source_pin`, `require_source_pin` and `revoked_key_sha256` parameters as
the existing loopback fixture intake. After verifying the exact evidence MAC,
plan, source, freshness and caller-held sequence, it reuses
`verify_observation_source_policy` and `verify_observation_source_pin`
before returning any classification. A valid HMAC under an explicitly revoked
key cannot be classified as `pass`; strict mode rejects missing pins.
Default unpinned behavior is unchanged for existing synthetic callers.

**Reuse-first review:** The existing in-repository source pin, key-revocation
policy, evidence verifier and Python 3.11 standard library are sufficient.
A separate key registry, cloud KMS, SPIFFE/SPIRE, OpenTelemetry exporter or
new monitoring SDK would introduce credentials, operational cost and unverified
trust assumptions without authenticating this fixture. No third-party code,
algorithm, translation, dependency or license was added. This is a bounded
composition of existing contracts, not a new source of truth.

Regressions cover all three outcomes with strict pins, missing pins, revoked
keys, wrong source/plan/key/time, malformed trust policy, key rotation and
forbidden external I/O. CI must validate the exact PR head and merged main.

**Trust limitation:** The policy and pin are caller-supplied and optional.
This does not authenticate the configuration channel or collector, protect
against a caller deliberately disabling the policy, atomically persist replay
state, establish a trusted clock or attest live service health. Real runtime
monitoring, deployment and recovery are still outside acceptance.
