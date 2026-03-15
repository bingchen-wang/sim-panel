from __future__ import annotations

from typing import Any, Dict, Optional

from sim_panel.outcomes.base import EvaluationContext, OutcomeConfig, OutcomeResult
from sim_panel.outcomes.parsing import extract_json_object, safe_excerpt
from sim_panel.outcomes.render import render_evaluation_prompt


class LLMOutcomeModel:
    """
    LLM-backed outcome model.

    - Renders a questionnaire prompt from YAML spec
    - Calls panelist.evaluate(...) (persona-endowed)
    - Extracts JSON and validates against the QuestionnaireSpec
    """

    def __init__(self, cfg: OutcomeConfig) -> None:
        self.cfg = cfg

    def evaluate(self, *, panelist, ctx: EvaluationContext, prompting_strategy: str = "persona") -> OutcomeResult:
        prompt = render_evaluation_prompt(
            ctx=ctx, 
            questionnaire=self.cfg.questionnaire,
            include_features=True, 
            outcome_cfg=self.cfg,
            prompting_strategy=prompting_strategy,
        )

        # Determine system prompt based on strategy
        system_prompt = None  # default: use panelist.persona_text
        if prompting_strategy in ("zero_shot", "few_shot"):
            system_prompt = "You are evaluating consumer products. Provide honest, thoughtful responses."

        # Panelist is responsible for backend calls (separate from policies/outcomes).
        raw = panelist.evaluate(
            task_prompt=prompt,
            temperature=self.cfg.temperature,
            max_tokens=self.cfg.max_tokens,
            metadata={"module": "outcomes.llm", "panelist_id": ctx.panelist_id, "product_id": ctx.product_id, "t": ctx.t},
            system_prompt=system_prompt,
        )

        obj, err = extract_json_object(raw)
        if err is not None or obj is None:
            traces = {
                "parse_error": err,
                "raw_excerpt": safe_excerpt(raw),
            }
            return OutcomeResult(
                outcomes=None,
                traces=traces,
                raw_text=raw if self.cfg.include_raw_text else None,
                errors=[err] if err else ["unknown parse error"],
            )

        outcomes, traces, errors = self.cfg.questionnaire.validate_payload(obj)

        # If validation fails, preserve debug info in traces
        if outcomes is None:
            debug_traces = dict(traces or {})
            debug_traces.setdefault("validation_errors", errors)
            debug_traces.setdefault("raw_excerpt", safe_excerpt(raw))
            return OutcomeResult(
                outcomes=None,
                traces=debug_traces,
                raw_text=raw if self.cfg.include_raw_text else None,
                errors=errors,
            )

        # Merge any warnings/errors into traces (non-fatal warnings start with [warn])
        final_traces = traces if traces is not None else {}
        warn = [e for e in (errors or []) if e.startswith("[warn]")]
        if warn:
            final_traces = dict(final_traces or {})
            final_traces["warnings"] = warn

        return OutcomeResult(
            outcomes=outcomes,
            traces=final_traces,
            raw_text=raw if self.cfg.include_raw_text else None,
            errors=errors,
        )