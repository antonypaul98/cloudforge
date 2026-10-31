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


## Verified bounded Python crash-recovery extension — 2026-10-30

Feature [PR #136](https://github.com/antonypaul98/cloudforge/pull/136)
merged at `57f94d338585d54a757b669e494a562fc94844ad` after exact
feature head `a060a4df8a5db8ab292bf2122320211596608d17` passed
[push product CI #41086809156](https://github.com/antonypaul98/cloudforge/actions/runs/41086809156),
[PR product CI #41086855011](https://github.com/antonypaul98/cloudforge/actions/runs/41086855011),
and [real rootless OCI PR #41086855313](https://github.com/antonypaul98/cloudforge/actions/runs/41086855313).
[Merged-main product CI #41087040423](https://github.com/antonypaul98/cloudforge/actions/runs/41087040423)
also passed. Python 3.11: **1,482 pytest passed, 2 existing skips**;
infrastructure guard suite: **33 tests, 1 existing skip**. The
real-runtime log records `sigkill_exit_137=pass`,
`crash_recovery_health=pass` and `cleanup=pass`.

The workflow reused the fixed first-party exact-source Python package,
rootless Podman and separate restricted observer. After its normal
stop/restart/health cycle, it deliberately issued `podman kill --signal KILL`,
required `State.Running=false` and `State.ExitCode=137`, restarted the
same container, observed HTTP health and verified cleanup. The existing
non-root, no-network, read-only, no-new-privileges, capability and resource
restrictions remained in place. Static regressions require the kill,
exit-code check, recovery order and third health measurement.

**Limits:** The earlier normal stop escalated to SIGKILL, so graceful
shutdown is **not** established. This remains a fixed CloudForge-owned
fixture, not an external selected Python/Node application. The observer
is not independently authenticated or signed. No independent human
authorization, hardened multi-tenant isolation, real provider deployment
or infrastructure rollback has been demonstrated. No third-party source
was copied or new dependency added; no Mac, Work/Astra or production
infrastructure used. Revert PR #136 for software rollback; no migration.

**Demo readiness: Partial, improved. Full product completion: Unverified.**
Next: independently authenticated, artifact-specific approval and safe
execution of a genuinely selected application with trusted health and
controlled rollback. Canonical documentation acceptance is separately
subject to its own exact-head PR CI and merged-main CI.


## Same-container health observer identity gate — verified feature, 2026-10-31

[Feature PR #159](https://github.com/antonypaul98/cloudforge/pull/159) merged as `d0bf1528784bc1e899ca8733834fecf603f825c4` after exact head `0dd8a625f8962045923c3e087d0989759a9f6a84` passed [push CI #41182976657](https://github.com/antonypaul98/cloudforge/actions/runs/41182976657), [PR product CI #41182990638](https://github.com/antonypaul98/cloudforge/actions/runs/41182990638), and [real rootless OCI PR #41182990688](https://github.com/antonypaul98/cloudforge/actions/runs/41182990688). [Feature merged-main CI #41183067965](https://github.com/antonypaul98/cloudforge/actions/runs/41183067965) succeeded. Python 3.11.17: **1,518 pytest passed, 2 skipped; 40 infrastructure tests run, 1 skipped**. The real OCI runner again passed exact-source admission, health, clean SIGTERM exit 0, deliberate SIGKILL exit 137, restart, recovery and cleanup.

The existing health probe now verifies that the named container has the exact original 64-character container ID, is running, and uses the exact locally built OCI image ID before each separate-container HTTP probe. This rejects accidental name reuse, wrong-image attachment and stopped-container observations. It reuses Podman's documented container-inspect `.Id`, `.Image` and `.State.Running` fields and existing static mutation regressions; no third-party code copied, new dependencies, credentials or provider cost. [Podman inspect documentation](https://docs.podman.io/en/latest/markdown/podman-container-inspect.1.html). Revert feature PR #159 for software rollback; no migration or real infrastructure change.

**Limits:** Checks are local and point-in-time on one disposable runner; they are not cryptographic signatures, independent collectors or hardened multi-tenant isolation. This still executes only CloudForge's fixed first-party Python fixture with synthetic approval keys, not an externally selected application under independently authenticated human authorization. No signed external health, real provider deployment or infrastructure rollback, physical Mac, Work or Astra. **Demo readiness: partial, improved. Full product completion: unverified.** Next: independent artifact-specific human authorization and selected-app sandbox execution, followed by independently trusted health and rollback. Canonical acceptance of this documentation/state checkpoint requires its own exact-head CI, guarded merge and merged-main CI.


## Post-response container identity guard (feature verified 2026-10-31)

The disposable first-party OCI workflow now checks the named container's exact
ID, image ID and running state **again after** the separate observer returns a
successful HTTP health response, before reporting health success. This narrows
a check-then-observe race where a container could change between the existing
pre-probe inspection and the response. The second inspection is a point-in-time
local Podman check, not atomic attestation, signed evidence or an independent
collector. It still runs only the fixed CloudForge-owned Python fixture under
synthetic keys, not a user-selected application or human-approved deployment.

Reuse: existing Podman `container inspect` fields, rootless OCI workflow and
static mutation tests; no new third-party source, dependency, credentials or
provider costs. Official interface: https://docs.podman.io/en/latest/markdown/podman-container-inspect.1.html.
Rollback: revert this feature commit; no schema, migration or persistent
infrastructure. Feature acceptance: [PR #162](https://github.com/antonypaul98/cloudforge/pull/162) exact head `357da12306ebe3be5ca81afdfa5a06e6f5d05456` passed [push CI #41187196523](https://github.com/antonypaul98/cloudforge/actions/runs/41187196523), [PR CI #41187206453](https://github.com/antonypaul98/cloudforge/actions/runs/41187206453) and [real rootless OCI CI #41187206495](https://github.com/antonypaul98/cloudforge/actions/runs/41187206495). Squash merge `fbf85b51bafddf6052938c9acc97c1a5818bba00` passed [merged-main CI #41187286068](https://github.com/antonypaul98/cloudforge/actions/runs/41187286068). Python 3.11.17: 1,518 pytest passed, 2 skipped; 41 infrastructure tests run, 1 skipped. The real OCI runner passed health, clean shutdown, deliberate SIGKILL recovery and cleanup. Canonical documentation/state acceptance requires this documentation PR's own exact-head and merged-main CI. Demo readiness remains partial; full product
completion remains unverified. The priority after acceptance is independently
authenticated artifact-specific approval for genuinely selected application
execution, then trusted health evidence and controlled rollback.
