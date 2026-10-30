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
