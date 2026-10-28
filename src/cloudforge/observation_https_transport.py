"""Unwired HTTPS socket primitive for a future independently approved collector.

Connecting to a live endpoint is not authorized by this module. The caller must
first establish authenticated approval and exact target/IP policy; no public
collector calls this primitive yet.
"""
from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl

from .observation_http import _PATH
from .observation_runtime_dns import _validate_address_sets
from .observation_runtime_request import (
    RuntimeObservationTarget, _LABEL, _TLD,
)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Dial an approved numeric IP, but verify TLS for the original DNS name.

    No DNS lookup, environment proxy, redirect or TLS verification bypass is
    performed here. This is an internal transport primitive, not authorization.
    """

    def __init__(self, target: RuntimeObservationTarget,
                 pinned_ip: str, timeout_seconds: int) -> None:
        if (type(target) is not RuntimeObservationTarget
                or type(target.kind) is not str
                or target.kind not in ("startup", "readiness", "liveness")
                or type(target.scheme) is not str or target.scheme != "https"
                or type(target.host) is not str
                or not 1 <= len(target.host) <= 253
                or target.host != target.host.lower()
                or type(target.port) is not int or not 1 <= target.port <= 65535
                or type(target.path) is not str
                or _PATH.fullmatch(target.path) is None or "//" in target.path
                or type(timeout_seconds) is not int
                or not 1 <= timeout_seconds <= 10):
            raise ValueError("invalid pinned HTTPS target or timeout")
        labels = target.host.split(".")
        if (len(labels) < 2 or _TLD.fullmatch(labels[-1]) is None
                or any(_LABEL.fullmatch(label) is None for label in labels)):
            raise ValueError("invalid pinned HTTPS hostname")
        if type(pinned_ip) is not str:
            raise ValueError("invalid pinned HTTPS address")
        try:
            address = ipaddress.ip_address(pinned_ip)
        except ValueError as exc:
            raise ValueError("invalid pinned HTTPS address") from exc
        if type(address) is ipaddress.IPv4Address:
            _validate_address_sets((target,), ((pinned_ip,),), ((),))
        else:
            _validate_address_sets((target,), ((),), ((pinned_ip,),))
        super().__init__(target.host, target.port, timeout=timeout_seconds,
                         context=ssl.create_default_context())
        self._pinned_address = address
        self._target_path = target.path

    def set_tunnel(self, *args, **kwargs) -> None:
        raise ValueError("HTTP CONNECT tunneling is forbidden")

    def request(self, method, url, body=None, headers=None, *,
                encode_chunked=False) -> None:
        """Allow only the exact HEAD path with a canonical original-host header.

        This constrains the intended request API, not low-level inherited APIs
        or independent authorization. The connection remains unwired.
        """
        if (type(method) is not str or method != "HEAD"
                or type(url) is not str or url != self._target_path
                or body is not None
                or (headers is not None and (type(headers) is not dict or headers))
                or encode_chunked is not False):
            raise ValueError("only exact bodyless HTTPS HEAD requests are supported")
        host = self.host if self.port == 443 else f"{self.host}:{self.port}"
        super().request("HEAD", self._target_path,
                        headers={"Host": host, "Connection": "close"})

    def connect(self) -> None:
        family = (socket.AF_INET if type(self._pinned_address) is ipaddress.IPv4Address
                  else socket.AF_INET6)
        raw = socket.socket(family, socket.SOCK_STREAM)
        try:
            raw.settimeout(self.timeout)
            # A numeric IP is sent directly to the socket. Never resolve the
            # hostname again at connection time, including after a redirect.
            raw.connect((str(self._pinned_address), self.port))
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise
