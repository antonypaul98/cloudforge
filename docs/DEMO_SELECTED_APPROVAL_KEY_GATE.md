# Separate-key sandbox approval preflight (synthetic)

This bounded checkpoint reuses the existing exact-source operator permit,
operator key-pin validator and local SQLite replay gate. A distinct reviewer
key signs the **exact operator permit MAC** with a shorter validity window.
The reviewer key fingerprint must be pinned separately and cannot match the
operator key. A rejected reviewer receipt is checked before any ledger file
is created; valid permits remain one-time within an intact trusted ledger.

**Not human authentication:** possession of two caller-supplied keys is not
proof of an independent human decision. The original single-key consume API
remains available, and no actual executor is wired to either API. The caller
controls the keys, trusted pins, clock and ledger. A future trusted executor
must enforce this path, independently authenticate the reviewer and obtain a
recorded artifact-specific decision before selected application execution.

Reuse/provenance: only first-party CloudForge contracts and Python 3.11 stdlib
`hmac`, `hashlib`, `json`, and `dataclasses`. No external code copied, new
dependency, credentials, cloud provider, production resource or API cost.
Tests cover normal/replay, forged receipt, changed source/target, wrong sequence,
key separation, bad key/pin, time boundaries and forbidden network/process
entry points. Exact-head CI and protected merge remain mandatory.

Rollback is reverting this feature PR; no schema migration. This is an
authorization prerequisite, not selected application execution, signed health
observation, infrastructure deployment or rollback.

**Demo readiness: Partial. Full product completion: Unverified.**

## Verified feature-head and merged-main evidence, 2026-10-30

Feature [PR #139](https://github.com/antonypaul98/cloudforge/pull/139)
merged at `fbe1079c9342933a6794f8ed6b4dcc586a0c1e04` after exact head
`abfb9721114fc1f5c9acd1957dae2eeb8f40e3c2` passed
[push CI #41103582725](https://github.com/antonypaul98/cloudforge/actions/runs/41103582725)
and [PR CI #41103617032](https://github.com/antonypaul98/cloudforge/actions/runs/41103617032).
[Merged-main CI #41104455652](https://github.com/antonypaul98/cloudforge/actions/runs/41104455652)
passed. Python 3.11.17: 1,504 passed, 2 existing skips;
infrastructure: 33 run, 1 existing skip. The test logs, not a local
runtime, support this bounded synthetic acceptance. No external selected
application was executed. Canonical documentation PR has its own CI gate.
