"""Caller-provided fixture key revocation and source-pin enforcement policy.

No trusted distribution or authenticated revocation is established here.
"""
from __future__ import annotations

import hashlib
import hmac

from .observation_source_pin import ObservationSourcePin


def verify_observation_source_policy(
    source_key: bytes,
    source_pin: ObservationSourcePin | None,
    *,
    require_source_pin: bool = False,
    revoked_key_sha256: tuple[str, ...] = (),
) -> bool:
    """Reject an explicitly revoked key before fixture network or ledger I/O.

    Both the optional pin and the revocation list must come from a separately
    trusted operator channel. This does not authenticate that channel.
    """
    if (type(require_source_pin) is not bool
            or type(revoked_key_sha256) is not tuple
            or len(revoked_key_sha256) > 64
            or any(type(value) is not str or len(value) != 64
                   or any(ch not in "0123456789abcdef" for ch in value)
                   for value in revoked_key_sha256)
            or len(set(revoked_key_sha256)) != len(revoked_key_sha256)):
        raise ValueError("invalid observation source trust policy")
    if ((require_source_pin or revoked_key_sha256) and source_pin is None):
        raise ValueError("observation source pin required by trust policy")
    if type(source_key) is not bytes or not 32 <= len(source_key) <= 128:
        raise ValueError("invalid observation source key for trust policy")
    fingerprint = hashlib.sha256(source_key).hexdigest()
    if any(hmac.compare_digest(fingerprint, revoked)
           for revoked in revoked_key_sha256):
        raise ValueError("observation source key is revoked")
    return True
