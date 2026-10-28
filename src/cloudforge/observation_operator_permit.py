"""Short-lived, separately keyed permit for the opt-in loopback HEAD fixture.

This MAC checks caller-supplied operator policy, not operator identity. An
independently protected key and trusted clock are mandatory for real use.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import asdict, dataclass, replace

from .observation_evidence import _validate_source
from .observation_http import LoopbackHTTPProbeTarget, _validate_targets
from .observation_plan import ObservationPlan

_MAX_UNIX = (1 << 63) - 1


@dataclass(frozen=True)
class LoopbackOperatorPermit:
    format_version: int
    plan_sha256: str
    targets_sha256: str
    source_id: str
    source_key_sha256: str
    valid_from_unix: int
    valid_until_unix: int
    mac_sha256: str
    ledger_path_sha256: str | None = None
    sequence: int | None = None


def _hex_digest(value: object) -> bool:
    return (type(value) is str and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def _validate_context(plan, targets, source_id, source_key, operator_key):
    _validate_targets(plan, targets, targets)
    _validate_source(source_id, source_key)
    if (type(operator_key) is not bytes or not 32 <= len(operator_key) <= 128
            or hmac.compare_digest(source_key, operator_key)):
        raise ValueError("operator permit requires a distinct 32-128-byte key")


def _target_digest(targets: tuple[LoopbackHTTPProbeTarget, ...]) -> str:
    body = json.dumps([asdict(target) for target in targets],
                      sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")
    return hashlib.sha256(body).hexdigest()


def _ledger_scope_digest(ledger_path: str, sequence: int) -> str:
    """Bind one replay-ledger attempt without opening the filesystem."""
    if (type(ledger_path) is not str or not ledger_path
            or not os.path.isabs(ledger_path) or "\x00" in ledger_path
            or os.path.normpath(ledger_path) != ledger_path
            or type(sequence) is not int
            or not 1 <= sequence <= _MAX_UNIX):
        raise ValueError("invalid scoped operator permit ledger or sequence")
    try:
        encoded = ledger_path.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("invalid scoped operator permit ledger or sequence") from exc
    if len(encoded) > 4096:
        raise ValueError("invalid scoped operator permit ledger or sequence")
    return hashlib.sha256(encoded).hexdigest()


def _permit_bytes(permit: LoopbackOperatorPermit) -> bytes:
    body = asdict(permit)
    del body["mac_sha256"]
    if permit.format_version == 1:
        # Keep the exact original v1 MAC bytes for backwards compatibility.
        del body["ledger_path_sha256"]
        del body["sequence"]
        body["operation"] = "loopback-head-only-v1"
    else:
        body["operation"] = "loopback-head-one-shot-v2"
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def issue_loopback_operator_permit(
    plan: ObservationPlan,
    targets: tuple[LoopbackHTTPProbeTarget, ...],
    *,
    source_id: str,
    source_key: bytes,
    operator_key: bytes,
    valid_from_unix: int,
    valid_until_unix: int,
    ledger_path: str | None = None,
    sequence: int | None = None,
) -> LoopbackOperatorPermit:
    """Issue a MAC-bound fixture permit using an independently held key."""
    _validate_context(plan, targets, source_id, source_key, operator_key)
    if (type(valid_from_unix) is not int
            or type(valid_until_unix) is not int
            or not 0 <= valid_from_unix < valid_until_unix <= _MAX_UNIX
            or valid_until_unix - valid_from_unix > 300):
        raise ValueError("invalid operator permit validity window")
    scoped = ledger_path is not None or sequence is not None
    scope_digest = _ledger_scope_digest(ledger_path, sequence) if scoped else None
    permit = LoopbackOperatorPermit(
        2 if scoped else 1, hashlib.sha256(plan.to_json().encode("ascii")).hexdigest(),
        _target_digest(targets), source_id,
        hashlib.sha256(source_key).hexdigest(),
        valid_from_unix, valid_until_unix, "0" * 64,
        scope_digest, sequence if scoped else None,
    )
    return replace(permit, mac_sha256=hmac.digest(
        operator_key, _permit_bytes(permit), "sha256",
    ).hex())


def verify_loopback_operator_permit(
    plan: ObservationPlan,
    targets: tuple[LoopbackHTTPProbeTarget, ...],
    permit: LoopbackOperatorPermit,
    *,
    source_id: str,
    source_key: bytes,
    operator_key: bytes,
    observed_at_unix: int,
    now_unix: int,
    ledger_path: str | None = None,
    sequence: int | None = None,
    require_one_shot: bool = False,
) -> bool:
    """Verify exact target, source key, plan, operation and short-lived MAC."""
    _validate_context(plan, targets, source_id, source_key, operator_key)
    if (type(permit) is not LoopbackOperatorPermit
            or type(permit.format_version) is not int
            or permit.format_version not in (1, 2)
            or not all(_hex_digest(value) for value in (
                permit.plan_sha256, permit.targets_sha256,
                permit.source_key_sha256, permit.mac_sha256,
            ))
            or type(permit.source_id) is not str
            or type(permit.valid_from_unix) is not int
            or type(permit.valid_until_unix) is not int
            or not 0 <= permit.valid_from_unix < permit.valid_until_unix <= _MAX_UNIX
            or permit.valid_until_unix - permit.valid_from_unix > 300
            or type(observed_at_unix) is not int
            or type(now_unix) is not int
            or not permit.valid_from_unix <= observed_at_unix <= now_unix <= permit.valid_until_unix):
        raise ValueError("invalid or expired operator permit")
    if type(require_one_shot) is not bool:
        raise ValueError("invalid scoped operator permit policy")
    if permit.format_version == 1:
        if (require_one_shot or permit.ledger_path_sha256 is not None
                or permit.sequence is not None):
            raise ValueError("scoped operator permit required")
    else:
        if (not _hex_digest(permit.ledger_path_sha256)
                or type(permit.sequence) is not int
                or not 1 <= permit.sequence <= _MAX_UNIX):
            raise ValueError("invalid scoped operator permit")
        expected_digest = _ledger_scope_digest(ledger_path, sequence)
        if (not hmac.compare_digest(permit.ledger_path_sha256, expected_digest)
                or permit.sequence != sequence):
            raise ValueError("scoped operator permit mismatch")
    if (permit.source_id != source_id
            or not hmac.compare_digest(
                permit.plan_sha256,
                hashlib.sha256(plan.to_json().encode("ascii")).hexdigest(),
            )
            or not hmac.compare_digest(permit.targets_sha256, _target_digest(targets))
            or not hmac.compare_digest(
                permit.source_key_sha256, hashlib.sha256(source_key).hexdigest(),
            )
            or not hmac.compare_digest(
                permit.mac_sha256,
                hmac.digest(operator_key, _permit_bytes(permit), "sha256").hex(),
            )):
        raise ValueError("operator permit mismatch")
    return True
