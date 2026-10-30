# Local rootless OCI candidate preflight (non-executing)

This bounded demo-first checkpoint adds `inspect_rootless_oci_candidate()` to
identify whether a **local Linux non-root Podman** installation appears capable
of hosting a future isolated *first-party fixture trial*. It does not run a
container, selected application, provider call, network probe or deployment.
A positive result is only a diagnostic candidate, **not** authenticated human
approval, a hardened sandbox attestation, an image trust decision or permission
to execute code. Podman `info` may initialize local runtime state.

The probe uses a fixed executable search path, explicit `--remote=false`, a
limited environment and a six-second timeout. It requires Podman to report
literal rootless and seccomp-enabled flags and cgroups v2. It suppresses all
raw command output and host/environment details. No caller-controlled path,
image, source package, credential or target is accepted. All failures return
fixed, redacted reason codes. Tests mock the process boundary and cover valid
candidates, missing binaries, remote-environment suppression, root/non-Linux
hosts, malformed information, false security flags, cgroups v1, nonzero exit
and timeout. **CI tests do not prove that a real Podman runtime works.**

Reuse-first: existing CloudForge source-bound sandbox review and permit/ledger
contracts were inspected; this adds a small separate diagnostic rather than
copying or changing their authorization semantics. Python 3.11 stdlib only;
no third-party code, dependency, provider permission or cloud cost. Compared
[Podman rootless documentation](https://docs.podman.io/en/latest/markdown/podman.1.html)
and [Podman remote option](https://docs.podman.io/en/v5.0.0/markdown/podman.1.html).
The remote flag defaults may be changed by environment, hence the explicit
local-only override. Runtime/container security must be independently
validated before any actual selected-source execution.

Next: obtain independent artifact-specific human approval, verify a trusted
digest-pinned local image and genuinely isolated rootless runtime, run a fixed
owned fixture with actual health observations and controlled cleanup, then
propose a separately approved selected-app trial. Never use this preflight
alone as a gate for real execution or infrastructure changes.

Rollback: revert the feature merge. No persistent database migration, provider
resource, application execution or infrastructure mutation is introduced.
