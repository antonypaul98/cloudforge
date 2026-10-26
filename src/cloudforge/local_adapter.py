"""Bounded local execution authorization. This module never mutates infrastructure."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import asdict, dataclass
from itertools import permutations

from .approval import ApprovalRequiredError, plan_digest as digest_plan
from .deployment import DeploymentHandoff, DeploymentRequest
from .iac import render_iac_proposal
from .models import InfrastructurePlan, ResourceRequirement


_MAX_LOCAL_RECEIPT_JSON_CHARS = 16384
_MAX_LOCAL_HANDOFF_DOCUMENT_CHARS = 65536


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _is_noncharacter(char: str) -> bool:
    """Reject Unicode-reserved noncharacters without banning all unassigned codepoints."""
    point = ord(char)
    return 0xFDD0 <= point <= 0xFDEF or (point & 0xFFFE) == 0xFFFE


def _is_invisible_mark(char: str) -> bool:
    """Reject invisible variation marks and blank filler codepoints in review text."""
    point = ord(char)
    return (point == 0x034F or 0x180B <= point <= 0x180F
            or 0xFE00 <= point <= 0xFE0F or 0xE0100 <= point <= 0xE01EF
            or point in (0x115F, 0x1160, 0x2800, 0x3164, 0xFFA0))


def _ambiguous_review_characters(value: str) -> bool:
    """Detect characters that can obscure a human-reviewed identity or field."""
    return value != value.strip() or any(
        unicodedata.category(char) in ("Cc", "Cf", "Cs", "Zl", "Zp")
        or (unicodedata.category(char) == "Zs" and char != " ")
        or _is_noncharacter(char) or _is_invisible_mark(char) for char in value
    )


def _text(value: object, name: str) -> None:
    if type(value) is not str or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be nonblank text without surrounding whitespace")
    if any(unicodedata.category(char) in ("Cc", "Cf", "Cs", "Zl", "Zp", "Zs")
           or _is_noncharacter(char) or _is_invisible_mark(char) for char in value):
        raise ValueError(f"{name} must not contain control characters")


@dataclass(frozen=True)
class LocalExecutionRequest:
    format_version: int
    handoff_digest: str
    target_id: str
    artifact_sha256: str
    handoff_receipt_sha256: str
    operation: str = "authorize-local-artifact"

    @property
    def digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class LocalExecutionApproval:
    request_digest: str
    approved_by: str


@dataclass(frozen=True)
class LocalExecutionReceipt:
    request: LocalExecutionRequest
    approved_by: str
    request_digest: str
    status: str = "authorized-local-only"
    infrastructure_mutated: bool = False

    def to_json(self) -> str:
        # A local-only receipt must never serialize a forged deployment claim.
        # This check does not authenticate the reviewer or replace revalidation
        # against the original handoff, artifact and execution approval.
        if (type(self.status) is not str or self.status != "authorized-local-only"
                or self.infrastructure_mutated is not False):
            raise ValueError("local-only receipt cannot claim deployment or mutation")
        # Reject malformed internal bindings before a receipt leaves this process.
        # This is structural consistency, not approver authentication; callers
        # still need verify_local_execution_receipt against the original inputs.
        request = self.request
        if type(request) is not LocalExecutionRequest:
            raise ValueError("malformed local-only receipt")
        # A receipt exceeding the ASCII JSON limit cannot be exported. Reject
        # obviously oversized identities before hashing a caller-supplied target.
        if ((type(request.target_id) is str
             and len(request.target_id) > _MAX_LOCAL_RECEIPT_JSON_CHARS)
                or (type(self.approved_by) is str
                    and len(self.approved_by) > _MAX_LOCAL_RECEIPT_JSON_CHARS)):
            raise ValueError("local-only receipt exceeds canonical JSON size limit")
        digest_fields = (request.handoff_digest, request.artifact_sha256,
                         request.handoff_receipt_sha256, self.request_digest)
        if (type(request.format_version) is not int or request.format_version != 1
                or type(request.operation) is not str
                or request.operation != "authorize-local-artifact"
                or any(type(value) is not str or len(value) != 64
                       or any(char not in "0123456789abcdef" for char in value)
                       for value in digest_fields)):
            raise ValueError("malformed local-only receipt")
        try:
            _text(request.target_id, "target_id")
            _text(self.approved_by, "approved_by")
        except ValueError as exc:
            raise ValueError("malformed local-only receipt") from exc
        if self.request_digest != request.digest:
            raise ValueError("malformed local-only receipt")
        serialized = json.dumps(asdict(self), sort_keys=True, indent=2, ensure_ascii=True) + "\n"
        if len(serialized) > _MAX_LOCAL_RECEIPT_JSON_CHARS:
            raise ValueError("local-only receipt exceeds canonical JSON size limit")
        return serialized


def prepare_local_execution_request(
    handoff: DeploymentHandoff, artifact: bytes,
) -> LocalExecutionRequest:
    """Bind an accepted handoff to exact artifact bytes without executing anything."""
    if type(handoff) is not DeploymentHandoff:
        raise ValueError("expected an accepted deployment handoff")
    # Invalid artifact types cannot be hashed. Reject them before the reviewed
    # document is parsed, even when the handoff itself is otherwise valid.
    if type(artifact) is not bytes:
        raise ValueError("artifact must be exact bytes")
    if type(handoff.request) is not DeploymentRequest:
        raise ValueError("expected a canonical deployment request")
    if (type(handoff.request.format_version) is not int
            or handoff.request.format_version != 1
            or type(handoff.request.operation) is not str
            or handoff.request.operation != "deployment-handoff"):
        raise ValueError("unsupported deployment handoff format or operation")
    # Reject malformed or unbounded review identities before parsing the
    # potentially large handoff document. The earlier handoff approval is
    # still only caller-supplied text, not authenticated reviewer evidence.
    for identity, name in ((handoff.request.target_id, "target_id"),
                           (handoff.approved_by, "handoff approved_by")):
        if type(identity) is str and len(identity) > _MAX_LOCAL_RECEIPT_JSON_CHARS:
            raise ValueError("local handoff identity exceeds size limit")
        _text(identity, name)
    # Reject ineligible or forged handoff outcomes before parsing the reviewed
    # document. A local-only execution request cannot derive from deployment.
    if (handoff.infrastructure_mutated is not False
            or type(handoff.status) is not str
            or handoff.status != "ready-for-adapter-review"):
        raise ValueError("handoff is not eligible for local adapter review")
    # The handoff's digest alone cannot validate caller-constructed metadata.
    # Reject malformed provenance/document fields before deriving execution approval.
    plan_digest = handoff.request.plan_digest
    document = handoff.request.document
    if (type(plan_digest) is not str
            or len(plan_digest) != 64
            or any(char not in "0123456789abcdef" for char in plan_digest)
            or type(document) is not str
            or len(document) > _MAX_LOCAL_HANDOFF_DOCUMENT_CHARS
            or not document.strip()):
        raise ValueError("malformed handoff provenance or document")
    # Fail fast on a malformed or stale exact-request digest before parsing
    # reviewed IaC JSON. This is integrity validation, not reviewer identity.
    if (type(handoff.request_digest) is not str
            or len(handoff.request_digest) != 64
            or any(char not in "0123456789abcdef"
                   for char in handoff.request_digest)):
        raise ValueError("malformed handoff request digest")
    if handoff.request_digest != handoff.request.digest:
        raise ValueError("handoff digest does not match its exact request")
    # A caller-constructed handoff can carry a self-consistent digest over
    # malformed text. Require the canonical review-only IaC document shape
    # before deriving any separate local execution authorization.
    try:
        payload = json.loads(document)
        canonical = json.dumps(payload, sort_keys=True, indent=2,
                               ensure_ascii=True, allow_nan=False) + "\n"
        if (type(payload) is not dict
                or set(payload) != {"application", "requires_approval", "resources"}
                or type(payload["application"]) is not str
                or not payload["application"].strip()
                or payload["application"] != payload["application"].strip()
                or payload["requires_approval"] is not True
                or type(payload["resources"]) is not list
                or not 1 <= len(payload["resources"]) <= 4
                or document != canonical
                or any(type(resource) is not dict
                       or set(resource) != {"kind", "reason", "properties"}
                       or type(resource["properties"]) is not dict
                       for resource in payload["resources"])):
            raise ValueError("malformed handoff provenance or document")
        # Reject invisible/control characters in the application identity,
        # while preserving ordinary internal ASCII spaces in display names.
        if _ambiguous_review_characters(payload["application"]):
            raise ValueError("malformed handoff provenance or document")
        # Human-reviewed resource provenance and runtime metadata must not
        # conceal controls, directional formatting or reserved noncharacters.
        # Ordinary internal ASCII spaces and Unicode letters remain valid.
        for resource in payload["resources"]:
            for value in (resource["reason"], *resource["properties"].values()):
                if type(value) is str and _ambiguous_review_characters(value):
                    raise ValueError("malformed handoff provenance or document")
        # Canonical JSON alone does not make the contained requirements valid.
        # Reuse the provider-neutral renderer to enforce kind, property,
        # provenance, uniqueness and deterministic resource ordering.
        parsed_plan = InfrastructurePlan(
            payload["application"],
            tuple(ResourceRequirement(**resource) for resource in payload["resources"]),
            True,
        )
        if render_iac_proposal(parsed_plan).document != document:
            raise ValueError("malformed handoff provenance or document")
        # The document sorts resources, while the reviewed plan digest binds
        # their original order. Check every bounded order (at most 4! = 24)
        # rather than accepting an arbitrary well-formed digest.
        if not any(
            digest_plan(InfrastructurePlan(payload["application"], order, True)) == plan_digest
            for order in permutations(parsed_plan.resources)
        ):
            raise ValueError("malformed handoff provenance or document")
    except (TypeError, ValueError, KeyError, RecursionError) as exc:
        raise ValueError("malformed handoff provenance or document") from exc
    return LocalExecutionRequest(
        1,
        handoff.request_digest,
        handoff.request.target_id,
        hashlib.sha256(artifact).hexdigest(),
        _digest(asdict(handoff)),
    )


def authorize_local_execution(
    handoff: DeploymentHandoff,
    artifact: bytes,
    request: LocalExecutionRequest,
    approval: LocalExecutionApproval | None,
) -> LocalExecutionReceipt:
    """Authorize exact local bytes; deliberately performs no runtime mutation."""
    if type(request) is not LocalExecutionRequest:
        raise ValueError("expected a local execution request")
    # Reject malformed artifact types before expensive handoff revalidation.
    # Only immutable exact bytes may be bound to a local execution approval.
    if type(artifact) is not bytes:
        raise ValueError("artifact must be exact bytes")
    # Reject forged container types before hashing exact artifact bytes. Full
    # provenance and execution-approval validation still follow for valid types.
    if type(handoff) is not DeploymentHandoff:
        raise ValueError("expected an accepted deployment handoff")
    if type(handoff.request) is not DeploymentRequest:
        raise ValueError("expected a canonical deployment request")
    # A receipt cannot export identities longer than the canonical JSON ceiling.
    # Reject those before parsing the handoff or hashing a huge target/reviewer.
    # Other malformed inputs retain their existing validation paths.
    if (type(handoff) is DeploymentHandoff
            and type(handoff.request) is DeploymentRequest
            and type(handoff.request.target_id) is str
            and len(handoff.request.target_id) > _MAX_LOCAL_RECEIPT_JSON_CHARS):
        raise ValueError("local-only receipt exceeds canonical JSON size limit")
    # Bound all other handoff scalar strings before computing the full-handoff
    # digest. A forged multi-megabyte reviewer, operation or provenance field
    # must not enter the pre-parse hashing path.
    if (type(handoff) is DeploymentHandoff
            and type(handoff.request) is DeploymentRequest
            and any(type(value) is str
                    and len(value) > _MAX_LOCAL_RECEIPT_JSON_CHARS
                    for value in (handoff.approved_by, handoff.request.plan_digest,
                                  handoff.request.operation, handoff.request_digest,
                                  handoff.status))):
        raise ValueError("local handoff scalar exceeds size limit")
    if (type(approval) is LocalExecutionApproval
            and type(approval.approved_by) is str
            and len(approval.approved_by) > _MAX_LOCAL_RECEIPT_JSON_CHARS):
        raise ValueError("local-only receipt exceeds canonical JSON size limit")
    # Reject structurally invalid approval before expensive handoff parsing.
    # This is a resource safeguard, not approver authentication.
    if type(approval) is not LocalExecutionApproval:
        raise ApprovalRequiredError("fresh local execution approval is required")
    try:
        _text(approval.approved_by, "approved_by")
    except ValueError as exc:
        raise ApprovalRequiredError(str(exc)) from exc
    if (type(approval.request_digest) is not str
            or len(approval.request_digest) != 64
            or any(char not in "0123456789abcdef"
                   for char in approval.request_digest)):
        raise ApprovalRequiredError("malformed local execution approval digest")
    # Fail closed on malformed caller-supplied request metadata before parsing
    # the potentially large reviewed handoff. Exact-request equality and fresh
    # approval verification still follow; this is not reviewer authentication.
    if (type(request.format_version) is not int or request.format_version != 1
            or type(request.operation) is not str
            or request.operation != "authorize-local-artifact"
            or any(type(value) is not str or len(value) != 64
                   or any(char not in "0123456789abcdef" for char in value)
                   for value in (request.handoff_digest, request.artifact_sha256,
                                 request.handoff_receipt_sha256))):
        raise ValueError("malformed local execution request")
    if type(request.target_id) is str and len(request.target_id) > _MAX_LOCAL_RECEIPT_JSON_CHARS:
        raise ValueError("local-only receipt exceeds canonical JSON size limit")
    try:
        _text(request.target_id, "target_id")
    except ValueError as exc:
        raise ValueError("malformed local execution request") from exc
    # A malformed or oversized reviewed document cannot authorize local work.
    # Reject it before hashing potentially large artifact bytes. Full canonical
    # document and provenance validation still occurs in preparation below.
    if (type(handoff) is DeploymentHandoff
            and type(handoff.request) is DeploymentRequest
            and (type(handoff.request.document) is not str
                 or len(handoff.request.document) > _MAX_LOCAL_HANDOFF_DOCUMENT_CHARS
                 or not handoff.request.document.strip())):
        raise ValueError("malformed handoff provenance or document")
    # A forged or ineligible handoff must not trigger artifact hashing.
    # Full canonical handoff validation still follows for eligible inputs.
    if (type(handoff) is DeploymentHandoff
            and (handoff.infrastructure_mutated is not False
                 or type(handoff.status) is not str
                 or handoff.status != "ready-for-adapter-review")):
        raise ValueError("handoff is not eligible for local adapter review")
    # Fail closed on malformed handoff metadata before hashing artifact bytes.
    # The full provenance/document validation still runs for eligible inputs.
    if (type(handoff) is DeploymentHandoff
            and type(handoff.request) is DeploymentRequest
            and (type(handoff.request.format_version) is not int
                 or handoff.request.format_version != 1
                 or type(handoff.request.operation) is not str
                 or handoff.request.operation != "deployment-handoff"
                 or type(handoff.request.plan_digest) is not str
                 or len(handoff.request.plan_digest) != 64
                 or any(char not in "0123456789abcdef"
                        for char in handoff.request.plan_digest))):
        raise ValueError("malformed handoff request metadata")
    # Reject stale target/handoff bindings before parsing reviewed IaC JSON.
    # The full handoff, artifact and approval checks remain mandatory below.
    if (type(handoff) is DeploymentHandoff
            and type(handoff.request) is DeploymentRequest
            and (request.target_id != handoff.request.target_id
                 or request.handoff_digest != handoff.request_digest)):
        raise ValueError("request differs from exact local execution inputs")
    # A handoff's recorded digest must still bind its exact reviewed request.
    # Check this bounded request before hashing potentially large artifact bytes.
    # Full canonical IaC and approval validation remains mandatory below.
    if (type(handoff) is DeploymentHandoff
            and type(handoff.request) is DeploymentRequest
            and handoff.request_digest != handoff.request.digest):
        raise ValueError("handoff digest does not match its exact request")
    # Preserve artifact-mismatch precedence when approval itself is stale.
    # A matching caller-supplied digest permits an early handoff receipt check;
    # it does not authenticate the reviewer.
    approval_matches_request = approval.request_digest == request.digest
    # An ambiguous claimed handoff reviewer cannot authorize even local work.
    # Fail before hashing artifact bytes when approval matches the request;
    # the full exact-input validation still follows for eligible handoffs.
    if approval_matches_request and type(handoff) is DeploymentHandoff:
        _text(handoff.approved_by, "handoff approved_by")
    # A handoff can change its claimed reviewer or receipt metadata without
    # changing the embedded request digest. Reject stale full-handoff binding
    # before parsing reviewed IaC, but only for bounded scalar handoffs.
    # Malformed/oversized handoffs retain the full preparation validation path.
    if (approval_matches_request
            and type(handoff) is DeploymentHandoff
            and type(handoff.request) is DeploymentRequest
            and type(handoff.request.document) is str
            and len(handoff.request.document) <= _MAX_LOCAL_HANDOFF_DOCUMENT_CHARS
            and type(handoff.request.format_version) is int
            and all(type(value) is str for value in (
                handoff.request.plan_digest, handoff.request.target_id,
                handoff.request.operation, handoff.approved_by,
                handoff.request_digest, handoff.status))
            and type(handoff.infrastructure_mutated) is bool
            and request.handoff_receipt_sha256 != _digest(asdict(handoff))):
        raise ValueError("request differs from exact local execution inputs")
    # Fail fast on stale exact-artifact bindings before parsing reviewed IaC.
    # Only immutable bytes are accepted above; this hash has no side effects.
    if request.artifact_sha256 != hashlib.sha256(artifact).hexdigest():
        raise ValueError("request differs from exact local execution inputs")
    if not approval_matches_request:
        raise ApprovalRequiredError("approval does not match the exact local execution request")
    expected = prepare_local_execution_request(handoff, artifact)
    if (type(request.format_version) is not int
            or any(type(value) is not str for value in (
                request.handoff_digest, request.target_id,
                request.artifact_sha256, request.handoff_receipt_sha256,
                request.operation))
            or request != expected):
        raise ValueError("request differs from exact local execution inputs")
    if approval.request_digest != expected.digest:
        raise ApprovalRequiredError("approval does not match the exact local execution request")
    receipt = LocalExecutionReceipt(expected, approval.approved_by, expected.digest)
    # Fail closed at authorization if the receipt cannot be represented by the
    # bounded canonical JSON format required for subsequent verification.
    receipt.to_json()
    return receipt

def verify_local_execution_receipt(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
) -> bool:
    """Recheck exact local-only authorization; never authenticate a person or deploy."""
    if type(receipt) is not LocalExecutionReceipt:
        raise ValueError("expected a local execution receipt")
    # Dataclass equality alone equates bool/int values (False == 0, True == 1).
    # Validate types before comparing the complete immutable receipt.
    if (type(receipt.request) is not LocalExecutionRequest
            or type(receipt.request.format_version) is not int
            or type(receipt.approved_by) is not str
            or type(receipt.request_digest) is not str
            or type(receipt.status) is not str
            or type(receipt.infrastructure_mutated) is not bool):
        raise ValueError("malformed local execution receipt")
    # A forged local-only receipt must not trigger artifact hashing or full
    # handoff revalidation. Type checks above prevent bool/int equivalence.
    if (receipt.status != "authorized-local-only"
            or receipt.infrastructure_mutated is not False):
        raise ValueError("local-only receipt cannot claim deployment or mutation")
    # When the supplied execution approval is bound to this same request,
    # reject a forged receipt reviewer before hashing artifact bytes. Stale
    # approvals still follow the normal ApprovalRequiredError path below.
    # Matching caller-supplied names are not proof of authenticated identity.
    if (type(approval) is LocalExecutionApproval
            and approval.request_digest == receipt.request_digest
            and type(approval.approved_by) is str
            and receipt.approved_by != approval.approved_by):
        raise ValueError("receipt differs from exact local execution authorization")
    expected = authorize_local_execution(handoff, artifact, receipt.request, approval)
    if receipt != expected:
        raise ValueError("receipt differs from exact local execution authorization")
    return True


def verify_local_execution_receipt_json(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt_json: str,
) -> bool:
    """Validate canonical receipt JSON against exact original authorization inputs."""
    if type(receipt_json) is not str or len(receipt_json) > _MAX_LOCAL_RECEIPT_JSON_CHARS:
        raise ValueError("expected bounded canonical local receipt JSON")
    try:
        payload = json.loads(receipt_json)
        if type(payload) is not dict or set(payload) != {
            "request", "approved_by", "request_digest", "status", "infrastructure_mutated"
        }:
            raise ValueError("unexpected local receipt fields")
        request_payload = payload["request"]
        if type(request_payload) is not dict or set(request_payload) != {
            "format_version", "handoff_digest", "target_id", "artifact_sha256",
            "handoff_receipt_sha256", "operation"
        }:
            raise ValueError("unexpected local request fields")
        receipt = LocalExecutionReceipt(
            LocalExecutionRequest(**request_payload), payload["approved_by"],
            payload["request_digest"], payload["status"], payload["infrastructure_mutated"],
        )
        if receipt.to_json() != receipt_json:
            raise ValueError("noncanonical local receipt JSON")
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        raise ValueError("malformed local execution receipt JSON") from exc
    return verify_local_execution_receipt(handoff, artifact, approval, receipt)


def export_local_execution_audit_event(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
) -> str:
    """Emit deterministic, redacted local-only evidence after exact revalidation.

    This is an integrity-checked observation, not an authenticated signature,
    reviewer identity proof, infrastructure observation or execution result.
    """
    verify_local_execution_receipt(handoff, artifact, approval, receipt)
    canonical_receipt = receipt.to_json()
    event = {
        "format_version": 1,
        "request_digest": receipt.request_digest,
        "receipt_sha256": hashlib.sha256(canonical_receipt.encode("ascii")).hexdigest(),
        "status": "authorized-local-only",
        "infrastructure_mutated": False,
    }
    return json.dumps(event, sort_keys=True, indent=2, ensure_ascii=True) + "\n"

# A redacted audit event is comparable evidence, not an authenticated signature.
# Keep the input bound small before deriving any trusted expected event.
_MAX_LOCAL_AUDIT_JSON_CHARS = 1024


def verify_local_execution_audit_event(
    handoff: DeploymentHandoff,
    artifact: bytes,
    approval: LocalExecutionApproval | None,
    receipt: LocalExecutionReceipt,
    audit_json: str,
) -> bool:
    """Recheck a canonical redacted audit event against exact original inputs."""
    if type(audit_json) is not str or len(audit_json) > _MAX_LOCAL_AUDIT_JSON_CHARS:
        raise ValueError("expected bounded canonical local audit event JSON")
    # Reject malformed evidence before expensive original-input revalidation.
    # Canonical structure is not authenticity: exact receipt/approval checks follow.
    try:
        payload = json.loads(audit_json)
        if (type(payload) is not dict
                or set(payload) != {"format_version", "request_digest",
                                   "receipt_sha256", "status", "infrastructure_mutated"}
                or type(payload["format_version"]) is not int
                or payload["format_version"] != 1
                or payload["status"] != "authorized-local-only"
                or type(payload["status"]) is not str
                or payload["infrastructure_mutated"] is not False
                or any(type(payload[key]) is not str
                       or len(payload[key]) != 64
                       or any(char not in "0123456789abcdef" for char in payload[key])
                       for key in ("request_digest", "receipt_sha256"))
                or audit_json != json.dumps(payload, sort_keys=True, indent=2,
                                            ensure_ascii=True, allow_nan=False) + "\n"):
            raise ValueError("noncanonical audit event")
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        raise ValueError("malformed canonical local audit event") from exc
    # Reject stale canonical audit bindings before revalidating original inputs.
    # This comparison is not proof that a caller-supplied receipt is authentic.
    if (type(receipt) is not LocalExecutionReceipt
            or type(receipt.request_digest) is not str
            or payload["request_digest"] != receipt.request_digest):
        raise ValueError("local audit event differs from exact local authorization")
    if payload["receipt_sha256"] != hashlib.sha256(
        receipt.to_json().encode("ascii")
    ).hexdigest():
        raise ValueError("local audit event differs from exact local authorization")
    if audit_json != export_local_execution_audit_event(handoff, artifact, approval, receipt):
        raise ValueError("local audit event differs from exact local authorization")
    return True
