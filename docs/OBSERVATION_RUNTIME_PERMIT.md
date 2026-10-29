# Proposed pinned HTTPS HEAD operator-key permit (no I/O)

This small checkpoint binds an exact runtime observation proposal, A/AAAA
pinset, opaque collector alias, source-key fingerprint, sequence and a
maximum five-minute validity window to a distinct operator-key HMAC.
The verifier rechecks the original handoff, exact artifact, local receipt,
observation plan, ordered HTTPS targets and caller-provided pin policy
before accepting the MAC. It performs no network, DNS, shell or clock I/O.

**This is not authenticated approval.** The caller supplies both keys, policy,
time and sequence. A MAC demonstrates possession of the supplied key, not a
human's identity, independently trusted DNS, secure key custody, an actual
collector, one-time execution or service health. A dishonest caller can
construct matching policy and MAC inputs. Nothing calls the pinned transport
or permits contact with a live endpoint. Do not treat a valid permit as
authorization to perform network operations.

## Reuse-first decision and compatibility

Reuses CloudForge's exact `verify_runtime_dns_pinset`, source-key validation,
canonical JSON and SHA-256 digest conventions. The Python 3.11 standard-library
`hmac.digest` and `hmac.compare_digest` implement MAC issuance and checking:
https://docs.python.org/3.11/library/hmac.html .
Compared with the existing loopback operator permit and signed observation
evidence; neither binds the HTTPS runtime request and dual-stack pinset.
No third-party source code was copied or translated. No new dependency,
license, service, permission, secret storage or cloud cost was introduced.

Synthetic tests exercise deterministic success, exact request/pinset bindings,
changed artifact/target/allowlist, malformed fields, wrong keys, replay
sequence, expired/future time, and forbidden I/O. Require exact-head PR CI,
guarded merge, and merged-main CI before software acceptance.

## Remaining production gates

Separately authenticate operator and collector, provision independent keys,
trusted clock and endpoint/DNS policy, persist one-time sequences atomically,
enforce the permit at a privileged execution boundary, then test read-only
TLS/HEAD behavior against explicitly approved endpoints. The caller-supplied
approval objects are not independently authenticated. Signed runtime
measurement, deployment and recovery remain unfinished.

Rollback: revert the feature merge. No schema migration or infrastructure
change; no physical Mac or live endpoint evidence.
