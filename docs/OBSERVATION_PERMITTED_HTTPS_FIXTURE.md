# Permit-gated synthetic pinned HTTPS HEAD fixture

This checkpoint composes the existing proposed runtime HEAD permit verifier
with the existing injected pinned HTTPS fixture. It verifies the exact local
receipt, observation plan, ordered HTTPS target request, full A/AAAA pinset,
caller-supplied allowlist, operator-key MAC, collector alias, source key,
sequence and caller-supplied clock **before invoking the connection factory**.
The existing fixture then issues only bodyless HEAD requests to injected
connections and returns unsigned synthetic samples.

**No live access is authorized.** The permit is not an independently
authenticated human approval. Caller-supplied keys, time, DNS answers,
allowlists and the injected factory are not trusted production identities or
policy. This is a composition test, not a sandbox: a malicious caller could
supply a network-capable factory. It neither establishes service health nor
produces signed runtime evidence. No real endpoint, DNS, subprocess, provider
or infrastructure mutation is performed by the included tests.

## Reuse-first and compatibility

Audited existing `observation_runtime_permit.py` and
`observation_https_fixture.py`, their typed interfaces and tests, and
`docs/OBSERVATION_RUNTIME_PERMIT.md` and
`docs/OBSERVATION_HTTPS_FIXTURE.md`. The missing piece was their
ordered composition, so no third-party code, new dependencies, credential
storage, schema migration or provider SDK were added. Existing
`collect_pinned_https_fixture_samples` remains unchanged for its existing
synthetic callers. Python 3.11 standard-library `hmac` and `http.client`
are already used by those components; see
https://docs.python.org/3.11/library/hmac.html and
https://docs.python.org/3.11/library/http.client.html .

Regressions cover exact two-target IPv4/IPv6 HEAD ordering and early
rejection of altered MAC, expired/future clock, collector alias, operator
key, sequence, artifact, target, pinset and allowlist before the injected
factory is invoked. Existing full-suite, infrastructure guard, exact-head
PR and merged-main CI are required before acceptance.

## Production blockers and rollback

An independent operator identity, independently authenticated collector,
trusted endpoint/DNS/key/clock provenance, durable atomic one-shot replay
enforcement, real transport authorization boundary, signed runtime evidence,
actual monitoring, deployment and recovery are still required. Real endpoint
contact requires exact artifacts/plans and explicit human approval.

Rollback: revert the feature merge. There are no migrations, external
resources, new permissions, physical Mac steps or cloud costs.
