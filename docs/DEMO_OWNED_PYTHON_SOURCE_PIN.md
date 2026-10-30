# First-party Python OCI fixture exact-source pin

The disposable GitHub runner's real rootless OCI fixture is fixed to the checked-in
`scripts/fixtures/owned_python_health_app.py` source at SHA-256
`af7b20dd3705b4cfe4c40cc0a84de490f553a246e392e808136a0c829c6d1af6`. The workflow now rejects changed bytes before creating
a selected-source package, staging a build context or invoking Podman build.
The Python infrastructure guard verifies the pin against the checked-in
fixture and checks ordering and removal of the digest guard. A changed fixture
requires a separately reviewed workflow pin update.

**Scope:** This prevents accidental or unreviewed source drift when the fixed
first-party CI demo runs. A contributor able to modify both the workflow and
its tests can also change the pin, so GitHub branch protections and independent
code review remain necessary. SHA-256 is not a signature or independent
attestation. The runner still executes only CloudForge's fixed first-party
fixture, not an external selected application. No independent human identity,
artifact-scoped deployment approval, signed external health, production
infrastructure mutation or infrastructure rollback is established.

Reuse/provenance: existing CloudForge workflow and Python 3.11 stdlib
`hashlib.sha256`; no external source or algorithm copied, dependency,
license change, credential, provider API or cost. Rollback is revert of the
feature PR. Exact-head product and real OCI CI, guarded merge, merged-main CI
and canonical acceptance are required; results must be recorded separately.
Demo readiness remains partial; full-product completion is unverified.

## Verified feature CI and guarded merge, 2026-10-30

[Feature PR #144](https://github.com/antonypaul98/cloudforge/pull/144)
merged at `12e0d378a90cd43916fb2b91b13fa7ec76e4ce17`. Exact feature head `7b37bf02b8d3a52ca5480eacca017c122af322f1` passed
[push product CI #41120020922](https://github.com/antonypaul98/cloudforge/actions/runs/41120020922),
[PR product CI #41120049902](https://github.com/antonypaul98/cloudforge/actions/runs/41120049902), and
[real rootless OCI PR CI #41120049929](https://github.com/antonypaul98/cloudforge/actions/runs/41120049929).
[Merged-main CI #41120188415](https://github.com/antonypaul98/cloudforge/actions/runs/41120188415)
succeeded. Python 3.11.17: 1,510 pytest passed, 2 existing skips;
infrastructure 35 run, 1 skipped. The actual OCI runner reported source
SHA-256 `af7b20dd3705b4cfe4c40cc0a84de490f553a246e392e808136a0c829c6d1af6`
and successful fixed-fixture health, restart, SIGKILL recovery and cleanup.
Normal SIGTERM stop escalated to SIGKILL, so graceful shutdown is not verified.
Canonical acceptance documentation still needs its own exact-head CI.
