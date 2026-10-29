# Explicitly rooted mTLS client-context foundation (unwired)

This small provider-neutral building block creates a Python 3.11 TLS client
context with an explicit CA bundle and an externally provisioned client
certificate/private key. It has no network entry point, no implicit system
CA fallback, no environment-enabled TLS key logging, no interactive password
prompt, and no deployment/collector integration. It verifies peer DNS hostnames
and requires TLS 1.2 or later; the remote endpoint must independently validate
client certificates and their authorized workload identities.

## Contract and boundaries

build_collector_mtls_client_context(ca_bundle_path, client_certificate_path,
client_key_path, *, key_password=None) accepts only absolute, bounded,
control-free string paths. Invalid paths and password types fail before TLS
credential I/O. It loads the explicit trust bundle before client identity,
and returns no context if either fails. A password can be injected from an
independent secret provider; when absent, a noninteractive empty-password
callback fails encrypted keys rather than prompting. Never commit keys,
certificates or passwords. The caller must protect filesystem permissions,
rotate identities, verify expiry/revocation, and provision the root and
client identity outside CloudForge.

This does **not** authenticate operators, authorize service endpoints,
validate SPIFFE URI SANs or server-side client identities, protect key custody,
secure clocks/replay ledgers, enforce egress, or connect to any service.
The existing pinned HTTPS primitive is deliberately **not wired** to this
context; no live monitoring, deployment, recovery or infrastructure mutation.
An authenticated operator approval service and a collector execution boundary
must be designed and tested separately before any production use.

## Reuse and validation

Audited CloudForge's observation_https_transport.py, runtime permit,
source/operator policy, observation intake, and synthetic tests. Compared
SPIFFE X.509-SVID workload identities against a standard TLS client-context
building block. Chose Python 3.11 standard-library ssl.SSLContext and
PROTOCOL_TLS_CLIENT to avoid new dependencies, translated code or license
uncertainty; SPIFFE workload API/rotation integration remains future work.
Official references:

- https://docs.python.org/3.11/library/ssl.html
- https://spiffe.io/docs/latest/deploying/svids/

Synthetic regressions cover strict trust configuration, input boundaries,
explicit password injection, noninteractive default, fail-closed trust and
identity loading, and rejection of absent CA material using the real SSL
implementation. No external certs, DNS, sockets or provider APIs are used.
Acceptance requires exact-head Python 3.11 full CI and infrastructure checks,
reviewed PR, guarded merge, and successful merged-main CI. Revert the feature
merge to roll back; no state migration, credentials or infrastructure change.
