"""Optional caller-provisioned key/plan pin for local observation fixtures.

A pin detects mismatched local configuration; it does not authenticate a
collector, securely provision a key, or establish a trusted clock.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

from .observation_plan import ObservationPlan

_MAX_UNIX = (1 << 63) - 1


@dataclass(frozen=True)
class ObservationSourcePin:
    source_id: str
    plan_sha256: str
    key_sha256: str
    valid_from_unix: int
    valid_until_unix: int


def _digest(value: object) -> bool:
    return (type(value) is str and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def verify_observation_source_pin(
    plan: ObservationPlan,
    pin: ObservationSourcePin,
    *,
    source_id: str,
    source_key: bytes,
    observed_at_unix: int,
    now_unix: int,
) -> bool:
    """Check an independently provisioned pin before fixture network or I/O.

    The caller must obtain the pin through a trusted channel, not construct it
    from untrusted evidence or from the same unverified source_key argument.
    """
    if (type(pin) is not ObservationSourcePin
            or type(pin.source_id) is not str
            or not pin.source_id
            or not _digest(pin.plan_sha256)
            or not _digest(pin.key_sha256)
            or type(pin.valid_from_unix) is not int
            or type(pin.valid_until_unix) is not int
            or not 0 <= pin.valid_from_unix < pin.valid_until_unix <= _MAX_UNIX
            or pin.valid_until_unix - pin.valid_from_unix > 86_400):
        raise ValueError("invalid observation source pin")
    if (type(source_id) is not str or type(source_key) is not bytes
            or not 32 <= len(source_key) <= 128
            or type(observed_at_unix) is not int
            or type(now_unix) is not int):
        raise ValueError("invalid observation source pin context")
    if (source_id != pin.source_id
            or not pin.valid_from_unix <= observed_at_unix <= now_unix <= pin.valid_until_unix):
        raise ValueError("observation source pin mismatch")
    plan_digest = hashlib.sha256(plan.to_json().encode("ascii")).hexdigest()
    key_digest = hashlib.sha256(source_key).hexdigest()
    if (not hmac.compare_digest(pin.plan_sha256, plan_digest)
            or not hmac.compare_digest(pin.key_sha256, key_digest)):
        raise ValueError("observation source pin mismatch")
    return True
