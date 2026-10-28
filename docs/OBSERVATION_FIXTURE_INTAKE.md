# Bounded fixture HEAD-to-evidence integration

This optional checkpoint composes existing CloudForge modules. It runs at most
three explicit numeric 127.0.0.1 HTTP HEAD probes, signs their raw samples with
a caller-supplied source key, and accepts the resulting HMAC envelope only if the
existing local SQLite replay ledger atomically advances the sequence. It does
**not** deploy, monitor a production service, authenticate a collector, prove
service health, or recover infrastructure.

## Interface and trust boundary

The public function collect_and_accept_loopback_fixture_evidence takes the
existing handoff, artifact, approval, receipt, plan, targets, plus explicit
allowed_targets, source_id, source_key, observed_at_unix, now_unix, sequence,
max_age_seconds and ledger_path keyword arguments. It returns an
ObservationEvidence envelope only after durable acceptance. Existing schemas
and serialized formats are unchanged.

The caller must independently provision and protect:

- the exact (kind, host, port, path) allowlist and separately authorized target;
- a 32-128-byte secret key, unique trusted source alias and source-key rotation;
- the observation timestamp, trusted current clock and increasing sequence;
- an absolute SQLite file in a protected, pre-existing local directory.

The adapter validates ledger-path shape, full target allowlist, source/key,
clock/age/sequence and exact plan/artifact/approval/receipt **before any HEAD
request**. It reuses the public HMAC verifier for preflight with an in-memory
all-unknown sample envelope that is neither exported nor persisted. The existing
HEAD collector revalidates authorization and allowlist again. Only the actual
HEAD results are signed and submitted to the existing durable verifier.

A duplicate sequence may still issue HEAD requests before the transactional
ledger rejects it. A corrupt/unavailable ledger also may fail after the probes;
the function does not promise exactly-once probe execution. It never emits an
accepted envelope if durable verification fails. No background polling,
scheduling, retries, cloud/provider APIs, DNS, shell or credential discovery
are added. Tests exercise only temporary loopback HTTP fixture servers.

Signing in the same caller-controlled process **does not authenticate** who
collected the samples. A stolen key, untrusted caller, false clock, rollback of
the SQLite database, or service that changes state on HEAD invalidates any
production trust assumption. The caller must not interpret HTTP 2xx as
independently verified readiness or a deployed service. The returned evidence
does not contain a deployment/health/recovery attestation.

## Reuse-first and external-code review

Existing implementation reused without copying or translating third-party code:

- observation_http._validate_targets and collect_loopback_http_samples
  (loopback allowlist, HEAD-only transport);
- sign_observation_evidence and verify_observation_evidence
  (canonical exact-plan-bound HMAC-SHA256, freshness and source validation);
- accept_observation_evidence_durably (transactional SQLite replay guard).

The private target validator is reused within the same package to avoid
duplicating its exact fail-closed semantics. Future refactoring must preserve
both callers and the existing test contract. Python 3.11 standard library
http.client, hmac and sqlite3 suffice. Compared with HTTPX/requests,
OpenTelemetry exporters, Redis and external secret managers, adding them now
would increase dependency, licensing, operational, auth and network surfaces
without solving source authentication. No external source code, model,
algorithm or translated implementation is introduced; no new package or
service cost is required.

Relevant upstream contracts:

- https://docs.python.org/3.11/library/http.client.html
- https://docs.python.org/3.11/library/hmac.html
- https://www.sqlite.org/lang_upsert.html

## Acceptance and limitations

Regression tests cover ephemeral-loopback HEAD 204/503/302 behavior,
signed evidence with exact-plan verification, durable persistence and
increasing/replayed sequence, refused connection, invalid source/key/time/path,
unsafe or reordered targets, changed artifact rejection before I/O, and
redacted evidence. The existing suite additionally covers concurrent ledger
acceptance, HMAC tampering and strict HTTP target bounds.

Only exact-head PR CI and merged-main CI can establish this checkpoint's
repository acceptance. Neither CI nor local fixture testing is evidence of
production collector identity, key management, trusted time, durable backup
safety, real deployment, service health, recovery, rollback or physical Mac
acceptance. Those remain separate future checkpoints.

## Read-only replay preflight before HEAD (2026-10-28)

After validating authorization, source trust policy, MAC, freshness and targets,
the fixture adapter now reads an existing SQLite replay ledger in `mode=ro`
before issuing HEAD. Known duplicate sequences, corrupted counters, altered
schemas and unreadable databases fail before probing. Missing or empty valid
SQLite files still initialize through the existing durable writer after probes.
URI escaping handles reserved filename characters.

This is **not** an atomic reservation or exactly-once guarantee. Concurrent
writers may advance the ledger after preflight; the existing `BEGIN IMMEDIATE`
write transaction remains authoritative. Path checks are not race-free and
SQLite may use auxiliary files. No collector authentication, production
monitoring, deployment or recovery is established.

Reuse-first: the existing schema validator and replay ledger plus Python 3.11
`sqlite3`, `urllib.parse.quote` and `contextlib.closing` were reused. No
third-party source code, dependency, license, permissions or service cost was
added. Official API references (not copied implementations):
https://docs.python.org/3.11/library/sqlite3.html#how-to-work-with-sqlite-uris
and https://www.sqlite.org/uri.html .

New synthetic tests cover duplicate rejection, corrupted DB/counter/schema,
empty database initialization and reserved URI characters. Full exact-head
and merged-main CI remain required for acceptance.
