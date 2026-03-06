from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class PersonaSpec:
    """
    Optional structured spec. Useful for extraction of panelist_features, policies, etc.
    Not required for LLM inference if persona_text is available.
    """
    persona_id: str
    attributes: Dict[str, Any]
    schema_version: str = "0.1.0"
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_features(self) -> Mapping[str, Any]:
        # Kept minimal for v0. Can extend this later.
        return self.attributes