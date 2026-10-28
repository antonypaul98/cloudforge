# Fixture-only observation key and clock lifecycle regression

This checkpoint adds three tests to the existing signed observation evidence and
SQLite replay boundary. It introduces no new production collector, key manager,
clock source, dependency, network endpoint, service or infrastructure action.

## What the tests establish

1. **Same-source key rotation retains the counter.** A sample signed with the
   previous key is rejected when the verifier is configured with the replacement
   key. A sample signed with the replacement key cannot restart the already
   persisted sequence at 1. A fresh, higher sequence is accepted and persisted.
   The ledger remains keyed by exact observation-plan digest and source alias,
   not by HMAC key bytes.
2. **Clock anomalies fail closed.** A backwards caller clock, stale observation
   timestamp, or future observation timestamp rejects the envelope before the
   durable counter advances. A subsequent fresh, higher-sequence sample can
   still be accepted.
3. **The 63-bit sequence ceiling is terminal.** The largest supported positive
   sequence can be accepted once; an overflowing sequence is rejected at signing
   and an attempted restart is rejected by the durable ledger.

These tests reuse the existing `sign_observation_evidence`,
`verify_observation_evidence` and `accept_observation_evidence_durably`
contracts. They are credential-free and use temporary local SQLite fixtures.
No third-party implementation or translated algorithm is introduced.

## Reuse-first assessment and provenance

Existing CloudForge HMAC-SHA256 verification and conditional SQLite UPSERT
already implement the necessary semantics. Python 3.11 standard-library HMAC
and SQLite are sufficient. A cloud key vault, Redis, PostgreSQL, OpenTelemetry
or a new dependency would add operational, security, licensing or credential
requirements without establishing a trusted collector in this fixture-only
checkpoint. No third-party source was copied.

References consulted on 2026-10-27:

- https://docs.python.org/3.11/library/hmac.html
- https://sqlite.org/lang_upsert.html
- Existing CloudForge docs: `docs/OBSERVATION_EVIDENCE.md` and
  `docs/OBSERVATION_REPLAY.md`.

## Explicit limitations and acceptance

The tests **do not implement key rotation**, securely provision or revoke keys,
prove that a caller actually rotated a secret, establish a trusted clock, detect
a rolled-back SQLite backup, authenticate a real collector or prove service
health. The caller remains responsible for source identity, secure key lifecycle,
trusted clock and durable ledger integrity. Under a reused source alias, a
compromised old key remains dangerous if a caller reconfigures the verifier to
trust it; the tests only verify the supplied current key.

Acceptance requires an exact-head PR CI pass, guarded merge and merged-main CI.
No physical Mac or production hardware evidence is claimed.
