# Owned first-party source package in Linux namespaces (demo-first)

## Bounded milestone

This opt-in demo reuses the exact-byte source package from
`cloudforge.demo_source_package` and executes **only CloudForge's fixed
first-party Python reference service** as `app.py` inside a temporary Linux
user, mount, network and PID namespace with a tmpfs root, read-only
host system libraries, a private loopback interface and chroot. A fixed
namespace-local observer measures actual HTTP `HEAD /health`:

1. Application running: HTTP 204 -> `pass`.
2. Application process stopped: connection refused -> `unknown`.
3. Application restarted: HTTP 204 -> `pass`.

It checks the exact package SHA-256, source-review digest and target before
staging bytes. All runtime inputs are fixed first-party files; the caller can
supply **manifest text for review only**, not executable source, commands,
hosts, ports, shell fragments, mounts, Docker images or credentials. The
namespace is temporary and no external endpoint or infrastructure is used.

From a **Linux checkout** with the package installed, unprivileged user
namespaces enabled, util-linux `unshare`, `mount`, `chroot`, `ip` and
`/usr/bin/python3`:

```sh
python -m cloudforge.demo_owned_namespace_source \
  --name owned-fixture --target local-review \
  --manifest ./requirements.txt --allow-owned-namespace
```

Without the explicit flag, it fails before launching anything. Output is
deterministic redacted JSON with package/source digests, a three-phase health
trace and explicit false claims for user-selected execution, independent
operator approval, signed evidence, production isolation attestation, real
deployment and infrastructure recovery. Raw manifest and source bytes are
never printed. The package is held in memory and staged only in a temporary
private directory; the mount namespace's root is tmpfs and disappears on
exit. This is **not** a durable immutable artifact or authorized deployment.

## Reuse-first and acceptance

Inspected the current real-manifest review, selected-source binding, exact-byte
package, first-party reference service/process demo, HTTP observation contract,
CI, checkpoint state and deployment handoff. Reuses those first-party contracts
and Python standard-library `hashlib`, `json`, `subprocess` and
`tempfile`, plus existing Linux util-linux namespaces/chroot. No third-party
source or algorithm was copied or translated, no new Python dependency,
provider permission, API key or cloud cost was introduced. Compared an
ordinary subprocess (not isolated), Docker (additional daemon/image/network
dependency), and Linux namespaces (available in some Linux environments);
chose a **first-party-only** bounded namespace fixture without arbitrary code.

Tests cover opt-in, exact fixed invocation, package verification failure,
malformed manifest rejection, redaction, bad observer output, real namespace
HEAD stop/restart and source-byte binding changes. Real namespace tests skip
**explicitly** if Linux user namespaces are unavailable; a skip does not
establish real namespace acceptance on that runner. Full Python 3.11 exact-head
CI and infrastructure guards, guarded merge, merged-main CI and canonical
checkpoint acceptance remain required. If the real namespace tests skip,
report the separate observed environment that actually ran them; never
silently equate mocked tests with runtime proof.

## Security and remaining original demo gap

This is **not a general security sandbox**. Linux namespaces and chroot alone
do not guarantee isolation from malicious code, kernel vulnerabilities or
privileged hosts. Read-only host runtime mounts are exposed inside the
namespace. It lacks seccomp, cgroup limits, signed executable provenance,
independent operator identity, trusted approval keys, hardened container
attestation and durable replay prevention. It **must not** execute untrusted
user source. Its source package hashes are caller-derived integrity checks,
not signatures or authenticated approval.

Most importantly, the source executed here is **the fixed CloudForge-owned
reference app**, not the actual caller-selected application. The observed
stop/restart is process recovery, not deployment or infrastructure rollback.
The next real demo milestone is an independently approved, exact-source-pinned
**user-selected application** running in a properly hardened isolated runtime,
with signed observations and controlled rollback. Explicit approval is
required before any real infrastructure access or external endpoint.

Rollback: revert the feature merge; no schema migration or persistent
infrastructure state. **Demo readiness: partial. Full product completion:
unverified.** No completion percentage or date is implied by test counts.
