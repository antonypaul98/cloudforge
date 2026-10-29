"""Unwired, fail-closed mTLS client context for a future trusted collector.

Certificate authority and workload credentials must be provisioned independently
of the caller. Building this context neither authenticates an operator nor
permits a network connection, deployment, or live monitoring.
"""
from __future__ import annotations

import os
import ssl


def _require_absolute_credential_path(value: str) -> None:
    # No relative-path resolution, implicit defaults, embedded controls or
    # subclass coercion for sensitive credential paths.
    if (type(value) is not str or not 1 <= len(value) <= 4096
            or not os.path.isabs(value)
            or any(ord(character) < 32 or ord(character) == 127
                   for character in value)):
        raise ValueError("mTLS credential paths must be absolute and valid")


def build_collector_mtls_client_context(
    ca_bundle_path: str,
    client_certificate_path: str,
    client_key_path: str,
    *,
    key_password: str | bytes | None = None,
) -> ssl.SSLContext:
    """Load an explicitly rooted TLS client context, without making a request.

    The caller must obtain the CA trust bundle and short-lived client identity
    from a separate, authenticated provisioning boundary. The returned context
    verifies server certificates and DNS names; a remote server must separately
    validate the client certificate and its authorized workload identity.
    """
    for path in (ca_bundle_path, client_certificate_path, client_key_path):
        _require_absolute_credential_path(path)
    if key_password is not None and type(key_password) not in (str, bytes):
        raise ValueError("invalid mTLS key password type")

    # A direct PROTOCOL_TLS_CLIENT context avoids SSLKEYLOGFILE environment
    # behavior and implicit system CA fallback in create_default_context().
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    context.hostname_checks_common_name = False
    try:
        context.load_verify_locations(cafile=ca_bundle_path)
        # A callback prevents an encrypted key from triggering an interactive
        # OpenSSL password prompt when no external secret was provided.
        password = key_password if key_password is not None else (lambda: "")
        context.load_cert_chain(
            certfile=client_certificate_path,
            keyfile=client_key_path,
            password=password,
        )
    except (OSError, ssl.SSLError, ValueError) as exc:
        raise ValueError("mTLS trust or client credential loading failed") from None
    return context
