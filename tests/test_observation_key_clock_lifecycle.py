"""Fixture-only key rotation, clock and sequence lifecycle regressions.

No real collector, secret provisioning, clock trust or service health is implied.
"""
import sqlite3

import pytest

from cloudforge.deployment import (
    DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request,
)
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import (
    LocalExecutionApproval, authorize_local_execution, prepare_local_execution_request,
)
from cloudforge.models import ApplicationProfile
from cloudforge.observation_evidence import (
    ObservationSample, sign_observation_evidence,
)
from cloudforge.observation_plan import ObservationProbe, prepare_observation_plan
from cloudforge.observation_replay import accept_observation_evidence_durably
from cloudforge.planner import derive_requirements

_OLD_KEY = bytes(range(32))
_NEW_KEY = bytes(range(1, 33))
_AT = 1_800_000_000
_NOW = _AT + 15
_MAX_SEQUENCE = (1 << 63) - 1


def _context():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "fixture")
    handoff = authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "fixture-reviewer"),
    )
    artifact = b"key-clock-fixture-artifact"
    local_request = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(local_request.digest, "fixture-approver")
    receipt = authorize_local_execution(handoff, artifact, local_request, approval)
    observation_plan = prepare_observation_plan(
        handoff, artifact, approval, receipt,
        (ObservationProbe("readiness", 10, 2, 3),
         ObservationProbe("liveness", 30, 5, 5)),
    )
    return handoff, artifact, approval, receipt, observation_plan


def _sign(context, *, key=_OLD_KEY, seq=1, observed_at=_AT):
    return sign_observation_evidence(
        context[-1],
        (ObservationSample("readiness", "unknown", 0),
         ObservationSample("liveness", "fail", 7)),
        "fixture-source", observed_at, seq, key,
    )


def _accept(context, evidence, path, *, key=_OLD_KEY, now=_NOW):
    return accept_observation_evidence_durably(
        *context, evidence, expected_source_id="fixture-source",
        source_key=key, now_unix=now, max_age_seconds=30,
        ledger_path=str(path),
    )


def _last_sequence(path):
    with sqlite3.connect(path) as db:
        return db.execute(
            "SELECT last_sequence FROM observation_replay"
        ).fetchone()[0]


def test_rotated_key_does_not_reset_source_sequence(tmp_path):
    context = _context()
    path = tmp_path / "replay.db"
    assert _accept(context, _sign(context), path)
    # The configured verifier key has changed; an old-key MAC is rejected
    # before the durable counter can be advanced.
    with pytest.raises(ValueError, match="MAC is invalid"):
        _accept(context, _sign(context, seq=2), path, key=_NEW_KEY)
    assert _last_sequence(path) == 1
    # New-key evidence cannot restart the counter under the same source alias.
    with pytest.raises(ValueError, match="already accepted"):
        _accept(context, _sign(context, key=_NEW_KEY, seq=1), path, key=_NEW_KEY)
    assert _accept(context, _sign(context, key=_NEW_KEY, seq=2), path, key=_NEW_KEY)
    assert _last_sequence(path) == 2
    with pytest.raises(ValueError, match="already accepted"):
        _accept(context, _sign(context, key=_NEW_KEY, seq=2), path, key=_NEW_KEY)
    assert _last_sequence(path) == 2


def test_clock_rollback_stale_and_future_evidence_do_not_advance_ledger(tmp_path):
    context = _context()
    path = tmp_path / "replay.db"
    assert _accept(context, _sign(context), path)
    for evidence, now in (
        (_sign(context, seq=2), _AT - 1),
        (_sign(context, seq=2, observed_at=_AT - 40), _NOW),
        (_sign(context, seq=2, observed_at=_NOW + 1), _NOW),
    ):
        with pytest.raises(ValueError, match="stale or future-dated"):
            _accept(context, evidence, path, now=now)
        assert _last_sequence(path) == 1
    assert _accept(context, _sign(context, seq=2), path)
    assert _last_sequence(path) == 2


def test_max_sequence_cannot_wrap_or_restart(tmp_path):
    context = _context()
    path = tmp_path / "replay.db"
    assert _accept(context, _sign(context, seq=_MAX_SEQUENCE), path)
    with pytest.raises(ValueError, match="malformed observation evidence"):
        _sign(context, seq=_MAX_SEQUENCE + 1)
    with pytest.raises(ValueError, match="already accepted"):
        _accept(context, _sign(context, seq=1), path)
    assert _last_sequence(path) == _MAX_SEQUENCE
