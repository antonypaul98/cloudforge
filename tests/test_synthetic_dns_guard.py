"""Guard the credential-free synthetic demo against DNS and host lookups.

This regression covers standard-library lookup entry points only; it is not
a sandbox, provider isolation proof, or evidence of real infrastructure.
"""
import socket

from cloudforge.synthetic_demo import run_synthetic_local_authorization_demo


def test_synthetic_demo_does_not_resolve_hosts(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("synthetic authorization must not resolve hosts")

    with monkeypatch.context() as guard:
        for name in (
            "getaddrinfo", "gethostbyname", "gethostbyname_ex",
            "gethostbyaddr", "getnameinfo", "getfqdn",
        ):
            if hasattr(socket, name):
                guard.setattr(socket, name, forbidden)
        result = run_synthetic_local_authorization_demo()

    assert result["demo_only"] is True
    assert result["authenticated_review"] is False
    assert result["infrastructure_mutated"] is False
    assert result["deployment_observed"] is False
    assert result["recovery_performed"] is False
