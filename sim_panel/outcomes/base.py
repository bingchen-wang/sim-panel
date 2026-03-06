from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

from sim_panel.outcomes.specs import QuestionnaireSpec


@dataclass(frozen=True)
class EvaluationContext:
    """
    Minimal context needed to render an evaluation prompt.
    Keep it JSON-serializable.
    """
    panelist_id: str
    product_id: str
    t: int
    product_display: str
    panelist_features: Optional[Dict[str, Any]] = None
    product_features: Optional[Dict[str, Any]] = None
    extra: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class OutcomeResult:
    outcomes: Optional[Dict[str, Any]]
    traces: Optional[Dict[str, Any]]
    raw_text: Optional[str] = None
    errors: Optional[list[str]] = None


@dataclass(frozen=True)
class OutcomeConfig:
    """
    YAML-governed config for outcomes module.
    """
    name: str  # "deterministic" | "llm"
    questionnaire: QuestionnaireSpec
    # LLM-specific defaults (Panelist also has defaults; this is an extra layer)
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    # Whether to include the raw model text in OutcomeResult (useful for debugging)
    include_raw_text: bool = True


class OutcomeModel(Protocol):
    cfg: OutcomeConfig

    def evaluate(self, *, panelist, ctx: EvaluationContext) -> OutcomeResult:
        ...