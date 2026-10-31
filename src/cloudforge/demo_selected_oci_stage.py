"""Ephemeral exact-byte OCI build-context staging; never executes selected code.

Source and manifests can contain secrets. Callers must keep the context private,
never upload or log its contents, and never mistake this for runtime approval.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import os
import stat
from pathlib import Path
import tempfile
from typing import Iterator

from .demo_source_package import verify_selected_source_package


@dataclass(frozen=True)
class StagedSelectedSource:
    directory: Path
    entrypoint: str
    package_sha256: str
    source_sha256: str
    manifest_sha256: tuple[tuple[str, str], ...]


def _write_exact(directory: Path, filename: str, content: bytes) -> str:
    # Names come only from the verified package's bounded root-file schema.
    if filename not in {"app.py", "server.js", "requirements.txt", "pyproject.toml", "package.json"}:
        raise ValueError("unsupported staging filename")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("no-follow file creation is unavailable")
    flags |= os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(directory / filename, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    digest = hashlib.sha256(content).hexdigest()
    if hashlib.sha256((directory / filename).read_bytes()).hexdigest() != digest:
        raise ValueError("staged source bytes changed")
    return digest


@contextmanager
def stage_verified_selected_source(
    package_bytes: bytes, *, expected_package_sha256: str,
    expected_review_binding_digest: str, expected_target_id: str,
) -> Iterator[StagedSelectedSource]:
    """Temporarily stage a verified source package, without build or execution.

    The caller must independently trust expected digests and target. The private
    directory is removed on normal exit and exceptions, not on process SIGKILL.
    It is not an approval, immutable artifact, or hardened sandbox.
    """
    verified = verify_selected_source_package(
        package_bytes,
        expected_package_sha256=expected_package_sha256,
        expected_review_binding_digest=expected_review_binding_digest,
        expected_target_id=expected_target_id,
    )
    with tempfile.TemporaryDirectory(prefix="cloudforge-selected-") as temp:
        directory = Path(temp)
        source_digest = _write_exact(directory, verified.entrypoint, verified.source_bytes)
        manifest_digests = tuple(
            (filename, _write_exact(directory, filename, content.encode("utf-8", "strict")))
            for filename, content in verified.manifests
        )
        yield StagedSelectedSource(
            directory=directory, entrypoint=verified.entrypoint,
            package_sha256=verified.package_sha256,
            source_sha256=source_digest, manifest_sha256=manifest_digests,
        )


def verify_staged_selected_source(staged: StagedSelectedSource) -> None:
    """Recheck exact staged source bytes immediately before a proposed OCI build.

    This is point-in-time consistency, not immutable storage, human approval or
    a defense against modifications after this check. Only Linux-style
    directory-fd and no-follow file access is supported; fail closed otherwise.
    """
    allowed = {"app.py", "server.js", "requirements.txt", "pyproject.toml", "package.json"}
    expected = {staged.entrypoint: staged.source_sha256}
    for filename, digest in staged.manifest_sha256:
        if filename in expected:
            raise ValueError("duplicate staged filename")
        expected[filename] = digest
    if not expected.keys() <= allowed or not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ValueError("unsupported staged verification platform or filename")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        directory_fd = os.open(staged.directory, flags)
    except OSError as exc:
        raise ValueError("staged directory is unavailable or unsafe") from exc
    try:
        if set(os.listdir(directory_fd)) != set(expected):
            raise ValueError("staged file set changed")
        for filename, digest in expected.items():
            try:
                fd = os.open(
                    filename, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=directory_fd,
                )
            except OSError as exc:
                raise ValueError("staged file is unavailable or unsafe") from exc
            with os.fdopen(fd, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ValueError("staged file is not regular")
                hasher = hashlib.sha256()
                for chunk in iter(lambda: stream.read(65536), b""):
                    hasher.update(chunk)
                if hasher.hexdigest() != digest:
                    raise ValueError("staged file digest changed")
    finally:
        os.close(directory_fd)
