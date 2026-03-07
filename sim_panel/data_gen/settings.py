from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LLMGenSettings:
    """
    Shared settings for LLM-driven spec generation.

    Notes:
    - Determinism is not guaranteed for LLMs; seed is passed as a hint.
    - batch_size controls how many specs we ask for per call.
    """
    prompt_version: str = "v1"
    temperature: float = 0.2
    max_tokens: Optional[int] = 1200
    metadata: Optional[Dict[str, Any]] = None

    batch_size: int = 10
    max_retries: int = 2

    # If True, we require the LLM output to be JSON-only. If False, we will attempt to extract JSON.
    require_json_only: bool = True

    # If True, inject a per-batch nonce into the system prompt to change output distribution.
    # Default False keeps old behavior.
    use_nonce: bool = False