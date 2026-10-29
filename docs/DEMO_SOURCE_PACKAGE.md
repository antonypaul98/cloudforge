# Exact-byte selected-source review package (demo-first)

This bounded milestone bridges a caller-selected Python `app.py` or Node
`server.js` and its real manifest text into a deterministic, portable
**in-memory byte package**. It reuses
`demo_selected_artifact.prepare_selected_artifact` and the existing
source-bound review digest. No application is executed.

`package_selected_source(name, manifests, target_id, entrypoint_name, source_bytes)`
returns canonical JSON **bytes containing the original source and manifest
contents** as strict base64. Treat these bytes as sensitive: never log, print,
commit, publish, or transmit a package without a separate explicit decision.
The module has no CLI, disk write, network call, package installation,
provider operation, process launch or runtime adapter.

`verify_selected_source_package(package_bytes, expected_package_sha256=...,
expected_review_binding_digest=..., expected_target_id=...)` rejects altered
bytes, noncanonical JSON/base64, unexpected fields, duplicate manifests,
unsupported runtimes, invalid UTF-8, oversized data, mismatched targets and
stale source-review digests. It reuses the existing manifest/source validation
and returns a frozen in-memory value containing the exact bytes. The expected
digests and target **must** be pinned by an independently authenticated
approval boundary before any future sandbox uses this data. The function
does not authenticate anyone and unkeyed SHA-256 is not a signature.

## Demonstration and acceptance

From a Python 3.11 environment with CloudForge installed:

```python
import hashlib
from cloudforge.demo_selected_artifact import prepare_selected_artifact
from cloudforge.demo_source_package import package_selected_source, verify_selected_source_package

manifests = {"requirements.txt": "redis>=5\n"}
source = b"print('hello')\n"
review = prepare_selected_artifact("demo", manifests, "review", "app.py", source)
package = package_selected_source("demo", manifests, "review", "app.py", source)
verified = verify_selected_source_package(
    package,
    expected_package_sha256=hashlib.sha256(package).hexdigest(),
    expected_review_binding_digest=review["selected_source_binding"]["digest"],
    expected_target_id="review",
)
assert verified.source_bytes == source
```

This is a **local self-consistency example**, not independent authorization.
Regression tests cover deterministic Python/Node roundtrips, exact-byte changes,
rehashed tampering, stale targets, noncanonical input, malformed packages,
secret-safe object representation and absence of process/network calls.
Full Python 3.11 CI, infrastructure guards, guarded merge and merged-main CI
are required before acceptance. An isolated local prototype with stubbed
review dependencies is not full-suite evidence.

## Reuse, trust and next gate

Inspected existing selected-source review, real-manifest inspector, handoff,
owned reference process and demo acceptance contracts. Reuses first-party
CloudForge review and Python 3.11 standard-library JSON/base64/hashlib/hmac;
no third-party source copied or translated, new dependency, license, cloud
cost or credentials. A bounded source snapshot is preferable to writing
untrusted application code to disk or launching it in an ordinary subprocess.

This **is not a durable immutable artifact**: a caller can replace package
bytes or recompute hashes, and no external trusted store or independent
signer pins the expected values. Frozen Python objects do not provide an OS
security boundary. This does not run the user's application, provide
authenticated human approval, OS/container isolation, signed observations,
deployment, rollback or recovery. Do not pass the package to the existing
reference subprocess or to any live infrastructure.

Next: independently authenticated approval and an OS-isolated sandbox that
pins and verifies the exact package bytes at execution, observes real
application health, and demonstrates controlled rollback with evidence.
No external endpoint or infrastructure mutation without exact human approval.
Rollback for this change is a feature-merge revert; no schema migration,
persistent state or external resource is created.

**DEMO READINESS:** Partial. **FULL PRODUCT COMPLETION:** Unverified.
