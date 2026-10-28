# Pinned HTTPS HEAD transaction deadline (unwired)

This bounded safeguard adds a single monotonic elapsed-time budget to the existing
internal `_PinnedHTTPSConnection`. The budget starts immediately before an
exact, bodyless HEAD request and covers numeric-IP TCP connect, original-host
TLS handshake, header send, and response header retrieval. Before each
blocking phase, the remaining budget is applied as a socket timeout; late
returns are rejected, the connection is closed and no response is accepted.
An unfinished response prevents a second request. Explicit close or failure
clears the pending transaction state.

## Trust and operational limits

This primitive is **not wired to a public collector** and must not contact
real endpoints without independent authenticated operator and collector
identity, exact approved hostname/IP/port/path, trusted DNS/allowlist/key/clock
and a separate execution authorization. It does not sign evidence, authenticate
a reviewer, assert health, deploy, or recover infrastructure.

Socket timeouts apply to individual blocking operations. A peer that trickles
data may keep one low-level read active beyond the overall budget; the
post-return elapsed check rejects that result but is **not a hard process-wide
cancellation or security sandbox**. Arbitrary same-process Python may bypass
private method restrictions. Cleanup may also block independently. The
collector must classify timeout/cleanup failures as unknown rather than pass.

## Reuse, validation, rollback

Reuses the existing CloudForge HEAD/Host/IP/TLS guards and Python 3.11
standard-library `http.client`, `socket`, `ssl` and `time.monotonic`.
Compared official Python 3.11 documentation for HTTPConnection, socket
timeouts and monotonic clocks. No external source code copied, dependency,
new SDK, cloud permission, service charge or infrastructure mutation.

- https://docs.python.org/3.11/library/http.client.html
- https://docs.python.org/3.11/library/socket.html#socket.socket.settimeout
- https://docs.python.org/3.11/library/time.html#time.monotonic

Synthetic regressions exercise successful completion, late send, late response,
expiration before read, duplicate pending request, slow connect, slow TLS
handshake and close/reset. Existing HEAD/TLS/IP and repository suites must
pass on exact PR head with Python 3.11, followed by guarded merge and
merged-main CI. These are software tests only, not physical Mac or live
service acceptance. Roll back by reverting the feature merge; no schema or
external resource changes.
