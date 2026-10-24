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


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _is_noncharacter(char: str) -> bool:
    """Reject Unicode-reserved noncharacters without banning all unassigned codepoints."""
    point = ord(char)
    return 0xFDD0 <= point <= 0xFDEF or (point & 0xFFFE) == 0xFFFE


def _ambiguous_review_characters(value: str) -> bool:
    """Detect characters that can obscure a human-reviewed identity or field."""
    return any(unicodedata.category(char) in ("Cc", "Cf", "Cs", "Zl", "Zp")
               or (unicodedata.category(char) == "Zs" and char != " ")
               or _is_noncharacter(char) for char in value)


def _text(value: object, name: str) -> None:
    if type(value) is not str or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be nonblank text without surrounding whitespace")
    if any(unicodedata.category(char) in ("Cc", "Cf", "Cs", "Zl", "Zp", "Zs")
           or _is_noncharacter(char) for char in value):
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
        return json.dumps(asdict(self), sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def prepare_local_execution_request(
    handoff: DeploymentHandoff, artifact: bytes,
) -> LocalExecutionRequest:
    """Bind an accepted handoff to exact artifact bytes without executing anything."""
    if type(handoff) is not DeploymentHandoff:
        raise ValueError("expected an accepted deployment handoff")
    if type(handoff.request) is not DeploymentRequest:
        raise ValueError("expected a canonical deployment request")
    if (type(handoff.request.format_version) is not int
            or handoff.request.format_version != 1
            or type(handoff.request.operation) is not str
            or handoff.request.operation != "deployment-handoff"):
        raise ValueError("unsupported deployment handoff format or operation")
    # The handoff's digest alone cannot validate caller-constructed metadata.
    # Reject malformed provenance/document fields before deriving execution approval.
    plan_digest = handoff.request.plan_digest
    document = handoff.request.document
    if (type(plan_digest) is not str
            or len(plan_digest) != 64
            or any(char not in "0123456789abcdef" for char in plan_digest)
            or type(document) is not str
            or not document.strip()):
        raise ValueError("malformed handoff provenance or document")
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
    _text(handoff.approved_by, "handoff approved_by")
    if (handoff.infrastructure_mutated is not False or type(handoff.status) is not str
            or handoff.status != "ready-for-adapter-review"):
        raise ValueError("handoff is not eligible for local adapter review")
    if type(handoff.request_digest) is not str or handoff.request_digest != handoff.request.digest:
        raise ValueError("handoff digest does not match its exact request")
    _text(handoff.request.target_id, "target_id")
    if type(artifact) is not bytes:
        raise ValueError("artifact must be exact bytes")
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
    expected = prepare_local_execution_request(handoff, artifact)
    if type(approval) is not LocalExecutionApproval:
        raise ApprovalRequiredError("fresh local execution approval is required")
    if (type(request.format_version) is not int
            or any(type(value) is not str for value in (
                request.handoff_digest, request.target_id,
                request.artifact_sha256, request.handoff_receipt_sha256,
                request.operation))
            or request != expected):
        raise ValueError("request differs from exact local execution inputs")
    try:
        _text(approval.approved_by, "approved_by")
    except ValueError as exc:
        raise ApprovalRequiredError(str(exc)) from exc
    if type(approval.request_digest) is not str or approval.request_digest != expected.digest:
        raise ApprovalRequiredError("approval does not match the exact local execution request")
    return LocalExecutionReceipt(expected, approval.approved_by, expected.digest)
