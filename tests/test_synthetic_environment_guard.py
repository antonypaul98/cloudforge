"""The in-memory authorization demo must not inspect or change process secrets.

This guards common Python environment entry points during the demo only.
It is not an OS-level sandbox or a claim of complete credential isolation.
"""
import os

from cloudforge.synthetic_demo import run_synthetic_local_authorization_demo


def test_synthetic_demo_does_not_access_process_environment(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("synthetic authorization must not access environment")

    with monkeypatch.context() as guard:
        guard.setattr(os, "getenv", forbidden)
        guard.setattr(os, "putenv", forbidden)
        guard.setattr(os, "unsetenv", forbidden)
        for name in (
            "__getitem__", "get", "__contains__", "__iter__", "copy",
            "items", "keys", "values", "__setitem__", "__delitem__",
            "pop", "popitem", "setdefault", "update", "clear",
        ):
            guard.setattr(type(os.environ), name, forbidden)
        result = run_synthetic_local_authorization_demo()

    assert result["demo_only"] is True
    assert result["authenticated_review"] is False
    assert result["infrastructure_mutated"] is False
    assert result["deployment_observed"] is False
    assert result["recovery_performed"] is False
