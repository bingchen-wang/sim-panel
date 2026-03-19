from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Type

from sim_panel.sources.base import BaseSource
from sim_panel.sources.types import SourceConfig


@dataclass
class SourceRegistry:
    """
    Name-to-source registry.
    """

    _registry: Dict[str, Type[BaseSource]] = field(default_factory=dict)

    def register(self, name: str, cls: Type[BaseSource]) -> None:
        key = name.strip()
        if not key:
            raise ValueError("Source name must be a non-empty string.")
        if key in self._registry:
            raise ValueError(f"Source '{key}' is already registered.")
        self._registry[key] = cls

    def get(self, name: str) -> Type[BaseSource]:
        try:
            return self._registry[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._registry)) or "<none>"
            raise KeyError(f"Unknown source '{name}'. Available sources: {available}") from exc

    def create(self, config: SourceConfig) -> BaseSource:
        cls = self.get(config.name)
        return cls(config)

    def names(self) -> list[str]:
        return sorted(self._registry.keys())


_REGISTRY = SourceRegistry()


def get_registry() -> SourceRegistry:
    return _REGISTRY


def register_source(name: str, cls: Type[BaseSource]) -> None:
    _REGISTRY.register(name, cls)


def build_source(config: SourceConfig) -> BaseSource:
    return _REGISTRY.create(config)


def list_sources() -> list[str]:
    return _REGISTRY.names()