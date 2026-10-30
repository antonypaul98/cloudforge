# Disposable rootless OCI separate-container health observation

## Bounded acceptance target

On a disposable GitHub-hosted Linux runner, the fixed first-party BusyBox HTTP
fixture must run with `--network=none` and all existing rootless, read-only,
non-root, no-new-privileges, resource and cleanup restrictions. A *separate*
short-lived observer container, using the same locally built content-addressed
image but an overridden BusyBox entrypoint, joins only the fixture's network
namespace with `--network=container:<fixture>`. It must fetch the HTTP health
response rather than reading the health file directly. The three observations
must pass before stop, after restart and after deliberate SIGKILL/restart.
The existing exit-code 137 and cleanup checks remain mandatory.

This is **not** independent operator trust or signed observation: both
containers share a network namespace and a single CI runner, and the observer
uses the same local image. It is a separate process/container with its own
filesystem and PID namespace, not a remote external observer or an isolation
attestation. It cannot authorize or run selected user applications. No host
port is published and no external network endpoint is contacted.

## Reuse and compatibility

Reuses the first-party rootless Podman fixture, fixed BusyBox HTTP content,
existing source checks and regression workflow. No external source code or
new Python dependency is introduced. Podman's documented
[`--network=container:id` mode](https://docs.podman.io/en/v4.0.0/markdown/podman-run.1.html)
reuses another container's network stack; `--network=none` does not
provide external connectivity. This is an isolated CI experiment, not a
claim of hardened multi-tenant security. The rootless CI runner must prove
the specific namespace-sharing behavior; documentation alone is insufficient.

## Failure, rollback and next milestone

Any failed observer probe, missing HTTP content, missing crash exit code,
unverified cleanup or unavailable runtime fails the workflow. The observer
uses `--rm`; the existing EXIT trap removes the fixture, local image and
temporary files. No provider credentials, real infrastructure, production
resources, physical Mac or Work/Astra are involved. Revert the feature PR
to roll back the workflow; there is no schema or external migration.

Next: independently authenticated, artifact-specific approval and controlled
execution of a user-selected Python/Node source package, followed by signed
external health evidence and real rollback. Until then demo readiness remains
partial and full-product completion unverified.
