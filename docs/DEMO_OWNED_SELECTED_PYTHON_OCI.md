# Fixed first-party Python source package in rootless OCI (CI-only)

This bounded demo-first checkpoint connects CloudForge's existing selected-source
package verification and private staging to an actual first-party Python HTTP
fixture in a disposable GitHub-hosted rootless Podman container. The workflow
packages the checked-in `scripts/fixtures/owned_python_health_app.py` as root
`app.py` with a comment-only `requirements.txt`, derives the source-review
binding, stages and verifies exact bytes, builds a local OCI image from the
staged source, starts the container, observes HTTP health from a separate
restricted BusyBox observer container, stops/restarts, rechecks health, and
removes the application container. Exact CI success is required before any
runtime acceptance is claimed.

## Reuse, provenance and trade-offs

Reuses `package_selected_source`, `prepare_selected_artifact`,
`stage_verified_selected_source`, `inspect_rootless_oci_candidate`, Python 3.11
stdlib `http.server`, rootless Podman, signed Ubuntu distro BusyBox, and the
existing separate-observer pattern. The Python runtime base is the Docker
Official Image `docker.io/library/python` multiarch index pinned to
`sha256:09d17d5e4c16d0a7a1eea690bcb7c6ab8616b211f8421e429e97c1bef5bd0ed2`
(identified on Docker Hub 2026-10-30, 3.11-alpine). It is pulled only during
CI preparation; builds use `--pull=never --network=none`, and application and
observer containers have no external networking. This trades a one-time public
registry fetch and third-party image trust for a maintained Python interpreter
without rebuilding a distro root filesystem. The image digest prevents tag
movement but is not an independent signature, SBOM, vulnerability scan or
runtime attestation. Official Python images include Alpine and other packages
with their own licenses; licensing/security must be reviewed before production.
No third-party code is copied into the CloudForge repository, and no Python
manifest dependency is installed. No provider API or production resource used.

## Limits and rollback

The executed code is a fixed CloudForge-owned fixture, **not a caller-selected
application**. Caller-provided digests are not independent authenticated
approval; no external selected code, provider infrastructure, signed health,
production rollback or hardened multi-tenant isolation is accepted. The observer
shares the application's network namespace and CI runner. A container stop may
escalate to SIGKILL. Revert the feature merge to roll back; disposable runner
resources are cleaned up after the job. If registry access or rootless runtime
is unavailable, report the CI failure rather than weakening isolation.

**Demo readiness: Partial. Full product completion: Unverified.** The next
milestone is independently authenticated, artifact-specific authorization for
controlled external selected-source execution, then independently trusted
health evidence and real rollback acceptance.

## Verified bounded acceptance, 2026-10-30

Feature PR [#134](https://github.com/antonypaul98/cloudforge/pull/134)
merged at `cf8771cedba53fdcb0283163214b8ca8e33a21f2` after final
exact-head `b6d082f23ca32340f56274e3f7e661c9150dbce0` checks:

- Python 3.11 full pytest: 1,482 passed, 2 existing namespace skips;
  infrastructure guard suite: 30 passed, 1 existing skip.
- Product push [#41077911336](https://github.com/antonypaul98/cloudforge/actions/runs/41077911336)
  and PR [#41077923048](https://github.com/antonypaul98/cloudforge/actions/runs/41077923048): success.
- Real rootless selected-Python fixture PR
  [#41077923250](https://github.com/antonypaul98/cloudforge/actions/runs/41077923250):
  success. Push [#41077911331](https://github.com/antonypaul98/cloudforge/actions/runs/41077911331):
  success on attempt 2 after a transient rootless prerequisite probe failure.
- Merged-main [#41078273066](https://github.com/antonypaul98/cloudforge/actions/runs/41078273066):
  success on the feature merge SHA.

The first runtime attempt failed because the private staged source retained mode
`0600` when copied into an image whose process runs as non-root. The corrected
Containerfile uses `COPY --chmod=0444`, preserving private staging and making
the fixed application source readable inside the image. The initial failed runs
and transient probe failure remain part of the evidence, not hidden successes.

**Accepted only:** fixed first-party Python package -> verified staging -> actual
rootless OCI execution -> separate-container HTTP health -> stop/restart ->
health -> cleanup. No caller-selected code, independent human authorization,
signed external observation, infrastructure deployment or rollback accepted.


## Bounded Python crash-recovery extension (pending exact-head CI)

The disposable first-party Python OCI workflow now attempts an explicit
`podman --remote=false kill --signal KILL` after its verified stop/restart
cycle, checks `State.Running=false` and `State.ExitCode=137`, starts the
same container again, measures HTTP health through the separate restricted
observer container, and verifies cleanup. Static regression guards require
the kill, exit-code check, recovery order and third health measurement.
The existing non-root, no-network, read-only, no-new-privileges, capability
and resource restrictions remain in place. No new runtime dependency,
third-party code, external selected source, infrastructure or secrets are
introduced; this reuses the checked-in fixture and Podman workflow.

**Acceptance is pending:** passing static guards alone cannot prove the
real runtime crash/restart sequence. Require exact feature-head push and PR
product CI **and** real rootless OCI CI, guarded merge, merged-main CI, and
canonical acceptance before claiming completion. A normal `podman stop`
may escalate to SIGKILL and is not evidence of graceful shutdown. Even
after success, this remains first-party fixture recovery, not an externally
selected application, independent human authorization, trusted health
attestation, production deployment or infrastructure rollback. Revert
the feature merge to roll back the workflow; no persistent migration.
