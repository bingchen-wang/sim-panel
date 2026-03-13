from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple
import json

from sim_panel.decisions.types import (
    ExecutionRules,
    SelectionConfig,
    SelectionContext,
    SelectionResult,
)


def render_selection_prompt(
    *,
    ctx: SelectionContext,
    cfg: SelectionConfig,
    prompting_strategy: str = "persona",
) -> str:
    """
    Render a selection prompt for the panelist.

    The model is asked to return JSON only:
      {"selected_product_ids": [...], "traces": {...}}

    The panelist has free will: can select any number of products (including none),
    unless allow_empty=False (in which case we ask them to pick at least one).
    """
    lines: List[str] = []

    if prompting_strategy == "persona_cot":
        lines.append("You are choosing which products you want to evaluate.")
        lines.append("Think step by step about which products align with your preferences and interests.")
        lines.append("First, consider what matters to you. Then review each product. Finally, make your selection.")
    else:
        lines.append("You are choosing which products you want to evaluate.")
        lines.append("Read the product list and select the items you want to evaluate next.")
    lines.append("")

    lines.append("## Products Shown")
    if not ctx.products_shown:
        lines.append("(no products were shown)")
    else:
        for i, p in enumerate(ctx.products_shown, start=1):
            pid = str(p.get("product_id", ""))
            disp = str(p.get("product_display", "")).strip()
            lines.append(f"{i}. product_id: {pid}")
            lines.append(f"   product_display: {disp if disp else '(no display)'}")
            # Optional additional fields
            if cfg.include_features and isinstance(p.get("product_features"), dict):
                lines.append(f"   product_features: {_compact_json(p['product_features'])}")
            lines.append("")

    if prompting_strategy == "few_shot":
        lines.append("## Example Selection")
        lines.append("Given products about craft beverages, a respondent might select:")
        ex = {"selected_product_ids": ["prod001", "prod003"], "traces": {"reasoning": "Selected based on personal taste preferences."}}
        lines.append(_pretty_json(ex))
        lines.append("")

    lines.append("## Instructions")
    if cfg.allow_empty:
        lines.append("- You may select any number of products, including none.")
    else:
        lines.append("- Select at least one product.")

    if cfg.max_selected_soft is not None:
        lines.append(f"- (Operational hint) Prefer selecting at most {cfg.max_selected_soft} products.")

    lines.append("- Return your selection as JSON only. No extra text.")
    lines.append("- IMPORTANT: Use the exact product_id strings shown above.")
    lines.append("")

    lines.append("## Output Format (STRICT)")
    lines.append("Return JSON with the following keys:")
    lines.append("- selected_product_ids: a list of product_id strings (may be empty if allowed)")
    if prompting_strategy == "persona_cot":
        lines.append("- traces: an object with a 'reasoning' field containing your step-by-step thinking")
    else:
        lines.append("- traces: an optional object with any brief notes (optional)")
    lines.append("")
    lines.append("Example:")
    if prompting_strategy == "persona_cot":
        example = {
            "selected_product_ids": [ctx.products_shown[0]["product_id"]] if ctx.products_shown else [],
            "traces": {"reasoning": "Step 1: I prefer... Step 2: Product X matches because... Step 3: Selected."},
        }
    else:
        example = {
            "selected_product_ids": [ctx.products_shown[0]["product_id"]] if ctx.products_shown else [],
            "traces": {"notes": "Optional brief note"},
        }
    lines.append(_pretty_json(example))

    return "\n".join(lines).strip() + "\n"


