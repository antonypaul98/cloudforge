# Verified observation failure-threshold window (synthetic, read-only)

`evaluate_verified_observation_thresholds` evaluates a **bounded, caller-supplied**
tuple of 1–10 signed observation envelopes for an exact CloudForge observation
plan. It reuses the existing `classify_verified_observation_samples` verification
boundary for **every** envelope: exact artifact, approval, plan, source, HMAC,
freshness, replay context, and optional source pin and key revocation policy.

The first sequence must be greater than caller-provided `last_sequence`;
subsequent sequences must be contiguous, and timestamps cannot move backward.
A `fail` sample increments that probe's current consecutive-failure count.
`pass` or `unknown` resets the proven-failure streak to zero. The returned
immutable per-probe record contains the streak, the existing plan's
`failure_threshold`, a threshold-reached boolean and latest raw outcome.
No result is emitted if any envelope fails validation. The function neither
persists a counter nor triggers alerts, probes, remediation or recovery.

**Meaning:** `threshold_reached=True` proves only that the supplied and
verified envelopes contain enough consecutive explicit `fail` values in
this exact window. `False` is not a healthy-service or safe-deployment
assertion. The caller may omit earlier history, and this function cannot
attest real probe execution, collector identity, key custody, clock origin,
durable replay state or actual service health. It does not enforce polling
cadence; `interval_seconds` remains a proposal, not a measured schedule.

## Reuse-first / compatibility gate

Inspected `ObservationPlan`, `ObservationEvidence`, existing HMAC/freshness
verification, source-key policy and sample rollup. Reused those exact
contracts and the already validated per-probe `failure_threshold`; no
schema, signature, caller permission, network surface or existing function
was modified. Compared with Prometheus Alertmanager and OpenTelemetry
collection/aggregation, an external SDK would add runtime, deployment,
credential, maintenance and license surfaces without establishing an
independently authenticated source in this offline checkpoint. Python 3.11
standard-library `dataclasses` and built-ins suffice. No external code,
algorithm or model was copied, translated or added as a dependency.

Reference material (design context, not copied implementation):
- https://prometheus.io/docs/alerting/latest/alertmanager/
- https://opentelemetry.io/docs/concepts/signals/metrics/
- Existing repository `docs/OBSERVATION_ROLLUP.md` and
  `docs/OBSERVATION_SOURCE_PIN.md`.

## Validation and limits

Synthetic regressions cover threshold crossing, pass/unknown streak breaks,
noninitial sequence windows, missing or duplicate sequences, time reversal,
tampering, stale/wrong-key/wrong-source evidence, changed artifact, strict
pins/revocation, bounded input and forbidden external I/O. Full exact-head
Python 3.11 and infrastructure CI, guarded PR merge and merged-main CI
are required before this is accepted as a **fixture-only** checkpoint.

**Not accepted:** actual service monitoring, independent collector
authentication, trusted clocks/keys, distributed replay, scheduling, alerting,
production deployment, rollback or infrastructure recovery. No physical Mac,
cloud service or real infrastructure is contacted.
