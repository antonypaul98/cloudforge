"""Bounded keyed policy for selected-source sandbox proposals, no execution."""
from dataclasses import replace
import hashlib
import json
import os
import socket
import subprocess

import pytest

from cloudforge.demo_selected_artifact import prepare_selected_artifact
from cloudforge.demo_source_package import package_selected_source
from cloudforge.demo_selected_execution_permit import (
    SelectedSandboxPermit, issue_selected_sandbox_permit,
    verify_selected_sandbox_permit,
)

KEY = b"independent-operator-key-32bytes-minimum"
PIN = hashlib.sha256(KEY).hexdigest()
IMAGE = "docker.io/library/python@sha256:" + "a" * 64


def _case(*, source=b"print('private-source')\n",
          manifests=None, target="isolated-demo", image=IMAGE,
          entrypoint="app.py"):
    if manifests is None:
        manifests = {"requirements.txt": "redis>=5\n# private-manifest\n"}
    raw = package_selected_source("fixture", manifests, target, entrypoint, source)
    review = prepare_selected_artifact(
        "fixture", manifests, target, entrypoint, source,
    )
    return {
        "package_bytes": raw,
        "expected_package_sha256": hashlib.sha256(raw).hexdigest(),
        "expected_review_binding_digest": review["selected_source_binding"]["digest"],
        "expected_target_id": target,
        "image_ref": image,
        "operator_key": KEY,
        "trusted_operator_key_sha256": PIN,
    }


def _issued(case=None, **kwargs):
    return issue_selected_sandbox_permit(
        **(case or _case()), sequence=7, valid_from_unix=1000,
        valid_until_unix=1200, **kwargs,
    )


def _verify(permit, case=None, *, sequence=7, now_unix=1100):
    return verify_selected_sandbox_permit(
        **(case or _case()), permit=permit, sequence=sequence,
        now_unix=now_unix,
    )


@pytest.mark.parametrize("entrypoint,manifests,source,image", [
    ("app.py", {"requirements.txt": "redis>=5\n"}, b"print('ok')\n", IMAGE),
    ("server.js", {"package.json": '{"dependencies":{"express":"^4"}}'},
     b"console.log('ok')\n", "docker.io/library/node@sha256:" + "b" * 64),
])
def test_python_and_node_permits_are_deterministic(entrypoint, manifests, source, image):
    case = _case(entrypoint=entrypoint, manifests=manifests, source=source, image=image)
    first = _issued(case)
    assert first == _issued(case)
    assert _verify(first, case)
    assert first.format_version == 1
    assert first.proposal_sha256 != first.mac_sha256
    assert set(first.__dict__) == {
        "format_version", "proposal_sha256", "operator_key_sha256",
        "sequence", "valid_from_unix", "valid_until_unix", "mac_sha256",
    }


@pytest.mark.parametrize("changed", [
    {"source": b"print('changed')\n"},
    {"manifests": {"requirements.txt": "redis>=6\n"}},
    {"target": "other-target"},
    {"image": "docker.io/library/python@sha256:" + "b" * 64},
])
def test_source_manifest_target_and_image_changes_reject_old_permit(changed):
    original = _issued()
    with pytest.raises(ValueError, match="differs from exact policy"):
        _verify(original, _case(**changed))


def test_old_package_with_new_expected_digest_rejected_before_mac():
    original = _issued()
    changed = _case(source=b"print('different')\n")
    original_case = _case()
    original_case["expected_package_sha256"] = changed["expected_package_sha256"]
    with pytest.raises(ValueError, match="package digest differs"):
        _verify(original, original_case)


@pytest.mark.parametrize("bad", [
    None, "", "0" * 64, "A" * 64, "f" * 63, True,
])
def test_independent_operator_key_pin_is_mandatory(bad):
    case = _case()
    case["trusted_operator_key_sha256"] = bad
    with pytest.raises(ValueError, match="pin"):
        _issued(case)


def test_wrong_key_and_forged_mac_rejected():
    permit = _issued()
    case = _case()
    case["operator_key"] = b"another-independent-operator-key-32bytes"
    with pytest.raises(ValueError, match="pin"):
        _verify(permit, case)
    with pytest.raises(ValueError, match="differs from exact policy"):
        _verify(replace(permit, mac_sha256="f" * 64))


@pytest.mark.parametrize("sequence,now_unix", [
    (8, 1100), (7, 999), (7, 1201), (True, 1100),
    (7, True), (7, -1), (7, 1 << 63),
])
def test_expired_future_or_replayed_sequence_fails_closed(sequence, now_unix):
    with pytest.raises(ValueError, match="expired or differs"):
        _verify(_issued(), sequence=sequence, now_unix=now_unix)


@pytest.mark.parametrize("sequence,start,end", [
    (0, 1000, 1200), (True, 1000, 1200),
    (7, True, 1200), (7, 1000, True),
    (7, -1, 1200), (7, 1000, 1000),
    (7, 1000, 1301), (7, 1000, 1 << 63),
])
def test_invalid_issue_window_or_sequence_fails_closed(sequence, start, end):
    with pytest.raises(ValueError, match="invalid selected sandbox permit"):
        issue_selected_sandbox_permit(
            **_case(), sequence=sequence,
            valid_from_unix=start, valid_until_unix=end,
        )


@pytest.mark.parametrize("field,value", [
    ("format_version", True), ("proposal_sha256", "a" * 63),
    ("operator_key_sha256", "B" * 64), ("mac_sha256", "a" * 63),
    ("valid_until_unix", 1301), ("sequence", True),
])
def test_forged_shape_fails_closed(field, value):
    with pytest.raises(ValueError, match="invalid selected sandbox permit"):
        _verify(replace(_issued(), **{field: value}))


def test_permit_never_contains_raw_source_or_manifest_or_key():
    case = _case()
    permit = _issued(case)
    encoded = json.dumps(permit.__dict__)
    for secret in ("private-source", "private-manifest", KEY.decode()):
        assert secret not in encoded
    assert _verify(permit, case)


def test_keyed_policy_never_executes_or_opens_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("keyed policy must not execute or open network")
    with monkeypatch.context() as guard:
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(subprocess, "run", forbidden)
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(os, "system", forbidden)
        permit = _issued()
        assert _verify(permit)


def test_permit_is_not_an_execution_approval_or_replay_ledger():
    permit = _issued()
    assert isinstance(permit, SelectedSandboxPermit)
    assert _verify(permit)
    # This intentionally proves a limitation: verification is stateless.
    # A future executor MUST atomically consume the sequence separately.
    assert _verify(permit)
