"""The credential-free in-memory demo must not inspect local files.

Guards standard Python file-read entry points, not every possible OS syscall.
This is a privacy regression, not a complete sandbox or deployment proof.
"""
import builtins
import io
import os
from pathlib import Path

from cloudforge.synthetic_demo import run_synthetic_local_authorization_demo


def test_synthetic_demo_never_reads_local_files(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("synthetic authorization must not read local files")

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(io, "open", forbidden)
        guard.setattr(os, "open", forbidden)
        for name in ("open", "read_text", "read_bytes"):
            guard.setattr(Path, name, forbidden)
        result = run_synthetic_local_authorization_demo()

    assert result["demo_only"] is True
    assert result["authenticated_review"] is False
    assert result["infrastructure_mutated"] is False
    assert result["deployment_observed"] is False
    assert result["recovery_performed"] is False
