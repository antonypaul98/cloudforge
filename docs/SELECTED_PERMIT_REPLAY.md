# Durable local admission for selected-source sandbox permits (non-executing)

This checkpoint adds `consume_selected_sandbox_permit`, a local SQLite
at-most-once gate for the existing exact-source, target, image and
operator-key-bound policy permit. It **first** re-verifies the exact selected
application package, source review binding, target, image, MAC, operator key
fingerprint, sequence and trusted caller-supplied time. Only then does it open
the explicitly supplied local ledger.

One `BEGIN IMMEDIATE` SQLite transaction validates the exact expected table
schema and absence of table triggers, then advances the sequence only if it is
strictly greater than the last consumed sequence for the same operator-key
fingerprint and proposal digest. A second use of the same permit fails closed,
including across processes using the same ledger. A changed proposal has a
separate counter. A downstream failure does not refund a consumed sequence.

## Reuse-first and compatibility

Reuses the accepted `verify_selected_sandbox_permit` contract, the existing
CloudForge replay-ledger path preflight, and the SQLite transaction/schema
pattern in `observation_permit_replay.py`. No third-party source was copied,
translated or added. Python 3.11 standard-library `sqlite3` is used:
https://docs.python.org/3.11/library/sqlite3.html

The pure `verify_selected_sandbox_permit` API remains stateless and unchanged.
The new opt-in admission API adds a **separate** SQLite table and file, never
changes the observation permit ledger or consumes its counters. Tests cover
replay, increasing sequences, changed source scope, malformed MAC/source before
file I/O, concurrent admission, malformed schema, triggers and unsafe paths.

## Trust boundary and rollback

This is **not** independently authenticated human approval, a signed health
observation, a hardened container sandbox, deployment or rollback. The operator
key, clock, ledger directory and ledger contents remain caller-controlled.
The path preflight is not an atomic no-follow open; symlink races, file restore,
database copying, and rollback of the ledger remain outside this guarantee.
SQLite provides at-most-once admission within one intact trusted ledger, not
exactly-once runtime execution or global one-time authorization.

The gate performs only explicitly requested local SQLite file I/O. It does not
execute selected code, launch containers, call cloud providers, use credentials,
open network sockets, or modify real infrastructure. No execution adapter is
wired to this function. Do not enable any external action on this basis alone.

Rollback the code by reverting its feature merge. Any local ledger created by
an integrating caller is not automatically deleted or reset; resetting it could
permit replay. Require exact-head Python 3.11 full pytest and infrastructure
guards on PR, guarded merge, merged-main CI and separate canonical acceptance.
Demo readiness remains partial; full-product completion is unverified.
