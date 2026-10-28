# HTTPS runtime IPv4 pinset preflight (no network)

This checkpoint adds a **pure, IPv4-only** preflight to the existing
[planning-only HTTPS runtime target proposal](OBSERVATION_RUNTIME_REQUEST.md).
It does not resolve DNS, open sockets, contact services, issue credentials,
authenticate an operator or collector, or prove service health.

`prepare_runtime_ipv4_pinset` revalidates the exact deployment handoff,
local receipt, observation plan and ordered HTTPS target proposal. It compares
caller-supplied resolved IPv4 sets with separately supplied allowed IPv4 sets,
requiring **exact equality**, canonical dotted-quad spelling, strictly increasing
numeric order, no duplicates and 1–4 addresses per target. It rejects
non-global, reserved, multicast, loopback, link-local, unspecified, private,
shared-address, documentation and metadata IPs using Python 3.11's
`ipaddress.IPv4Address`. IPv6, mapped IPv6, integer/octal/hex spellings and
CIDR are deliberately unsupported. Changing an address, plan, target or
artifact invalidates the digest-only pinset.

The exported immutable pinset contains only digests and explicit
`pending-independent-approval` status; it does not expose addresses, DNS names,
paths, artifacts, reviewers or secrets. `verify_runtime_ipv4_pinset`
recomputes the exact inputs and grants **no** network permission.

## Trust and runtime limits

The caller supplies both the resolved and allowed sets. This is an
**integrity and format check**, not evidence of independent DNS resolution,
trusted address ownership, approved network access or DNS completeness.
A compromised caller can provide matching false sets. No AAAA records are
handled. Python's `is_global` classifications can change between interpreter
patch versions; CI pins Python 3.11, but production must lock and test the
exact runtime version and IP policy. Real network access remains forbidden.

A future separately authorized adapter must independently authenticate the
operator and collector, provision trusted keys/clocks, validate **all** A/AAAA
DNS answers, pin a verified destination IP at connection time, avoid any
unchecked second DNS lookup, preserve original hostname for TLS SNI, Host
header and certificate verification, disable redirects and proxies, bound
timeouts/retries, enforce per-attempt address policy, and capture measured
runtime evidence. An allowlist alone is insufficient against DNS rebinding.

## Reuse-first review, provenance and validation

Existing CloudForge observation request, receipt and plan verification were
reused. The Python 3.11 standard-library `ipaddress`, `hashlib`, `json`
and `dataclasses` supply parsing and deterministic digests. External
HTTP clients, DNS SDKs, TLS wrappers and cloud libraries were considered
premature because no authenticated runtime/transport is authorized. No
third-party source code, translated algorithm, dependency, credential, license
or provider permission was added. Reference guidance, not copied code:

- https://docs.python.org/3.11/library/ipaddress.html
- https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html

Synthetic tests cover valid exact sets, tampering, changed targets/artifacts,
unsafe addresses, malformed encodings, sorting/duplicates, redaction and
no DNS/socket/subprocess calls. Run the complete Python 3.11 CI and
infrastructure checks on the exact PR head and merged main before acceptance.
An isolated Python 3.13 module smoke is not repository acceptance.

Rollback: revert the feature merge. No schema migration, external network,
cloud resource or persistent state is touched.
