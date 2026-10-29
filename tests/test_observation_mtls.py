"""Offline trust-context regressions: no certs, sockets or providers required."""
import os
import ssl
from unittest import mock

import pytest

from cloudforge.observation_mtls import build_collector_mtls_client_context


class FakeContext:
    def __init__(self):
        self.minimum_version = None
        self.verify_mode = None
        self.check_hostname = None
        self.hostname_checks_common_name = None
        self.loaded = []
        self.fail_on = None

    def load_verify_locations(self, **kwargs):
        self.loaded.append(("roots", kwargs))
        if self.fail_on == "roots":
            raise OSError("fake root path")

    def load_cert_chain(self, **kwargs):
        self.loaded.append(("identity", kwargs))
        if self.fail_on == "identity":
            raise ssl.SSLError("fake certificate failure")


def _build(*args, **kwargs):
    return build_collector_mtls_client_context(
        *(args or ("/protected/root.pem", "/protected/client.pem", "/protected/key.pem")),
        **kwargs,
    )


def test_explicit_trust_root_client_certificate_and_verified_hostname(monkeypatch):
    fake = FakeContext()
    constructor = mock.Mock(return_value=fake)
    monkeypatch.setattr(ssl, "SSLContext", constructor)
    monkeypatch.setenv("SSLKEYLOGFILE", "/tmp/should-not-be-created.keys")
    assert _build() is fake
    constructor.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)
    assert fake.minimum_version == ssl.TLSVersion.TLSv1_2
    assert fake.verify_mode == ssl.CERT_REQUIRED
    assert fake.check_hostname is True
    assert fake.hostname_checks_common_name is False
    assert fake.loaded[0] == ("roots", {"cafile": "/protected/root.pem"})
    assert fake.loaded[1][0] == "identity"
    assert fake.loaded[1][1]["certfile"] == "/protected/client.pem"
    assert fake.loaded[1][1]["keyfile"] == "/protected/key.pem"
    assert fake.loaded[1][1]["password"]() == ""


@pytest.mark.parametrize("bad", [None, "", "relative.pem", "../key.pem", "\x00/x", "/tmp/a\n", "/tmp/a\x7f", b"/tmp/key", True, 5, "/" + "a" * 4096])
@pytest.mark.parametrize("position", [0, 1, 2])
def test_bad_paths_fail_before_any_tls_context(monkeypatch, bad, position):
    constructor = mock.Mock()
    monkeypatch.setattr(ssl, "SSLContext", constructor)
    paths = ["/protected/root.pem", "/protected/client.pem", "/protected/key.pem"]
    paths[position] = bad
    with pytest.raises(ValueError, match="credential paths"):
        _build(*paths)
    constructor.assert_not_called()


@pytest.mark.parametrize("bad", [False, 1, bytearray(b"abc"), object()])
def test_password_type_fails_before_tls_context(monkeypatch, bad):
    constructor = mock.Mock()
    monkeypatch.setattr(ssl, "SSLContext", constructor)
    with pytest.raises(ValueError, match="password type"):
        _build(key_password=bad)
    constructor.assert_not_called()


@pytest.mark.parametrize("failure", ["roots", "identity"])
def test_missing_or_invalid_trust_material_fails_closed(monkeypatch, failure):
    fake = FakeContext()
    fake.fail_on = failure
    monkeypatch.setattr(ssl, "SSLContext", mock.Mock(return_value=fake))
    with pytest.raises(ValueError, match="credential loading failed") as error:
        _build()
    assert "/protected/" not in str(error.value)
    assert fake.loaded[0][0] == "roots"
    if failure == "roots":
        assert len(fake.loaded) == 1
    else:
        assert [entry[0] for entry in fake.loaded] == ["roots", "identity"]


@pytest.mark.parametrize("secret", ["passphrase", b"passphrase", ""])
def test_supplied_secret_is_used_without_interactive_callback(monkeypatch, secret):
    fake = FakeContext()
    monkeypatch.setattr(ssl, "SSLContext", mock.Mock(return_value=fake))
    _build(key_password=secret)
    assert fake.loaded[-1][1]["password"] == secret


def test_real_ssl_rejects_missing_external_ca_without_fallback(tmp_path):
    with pytest.raises(ValueError, match="credential loading failed"):
        _build(str(tmp_path / "missing-ca.pem"), str(tmp_path / "client.pem"),
               str(tmp_path / "key.pem"))
