# Read-only synthetic HTTPS replay-gap diagnostic

The inspect_synthetic_https_replay_gap function compares the last consumed
synthetic runtime permit sequence for an exact (source_id, runtime_request_sha256)
with the last accepted synthetic observation evidence sequence for an exact
(plan_sha256, source_id) in one caller-supplied local SQLite file. It returns
only two counters and a permit_ahead signal. A consumed permit ahead of the
evidence counter **may** mean a crash or failure between the two separate
transactions. The diagnostic **never** reissues a permit, resets a counter,
retries a probe, opens a network connection or mutates infrastructure.

This is a *possible gap*, not a definitive recovery decision. The permit and
evidence tables have different key scopes, and one evidence counter may cover
other requests. Equality, evidence ahead, or no gap **cannot prove** that a
particular probe executed or its evidence was signed. A missing, empty,
corrupt or path-unsafe ledger fails closed rather than reporting health.
A file containing only the permit table is inspectable to expose the
interrupted two-stage intake. The diagnostic cannot establish actual service
health, independent operator/collector identity or trusted runtime provenance.

## Reuse-first and compatibility

Reuses CloudForge's existing observation_replay path and canonical schema
checks, observation_permit_replay schema check, and observation source/digest
validation, plus Python 3.11 standard-library sqlite3 read-only URI mode and
dataclasses. Compared a new recovery store or an external queue, but neither
is justified for this small, no-I/O fixture inspection. No third-party code,
translation, dependency, credentials, cloud cost, new schema, or changed public
fixture API. Official reference: https://docs.python.org/3.11/library/sqlite3.html
and https://www.sqlite.org/uri.html .

Synthetic tests cover permit-only crash gap, monotonic/equal/advanced counters,
read-only file integrity, missing and empty ledger, malformed identifiers,
corrupt schemas/triggers/counters, symlink aliases and forbidden socket access.
Full exact-head Python 3.11 CI and merged-main CI are required before acceptance.

## Safety and rollback

The ledger path, plan/request digest and source alias are caller-controlled;
this diagnostic authenticates none of them. SQLite mode=ro prevents normal
database writes but path preflight is not a race-free openat boundary, and
SQLite may interact with auxiliary journal files. A privileged actor can
replace/roll back a ledger. The diagnostic does not attempt automated recovery:
a consumed permit must remain consumed even if evidence is absent. Only an
independently authorized operator should decide whether a new, higher sequence
is appropriate in a future trusted collector. No real endpoint, Mac/device,
provider or infrastructure is accessed. Rollback is reverting the feature
merge; no migration or production files are involved.


## Concurrent writer snapshot safeguard

The read-only diagnostic explicitly starts one deferred SQLite read transaction
after enabling query-only mode, so the table inventory, schema checks and both
counter reads share the same database snapshot. Without this, separate implicit
SELECT transactions could mix a permit value from before a concurrent commit
with evidence from after it, masking or manufacturing a gap. This reuses SQLite's
documented transaction/snapshot behavior; no external code or dependency is
introduced. Official sources: https://www.sqlite.org/isolation.html and
https://www.sqlite.org/lang_transaction.html .

Two deterministic WAL-mode regressions inject a concurrent evidence counter
advance and a new evidence-table creation between the permit and evidence
reads. The first diagnostic sees the earlier consistent snapshot, while a new
inspection sees the committed change. This does not make the caller-selected
ledger authentic, protect it against replacement/rollback, or prove a probe
ran. The diagnostic remains read-only and does not retry or recover permits.
Rollback: revert this feature commit; no schema or deployment migration.
