# Optional observation source/key pin (fixture-only)

The local HEAD-to-HMAC-to-SQLite fixture intake accepts an optional
`ObservationSourcePin`. It binds a caller-provisioned source alias, the exact
observation-plan SHA-256, the SHA-256 fingerprint of a 32–128-byte source key,
and a short inclusive Unix-time validity window (maximum 24 hours).
`verify_observation_source_pin` rejects a mismatched source, plan, key,
malformed digest or validity window **before any HTTP request or ledger I/O**.

The pin must be obtained through a **separately trusted operator configuration
channel**. Deriving it from the same untrusted key or sample being verified
would make the check circular and ineffective. The existing unpinned API remains
supported for backwards-compatible synthetic fixtures; operators must explicitly
pass `source_pin` to enable this additional preflight. Neither the key nor
its fingerprint is written to the replay ledger or exported in evidence.

A rotation requires a newly trusted pin and new key. The existing durable
counter still belongs to the same (plan digest, source alias) and **must not**
reset on key rotation. The validity window is checked against both the
caller-supplied observation time and caller-supplied current time. It is **not**
a trusted clock, revocation service, identity attestation or authenticated
collector. An attacker controlling the caller configuration, key, clock or
ledger can defeat assumptions outside this module.

## Reuse-first and compatibility review

- Reuses the existing exact-plan canonical `to_json()` serialization, HMAC
  observation verifier and SQLite sequence ledger. No schema, authorization,
  probe target, network or infrastructure behavior changes when the optional
  pin is absent.
- Python 3.11 standard-library `hashlib.sha256`, `hmac.compare_digest`
  and frozen `dataclasses` are sufficient. No external code was copied,
  translated or imported, and no new dependency, license or service cost is
  introduced.
- Considered key vaults, cloud IAM, SPIFFE/SPIRE and certificate identity,
  but none can be safely configured or validated from this synthetic local
  runtime. Adding them would imply unverified identity and deployment.
- References: https://docs.python.org/3.11/library/hashlib.html ,
  https://docs.python.org/3.11/library/hmac.html ,
  https://spiffe.io/docs/latest/spiffe-about/overview/ .
  These are design references, not copied source.

## Acceptance and non-claims

Regression tests cover valid pins, malformed and changed aliases/digests,
invalid time bounds, key substitution before network/ledger I/O and key
rotation retaining the existing SQLite replay sequence. Exact-head Python
3.11 full-suite and infrastructure CI, guarded PR merge, and merged-main CI
are required for acceptance.

No real collector, key distribution, secure revocation, independently trusted
clock, hardware attestation, live monitoring, deployment or recovery has been
implemented or tested. No physical Mac or cloud resource is accessed.


## Optional strict pin and key-revocation preflight (fixture-only, 2026-10-28)

The fixture intake also accepts require_source_pin=True and an immutable
revoked_key_sha256 tuple of at most 64 distinct lowercase SHA-256 fingerprints.
With strict mode, omitting source_pin fails before HTTP or ledger I/O. A
nonempty revocation list also requires a pin. The configured key's fingerprint
is compared with the list before collection; a match fails closed. Malformed
types, duplicates and fingerprints are rejected. An unrelated revoked
fingerprint does not block a valid pinned key. Key rotation continues to use
the existing (plan, source) SQLite sequence without resetting it.

These settings are caller-provisioned, not retrieved from an authenticated
revocation service. A caller able to remove the policy, alter its denylist,
replace a trusted pin or use the old unpinned API can bypass this opt-in guard.
No runtime collector identity, trusted distribution, revocation propagation,
trusted clock, rollback defense or real service health is established.

Reuse review: the existing source pin and replay verifier remain unchanged.
Python 3.11 stdlib SHA-256 and constant-time digest comparison are sufficient
for this bounded fixture policy; no external code, SDK, model, dependency or
provider API is introduced. Considered SPIFFE/SPIRE workload identity and
cloud KMS/secret managers, but these need deployment and identity trust that
cannot be validated by the current local fixture. References:
https://docs.python.org/3.11/library/hashlib.html and
https://docs.python.org/3.11/library/hmac.html and
https://spiffe.io/docs/latest/spiffe-about/overview/ .

Acceptance requires exact-head complete Python 3.11 CI, infrastructure guards,
protected merge and merged-main CI. Isolated policy-only smoke tests are not
a substitute for full repository or real-service validation.
