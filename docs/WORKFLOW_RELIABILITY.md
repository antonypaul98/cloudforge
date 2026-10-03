# Workflow reliability — stabilization 2026-10-03

No product checkpoint advanced. No feature source/test changed.

## Environment

Metadata minimum remains Python >=3.11 where present; this repository's
reproducible development/CI interpreter is **3.11** (`.python-version`).
Other interpreters are not validated by this stabilization. Existing dependency
ranges are retained; version ranges do not guarantee byte-for-byte dependency
reproducibility. No dependencies upgraded or new lockfile guessed.

```sh
python3.11 -m venv .venv
. .venv/bin/activate
python scripts/session_preflight.py
python -m pip install -e . pytest
python -m pip check
python scripts/ci_diagnostics.py
```

Preflight failing on a new clean checkout on main is intentional: switch to the
existing recorded branch. Missing gh is a tooling blocker, not proof that the
connected GitHub integration is unavailable. Follow AGENTS.md's fallback.
A dry-run is preliminary; branch protections/token scopes can still reject a
real write. Verify the first actual coherent commit remotely before larger work.

## CI event contract

Push main/build/** and PRs targeting main; Python 3.11.
CI uses scoped concurrency, contents:read, bounded jobs and early environment
checks. Package import/pip check/connectivity success is not product acceptance.
Never print environment variables, tokens, DSNs or credential helper output.

This infrastructure commit uses `[skip ci]` deliberately to preserve execution
capacity and avoid running feature-checkpoint suites in this repair-only run.
No PR is opened for a skipped commit (required checks could remain pending).
Future normal commits must not copy that marker; expected push/PR events will
run the documented workflows. CI execution after these edits is not claimed.

## Audit evidence and recovery

No active-head run expected before repair: push filter excluded build/deterministic-iac; no active PR.

Observed main: `0956f19cb484d4ec8c734832a2a48914626447a7`. Active feature head: `f85b27a57591e17dd939a68303d1e9cf9f480535`.
All current remote feature work was ahead of main, not behind it. Local worktrees
from September 30 had stale refs; some contained uncommitted/untracked work.
Shell access initially failed through an unavailable sandbox proxy; a permitted
network execution context restored read/fetch. Shell GitHub CLI was absent;
connector repository metadata reported push permission. Actual connector
publication must be verified before claiming a durable fix.

`docs/recovery/2026-10-03/` preserves source patches without applying them.
Original worktrees remain untouched. AgentFlight also had a local-only commit
63fcc3d; its patch is archived, not activated or merged. These archives cover the
identified September 30 worktrees, not inaccessible devices or unknown sessions.

## Branch discipline

Use `git fetch --all --prune`, `git merge-base origin/main HEAD`,
`git rev-list --left-right --count origin/main...HEAD` and
`git rev-list --left-right --count HEAD...origin/<active-branch>`.
Inspect dirty status before switching and check `git worktree list`.
No deletions are needed. Historical classifications are in `docs/BRANCH_AUDIT.md`.
Only merge stale main into a feature branch or rebase after reviewing conflicts
and scope; this stabilization does neither. Preserve divergent local variants
for comparison, not automatic integration.
