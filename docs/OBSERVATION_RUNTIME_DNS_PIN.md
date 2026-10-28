# HTTPS runtime A/AAAA pinset preflight (no network)

`prepare_runtime_dns_pinset` is an **optional, planning-only** extension to
`prepare_runtime_ipv4_pinset`. It revalidates the exact handoff, artifact,
local receipt, observation plan and ordered HTTPS target proposal. It compares
caller-supplied A **and** AAAA address sets against separately supplied exact
allowlists for each target. Both address families must be explicitly supplied,
including an empty tuple when one family is absent. Each target must have at
least one address overall; each family permits at most four. The order is
strictly increasing within each family and duplicates are rejected.

IPv4 uses CloudForge's existing public-address validator. IPv6 uses Python
3.11 `ipaddress.IPv6Address`: only canonical lowercase compressed public
unicast addresses are accepted. Private, documentation, loopback, multicast,
link-local, reserved, scoped, IPv4-mapped, 6to4, Teredo and known NAT64
translation ranges are rejected. Both families must match their allowlists
exactly. The immutable result exposes only digests and
`pending-independent-approval`; it never exposes hostnames, IPs, paths,
artifacts or reviewers. `verify_runtime_dns_pinset` recomputes the same
integrity boundary without granting network permission.

## Trust boundary

The caller provides the **resolved** and **allowed** sets for both families.
This is neither independent DNS resolution nor proof that all A/AAAA records
were returned. A compromised caller can invent matching values. This module
does not open sockets, resolve DNS, authenticate operators/collectors, perform
TLS verification, contact a service or prove health. It does not authorize
any real service access, deployment or recovery.

Before a real runtime collector, require an independently authenticated
operator and collector, trusted resolver and full A/AAAA answer provenance,
explicit approved endpoint identity, trusted keys/clocks, connection-time
address pinning without a second unchecked lookup, original hostname in TLS
SNI/Host/certificate verification, disabled redirects/proxies, bounded
retries/timeouts, and verified runtime evidence. Never treat a digest-only
pinset as approval. IPv6 address classification varies across Python patch
versions, so lock and test the production interpreter and policy.

## Reuse and validation

This is a narrow extension of existing CloudForge receipt/request and IPv4
pinset validation, using Python 3.11 standard-library `ipaddress`, `hashlib`,
`json` and `dataclasses`. No third-party code, SDK, dependencies or
provider permissions are added. Relevant design references (not copied):

- https://docs.python.org/3.11/library/ipaddress.html
- https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html

Synthetic tests cover mixed, IPv4-only and IPv6-only answers, malformed and
unsafe addresses, duplicates, ordering, changed A/AAAA allowlists, forged
claims, changed artifacts, redaction and forbidden DNS/socket/process I/O.
Require exact-head Python 3.11 CI and infrastructure checks, guarded merge
and merged-main CI before software acceptance. Rollback by reverting the
feature merge. No schema change or infrastructure mutation.
