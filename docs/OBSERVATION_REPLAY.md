# Durable observation replay guard (local SQLite)

`accept_observation_evidence_durably` is an opt-in, synchronous persistence
boundary for the already accepted in-memory observation evidence verifier.
It verifies exact plan/handoff/artifact/approval/receipt, collector alias,
HMAC and caller-supplied timestamp first, **before opening the ledger file**.
Then SQLite `BEGIN IMMEDIATE` and a conditional UPSERT atomically advance the
accepted sequence for each (plan SHA-256, source alias). A duplicate, lower
sequence, database lock/error or corrupted database fails closed.

The caller must provide an **absolute path** to a database file in a trusted,
operator-owned local directory. The directory must already exist. Provision
restrictive filesystem permissions, backups and retention externally. The ledger
contains only plan digests, source aliases and monotonic sequence numbers;
no HMAC keys, raw artifacts, samples or reviewer names are persisted. Do not
delete, restore an older backup, or copy a stale ledger while accepting samples:
rolling back the ledger can permit previously accepted sequences again.
Rotating a key under the same source alias must continue the sequence; use
a distinct alias for a deliberately independent counter.

The source key, authenticated collector identity, trusted time, operational
lifecycle, and actual measurement process are **not** established here.
The caller supplies `now_unix` and protects `source_key`. The module does not
execute probes, access a network, call providers, mutate infrastructure, claim
a deployment, establish service health, alert or recover. It does perform
**explicit local SQLite file I/O**. A successful return proves only envelope
verification plus atomic local replay-counter acceptance, not real observation.

## Reuse and external-code review

- Reuses `verify_observation_evidence` from CloudForge rather than duplicating
  HMAC or exact-authorization logic.
- Uses Python 3.11 standard-library `sqlite3`, `contextlib.closing` and
  parameterized SQL; no third-party code or dependency is copied or ported.
- Considered external Redis/PostgreSQL replay stores, but they require service
  credentials and operational setup and are unnecessary for this bounded
  single-host local checkpoint. SQLite supplies transactional compare-and-set
  semantics without external services or license additions.
- Python documentation: https://docs.python.org/3.11/library/sqlite3.html
  (consulted 2026-10-27). The UPSERT conditional sequence behavior is covered
  by repository tests rather than assumed from documentation.

## Acceptance and remaining work

Tests exercise durable reopen/replay, increasing sequence, independent plan
and source namespaces, invalid-MAC/stale rejection before I/O, concurrent
same-sequence acceptance (only one winner), corrupt database rejection, strict
absolute path input, and no network/shell/wall-clock access. Exact-head PR CI
and merged-main CI are required before marking this checkpoint accepted.

Not accepted: a live read-only collector, authenticated key provisioning,
trusted runtime measurements, multi-host distributed replay protection,
real deployment, service health, monitoring or recovery. A local ledger is
not a distributed consensus store and must not be shared across hosts.


## Canonical schema and counter-integrity guard (2026-10-27)

The replay store now checks the exact canonical SQLite table definition and
rejects unexpected triggers inside the same BEGIN IMMEDIATE transaction as the
conditional UPSERT. A lookalike TEXT counter can compare 9 > 10
lexicographically; an altered schema, missing CHECK constraint, trigger or
corrupt noninteger/out-of-range counter now fails closed. No automatic schema
migration is attempted. This uses the existing Python 3.11 sqlite3 module,
SQLite sqlite_master, and no external code or new dependencies.

Upstream references (reviewed 2026-10-27):
https://www.sqlite.org/schematab.html
https://docs.python.org/3.11/library/sqlite3.html

This is local corruption/tamper detection, not authenticated database ownership.
A privileged attacker can still replace or roll back a ledger backup. Collector
identity, trusted clocks, deployment, live monitoring and recovery are unproven.
