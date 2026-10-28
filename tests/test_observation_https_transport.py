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


@pytest.mark.parametrize("port,host", [
    (443, "api.example.com"),
    (8443, "api.example.com:8443"),
])
def test_head_guard_canonical_host_and_bodyless_wire_bytes(port, host):
    target = replace(_target(), port=port)
    conn = _PinnedHTTPSConnection(target, "1.1.1.1", 2)
    fake = Mock()
    conn.sock = fake
    conn.request("HEAD", "/ready")
    payload = b"".join(call.args[0] for call in fake.sendall.call_args_list)
    assert payload.startswith(b"HEAD /ready HTTP/1.1\r\n")
    assert payload.count(b"Host: ") == 1
    assert ("Host: " + host + "\r\n").encode() in payload
    assert b"Connection: close\r\n" in payload
    assert b"Accept-Encoding: identity\r\n" in payload
    assert b"Content-Length:" not in payload
    assert b"Transfer-Encoding:" not in payload


@pytest.mark.parametrize("args,kwargs", [
    (("GET", "/ready"), {}),
    (("POST", "/ready"), {}),
    (("HEAD", "/other"), {}),
    (("HEAD", "https://api.example.com/ready"), {}),
    (("HEAD", "/ready?token=x"), {}),
    (("HEAD", "/ready"), {"body": b""}),
    (("HEAD", "/ready"), {"body": "x"}),
    (("HEAD", "/ready"), {"headers": {"Host": "evil.example.com"}}),
    (("HEAD", "/ready"), {"headers": {"Authorization": "secret"}}),
    (("HEAD", "/ready"), {"headers": {"Transfer-Encoding": "chunked"}}),
    (("HEAD", "/ready"), {"headers": [("Host", "evil")]}),
    (("HEAD", "/ready"), {"encode_chunked": True}),
    (("head", "/ready"), {}),
    ((True, "/ready"), {}),
    (("HEAD", None), {}),
])
def test_head_guard_rejects_variants_before_io(args, kwargs):
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    fake = Mock()
    conn.sock = fake
    with pytest.raises(ValueError, match="bodyless HTTPS HEAD"):
        conn.request(*args, **kwargs)
    fake.sendall.assert_not_called()


def test_head_guard_explicit_empty_headers_still_canonical():
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    fake = Mock()
    conn.sock = fake
    conn.request("HEAD", "/ready", headers={})
    payload = b"".join(call.args[0] for call in fake.sendall.call_args_list)
    assert payload.count(b"Host: ") == 1


@pytest.mark.parametrize("method,args", [
    ("putrequest", ("POST", "/admin")),
    ("putheader", ("Authorization", "secret")),
    ("endheaders", ()),
    ("send", (b"POST /admin HTTP/1.1\\r\\n\\r\\n",)),
    ("_send_request", ("POST", "/admin", None, {}, False)),
    ("_send_output", ()),
])
def test_low_level_inherited_methods_rejected_before_network(method, args):
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    fake = Mock()
    conn.sock = fake
    with pytest.raises(ValueError, match="low-level HTTP request APIs"):
        getattr(conn, method)(*args)
    fake.sendall.assert_not_called()


def test_low_level_guard_resets_after_successful_head():
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    fake = Mock()
    conn.sock = fake
    conn.request("HEAD", "/ready")
    assert fake.sendall.called
    with pytest.raises(ValueError, match="low-level HTTP request APIs"):
        conn.putrequest("POST", "/admin")


def test_low_level_guard_resets_after_failed_head_send():
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    fake = Mock()
    fake.sendall.side_effect = OSError("synthetic send failure")
    conn.sock = fake
    with pytest.raises(OSError, match="synthetic send failure"):
        conn.request("HEAD", "/ready")
    with pytest.raises(ValueError, match="low-level HTTP request APIs"):
        conn.send(b"POST /admin HTTP/1.1\\r\\n\\r\\n")


def _clock(monkeypatch):
    """Deterministic synthetic clock, never a real endpoint."""
    import cloudforge.observation_https_transport as transport
    ticks = [100.0]
    monkeypatch.setattr(transport.time, "monotonic", lambda: ticks[0])
    return ticks


def test_head_deadline_valid_response_resets_budget(monkeypatch):
    import http.client
    ticks = _clock(monkeypatch)
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    fake = Mock()
    conn.sock = fake
    conn.request("HEAD", "/ready")
    response = Mock(status=204)
    monkeypatch.setattr(http.client.HTTPSConnection, "getresponse",
                        lambda self: response)
    ticks[0] += 1.5
    assert conn.getresponse() is response
    assert conn._deadline is None
    assert conn._request_sent is False
    assert fake.settimeout.called
    with pytest.raises(ValueError, match="pending request"):
        conn.getresponse()


