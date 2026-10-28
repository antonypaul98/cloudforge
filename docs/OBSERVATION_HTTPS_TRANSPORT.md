# Pinned HTTPS socket primitive (not yet wired to a collector)

`cloudforge.observation_https_transport._PinnedHTTPSConnection` is an internal,
opt-in transport building block. It accepts one already-proposed HTTPS target,
one canonical public A/AAAA address and a 1–10 second per-operation timeout.
It validates the target and reuses the existing A/AAAA safety checks **before**
constructing a socket. Its `connect()` opens a numeric IPv4/IPv6 socket directly
to that address, then uses Python's default verified TLS context with the
**original hostname** as SNI and certificate hostname identity. It rejects
HTTP CONNECT tunneling. It does not resolve DNS or consult environment proxy
settings. The primitive remains unwired to any collector. Its intended `request()` API now
accepts only bodyless `HEAD` for the exact validated target path, refuses
caller-supplied headers and chunked encoding, and emits a canonical `Host`
header from the original DNS hostname (including the port when not 443),
plus `Connection: close`. Python `http.client` does not automatically
follow redirects. This is an intended API guard, **not a security sandbox**:
inherited lower-level request methods can still be invoked by other Python
code, and directly calling `request()` can initiate network I/O.

## Authorization and limitations

This module is **not** an approved collector, public service monitor or
permission to contact any real endpoint. It is intentionally not wired into
the observation workflow. Before any real use, separately authenticate the
operator and collector, bind exact signed approval to endpoint and selected IP,
verify trusted DNS/allowlist provenance and key/clock custody, independently enforce the HEAD-only call boundary (including lower-level inherited APIs),
disable redirects and proxies, and enforce an end-to-end elapsed-time budget, evidence/replay
protection and independent runtime acceptance. `socket.settimeout` alone is
not an overall transaction deadline. DNS/IP pinning alone does not authenticate
the operator or prove service health. No infrastructure mutation is supported.

## Reuse, tests and rollback

This small adapter reuses existing CloudForge target and dual-stack validation
and Python 3.11 standard-library `socket`, `ssl` and `http.client`. No external
code or dependencies were copied. The official Python 3.11 documentation
informed the transport contract:

- https://docs.python.org/3.11/library/http.client.html
- https://docs.python.org/3.11/library/ssl.html
- https://docs.python.org/3.11/library/socket.html

Synthetic tests use fake sockets and TLS contexts to check IPv4/IPv6 numeric
connect, original-host SNI, no DNS, rejection of unsafe inputs and tunnels,
certificate-verification defaults, and cleanup after failed TCP/TLS handshakes.
No real network access is performed. Exact-head CI and merged-main CI are
required before accepting this software slice. Roll back by reverting its
feature merge; there is no state/schema migration or deployment to undo.

## Bounded HEAD request guard checkpoint

This follow-up reuses the existing `_PinnedHTTPSConnection` and Python 3.11
`http.client.HTTPSConnection.request` instead of adding an HTTP client or
copying external code. The standard-library request contract was compared at
https://docs.python.org/3.11/library/http.client.html. Added fake-socket
regressions cover canonical Host (443 and nondefault port), bodyless HEAD wire
bytes, exact path, forbidden verbs/bodies/custom headers/chunking, and zero
socket sends for rejected inputs. No DNS, TCP, TLS handshake, real endpoint or
cloud infrastructure was exercised. This is a **synthetic, unwired guard only**,
not authenticated approval, a complete runtime collector, a network sandbox,
a transaction deadline, or live service health. Revert the feature merge to
roll back; no persistent schema, dependencies or infrastructure changes.
