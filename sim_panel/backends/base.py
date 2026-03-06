from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from .types import ChatResult, Message


@dataclass(frozen=True)
class BackendConfig:
    """
    Minimal backend configuration.

    name:
        Registry key, e.g. "mock", "ollama".
    model:
        Provider model name (or any string for mock).
    return_usage:
        If True, backend should populate ChatResult.usage when possible.
    seed:
        Optional seed.
    """
    name: str
    model: str = "unknown"
    return_usage: bool = False
    seed: Optional[int] = None
    params: dict[str, Any] = field(default_factory=dict) #YAML-governed extras

class Backend(ABC):
    """
    Provider-agnostic chat backend interface.
    """

    def __init__(self, config: BackendConfig):
        self.config = config

    @abstractmethod
    def chat(
        self,
        messages: Sequence[Message],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> ChatResult:
        """
        Run a chat completion.

        messages:
            List of dict messages with role/content.
        temperature, max_tokens:
            Optional decoding controls; may be ignored by some backends.
        metadata:
            Optional extra information for logging / provider features.

        Returns:
            ChatResult with assistant content and optional usage/raw fields.
        """
        raise NotImplementedError