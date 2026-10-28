# Bounded loopback HTTP HEAD observation fixture

`collect_loopback_http_samples` is an **opt-in local-only** adapter. It revalidates
an exact existing observation plan, artifact, handoff, approval and local receipt
*before* any network operation, then performs one `HEAD` request per planned
startup/readiness/liveness probe against an exact operator-supplied allowlist.
This checkpoint does **not** establish authenticated reviewer approval or a
trusted collector identity. Production use requires those separate controls.

## Scope and restrictions

- Only literal IPv4 `127.0.0.1` is accepted. No hostnames, DNS targets, IPv6,
  arbitrary IP addresses, URLs, redirects, proxy discovery or cloud endpoints.
- Exact target `(kind, host, port, path)` tuples must match a separately supplied
  `allowed_targets` tuple and the existing probe order. The integrating operator
  must keep that allowlist trusted; passing the same untrusted input as both
  parameters is **not** an authorization mechanism.
- The path is an ASCII absolute origin path of at most 128 characters, without
  dots, percent encoding, queries, fragments, backslashes, control characters
  or repeated slashes. No user-supplied HTTP headers or bodies are sent.
- The only method is `HEAD`. A 2xx HTTP status maps to a raw `pass` sample;
  non-2xx, including 3xx redirects and 405, maps to `fail`; transport errors
  map to `unknown`. A connection-close OSError or HTTPException also maps to
  `unknown`, even if HEAD returned 2xx, so failed cleanup cannot sign a
  successful observation. Unexpected cleanup exceptions still abort collection
  without publishing evidence. No redirect is followed and no response body is read.
- Individual probe timeout is limited to 1–10 seconds. The existing observation
  plan's larger allowable timeout values are rejected for this adapter. At most
  three sequential requests are issued. This is not a hard total deadline.
- No source key, HMAC, replay ledger, credentials, artifacts or reviewer names
  are written or logged. Returned samples are unsigned, untrusted HTTP-status
  observations, **not** authenticated monitoring evidence or service-health
  attestations. They are not automatically signed or persisted.
- `HEAD` is specified as safe by HTTP semantics, but an incorrectly implemented
  service could still mutate state. The CI suite contacts only ephemeral local
  fixture servers; no real service is contacted or approved by this checkpoint.

## Reuse and pre-merge compatibility

- Reuses CloudForge's existing `verify_observation_plan`, `ObservationPlan`,
  `ObservationProbe` and `ObservationSample` contracts without changing their
  schemas, keys, approval or replay semantics.
- Uses Python 3.11 standard-library `http.client` and `time.monotonic` only;
  no third-party implementation, code, model, SDK, license or dependency added.
- Evaluated `urllib.request` and third-party `requests`/`httpx`: their redirect,
  URL, proxy and dependency surfaces are unnecessary for an exact numeric
  loopback fixture. The lower-level `http.client` API supports explicit HEAD,
  numeric host, timeout and response-status-only handling.
- Consulted Python 3.11 `http.client` reference and OWASP SSRF Prevention Cheat
  Sheet on strict allowlisting, DNS rebinding and redirects:
  https://docs.python.org/3.11/library/http.client.html
  https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.md
  Conceptual security guidance only; no external code or algorithm copied.

## Acceptance and limits

Regression tests cover a fixture-only 2xx HEAD path, 3xx redirect refusal,
non-2xx classification, malformed/ambiguous host/path/port, allowlist/order,
changed artifact, excessive timeout, transport refusal, close failures
(including the signed-evidence integration), unexpected cleanup exceptions,
and no network before validation. Exact-head PR and merged-main CI are
required for acceptance.

**Not accepted:** real service monitoring, authenticated source/key provisioning,
trusted time, HMAC signing, durable replay integration, provider execution,
cloud deployment, alerting, automatic recovery, rollback or physical hardware
acceptance. An actual collector runtime needs separately authorized end-to-end
security, source identity, scheduling, provenance and lifecycle validation.

## Bounded transport cleanup safeguard (2026-10-27)

The existing Python 3.11 `http.client.HTTPConnection.close` cleanup path
is now treated as part of the transport outcome. Known OSError/HTTPException
close failures yield `unknown` even after a 2xx response; unexpected runtime
exceptions fail the entire collection and do not reach the signing/ledger
boundary. No new dependency, network target, source key, schema, approval
path or external implementation is introduced. Reuse was preferred over
switching to requests/httpx, which would broaden dependencies and URL
handling without addressing trusted collector provenance.

Reference: https://docs.python.org/3.11/library/http.client.html
This is fixture failure handling, not collector authentication, trusted
time, service-health proof, production monitoring or infrastructure recovery.


## Total HEAD elapsed-budget classification (2026-10-28)

A configured 1–10 second socket timeout bounds individual blocking operations
in Python 3.11 `http.client`, not necessarily the entire request plus connection
cleanup. CloudForge now checks elapsed `time.monotonic()` duration after cleanup:
if the full transaction exceeded the probe's `timeout_seconds`, an otherwise
successful 2xx or explicit non-2xx result becomes `unknown` before signing.
Exact-boundary responses remain classified normally. An impossible negative
elapsed duration also becomes `unknown`.

This is **post-hoc classification**, not a hard execution deadline, cancellation
mechanism, authenticated clock, collector identity or production health proof.
It cannot prevent a slow or blocked HTTP operation from taking longer than the
configured duration. CI exercises only fake connections and loopback fixtures.

Reuse-first review: the existing collector already measures monotonic elapsed
time and uses the standard-library `http.client` socket timeout. We reused
those values and the existing `ObservationSample` outcome contract; no new
package, copied algorithm, license, permission, credential or cloud cost.
References: https://docs.python.org/3.11/library/http.client.html and
https://docs.python.org/3.11/library/time.html#time.monotonic .
Four elapsed-boundary regressions plus one signed/SQLite integration regression
must pass alongside the full Python 3.11 suite and infrastructure guards at the
exact PR head and merged main before acceptance.
