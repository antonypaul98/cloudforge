# CloudForge

Provider-neutral infrastructure planning, reviewable deployment handoffs, and local-only authorization safeguards. **This repository does not yet deploy cloud infrastructure, observe deployed services, or perform recovery.**

A separate [read-only observation proposal](docs/OBSERVATION_PLAN.md) can now describe bounded startup/readiness/liveness checks tied to an exact local authorization receipt. It does not run probes or verify health. A separate [in-memory observation evidence intake](docs/OBSERVATION_EVIDENCE.md) can verify keyed, exact-plan-bound synthetic sample envelopes, but cannot authenticate a live collector or establish service health. An opt-in [local SQLite replay ledger](docs/OBSERVATION_REPLAY.md) now rejects repeated sequences across local processes, but does not run probes or establish collector identity.

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
