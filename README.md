# CloudForge

Provider-neutral infrastructure planning, reviewable deployment handoffs, and local-only authorization safeguards. **This repository does not yet deploy cloud infrastructure, observe deployed services, or perform recovery.**

An [unwired explicit-root mTLS client context](docs/OBSERVATION_MTLS_BOUNDARY.md) prepares a certificate-verification building block; it does not authenticate an operator, connect to any endpoint or authorize monitoring.

A separate [read-only observation proposal](docs/OBSERVATION_PLAN.md) can now describe bounded startup/readiness/liveness checks tied to an exact local authorization receipt. It does not run probes or verify health. A separate [in-memory observation evidence intake](docs/OBSERVATION_EVIDENCE.md) can verify keyed, exact-plan-bound synthetic sample envelopes, but cannot authenticate a live collector or establish service health. An opt-in [local SQLite replay ledger](docs/OBSERVATION_REPLAY.md) now rejects repeated sequences across local processes, but does not run probes or establish collector identity.

## Review a real application manifest (read-only demo)

CloudForge can now inspect a **caller-selected real Python or Node manifest** and produce deterministic, provider-neutral proposed resources plus an exact-target deployment handoff request, without credentials or executing the application:

```sh
python -m cloudforge.application_demo --name my-api --target review-staging --manifest ./requirements.txt
```

The output also includes a separate, reproducible `source_review_binding` digest: even a manifest edit that leaves inferred resources unchanged gets a different review provenance packet. It is **not** a signature or execution approval. See [demo readiness, limitations, and competitive comparison](docs/DEMO_READINESS.md). This remains a **review-only first milestone**, not executable Terraform/OpenTofu/Pulumi IaC, authenticated approval, real deployment, monitoring, or recovery.
## Observe actual loopback fixture HEAD results (opt-in)

```sh
python -m cloudforge.demo_loopback_observation --name my-api --target fixture-target --manifest ./requirements.txt --allow-loopback-fixture
```

This starts a temporary local-only HTTP fixture and measures real HEAD results
through pass, simulated failure and restored fixture responses. It **does not**
execute the selected application, authenticate reviewers, deploy infrastructure
or perform real recovery. See [demo readiness](docs/DEMO_READINESS.md).

## Try the credential-free synthetic demo

The demonstration was integrated into `main` through [PR #6](https://github.com/antonypaul98/cloudforge/pull/6) after exact-head CI and merged-main CI passed. It uses in-memory synthetic reviewers, a synthetic target and fixed artifact bytes. It does not require AWS credentials, a cloud account or physical hardware.

With Python 3.11 installed:

```sh
git clone https://github.com/antonypaul98/cloudforge.git
cd cloudforge
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e . pytest
python -m cloudforge.synthetic_demo
python -m pytest -q
```

The demo prints deterministic JSON with a redacted audit event and fourteen synthetic rejection checks, including stale approvals after changed artifact, plan, target or claimed handoff reviewer, plus forged receipts, audit evidence and cross-target authorization. Look for `"demo_only": true`, `"infrastructure_mutated": false`, `"deployment_observed": false`, `"recovery_performed": false` and `"authenticated_review": false`. A passing demonstration proves only the synthetic authorization path, **not** a real deployment or authenticated human approval.

For implementation boundaries, see [the local adapter specification](docs/LOCAL_DEPLOYMENT_ADAPTER.md) and [checkpoint state](CHECKPOINT_STATE.json). Real deployment and recovery require separate runtime implementation, independent validation and explicit authorization.

## Observe an owned reference application process (opt-in)

```sh
python -m cloudforge.demo_owned_reference_process --name my-api --target local-demo --manifest ./requirements.txt --allow-owned-reference-app
```

Runs a fixed first-party Python reference service in a child process and
observes real HEAD success, process stop, and restart. This is **not** the
selected application's execution, an OS-isolated sandbox, authenticated
approval, infrastructure deployment or recovery. See
[demo readiness](docs/DEMO_READINESS.md).

## Bind a selected real application source file (read-only)

```sh
python -m cloudforge.demo_selected_artifact --name my-api --target sandbox-review --manifest ./requirements.txt --source ./app.py
```

Supports a single root `app.py` or `server.js` matching the manifest runtime.
Prints a deterministic source/manifest/target review binding, without printing
source code or running the selected application. **Not** an immutable artifact,
authenticated approval, OS sandbox, deployment, monitoring, or rollback.
See [demo readiness](docs/DEMO_READINESS.md).
