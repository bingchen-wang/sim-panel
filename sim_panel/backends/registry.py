from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional

from .base import Backend, BackendConfig
from .errors import BackendNotFoundError


Factory = Callable[[BackendConfig], Backend]


@dataclass
class BackendRegistry:
    _factories: dict[str, Factory]

    def register(self, name: str, factory: Factory, *, overwrite: bool = False) -> None:
        key = name.strip().lower()
        if not overwrite and key in self._factories:
            raise ValueError(f"Backend already registered: {key}")
        self._factories[key] = factory

    def create(self, config: BackendConfig) -> Backend:
        key = config.name.strip().lower()
        if key not in self._factories:
            raise BackendNotFoundError(
                f"Unknown backend '{config.name}'. Available: {sorted(self._factories.keys())}"
            )
        return self._factories[key](config)


_DEFAULT_REGISTRY: Optional[BackendRegistry] = None


def get_registry() -> BackendRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = BackendRegistry(_factories={})
    return _DEFAULT_REGISTRY


def build_backend_from_dict(d: Mapping[str, Any]) -> Backend:
    """
    Build a Backend instance from a YAML-parsed mapping.

    Supported keys (matching BackendConfig):
      - name (required): registry key, e.g. "ollama", "server"
      - model (optional): provider model name (default: "unknown")
      - return_usage (optional): bool
      - seed (optional): int | null
      - params (optional): mapping of extra provider-specific options

    Convenience: any unknown keys under `backend:` are folded into `params`
    (unless `params` is explicitly provided).
    """
    if not isinstance(d, Mapping):
        raise ValueError(f"backend config must be a mapping/dict, got {type(d).__name__}")

    name = d.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("backend.name must be a non-empty string")

    model = d.get("model", "unknown")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("backend.model must be a non-empty string if provided")

    return_usage = d.get("return_usage", False)
    if not isinstance(return_usage, bool):
        raise ValueError("backend.return_usage must be a bool if provided")

    seed = d.get("seed", None)
    if seed is not None and not isinstance(seed, int):
        raise ValueError("backend.seed must be an int or null if provided")

    params = d.get("params", None)
    if params is not None and not isinstance(params, Mapping):
        raise ValueError("backend.params must be a mapping/dict if provided")

    # Fold unknown keys into params for ergonomic YAML.
    if params is None:
        known = {"name", "model", "return_usage", "seed", "params"}
        extra: Dict[str, Any] = {k: v for k, v in d.items() if k not in known}
        params_dict: Dict[str, Any] = extra
    else:
        params_dict = dict(params)

    cfg = BackendConfig(
        name=name.strip(),
        model=model,
        return_usage=return_usage,
        seed=seed,
        params=params_dict,
    )
    return get_registry().create(cfg)