def test_head_deadline_rejects_overdue_send_and_closes(monkeypatch):
    ticks = _clock(monkeypatch)
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    fake = Mock()
    fake.sendall.side_effect = lambda *_: ticks.__setitem__(0, 103.0)
    conn.sock = fake
    with pytest.raises(TimeoutError, match="transaction deadline"):
        conn.request("HEAD", "/ready")
    fake.close.assert_called_once()
    assert conn._deadline is None
    assert conn._request_sent is False


def test_head_deadline_rejects_overdue_response_and_closes(monkeypatch):
    import http.client
    ticks = _clock(monkeypatch)
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    fake = Mock()
    conn.sock = fake
    conn.request("HEAD", "/ready")
    def slow_response(_self):
        ticks[0] = 103.0
        return Mock(status=204)
    monkeypatch.setattr(http.client.HTTPSConnection, "getresponse", slow_response)
    with pytest.raises(TimeoutError, match="transaction deadline"):
        conn.getresponse()
    fake.close.assert_called_once()
    assert conn._deadline is None


def test_head_deadline_expired_before_response_never_reads(monkeypatch):
    import http.client
    ticks = _clock(monkeypatch)
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    fake = Mock()
    conn.sock = fake
    conn.request("HEAD", "/ready")
    read = Mock()
    monkeypatch.setattr(http.client.HTTPSConnection, "getresponse", read)
    ticks[0] = 102.0
    with pytest.raises(TimeoutError, match="transaction deadline"):
        conn.getresponse()
    read.assert_not_called()
    fake.close.assert_called_once()


def test_head_deadline_rejects_second_request_while_response_pending():
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    fake = Mock()
    conn.sock = fake
    conn.request("HEAD", "/ready")
    count = fake.sendall.call_count
    with pytest.raises(ValueError, match="previous HTTPS HEAD"):
        conn.request("HEAD", "/ready")
    assert fake.sendall.call_count == count


def test_head_deadline_expires_during_connect_before_tls(monkeypatch):
    ticks = _clock(monkeypatch)
    raw, context = Mock(), Mock()
    raw.connect.side_effect = lambda *_: ticks.__setitem__(0, 103.0)
    monkeypatch.setattr(socket, "socket", Mock(return_value=raw))
    monkeypatch.setattr(ssl, "create_default_context", Mock(return_value=context))
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    with pytest.raises(TimeoutError, match="transaction deadline"):
        conn.request("HEAD", "/ready")
    context.wrap_socket.assert_not_called()
    raw.close.assert_called()
    assert conn.sock is None


def test_head_deadline_expires_during_tls_and_closes_both(monkeypatch):
    ticks = _clock(monkeypatch)
    raw, tls, context = Mock(), Mock(), Mock()
    def handshake(*_args, **_kwargs):
        ticks[0] = 103.0
        return tls
    context.wrap_socket.side_effect = handshake
    monkeypatch.setattr(socket, "socket", Mock(return_value=raw))
    monkeypatch.setattr(ssl, "create_default_context", Mock(return_value=context))
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    with pytest.raises(TimeoutError, match="transaction deadline"):
        conn.request("HEAD", "/ready")
    tls.close.assert_called()
    raw.close.assert_called()
    assert conn.sock is None


def test_head_deadline_close_discards_pending_response():
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    fake = Mock()
    conn.sock = fake
    conn.request("HEAD", "/ready")
    conn.close()
    assert conn._deadline is None
    assert conn._request_sent is False
    with pytest.raises(ValueError, match="pending request"):
        conn.getresponse()


def test_head_deadline_rejects_late_response_even_if_base_closes(monkeypatch):
    import http.client
    ticks = _clock(monkeypatch)
    conn = _PinnedHTTPSConnection(_target(), "1.1.1.1", 2)
    fake = Mock()
    conn.sock = fake
    conn.request("HEAD", "/ready")
    def closing_response(self):
        ticks[0] = 103.0
        self.close()  # http.client does this for Connection: close
        return Mock(status=204)
    monkeypatch.setattr(http.client.HTTPSConnection, "getresponse", closing_response)
    with pytest.raises(TimeoutError, match="transaction deadline"):
        conn.getresponse()
    fake.close.assert_called()
    assert conn._deadline is None