def parse_selection_response(
    *,
    raw_text: str,
    choice_set_ids: Sequence[str],
    cfg: SelectionConfig,
) -> SelectionResult:
    """
    Parse the panelist's selection model output into requested_product_ids.

    - Expects JSON object with key 'selected_product_ids'.
    - Filters out invalid ids if enforce_subset_of_choice_set is later enabled.
      (Filtering is applied in apply_execution_rules; here we only parse.)
    """
    errors: List[str] = []
    obj, err = _extract_json_object(raw_text)
    if err is not None or obj is None:
        errors.append(err or "unknown parse error")
        return SelectionResult(
            requested_product_ids=[],
            traces={"parse_error": err, "raw_excerpt": _safe_excerpt(raw_text)},
            raw_text=raw_text if cfg.include_raw_text else None,
            errors=errors,
        )

    if "selected_product_ids" not in obj:
        errors.append("Missing key 'selected_product_ids' in selection JSON.")
        return SelectionResult(
            requested_product_ids=[],
            traces={"validation_errors": errors, "raw_excerpt": _safe_excerpt(raw_text)},
            raw_text=raw_text if cfg.include_raw_text else None,
            errors=errors,
        )

    sp = obj.get("selected_product_ids")
    if not isinstance(sp, list) or any(not isinstance(x, str) for x in sp):
        errors.append("'selected_product_ids' must be a list of strings.")
        return SelectionResult(
            requested_product_ids=[],
            traces={"validation_errors": errors, "raw_excerpt": _safe_excerpt(raw_text)},
            raw_text=raw_text if cfg.include_raw_text else None,
            errors=errors,
        )

    traces = obj.get("traces")
    if traces is not None and not isinstance(traces, dict):
        # keep it but warn
        errors.append("[warn] 'traces' should be an object/dict if provided; ignoring.")
        traces = None

    # De-dupe while preserving order
    requested = _dedupe_preserve_order([s.strip() for s in sp if s.strip()])

    # We do not filter by choice_set_ids here; execution rules handle it.
    return SelectionResult(
        requested_product_ids=requested,
        traces=traces,
        raw_text=raw_text if cfg.include_raw_text else None,
        errors=errors,
    )


def apply_execution_rules(
    *,
    requested_product_ids: Sequence[str],
    choice_set_ids: Sequence[str],
    rules: ExecutionRules,
) -> Tuple[List[str], List[str]]:
    """
    Apply generator-side operational rules to the panelist's requested list.

    Returns (executed_product_ids, dropped_product_ids).
    """
    requested = list(requested_product_ids)
    dropped: List[str] = []

    if rules.enforce_subset_of_choice_set:
        allowed = set(choice_set_ids)
        kept = []
        for pid in requested:
            if pid in allowed:
                kept.append(pid)
            else:
                dropped.append(pid)
        requested = kept

    # De-dupe again defensively
    requested = _dedupe_preserve_order(requested)

    # Cap if needed
    if rules.max_evals_per_panelist_per_t is not None:
        k = rules.max_evals_per_panelist_per_t
        if k < 0:
            raise ValueError("ExecutionRules.max_evals_per_panelist_per_t must be >= 0 or None.")
        if len(requested) > k:
            if rules.keep_strategy != "keep_first":
                raise ValueError(f"Unknown keep_strategy: {rules.keep_strategy}")
            dropped.extend(requested[k:])
            requested = requested[:k]

    # Empty handling: generator chooses fallback strategy elsewhere; here we just report.
    if not rules.allow_empty and len(requested) == 0:
        # No forced fallback here (keeps this function pure).
        pass

    return requested, dropped


# --------------------
# helpers
# --------------------

def _extract_json_object(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if text is None:
        return None, "No text to parse."
    s = text.strip()
    if not s:
        return None, "Empty text."

    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj, None
        return None, f"Top-level JSON must be an object/dict, got {type(obj).__name__}."
    except Exception:
        pass

    i = s.find("{")
    j = s.rfind("}")
    if i == -1 or j == -1 or j <= i:
        return None, "Could not find JSON object braces in output."
    candidate = s[i : j + 1]
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj, None
        return None, f"Top-level JSON must be an object/dict, got {type(obj).__name__}."
    except Exception as e:
        return None, f"JSON parse error: {type(e).__name__}: {e}"


def _pretty_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)


def _compact_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _safe_excerpt(text: str, max_chars: int = 800) -> str:
    s = (text or "").strip()
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + "…"


def _dedupe_preserve_order(xs: Sequence[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in xs:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out