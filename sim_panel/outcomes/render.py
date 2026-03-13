from __future__ import annotations

from typing import Any, Dict, Optional

from sim_panel.outcomes.base import EvaluationContext
from sim_panel.outcomes.specs import FieldSpec, QuestionnaireSpec


def render_evaluation_prompt(
    *,
    ctx: EvaluationContext,
    questionnaire: QuestionnaireSpec,
    include_features: bool = True,
    prompting_strategy: str = "persona",
) -> str:
    """
    Render an evaluation "questionnaire" prompt for the panelist.

    The model is instructed to return JSON only:
      {"outcomes": {...}, "traces": {...}}

    Product display is the primary stimulus. Features are optional.
    """
    lines: list[str] = []

    if prompting_strategy == "persona_cot":
        lines.append("You are evaluating a product. Think step by step:")
        lines.append("1. Consider your personal preferences and background.")
        lines.append("2. Read the product information carefully.")
        lines.append("3. Form your opinion based on how this product fits your needs.")
        lines.append("4. Answer the questionnaire with your reasoning.")
    elif prompting_strategy == "few_shot":
        lines.append("You are evaluating a product. Read the product information and answer the questionnaire.")
        lines.append("")
        lines.append("## Example Evaluation")
        lines.append("For a product like 'Classic Lager - A traditional pale lager with crisp finish',")
        lines.append("a respondent might answer:")
        ex = {"outcomes": {"rating": 7, "purchase_intent": "maybe"}, "traces": {"rationale": "Solid traditional beer, nothing exceptional but reliable."}}
        lines.append(_pretty_json(ex))
    else:
        lines.append("You are evaluating a product. Read the product information and answer the questionnaire.")
    lines.append("")
    lines.append("## Product")
    lines.append(f"Product ID: {ctx.product_id}")
    lines.append("Product Display:")
    lines.append(ctx.product_display.strip() if ctx.product_display else "(no display provided)")
    lines.append("")

    if include_features:
        if ctx.product_features:
            lines.append("Product Features (JSON):")
            lines.append(_pretty_json(ctx.product_features))
            lines.append("")
        # if ctx.panelist_features:
        #     lines.append("Your Attributes (JSON):")
        #     lines.append(_pretty_json(ctx.panelist_features))
        #     lines.append("")

    lines.append("## Questionnaire")
    lines.append("Fill in the following fields.")
    lines.append("")

    lines.append("### Outcomes (required unless marked optional)")
    for fs in questionnaire.outcome_fields:
        lines.extend(_render_field(fs))
    lines.append("")

    if questionnaire.trace_fields:
        lines.append("### Traces (free-form unless otherwise specified)")
        for fs in questionnaire.trace_fields:
            lines.extend(_render_field(fs))
        lines.append("")

    lines.append("## Output Format (STRICT)")
    lines.append("Return JSON only. No extra text. Use exactly these top-level keys: outcomes, traces.")
    lines.append("All field names must match the questionnaire keys exactly.")
    if prompting_strategy == "persona_cot":
        lines.append("Include a 'reasoning' field in traces with your step-by-step thinking.")
    lines.append("")
    lines.append("Example:")
    example = _example_json(questionnaire, include_reasoning=(prompting_strategy == "persona_cot"))
    lines.append(example)

    return "\n".join(lines).strip() + "\n"


def _render_field(fs: FieldSpec) -> list[str]:
    parts: list[str] = []
    req = "required" if fs.required else "optional"
    parts.append(f"- {fs.name} ({fs.type}, {req})")
    parts.append(f"  - Question: {fs.question}")
    if fs.instruction:
        parts.append(f"  - Instruction: {fs.instruction}")
    if fs.choices is not None:
        parts.append(f"  - Choices: {fs.choices}")
    if fs.min_value is not None or fs.max_value is not None:
        parts.append(f"  - Range: [{fs.min_value if fs.min_value is not None else '-inf'}, {fs.max_value if fs.max_value is not None else 'inf'}]")
    return parts


def _example_json(q: QuestionnaireSpec, include_reasoning: bool = False) -> str:
    outcomes: Dict[str, Any] = {}
    for fs in q.outcome_fields:
        outcomes[fs.name] = _example_value(fs)

    traces: Dict[str, Any] = {}
    for fs in q.trace_fields:
        traces[fs.name] = _example_value(fs)
    if include_reasoning:
        traces["reasoning"] = "Step 1: ... Step 2: ... Step 3: ..."

    payload = {"outcomes": outcomes, "traces": traces}
    return _pretty_json(payload)


def _example_value(fs: FieldSpec) -> Any:
    if fs.choices:
        return fs.choices[0]
    if fs.type == "int":
        return int(fs.min_value) if fs.min_value is not None else 0
    if fs.type == "float":
        return float(fs.min_value) if fs.min_value is not None else 0.0
    if fs.type == "bool":
        return False
    if fs.type == "categorical":
        return fs.choices[0] if fs.choices else "option"
    if fs.type == "text":
        return "..."
    if fs.type == "json":
        return {}
    return None


def _pretty_json(obj: Any) -> str:
    # Avoid importing json at top-level in case someone swaps serializer; but it's standard.
    import json

    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)