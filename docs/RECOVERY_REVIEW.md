# Deterministic recovery review proposal (synthetic, read-only)

The provider-neutral propose_recovery_review API turns a bounded window of
already signed observation samples into a **non-executing** review proposal.
It reuses the existing exact-artifact/approval/plan/source HMAC verifier,
optional source-key pin/revocation policy, contiguous sequence and claimed
minimum polling cadence, and the per-probe failure thresholds. Any invalid
envelope fails the whole proposal. A failure streak at threshold recommends
manual investigation; an unknown latest probe yields insufficient evidence
unless another probe already crossed its threshold. No trigger in the supplied
window is **not** evidence of a healthy service.

The immutable proposal binds the canonical observation plan and complete
canonical evidence window by SHA-256, records the last sequence, affected
probe kinds, and an explicitly non-executable action. Canonical JSON excludes
artifact bytes, reviewer names, raw target IDs, source IDs and source keys.
The digests are linkable metadata, not anonymization or signatures. Forged
status, action, mutation, recovery or deployment claims cannot be serialized
through the proposal's exporter. Callers must recompute the proposal from
verified inputs; a hand-constructed JSON record is not trusted evidence.

## Reuse-first and external implementation comparison

Inspected existing CloudForge observation_plan, observation_evidence,
observation_rollup, observation_thresholds, source pin/policy and their tests.
Reused their typed interfaces and Python 3.11 standard-library dataclasses,
hashlib and json. No copied external implementation, translated algorithm,
dependency, license, credentials, API call or service cost was added.

Considered Prometheus Alertmanager's grouping/routing/inhibition/silencing
(https://prometheus.io/docs/alerting/latest/alertmanager/) and OpenTelemetry
signal collection (https://opentelemetry.io/docs/concepts/signals/). Those
systems address real alert transport/telemetry, which is outside this pure
fixture and would add deployment and security surfaces without solving
independent collector authentication. No code was imported from them.

## Trust, validation and rollback

This feature does not authenticate a human or collector, trust keys or clocks,
collect a real probe, trigger an alert, execute rollback, mutate infrastructure,
or prove recovery. Caller-supplied signed samples can be forged by whoever
controls the source key. The evidence window is bounded to 1-10 envelopes,
with no durable historical inference. This is a **review proposal only**.

Offline regressions cover threshold crossing, unknowns, no-trigger,
determinism, privacy, source revocation, tampering, sequence gaps, forged
execution claims and forbidden network, shell, SQLite and clock I/O.
Require exact-head Python 3.11 full pytest and infrastructure guard CI,
guarded PR merge, merged-main CI and separate canonical checkpoint acceptance.
Rollback is a revert of the feature merge; no schema, network or infrastructure
change. Production work still requires independently authenticated operator
and collector identities, trusted key/clock/endpoint policy, protected replay
execution and explicit human approval before any real endpoint or mutation.
