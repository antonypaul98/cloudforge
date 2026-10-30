# Selected-application rootless sandbox review (non-executing)

This demo-first checkpoint connects an exact-byte, verified caller-selected
Python `app.py` or Node `server.js` source package to a deterministic
**review-only** proposed rootless OCI runtime configuration.

`prepare_selected_sandbox_review(package_bytes, expected_package_sha256=...,
expected_review_binding_digest=..., expected_target_id=..., image_ref=...)`
revalidates the original package, target and source binding before proposing
the runtime, a digest-pinned image reference and fixed restrictive constraints.
The returned `proposal_sha256` binds the canonical proposal. It never includes
raw source or manifest text, credentials, host paths, shell commands, or
environment variables.

## Strict limitations

**Nothing is executed.** This is not an executable Podman command, a deployed
service, an independently authenticated approval, an immutable artifact store,
an attested container, real health evidence, or rollback. The caller supplies
all expected digests and the image name; this module cannot establish their
trustworthiness. A digest-pinned image is stable only if its content is
independently verified; pinning does not establish provenance, freshness,
security or authorization. The plan cannot safely be converted into a command
without a separate trusted operator/collector, runtime capability verification,
artifact staging and execution controls.

The proposed limits are network none, read-only root, no-new-privileges,
all capabilities dropped, no host mounts or devices, non-root user, bounded
PIDs/memory/CPU and no automatic image pull. These are review requirements,
**not** proof that a host runtime can enforce them. Rootless Podman/OCI
isolation is not a hardened guarantee against hostile code.

## Reuse and provenance

Reuses `verify_selected_source_package` and the existing exact source/manifest/
target binding, Python 3.11 standard-library `hashlib`, `json` and `re`.
No copied third-party code, translated implementation, dependency, network
access, provider credentials or infrastructure mutation.

The constrained proposal draws on:
- [Podman run reference](https://docs.podman.io/en/latest/markdown/podman-run.1.html)
  for rootless-related runtime options and limits; actual support depends on
  host, cgroups and runtime.
- [OCI image descriptor](https://github.com/opencontainers/image-spec/blob/main/descriptor.md)
  for digest-pinned image identity.

No competitive uniqueness is claimed for container isolation, image pinning,
policy or runtime constraints. The differentiated CloudForge demo still needs
an independently authorized **selected app -> actual isolated execution ->
signed observed health -> controlled rollback** flow. That complete demo is
not accepted. The feature can be rolled back by reverting its merge; no
schema, credentials, persistent state or infrastructure changes.

## Acceptance

Require exact-head Python 3.11 full pytest and infrastructure guards on push
and PR, expected-head guarded merge with unchanged main, then successful
merged-main CI and canonical state acceptance. The tests cover Python and Node
source packages, reproducibility, changed source/manifest/target/image,
tampering, invalid image references, output redaction and no subprocess/network
activity. No physical Mac, external infrastructure or Work/Astra is involved.
