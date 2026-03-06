from __future__ import annotations

from .base import Backend, BackendConfig
from .errors import (
    BackendError,
    BackendNotFoundError,
    BackendConfigError,
    BackendRequestError,
)
from .registry import get_registry, build_backend_from_dict
from .types import ChatResult, Message, Usage

# Import backends and register them
from .ollama import OllamaBackend 
from .server import ServerBackend

_registry = get_registry()
_registry.register("ollama", lambda cfg: OllamaBackend(cfg), overwrite=True)
_registry.register("server", lambda cfg: ServerBackend(cfg), overwrite=True)

__all__ = [
    "Backend",
    "BackendConfig",
    "ChatResult",
    "Message",
    "Usage",
    "get_registry",
    "build_backend_from_dict",
    "BackendError",
    "BackendNotFoundError",
    "BackendConfigError",
    "BackendRequestError",
    "OllamaBackend",
]