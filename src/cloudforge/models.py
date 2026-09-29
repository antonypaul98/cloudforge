from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

@dataclass(frozen=True)
class ApplicationProfile:
    name: str
    runtime: str
    port: int | None = None
    stateful: bool = False
    dependencies: tuple[str, ...] = ()

@dataclass(frozen=True)
class ResourceRequirement:
    kind: Literal["compute", "network", "database", "cache"]
    reason: str
    properties: dict[str, object] = field(default_factory=dict)

@dataclass(frozen=True)
class InfrastructurePlan:
    application: str
    resources: tuple[ResourceRequirement, ...]
    requires_approval: bool = True
