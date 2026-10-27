# CloudForge

Provider-neutral infrastructure planning, reviewable deployment handoffs, and local-only authorization safeguards. **This repository does not yet deploy cloud infrastructure, observe deployed services, or perform recovery.**

## Try the credential-free synthetic demo

The demonstration is currently on [PR #6](https://github.com/antonypaul98/cloudforge/pull/6), branch `build/local-deployment-adapter`, **not yet merged into `main`**. It uses in-memory synthetic reviewers, a synthetic target and fixed artifact bytes. It does not require AWS credentials, a cloud account or physical hardware.

With Python 3.11 installed:

```sh
git clone https://github.com/antonypaul98/cloudforge.git
cd cloudforge
git switch build/local-deployment-adapter
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e . pytest
python -m cloudforge.synthetic_demo
python -m pytest -q
```

The demo prints deterministic JSON with a redacted audit event and ten synthetic rejection checks: altered artifact, stale approval replay with a fresh changed-artifact request, forged recovery status, forged receipt reviewer, cross-target authorization, forged infrastructure mutation, forged deployment observation, forged recovery evidence, forged request digest and forged receipt digest. Look for `"demo_only": true`, `"infrastructure_mutated": false`, `"deployment_observed": false`, `"recovery_performed": false` and `"authenticated_review": false`. A passing demonstration proves only the synthetic authorization path, **not** a real deployment or authenticated human approval.

For implementation boundaries, see [the local adapter specification](docs/LOCAL_DEPLOYMENT_ADAPTER.md) and [checkpoint state](CHECKPOINT_STATE.json). Real deployment and recovery require separate runtime implementation, independent validation and explicit authorization.
