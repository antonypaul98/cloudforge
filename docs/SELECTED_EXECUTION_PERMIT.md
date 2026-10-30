# Selected-source sandbox operator-key permit (non-executing)

This bounded checkpoint adds `issue_selected_sandbox_permit` and
`verify_selected_sandbox_permit` for a previously verified selected Python
or Node source package. Both re-derive the source/manifest/target/image-bound
`prepare_selected_sandbox_review` proposal. The short-lived HMAC-SHA256
envelope binds its digest, a monotonically increasing caller-supplied sequence,
a maximum 300-second validity interval and a separately pinned operator key.

The key and its expected SHA-256 fingerprint must come from independent trusted
configuration. The integrating application must authenticate the operator,
secure the key and clock, atomically consume the sequence in a durable ledger,
verify an approved image and isolated runtime, and obtain explicit
artifact-scoped approval before any execution. **This module does none of
those operations.** A matching MAC proves only possession of the configured
key, not human identity or permission to deploy.

No source is executed, no network request is made, and no container, file,
database, cloud resource or infrastructure is modified. The returned permit
contains digests, sequence and time bounds, not source, manifest text or
credentials. Tests intentionally show that verifying the same permit twice
succeeds; this is NOT a one-time authorization mechanism. A future executor
must fail closed unless it has a separately trusted replay ledger.

## Reuse-first and compatibility

Reuses first-party `prepare_selected_sandbox_review` and
`verify_observation_operator_key_pin`, Python 3.11 standard-library
`dataclasses`, `hashlib`, `hmac` and `json`. No copied third-party
code, translated algorithm, new package, credential, provider SDK or paid
service. This deliberately keeps the selected-source verification contract
and its error handling unchanged.

The domain-separated canonical HMAC envelope is not interoperable with the
existing HTTPS HEAD permit: the operation and proposal identity are different.
The permit is not accepted by the observation collector or by any execution
adapter. See `docs/SELECTED_SANDBOX_REVIEW.md` for runtime constraints and
provenance, including the official Podman and OCI references.

## Acceptance and rollback

Run exact-head Python 3.11 full pytest and infrastructure guard suite on
push and PR; require guarded merge and successful merged-main CI. Regression
coverage includes Python and Node, changed source/manifest/target/image,
independent key pin, altered MAC, malformed fields, clock and sequence
boundaries, redaction and absence of network/process calls. Revert the feature
merge to roll back. No persistent state or migration is introduced.

**Demo readiness remains partial** until a controlled selected app actually
executes in a verified isolated runtime under independent authorization and
produces signed health plus controlled rollback evidence. **Full product
completion remains unverified.** No physical Mac, Work/Astra or real
infrastructure acceptance is claimed.
