from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
import json
import tomllib

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
    normalized: dict[str, str] = {}
    for path, content in sorted(files.items()):
        if not isinstance(path, str) or not isinstance(content, str):
            raise ValueError("inspection requires text paths and contents")
        parsed = PurePosixPath(path)
        if parsed.is_absolute() or ".." in parsed.parts or "\\" in path:
            raise ValueError("inspection paths must be relative POSIX paths")
        key = parsed.as_posix()
        if key in normalized and normalized[key] != content:
            raise ValueError("conflicting normalized paths")
        normalized[key] = content
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

    # Read declared dependencies only; comments, scripts and descriptions are not
    # infrastructure evidence. Keep exact source paths in deterministic order.
    for path in ("pyproject.toml", "requirements.txt", "package.json"):
        if path not in normalized:
            continue
        try:
            if path == "pyproject.toml":
                declared = tomllib.loads(normalized[path]).get("project", {}).get("dependencies", [])
            elif path == "package.json":
                manifest = json.loads(normalized[path])
                declared = list(manifest.get("dependencies", {}))
            else:
                declared = [line.split("#", 1)[0].strip() for line in normalized[path].splitlines()]
            if not isinstance(declared, list) or any(not isinstance(item, str) for item in declared):
                raise ValueError("invalid dependencies")
        except (ValueError, TypeError, AttributeError):
            warnings.append(f"could not parse dependencies in {path}")
            continue
        found = set()
        for item in declared:
            match = re.match(r"^([A-Za-z0-9_.-]+)(?=\s|[<>=!~;\[]|$)", item.strip())
            if match and match[1].lower() in {"postgres", "postgresql", "redis"}:
                found.add("postgresql" if match[1].lower() in {"postgres", "postgresql"} else "redis")
        for dependency in sorted(found):
            dependencies.add(dependency)
            evidence.append(InspectionEvidence(path, "dependency", dependency))

    profile = ApplicationProfile(name=name, runtime=runtime, dependencies=tuple(sorted(dependencies)))
    return InspectionResult(profile=profile, evidence=tuple(evidence), warnings=tuple(warnings))
