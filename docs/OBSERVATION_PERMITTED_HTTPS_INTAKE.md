# Signed permitted HTTPS fixture evidence (synthetic only)

This opt-in seam composes existing CloudForge components in order:
exact artifact/receipt/plan/target/A+AAAA pinset and operator-key permit
verification; remaining caller-clock budget; signed all-unknown evidence
freshness preflight; read-only evidence replay preflight; atomic SQLite
permit consumption; injected fake HEAD probes; HMAC signing of returned
samples; and durable evidence replay acceptance. The same explicit SQLite
file holds independent permit and observation tables.

The code is **not a live collector or an authorization service**.
Caller-controlled operator and source keys, aliases, DNS, clock, endpoint
allowlist, SQLite file and connection factory are not independently trusted.
The fake factory is injectable and is not a sandbox. No production service
may be contacted through this fixture. A valid HMAC proves key possession,
not operator identity, measurement authenticity, deployment, or health.

## Reuse-first and compatibility

Inspected existing `observation_permitted_https_fixture.py`,
`observation_fixture_intake.py`, `observation_evidence.py`,
`observation_replay.py`, `observation_permit_replay.py` and tests.
Reused their public typed contracts and Python 3.11 standard-library
HMAC/SQLite; no copied third-party implementation, language port, new
package, external service, credential, cloud cost or schema migration.
The existing fixture and intake APIs remain unchanged. Official contracts:
https://docs.python.org/3.11/library/sqlite3.html and
https://docs.python.org/3.11/library/hmac.html .

Regressions check exact success, signed envelope verification and privacy,
duplicate rejection before injected HEAD, invalid MAC/freshness/budget/path
before I/O, corrupt evidence schema, concurrent duplicate admission,
unknown-on-failure, and monotonic next sequence. Full exact-head PR CI,
infrastructure checks and merged-main CI are mandatory for acceptance.

## Failure, trust and rollback

A permit is consumed before probes. If a fake probe fails, the signed
outcome is `unknown` and both counters can advance. If the process crashes
between permit consumption and evidence acceptance, the permit stays
consumed but evidence is absent; this is **not exactly-once** execution.
The evidence preflight is not an atomic lock, though final SQLite updates
are transactional. Separate tables in one file are not one transaction.
A second ledger, restored backup, forged alias, compromised caller,
network-capable factory, or direct ungated fixture can bypass these
synthetic safeguards.

Next production gate: independently authenticated operator and collector
identity, protected key/clock/DNS/endpoint policy, a privileged single-ledger
execution boundary, exact human approval of a read-only endpoint, and
signed runtime measurements. Deployment and recovery require their own
explicit approvals. No real DNS, endpoint, provider, physical Mac or
infrastructure mutation was performed.

Rollback is revert of the feature merge. New synthetic SQLite files are
disposable test artifacts only; do not remove production or unknown files.


## Optional source-key pin and revocation preflight (2026-10-29)

The signed synthetic HTTPS intake now reuses the existing loopback-fixture
`verify_observation_source_policy` and `verify_observation_source_pin`
contracts. Optional `source_pin`, `require_source_pin` and
`revoked_key_sha256` arguments bind the exact observation plan, source alias,
source-key fingerprint, caller-provided observation/current time window, and
an explicit revoked-key set. The policy is checked after exact HEAD permit
validation but **before** SQLite replay preflight, permit consumption or any
injected connection factory. Missing strict pins, revoked keys, malformed
policy, changed source/plan/key and expired/future pin windows fail closed.

This is an opt-in compatibility-preserving addition to the signed intake;
the lower-level permitted fixture and old unpinned callers still exist. A
caller can omit the policy, change its trust inputs or bypass the intake.
Nothing here authenticates the operator or collector, securely distributes
keys, trusts DNS/clock/ledger, authorizes a real endpoint, or creates an
isolated network sandbox. The new regression cases cover valid strict mode,
12 invalid/malformed/boundary policies rejected before any factory or ledger
creation, and key rotation requiring a new pin without resetting counters.

Reuse/provenance: audited the existing loopback intake, source policy, pin
verifier, HTTPS permit/intake and their tests. Reused existing CloudForge
Python 3.11 code and standard-library SHA-256, HMAC and dataclasses; no
external code, translation, package, provider, credentials or cost. Compared
reusing the existing strict policy with inventing a new HTTPS-only trust
schema; reused the former to avoid divergent semantics. Relevant existing
reference: [source-pin contract](OBSERVATION_SOURCE_PIN.md).
Validation requires exact-head Python 3.11 complete suite, infrastructure
guards, guarded merge and merged-main CI. Rollback: revert the feature merge;
no migration or infrastructure change. Next production gate remains
independently authenticated operator/collector identities and protected
key/clock/endpoint/replay execution boundary, followed by separately approved
read-only service monitoring.
