# Separately keyed loopback HEAD operator permit (fixture only)

This opt-in checkpoint adds a **short-lived, separately keyed** MAC permit to
the existing local-only HTTP HEAD -> signed evidence -> SQLite replay path.
`issue_loopback_operator_permit` binds the exact observation plan digest,
ordered numeric-loopback HEAD targets, source alias, source-key fingerprint,
validity window (at most 300 seconds) and a domain-separated operation string.
`verify_loopback_operator_permit` requires a **different** 32-128-byte operator
key from the observation signing key, and checks the exact bound values and
caller-supplied observation/current time before network or ledger I/O.
`collect_and_accept_operator_permitted_loopback_fixture_evidence` is the
opt-in entrypoint; the legacy fixture entrypoint remains unchanged.

**Trust boundary:** An HMAC demonstrates possession of the operator key,
**not** authenticated human approval, collector identity, trustworthy clock,
or legitimate live service health. A collector controlling both keys can forge
permits. Real use requires separate operator-key custody, an authenticated
operator decision and trusted clock, secure key distribution/revocation, and
separate runtime authorization. Never store keys in the permit or evidence.
The existing allowlist and numeric 127.0.0.1 restriction still apply; CI
contacts only ephemeral local fixture servers. No real infrastructure is
accessed or modified. This is not production monitoring, deployment or recovery.

## Reuse-first and validation

Inspected existing CloudForge `observation_http`, `observation_evidence`,
`observation_source_pin`, `observation_fixture_intake`, exact plan, tests and
deployment handoff. Reused Python 3.11 stdlib `hashlib`, `hmac.digest`,
`hmac.compare_digest`, `json`, and the existing target validation, signing
and durable replay contracts. No external code, model, translated algorithm,
dependency, runtime permission or license added. A third-party JWT/identity
SDK would add deployment and key-management scope without an authenticated
operator identity. References: https://docs.python.org/3.11/library/hmac.html
and https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
(conceptual guidance only, no source copied).

Synthetic tests cover exact permitted fixture HEAD+SQLite, forged/tampered
MAC/plan/target/source/key, expiry/future time, malformed validity windows,
role-key separation and no network or ledger I/O before rejection. Require
exact-head full Python 3.11 and infrastructure CI, guarded merge and merged-main
CI before software acceptance. Rollback is reverting the feature merge;
there is no persistent schema migration.
