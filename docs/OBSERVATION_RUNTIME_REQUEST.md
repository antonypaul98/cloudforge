# Read-only HTTPS runtime observation target proposal (planning only)

This checkpoint creates a deterministic, redacted **proposal** for HTTPS HEAD
observation targets. It does **not** contact those targets, resolve DNS, issue
credentials, authenticate an operator or collector, approve a service, assert
health, deploy anything or perform recovery.

`prepare_runtime_observation_request` first revalidates the exact existing
CloudForge handoff, artifact, local approval, receipt and ObservationPlan. It
then validates one ordered HTTPS target per planned probe and hashes the
canonical target tuple. The exported immutable request contains only the
observation-plan digest and ordered-target digest. Raw hostnames, paths, source
artifacts, reviewers, secrets and authorization claims are excluded. The status
is always `pending-independent-approval` and all execution/health/recovery
flags remain false. `verify_runtime_observation_request` rederives the
request from the exact inputs. It is an integrity check, **not** an approval.

The target grammar is deliberately narrow: lowercase ASCII DNS hostname with
at least two valid labels and alphabetic top-level domain; explicit HTTPS,
integer TCP port 1-65535, bounded ASCII path with no query, fragment, percent
escapes, traversal or double slash. IP literals, userinfo and bare localhost
are rejected. A syntactically valid DNS hostname can still resolve to a
private, loopback or metadata IP, or be rebound later. **Do not pass these
proposals directly to a network client.** A future runtime adapter must
require separately authenticated operator approval, a trusted exact endpoint
allowlist, DNS/IP pinning and revalidation, TLS peer verification, independent
collector identity, trusted clocks, key custody, no redirects, request limits,
replay resistance and bounded read-only operation before contacting any real
service. No production permission is inferred from a proposal.

## Reuse-first and validation boundary

Inspected the existing observation plan, fixture HTTP target validator, HMAC
operator permit, durable replay ledger, deployment handoff and current tests.
Reused `verify_observation_plan`, its exact receipt binding, existing bounded
path grammar and Python 3.11 standard-library `dataclasses`, `hashlib`,
`json` and `re`. No third-party source or algorithm was copied or translated,
and no dependencies, cloud SDKs, credentials, licenses, new permissions or
provider costs were introduced. This is a simpler precursor to an authenticated
runtime adapter, not a substitute for an identity provider or TLS library.
Official references for later implementation:
https://docs.python.org/3.11/library/ssl.html and
https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
(conceptual guidance only).

Synthetic regressions cover deterministic redacted output, exact target and
plan binding, changed artifact, malformed host/port/path/scheme/probe order,
forged approval/execution flags, and no network or subprocess use. Run the
complete Python 3.11 and infrastructure CI on the exact PR head and merged
main before marking software acceptance. No physical Mac or real-service test
is part of this checkpoint. Rollback: revert the feature merge; no persistent
schema migration or external side effects.
