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


## Invalid synthetic connection factory preflight (2026-10-29)

A missing or noncallable injected connection factory is now rejected *before*
the permitted HEAD fixture consumes its one-shot SQLite permit. The signed
HTTPS intake also rejects it before its read-only evidence replay preflight.
Previously, the lower-level fixture rejected such a factory only after permit
consumption, unnecessarily burning a valid sequence and leaving a possible
replay-gap diagnostic. These are configuration errors, not attempted probes.

The gate reuses the existing lower-level `callable(connection_factory)`
contract; no external code, dependencies, key service, provider, network
access, infrastructure change or migration. Six parameterized synthetic
regressions cover missing and noncallable factories in both entry points,
verify that invalid input never reaches permit consumption or ledger read,
and demonstrate that the same valid permit can subsequently be used with
a proper fake factory. Existing valid HEAD behavior is unchanged.

This does not guarantee that a callable factory is safe, honest, network-free
or successful. Once a callable factory passes the preflight, the permit is
still intentionally consumed before any fake probe, including when that probe
fails. The two SQLite transactions remain separate and not exactly-once.
Production requires independently authenticated operators/collectors,
protected keys, clock, endpoint/DNS policy and replay ledger, explicit
approval of any real endpoint, and runtime evidence. Revert the feature
merge to roll back; no data migration or real deployment is involved.
Acceptance requires exact-head PR CI, complete Python 3.11 and infrastructure
suites, guarded merge, merged-main CI and canonical checkpoint update.


## Exact permit-window timestamp for signed synthetic HTTPS samples

The signed HTTPS intake now rejects an `observed_at_unix` that predates
the MAC-verified runtime permit's `valid_from_unix`, even when the timestamp
would pass the ordinary evidence freshness limit. A non-integer timestamp
(including `bool`) is also rejected before SQLite preflight, permit
consumption or injected HEAD execution. The lower permit boundary is inclusive.
The runtime permit verifier already constrains caller-supplied `now_unix`
to the permit's upper bound; existing evidence verification still enforces
sample freshness and non-future timestamps.

Reuse-first: the existing `verify_loopback_operator_permit` already
applies the same inclusive timestamp relationship. The HTTPS composition
reuses that in-repository rule and Python's built-in integer checks; no
third-party code, language translation, dependency, provider API, license,
credentials or service cost is introduced. Four parameterized no-network
regressions verify pre-permit and malformed timestamps are rejected before
factory/ledger access, and the same permit succeeds at its valid lower
boundary. Require exact-head CI, guarded merge and merged-main CI before
acceptance.

This is **caller-supplied synthetic timestamp consistency only**, not a
trusted clock, independently authenticated operator or collector, verified
probe timestamp, live monitoring, deployment or recovery. Roll back by
reverting the feature merge; no migration or infrastructure mutation.


## Optional operator-key fingerprint preflight (2026-10-29)

The signed synthetic HTTPS intake accepts optional `operator_key_sha256`
and `require_operator_pin` arguments. The new pure verifier checks that the
operator HMAC key matches a strict lowercase SHA-256 fingerprint, and rejects
missing mandatory pins, invalid types, malformed digests and mismatches
before reading or creating the SQLite replay ledger or invoking an injected
HEAD factory. Existing calls without an operator pin remain compatible.
The existing runtime permit already rejects an operator key equal to the
collector/source key. Strict source and operator pins can now be composed.

**This is not independent operator authentication.** Both key and expected
fingerprint are still caller-supplied. A caller controlling both can forge
the check, omit the optional pin, invoke lower-level fixtures, or provide a
network-capable factory. A production trust root must provision the expected
operator fingerprint independently, authenticate operator and collector
workloads, protect key custody and clocks, enforce one protected replay
store, restrict egress to explicitly approved endpoints, and sign runtime
provenance. This checkpoint makes no production readiness claim.

Reuse-first: audited the existing runtime HEAD permit's distinct-key check,
the source-key pin/revocation policy, signed HTTPS intake and tests. Reused
Python 3.11 standard-library `hashlib.sha256` and `hmac.compare_digest`,
without copying external code or introducing a package, API, credential,
provider dependency, license obligation or service cost. Compared SPIFFE
workload X.509-SVID/mTLS identity and OpenID Connect issuer/audience/signature
verification as future independently rooted options; neither was imported
or configured because no authenticated runtime or trusted issuer is currently
provisioned. References:
https://spiffe.io/docs/latest/deploying/svids/ and
https://openid.net/specs/openid-connect-core-1_0.html .

Offline regression coverage includes valid combined operator/source pins,
malformed and mismatched pins, changed operator keys, direct helper invalid
inputs, and backwards-compatible opt-out. Require exact-head full Python
3.11 pytest plus infrastructure guards, guarded merge and merged-main CI
before acceptance. Rollback: revert the feature merge; no schema migration
or infrastructure mutation. Next milestone is an **independently provisioned
and authenticated** operator/collector runtime boundary, not more optional
fixture policy.
