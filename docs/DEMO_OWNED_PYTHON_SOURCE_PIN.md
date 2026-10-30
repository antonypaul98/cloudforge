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
