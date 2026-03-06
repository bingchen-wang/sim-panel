from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Sequence, Mapping
from sim_panel.backends import Backend
from sim_panel.backends.types import Message



@dataclass
class PanelistState:
    t: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)



@dataclass(frozen=True)
class EvalSettings:
    """
    Default LLM call settings for Panelist evaluation.

    These are governed by YAML and applied to Panelist.evaluate() unless overridden.
    """
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class SelectSettings:
    """
    Default LLM call settings for Panelist selection.

    These are governed by YAML and applied to Panelist.select() unless overridden.
    """
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class Panelist:
    """
    Runtime agent. The only required thing for LLM-based actions is persona_text.
    """
    def __init__(
        self,
        *,
        panelist_id: str,
        persona_text: str,
        attributes: Optional[Dict[str, Any]] = None,
        backend: Optional[Backend] = None,
        state: Optional[PanelistState] = None,
        eval_settings: Optional[EvalSettings] = None,
        select_settings: Optional[SelectSettings] = None,
    ) -> None:
        self.panelist_id = panelist_id
        self.persona_text = persona_text
        # Static identity features (copied from PersonaRecord.attributes). Do not mutate.
        self.attributes: Dict[str, Any] = dict(attributes) if attributes is not None else {}
        self.backend = backend
        self.state = state or PanelistState()
        self.eval_settings = eval_settings or EvalSettings()
        self.select_settings = select_settings or SelectSettings()

    def select(
        self,
        *,
        task_prompt: str,
        choice_set: Sequence[str],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Run a selection call. The generator/policy provides the choice_set (IDs),
        while the prompt should typically include product_display text.

        Returns raw model text. Parsing into selected_product_ids should be handled
        by a SelectionParser / ResponseCleaner layer (later), not inside Panelist.
        """
        md = {} if self.select_settings.metadata is None else dict(self.select_settings.metadata)
        if metadata:
            md.update(metadata)
        md.setdefault("module", "panelists.select")
        md.setdefault("panelist_id", self.panelist_id)
        md.setdefault("t", self.state.t)
        md.setdefault("choice_set_size", len(choice_set))

        t = self.select_settings.temperature if temperature is None else temperature
        mt = self.select_settings.max_tokens if max_tokens is None else max_tokens

        return self._chat(task_prompt=task_prompt, temperature=t, max_tokens=mt, metadata=md, kind="select")
    
    def evaluate(
        self,
        *,
        task_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Run an evaluation call (panelist evaluating a single product).
        Returns raw model text; parsing into structured outcomes/traces is handled elsewhere.
        """
        md = {} if self.eval_settings.metadata is None else dict(self.eval_settings.metadata)
        if metadata:
            md.update(metadata)
        md.setdefault("module", "panelists.evaluate")
        md.setdefault("panelist_id", self.panelist_id)
        md.setdefault("t", self.state.t)

        t = self.eval_settings.temperature if temperature is None else temperature
        mt = self.eval_settings.max_tokens if max_tokens is None else max_tokens

        return self._chat(task_prompt=task_prompt, temperature=t, max_tokens=mt, metadata=md, kind="evaluate")

    def _chat(
        self,
        *,
        task_prompt: str,
        temperature: float,
        max_tokens: Optional[int],
        metadata: Optional[dict[str, Any]],
        kind: str,
    ) -> str:
        if self.backend is None:
            raise RuntimeError("Panelist.backend is None; cannot run LLM calls.")

        messages: List[Message] = [
            {"role": "system", "content": self.persona_text},
            {"role": "user", "content": task_prompt},
        ]
        res = self.backend.chat(messages, temperature=temperature, max_tokens=max_tokens, metadata=metadata)

        # Minimal runtime logging (kept tiny; avoid storing full prompts by default)
        self.state.history.append(
            {
                "kind": kind,
                "t": self.state.t,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "metadata": metadata,
                "n_chars": len(res.content),
            }
        )
        return res.content