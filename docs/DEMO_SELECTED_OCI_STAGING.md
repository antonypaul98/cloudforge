# Selected-source ephemeral OCI build-context staging (review-only)

This checkpoint connects the existing canonical, exact-byte Python/Node source
package verifier to a private temporary filesystem context. The new
`stage_verified_selected_source` context manager verifies caller-pinned
package SHA-256, source-review binding and target **before** creating a
temporary directory. It writes only the verified root `app.py` or `server.js`
and its verified root manifests, rechecks the written bytes, and removes the
directory on normal exit and Python exceptions.

## Acceptance and reuse

The regression tests cover Python/Node exact-byte round trips, private file
modes, wrong target, changed package bytes, cleanup on normal/exception/I/O
failure, and no subprocess or network use. The stage does not install manifest
dependencies. Reuse is limited to first-party
`verify_selected_source_package` and Python 3.11 standard-library
`tempfile.TemporaryDirectory`, `os.open` exclusive/no-follow flags and
`hashlib`. No external source is copied or new runtime dependency added.
See [Python 3.11 tempfile](https://docs.python.org/3.11/library/tempfile.html)
for the temporary-directory creation/cleanup contract.

## Explicit limits

Source and manifest bytes may contain credentials; never log, publish or upload
the staging directory. Caller-provided expected digests are **not** independently
authenticated approval. The private directory is not an immutable artifact,
runtime sandbox or guarantee against a same-user attacker, and process SIGKILL
may prevent cleanup. No selected code is executed, no OCI image is built, no
operator authenticated, no real health signed and no infrastructure deployed
or rolled back. This staging step is a direct prerequisite for a future
disposable-runner, source-pinned selected-application OCI trial; it does not
itself establish that trial.

**Demo readiness: Partial. Full product completion: Unverified.**
Next: connect a fixed, first-party selected Python source fixture to a trusted
offline Python OCI runtime in disposable CI, with independently measured health,
cleanup and separate artifact-specific approval before any external execution.


## Point-in-time pre-build staging verification (2026-10-31)

The fixed first-party Python OCI workflow now invokes
`verify_staged_selected_source(staged)` after private staging and before
writing the Containerfile or starting the image build. It uses directory-fd
and `O_NOFOLLOW` reads, requires only the exact staged source/manifest
filenames, rejects symlinks/nonregular files, and rehashes each staged file
against the original verified package metadata. Tests cover Python/Node,
changed bytes, missing/extra files, symlinks and directory substitutions.

This is a **bounded pre-build consistency safeguard**, not an immutable
build context or a TOCTOU-free security boundary. The caller can still
mutate staged files after verification; the OCI workflow remains limited to
a fixed CloudForge-owned source fixture. It does not independently authenticate
a human, authorize selected external code, sign health evidence or roll back
infrastructure. Reuses existing first-party staging metadata and Python 3.11
standard-library `os`, `stat`, `hashlib`; no third-party code, new dependency,
provider API, production infrastructure or secrets. Revert the feature PR to
roll back. Exact-head product and real OCI CI plus guarded merge and merged-main
CI are required before acceptance. Demo readiness remains partial; full
product completion remains unverified.


## Verified feature acceptance, 2026-10-31

Feature [PR #147](https://github.com/antonypaul98/cloudforge/pull/147)
merged as `72eef31234682bc6324ceb2c5e88249bec18239f` after final exact
head `46d61077fec92bee5b238ad0246422d34596aec5` passed
[push product CI #41167124219](https://github.com/antonypaul98/cloudforge/actions/runs/41167124219),
[PR product CI #41167128222](https://github.com/antonypaul98/cloudforge/actions/runs/41167128222)
and [real rootless OCI PR #41167128218](https://github.com/antonypaul98/cloudforge/actions/runs/41167128218).
[Merged-main CI #41167219742](https://github.com/antonypaul98/cloudforge/actions/runs/41167219742)
succeeded. Python 3.11.17: **1,515 pytest passed, 2 existing skips**;
infrastructure: **36 run, 1 skipped**. The first feature head
`785a3e2e28e514b6f9f38a8fc368126084bf78ae` failed one regression
because Python rejected opening a substituted directory before its type
could be checked; the fix checks `fstat` before creating the stream and
closes the descriptor on rejection. Both failed and successful runs are
retained as evidence. No selected external application or authenticated
human approval is claimed. This documentation/state acceptance PR requires
its own exact-head CI and merged-main CI before canonical acceptance.
