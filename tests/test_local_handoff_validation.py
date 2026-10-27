"""Fail-closed metadata regressions for the local-only adapter checkpoint."""
from dataclasses import replace
import pytest

from cloudforge.deployment import DeploymentApproval, authorize_deployment_handoff, prepare_deployment_request
from cloudforge.iac import render_iac_proposal
from cloudforge.local_adapter import prepare_local_execution_request
from cloudforge.models import ApplicationProfile
from cloudforge.planner import derive_requirements


def _handoff():
    plan = derive_requirements(ApplicationProfile("api", "python", port=8080))
    proposal = render_iac_proposal(plan)
    request = prepare_deployment_request(plan, proposal, "staging")
    return authorize_deployment_handoff(plan, proposal, request, DeploymentApproval(request.digest, "reviewer"))


@pytest.mark.parametrize("field,value", [
    ("format_version", 2), ("format_version", True), ("format_version", "1"), ("operation", "deploy"), ("operation", None),
])
def test_forged_handoff_metadata_fails_closed(field, value):
    handoff = _handoff()
    forged_request = replace(handoff.request, **{field: value})
    forged_handoff = replace(handoff, request=forged_request, request_digest=forged_request.digest)
    with pytest.raises(ValueError):
        prepare_local_execution_request(forged_handoff, b"exact artifact")


@pytest.mark.parametrize("name", ["", " ", "bad\nname", "bad\x00name", " reviewer", "reviewer ", None, 42])
def test_forged_handoff_approver_fails_closed(name):
    handoff = _handoff()
    with pytest.raises(ValueError):
        prepare_local_execution_request(replace(handoff, approved_by=name), b"exact artifact")


def test_noncanonical_handoff_request_type_fails_closed():
    handoff = _handoff()
    forged_handoff = replace(handoff, request={"target_id": "staging"}, request_digest="0" * 64)
    with pytest.raises(ValueError):
        prepare_local_execution_request(forged_handoff, b"exact artifact")


@pytest.mark.parametrize("separator", [chr(0x00A0), chr(0x2007), chr(0x202F)])
def test_ambiguous_unicode_space_separators_fail_closed(separator):
    """Visually ambiguous Unicode space separators must not enter exact identity bindings."""
    from cloudforge.approval import ApprovalRequiredError
    from cloudforge.local_adapter import LocalExecutionApproval, authorize_local_execution
    handoff = _handoff()
    artifact = b"reviewed artifact"
    changed_request = replace(handoff.request, target_id="prod" + separator + "west")
    changed_handoff = replace(handoff, request=changed_request, request_digest=changed_request.digest)
    with pytest.raises(ValueError):
        prepare_local_execution_request(changed_handoff, artifact)
    with pytest.raises(ValueError):
        prepare_local_execution_request(replace(handoff, approved_by="review" + separator + "er"), artifact)
    execution = prepare_local_execution_request(handoff, artifact)
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(
            handoff, artifact, execution,
            LocalExecutionApproval(execution.digest, "review" + separator + "er"),
        )


class _AlwaysEqual:
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


class _NoncanonicalString(str):
    pass


def test_handoff_digest_comparator_cannot_bypass_binding():
    handoff = _handoff()
    with pytest.raises(ValueError):
        prepare_local_execution_request(replace(handoff, request_digest=_AlwaysEqual()), b"artifact")


def test_handoff_status_comparator_cannot_bypass_review_gate():
    handoff = _handoff()
    with pytest.raises(ValueError):
        prepare_local_execution_request(replace(handoff, status=_AlwaysEqual()), b"artifact")


@pytest.mark.parametrize("field", ["operation", "target_id"])
def test_handoff_request_rejects_string_subclasses(field):
    handoff = _handoff()
    request = replace(handoff.request, **{field: _NoncanonicalString(getattr(handoff.request, field))})
    forged = replace(handoff, request=request, request_digest=request.digest)
    with pytest.raises(ValueError):
        prepare_local_execution_request(forged, b"artifact")


def test_handoff_approver_rejects_string_subclass():
    handoff = _handoff()
    with pytest.raises(ValueError):
        prepare_local_execution_request(replace(handoff, approved_by=_NoncanonicalString("reviewer")), b"artifact")


def test_execution_approval_digest_rejects_custom_comparator():
    from cloudforge.approval import ApprovalRequiredError
    from cloudforge.local_adapter import LocalExecutionApproval, authorize_local_execution
    handoff = _handoff()
    artifact = b"artifact"
    request = prepare_local_execution_request(handoff, artifact)
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(handoff, artifact, request, LocalExecutionApproval(_AlwaysEqual(), "reviewer"))


@pytest.mark.parametrize("field", ["handoff_digest", "target_id", "artifact_sha256", "operation"])
def test_execution_request_rejects_custom_comparators(field):
    from cloudforge.local_adapter import LocalExecutionApproval, authorize_local_execution
    handoff = _handoff()
    artifact = b"artifact"
    request = prepare_local_execution_request(handoff, artifact)
    forged = replace(request, **{field: _AlwaysEqual()})
    with pytest.raises(ValueError):
        authorize_local_execution(handoff, artifact, forged, LocalExecutionApproval(request.digest, "reviewer"))


def test_execution_approver_rejects_string_subclass():
    from cloudforge.approval import ApprovalRequiredError
    from cloudforge.local_adapter import LocalExecutionApproval, authorize_local_execution
    handoff = _handoff()
    artifact = b"artifact"
    request = prepare_local_execution_request(handoff, artifact)
    with pytest.raises(ApprovalRequiredError):
        authorize_local_execution(handoff, artifact, request, LocalExecutionApproval(request.digest, _NoncanonicalString("reviewer")))

@pytest.mark.parametrize("bad_digest", [
    None, True, "", "0" * 63, "G" * 64, "0" * 65,
    _AlwaysEqual(), _NoncanonicalString("0" * 64),
])
def test_malformed_handoff_digest_fails_before_document_parse(monkeypatch, bad_digest):
    handoff = replace(_handoff(), request_digest=bad_digest)

    def forbidden(*args, **kwargs):
        raise AssertionError("malformed digest must fail before JSON parsing")

    monkeypatch.setattr("cloudforge.local_adapter.json.loads", forbidden)
    with pytest.raises(ValueError, match="malformed handoff request digest"):
        prepare_local_execution_request(handoff, b"artifact")


def test_stale_handoff_digest_fails_before_document_parse(monkeypatch):
    handoff = _handoff()
    stale = "0" * 64 if handoff.request_digest != "0" * 64 else "f" * 64

    def forbidden(*args, **kwargs):
        raise AssertionError("stale digest must fail before JSON parsing")

    monkeypatch.setattr("cloudforge.local_adapter.json.loads", forbidden)
    with pytest.raises(ValueError, match="handoff digest does not match"):
        prepare_local_execution_request(replace(handoff, request_digest=stale), b"artifact")
