"""The in-memory authorization demo must not depend on clocks or entropy.

Guards common Python clock and random entry points during the demo only.
This is a bounded determinism regression, not an OS-level sandbox.
"""
import os
import random
import secrets
import time
import uuid

from cloudforge.synthetic_demo import run_synthetic_local_authorization_demo


def test_synthetic_demo_uses_no_common_clock_or_entropy_sources(monkeypatch):
    baseline = run_synthetic_local_authorization_demo()

    def forbidden(*args, **kwargs):
        raise AssertionError("synthetic authorization must be clock/entropy independent")

    with monkeypatch.context() as guard:
        for module, names in (
            (time, ("time", "monotonic", "perf_counter", "process_time")),
            (random, ("random", "randrange", "randint", "getrandbits",
                      "choice", "choices", "shuffle", "sample")),
            (secrets, ("token_bytes", "token_hex", "token_urlsafe",
                       "choice", "randbelow", "randbits")),
            (uuid, ("uuid1", "uuid4", "uuid6", "uuid7", "uuid8")),
        ):
            for name in names:
                if hasattr(module, name):
                    guard.setattr(module, name, forbidden)
        guard.setattr(os, "urandom", forbidden)
        result = run_synthetic_local_authorization_demo()

    assert result == baseline
    assert result["demo_only"] is True
    assert result["authenticated_review"] is False
    assert result["infrastructure_mutated"] is False
    assert result["deployment_observed"] is False
    assert result["recovery_performed"] is False
