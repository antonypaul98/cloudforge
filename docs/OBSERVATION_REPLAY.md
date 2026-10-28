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

## Existing ledger file-type guard (2026-10-27)

Before SQLite opens a ledger, the durable verifier now checks an existing
final path component with Python standard-library `os.lstat` and `stat`.
It rejects symlinks (including dangling symlinks), directories and special
files, rather than following an alias or treating a non-file as a ledger.
The HMAC, exact authorization and freshness checks still run before this
filesystem metadata access. A missing file may be created in the caller's
pre-existing trusted directory. Tests verify rejection without modifying
a real ledger, dangling-link target creation, and pre-MAC I/O avoidance.

This is **best-effort path hygiene**, not a race-free file-open primitive.
Another process with write access to the ledger directory could replace
a path between `lstat` and `sqlite3.connect`. Parent-directory symlinks
are not resolved or prohibited. Operators must still own and protect the
entire directory and avoid untrusted concurrent writers. No claim is made
about tamper-proof storage, backup rollback prevention, authenticated
collector identity or live monitoring.

Reuse review: existing SQLite transactional verifier remains authoritative;
Python 3.11 `os.lstat` and `stat.S_ISREG` are sufficient for this narrow
pre-open guard. No third-party code or dependency was added.
References: https://docs.python.org/3.11/library/os.html#os.lstat and
https://docs.python.org/3.11/library/stat.html#stat.S_ISREG .


## Existing ledger hard-link alias safeguard (2026-10-28)

The final-component `os.lstat` guard now additionally requires exactly one
hard link for an existing regular SQLite ledger. Two filenames can otherwise
refer to the same inode even when neither is a symlink. This check rejects
both names once a second hard link exists, before SQLite opens the file or
advances the sequence. Parametrized fixture tests exercise both names and
confirm the stored counter remains unchanged.

This is a conservative, pre-open **best-effort** check, not atomic protection:
an untrusted process with directory write access can race the check, and parent
directory aliases, inode replacement, backup rollback and external collectors
remain outside this checkpoint. Existing ledger files on filesystems with
unavailable/unknown link counts fail closed. Operators must still protect the
entire ledger directory.

Reuse-first: extended the existing `os.lstat` inspection using Python 3.11
`os.stat_result.st_nlink`, without new packages, third-party source code,
network permissions or infrastructure changes. Compared with platform-specific
openat/O_NOFOLLOW and external stores, neither solves the existing
`sqlite3.connect(path)` race within this narrow change. Official reference:
https://docs.python.org/3.11/library/os.html#os.stat_result


## Ledger parent-path hygiene (fixture-only, 2026-10-28)

Before opening SQLite, the replay verifier now rejects noncanonical absolute
paths containing dot/parent traversal or repeated separators, and checks every
parent component with Python 3.11 standard-library `os.lstat`/`stat.S_ISDIR`.
Every parent must already be a real directory, not a symlink. A symlink to an
existing ledger directory and a dangling parent symlink both fail closed before
opening the ledger. An absent parent is not created automatically. The exact
authorization and evidence MAC are verified before filesystem inspection.

This reuses the existing file-type guard and Python standard library; no
third-party implementation, translated code, new dependency, credential,
network endpoint or infrastructure action is introduced. Compared with
`pathlib.resolve` (which follows links) and platform-specific `openat`
strategies (which cannot make the current `sqlite3.connect(path)` atomic),
`lstat` is a small, compatible best-effort guard.

This does **not** prevent a concurrent attacker from replacing parent paths
after the check, inode substitution, SQLite journal-file attacks, ledger
backup rollback, or a privileged writer changing the database. Trusted
operator-owned directories and external key/clock/collector provisioning
remain mandatory. Some operating systems use symlinked standard temporary
directories; such paths now intentionally fail closed until a real canonical
directory path is supplied. No Mac, live service, deployment, recovery or
production-monitoring acceptance is claimed.

References: https://docs.python.org/3.11/library/os.html#os.lstat ;
https://docs.python.org/3.11/library/os.path.html#os.path.normpath ;
https://docs.python.org/3.11/library/stat.html#stat.S_ISDIR .


## Reject unsafe ledger paths before fixture HEAD requests (2026-10-28)

The composed local fixture collector now reuses the durable replay ledger's
existing path checks **after exact authorization, source policy, source pin and
MAC/freshness preflight but before any HTTP HEAD request**. Known symlinked
files or parent directories, hard-linked ledger aliases, noncanonical paths
and missing parents fail closed without probing. The durable replay writer
repeats the same checks immediately before opening SQLite; this is deliberate
defense in depth, not a new trust boundary.

The standalone durable verifier retains its prior authorization-before-I/O
behavior. The existing unpinned synthetic fixture API and valid ledger paths
remain compatible. The change uses only existing CloudForge logic and Python
3.11 standard-library os/stat; no third-party code, package, cloud permission,
new network destination, real infrastructure or hardware is involved.

A metadata check cannot guarantee the path stays unchanged between preflight
and SQLite open. A duplicate sequence can still cause HEAD requests before
SQLite rejects the replay. Authenticated collectors, trusted clock/key
distribution, durable backup rollback prevention, real deployment and
recovery remain unimplemented. Full exact-head CI and merged-main CI are
required before acceptance.
