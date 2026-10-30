# Synthetic dual-key admission-to-staging integration

This bounded demo-first step composes the existing selected-source package,
exact proposal permit, distinct reviewer-key receipt, local SQLite replay
ledger, and private temporary OCI source staging. It adds no new signature,
identity scheme, container executor, third-party dependency or provider API.

`stage_synthetically_admitted_selected_source` checks the reviewer receipt
and the exact source/target/image/operator permit before staging source.
It then stages verified source bytes and consumes the replay sequence **before**
yielding the temporary directory. Invalid receipts, changed source, image or
target do not stage source. A staging error leaves the sequence unused;
a downstream failure after admission leaves the sequence consumed and removes
the temporary directory on normal Python exception unwinding. Process SIGKILL
can leave temporary files behind. The source directory is not immutable.

This gate is **synthetic only**. The caller controls the keys, trusted
fingerprints, clock, ledger and package. It does not authenticate a person,
obtain an independent decision, execute a selected app, attest isolation,
observe live health or roll back infrastructure. In particular, the returned
directory must **not** be used as permission to execute arbitrary code.
An actual executor must independently authenticate an artifact-specific
reviewer decision, enforce the approval boundary, use trusted key custody and
clock, revalidate exact bytes, and verify isolation before execution.

Reuse-first: existing CloudForge first-party modules and Python 3.11 standard
library `contextlib` only. No external source code copied or translated, no
new license, credentials, cloud cost, migration or real infrastructure mutation.
Tests exercise valid staging, replay, changed source/target/image, forged
approval, stage failure, downstream cleanup and forbidden process/network use.
Full exact-head CI, guarded merge and merged-main CI are required before
acceptance. Revert the feature commit to roll back the code; do not reset any
trusted ledger because doing so can permit replay.

**Demo readiness: partial. Full product completion: unverified.**
