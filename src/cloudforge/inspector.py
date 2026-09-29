from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re

from .models import ApplicationProfile


@dataclass(frozen=True)
class InspectionEvidence:
    path: str
    fact: str
    value: str


@dataclass(frozen=True)
class InspectionResult:
    profile: ApplicationProfile
    evidence: tuple[InspectionEvidence, ...]
    warnings: tuple[str, ...] = ()


def inspect_application(name: str, files: dict[str, str]) -> InspectionResult:
    """Inspect supplied text files without executing application code."""
    normalized = {PurePosixPath(path).as_posix(): content for path, content in files.items()}
    runtime = "unknown"
    dependencies: set[str] = set()
    evidence: list[InspectionEvidence] = []
    warnings: list[str] = []

    pyproject = normalized.get("pyproject.toml")
    requirements = normalized.get("requirements.txt")
    package_json = normalized.get("package.json")

    if pyproject is not None or requirements is not None:
        runtime = "python"
        source = "pyproject.toml" if pyproject is not None else "requirements.txt"
        evidence.append(InspectionEvidence(source, "runtime", runtime))
    elif package_json is not None:
        runtime = "node"
        evidence.append(InspectionEvidence("package.json", "runtime", runtime))
    else:
        warnings.append("runtime could not be determined from supported manifests")

    manifest_text = "\n".join(x for x in (pyproject, requirements, package_json) if x is not None).lower()
    for dependency in ("postgresql", "postgres", "redis"):
        if re.search(rf"(?<![a-z0-9_-]){re.escape(dependency)}(?![a-z0-9_-])", manifest_text):
            canonical = "postgresql" if dependency in {"postgres", "postgresql"} else dependency
            if canonical not in dependencies:
                dependencies.add(canonical)
                evidence.append(InspectionEvidence("manifest", "dependency", canonical))

    profile = ApplicationProfile(name=name, runtime=runtime, dependencies=tuple(sorted(dependencies)))
    return InspectionResult(profile=profile, evidence=tuple(evidence), warnings=tuple(warnings))
