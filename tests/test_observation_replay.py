"""Credential-free persistence, replay and concurrency regressions."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
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


_KEY = bytes(range(32))


def _context(target="staging"):
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, target)
    handoff = authorize_deployment_handoff(
        plan, proposal, request, DeploymentApproval(request.digest, "fixture-reviewer"),
    )
    artifact = b"fixture-observation-bytes"
    local_request = prepare_local_execution_request(handoff, artifact)
    approval = LocalExecutionApproval(local_request.digest, "fixture-approver")
    receipt = authorize_local_execution(handoff, artifact, local_request, approval)
    observation_plan = prepare_observation_plan(
        handoff, artifact, approval, receipt,
        (ObservationProbe("readiness", 10, 2, 3),
         ObservationProbe("liveness", 30, 5, 5)),
    )
    return handoff, artifact, approval, receipt, observation_plan


def _evidence(context, *, source="collector-1", seq=1, key=_KEY):
    return sign_observation_evidence(
        context[-1],
        (ObservationSample("readiness", "pass", 21),
         ObservationSample("liveness", "unknown", 0)),
        source, 1_800_000_000, seq, key,
    )


def _accept(context, evidence, path, **overrides):
    args = dict(expected_source_id=evidence.source_id, source_key=_KEY,
                now_unix=1_800_000_015, max_age_seconds=30,
                ledger_path=str(path))
    args.update(overrides)
    return accept_observation_evidence_durably(
        *context, evidence, **args,
    )


def test_acceptance_survives_reopen_and_rejects_replay(tmp_path):
    path = tmp_path / "replay.sqlite3"
    context = _context()
    first = _evidence(context)
    assert _accept(context, first, path) is True
    with pytest.raises(ValueError, match="already accepted"):
        _accept(context, first, path)
    assert _accept(context, _evidence(context, seq=2), path) is True
    with pytest.raises(ValueError, match="already accepted"):
        _accept(context, first, path)
    with sqlite3.connect(path) as db:
        assert db.execute(
            "SELECT source_id, last_sequence FROM observation_replay"
        ).fetchall() == [("collector-1", 2)]
        columns = {row[1] for row in db.execute("PRAGMA table_info(observation_replay)")}
    assert columns == {"plan_sha256", "source_id", "last_sequence"}


def test_invalid_mac_and_stale_evidence_never_open_database(tmp_path):
    path = tmp_path / "replay.sqlite3"
    context = _context()
    valid = _evidence(context)
    for evidence, kwargs in (
        (replace(valid, mac_sha256="0" * 64), {}),
        (valid, {"source_key": bytes(range(1, 33))}),
        (valid, {"now_unix": 1_800_000_500}),
    ):
        with pytest.raises(ValueError):
            _accept(context, evidence, path, **kwargs)
        assert not path.exists()


def test_plan_and_source_replay_namespaces_are_independent(tmp_path):
    path = tmp_path / "replay.sqlite3"
    context = _context()
    different_plan = _context(target="other-target")
    assert _accept(context, _evidence(context), path)
    assert _accept(context, _evidence(context, source="collector-2"), path)
    assert _accept(different_plan, _evidence(different_plan), path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM observation_replay").fetchone()[0] == 3


def test_two_concurrent_acceptors_cannot_both_accept_same_sequence(tmp_path):
    path = tmp_path / "replay.sqlite3"
    context = _context()
    evidence = _evidence(context)

    def attempt():
        try:
            return _accept(context, evidence, path)
        except ValueError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert results.count(True) == 1
    assert sum(isinstance(x, str) and "already accepted" in x for x in results) == 1


def test_corrupted_existing_database_fails_closed(tmp_path):
    path = tmp_path / "replay.sqlite3"
    path.write_bytes(b"not a SQLite database")
    with pytest.raises(ValueError, match="ledger unavailable"):
        context = _context()
        _accept(context, _evidence(context), path)
    assert path.read_bytes() == b"not a SQLite database"


@pytest.mark.parametrize("invalid_path", ["", "relative.db", ":memory:", "file:replay.db", True, None])
def test_ledger_requires_explicit_absolute_filename(tmp_path, invalid_path):
    context = _context()
    with pytest.raises(ValueError, match="absolute local file"):
        _accept(context, _evidence(context), tmp_path / "unused.db",
                ledger_path=invalid_path)


def test_durable_verifier_does_not_use_network_shell_or_wall_clock(tmp_path, monkeypatch):
    import os
    import socket
    import subprocess
    import time

    def forbidden(*args, **kwargs):
        raise AssertionError("durable verification must not use external services")

    context = _context()
    with monkeypatch.context() as guard:
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(os, "system", forbidden)
        guard.setattr(time, "time", forbidden)
        assert _accept(context, _evidence(context), tmp_path / "replay.db")
