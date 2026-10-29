"""Caller-provisioned operator-key fingerprint preflight for synthetic intake.

This is configuration consistency, not operator authentication or key custody.
"""
from __future__ import annotations

import hashlib
import hmac


def verify_observation_operator_key_pin(
    operator_key: bytes,
    *,
    operator_key_sha256: str | None = None,
    require_operator_pin: bool = False,
) -> bool:
    """Compare a separately provisioned fingerprint before fixture I/O.

    The integrating application must obtain the expected digest independently
    of the untrusted operator_key input. This function cannot enforce that.
    """
    if type(require_operator_pin) is not bool:
        raise ValueError("invalid observation operator pin policy")
    if type(operator_key) is not bytes or not 32 <= len(operator_key) <= 128:
        raise ValueError("invalid observation operator key")
    if operator_key_sha256 is None:
        if require_operator_pin:
            raise ValueError("observation operator key pin required")
        return True
    if (type(operator_key_sha256) is not str
            or len(operator_key_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in operator_key_sha256)):
        raise ValueError("invalid observation operator key pin")
    if not hmac.compare_digest(
        hashlib.sha256(operator_key).hexdigest(), operator_key_sha256,
    ):
        raise ValueError("observation operator key pin mismatch")
    return True
