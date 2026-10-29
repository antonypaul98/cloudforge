# Synthetic pinned HTTPS HEAD orchestration seam

This checkpoint composes the existing exact local receipt, observation plan,
runtime target request and A/AAAA pinset verifier **before any connection
factory is called**. An explicit injected fake connection factory receives one
approved numeric IP, exact target and timeout per probe. Its HEAD-only
responses are mapped to unsigned `ObservationSample` values. A 2xx status is
a raw `pass`, 3xx–5xx is `fail` (redirects are not followed), and malformed
status, transport errors, cleanup failure or elapsed budget violations are
`unknown`. The output is not verified service health.

This function has **no default connection factory**, does not import or
instantiate the real pinned transport, does not sign evidence and never reads
credentials. Tests use injected mocks, not real endpoints. The caller supplies
both DNS answers and the allowlist: equality is not independent DNS trust.
Nothing here authenticates an operator, collector, human approval, key, clock,
resolver or execution. A caller could inject a network-capable factory; this
is **not a security sandbox or authorization** and must not be used for live
traffic. Production wiring needs a separately enforced execution boundary,
independent identities, trusted endpoint policy and explicit human approval.

## Reuse and provenance

Existing CloudForge `verify_runtime_dns_pinset`, `ObservationSample` and
standard-library `http.client` exception semantics were reused. Compared the
existing loopback collector and Python 3.11 HTTP client documentation:
https://docs.python.org/3.11/library/http.client.html .
No third-party code, new dependency, provider SDK, permission, credential or
cloud charge. Inputs, outputs, ordering, status boundaries, cleanup and
deadline behavior are covered by synthetic regressions. The full existing
suite and infrastructure guards must pass on exact PR head and merged main.

Rollback: revert the feature merge. No migrations, provider actions or external
resources are involved. This is synthetic software acceptance only; no physical
Mac/device or real-service validation.

## Monotonic-clock failure and nonfinite elapsed regression (2026-10-29)

The synthetic HEAD fixture now returns an `unknown` sample with zero
elapsed milliseconds if reading the monotonic clock fails or the elapsed
value is NaN/infinite. A start-clock failure prevents invoking the injected
connection factory for that probe. A finish-clock failure still closes the
connection before returning `unknown`. Extremely large but finite elapsed
values are clamped *before* conversion to integer milliseconds, so overflow
cannot escape the fixture. Existing normal, negative and over-budget elapsed
behavior remains fail-closed; this does not establish a trusted clock.

Reuse-first: inspected existing fixture/permit/intake contracts and tests;
reused Python 3.11 standard-library `math.isfinite` rather than introducing
a new dependency or external algorithm. Reference:
https://docs.python.org/3.11/library/math.html#math.isfinite .
Six parameterized no-network regression cases cover NaN, both infinities,
a huge finite duration and start/finish clock exceptions. Python 3.13
isolated arithmetic prototype is not full repository validation; exact-head
Python 3.11 PR CI, infrastructure checks and merged-main CI are required.

No real endpoint, credential, infrastructure, device or provider was accessed.
This is still an untrusted caller-controlled synthetic fixture, not live
monitoring, authentication, hard cancellation, deployment or recovery.
Rollback: revert the feature merge; no schema migration.
