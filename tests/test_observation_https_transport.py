"""No-network regressions for the unwired, IP-pinned HTTPS socket primitive."""
from dataclasses import replace
import socket
import ssl
from unittest.mock import Mock

import pytest

from cloudforge.observation_https_transport import _PinnedHTTPSConnection
from cloudforge.observation_runtime_request import RuntimeObservationTarget


def _target():
    return RuntimeObservationTarget(
        "readiness", "https", "api.example.com", 443, "/ready",
    )


@pytest.mark.parametrize("ip,family", [
    ("1.1.1.1", socket.AF_INET),
    ("2606:4700:4700::1111", socket.AF_INET6),
])
def test_dials_numeric_ip_with_original_hostname_tls_sni(monkeypatch, ip, family):
    raw, tls, context = Mock(), Mock(), Mock()
    context.wrap_socket.return_value = tls
    socket_factory = Mock(return_value=raw)
    monkeypatch.setattr(socket, "socket", socket_factory)
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_a, **_kw: pytest.fail("DNS used"))
    monkeypatch.setattr(ssl, "create_default_context", Mock(return_value=context))
    conn = _PinnedHTTPSConnection(_target(), ip, 2)
    assert socket_factory.call_count == 0
    conn.connect()
    socket_factory.assert_called_once_with(family, socket.SOCK_STREAM)
    raw.settimeout.assert_called_once_with(2)
    raw.connect.assert_called_once_with((ip, 443))
    context.wrap_socket.assert_called_once_with(raw, server_hostname="api.example.com")
    assert conn.sock is tls
    conn.close()
    tls.close.assert_called_once()


@pytest.mark.parametrize("ip", [
    "127.0.0.1", "169.254.169.254", "10.0.0.1", "2001:db8::1",
    "::ffff:1.1.1.1", "64:ff9b::101:101", "1.1.1.01", "1.1.1.1:443", "",
    None, True,
])
def test_rejects_untrusted_ip_before_socket_or_tls(monkeypatch, ip):
    socket_factory, tls_factory = Mock(), Mock()
    monkeypatch.setattr(socket, "socket", socket_factory)
    monkeypatch.setattr(ssl, "create_default_context", tls_factory)
    with pytest.raises(ValueError):
        _PinnedHTTPSConnection(_target(), ip, 2)
    socket_factory.assert_not_called()
    tls_factory.assert_not_called()


@pytest.mark.parametrize("change", [
    {"scheme": "http"}, {"host": "localhost"},
    {"host": "api.example.com.evil/"}, {"host": "API.example.com"},
    {"port": True}, {"path": "//admin"}, {"kind": "unknown"},
])
def test_rejects_unsafe_target_before_socket(monkeypatch, change):
    socket_factory = Mock()
    monkeypatch.setattr(socket, "socket", socket_factory)
    with pytest.raises(ValueError):
        _PinnedHTTPSConnection(replace(_target(), **change), "1.1.1.1", 2)
    socket_factory.assert_not_called()


@pytest.mark.parametrize("timeout", [True, 0, 11, 1.0, None])
def test_rejects_unsafe_timeout(timeout):
    with pytest.raises(ValueError):
        _PinnedHTTPSConnection(_target(), "1.1.1.1", timeout)


def test_tls_handshake_failure_closes_raw_socket(monkeypatch):
    raw, context = Mock(), Mock()
    context.wrap_socket.side_effect = ssl.SSLCertVerificationError("bad cert")
    monkeypatch.setattr(socket, "socket", Mock(return_value=raw))
    monkeypatch.setattr(ssl, "create_default_context", Mock(return_value=context))
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    with pytest.raises(ssl.SSLCertVerificationError):
        conn.connect()
    raw.close.assert_called_once()
    assert conn.sock is None


def test_connect_failure_closes_raw_socket_and_tunnel_forbidden(monkeypatch):
    raw = Mock()
    raw.connect.side_effect = OSError("unreachable")
    monkeypatch.setattr(socket, "socket", Mock(return_value=raw))
    monkeypatch.setattr(ssl, "create_default_context", Mock(return_value=Mock()))
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    with pytest.raises(ValueError, match="tunneling"):
        conn.set_tunnel("attacker.example.com")
    with pytest.raises(OSError):
        conn.connect()
    raw.close.assert_called_once()
    assert conn.sock is None


def test_real_default_ssl_policy_requires_certificate_and_hostname():
    # No socket is opened; assert the standard-library trust defaults.
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    assert conn._context.verify_mode == ssl.CERT_REQUIRED
    assert conn._context.check_hostname is True
