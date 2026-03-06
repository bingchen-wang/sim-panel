from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Type

from pydantic import BaseModel

from sim_panel.schema.versions.v0_1_0 import EventV0_1_0, SCHEMA_VERSION as V0_1_0


@dataclass(frozen=True)
class SchemaSpec:
    version: str
    model: Type[BaseModel]


_REGISTRY: Dict[str, SchemaSpec] = {
    V0_1_0: SchemaSpec(version=V0_1_0, model=EventV0_1_0),
}


def get_schema(version: str) -> SchemaSpec:
    try:
        return _REGISTRY[version]
    except KeyError as e:
        known = ", ".join(sorted(_REGISTRY.keys()))
        raise ValueError(f"Unknown schema_version={version!r}. Known: {known}") from e