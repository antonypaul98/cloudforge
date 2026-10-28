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
