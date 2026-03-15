from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


@dataclass(frozen=True)
class SelectionContext:
    """
    Context used to render a selection prompt.

    products_shown should already reflect the exposure policy (choice_set), and each item
    should include a stable product_id plus panelist-facing product_display.
    """
    panelist_id: str
    t: int
    products_shown: List[Dict[str, Any]]  # each: {"product_id": str, "product_display": str, ...}
    extra: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class SelectionResult:
    """
    Parsed selection output.

    requested_product_ids are what the panelist asked to evaluate (free will).
    The generator may later apply execution rules to decide what to actually execute.
    """
    requested_product_ids: List[str]
    traces: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None
    errors: Optional[List[str]] = None


@dataclass(frozen=True)
class SelectionConfig:
    """
    YAML-governed config for selection prompting/parsing.

    If allow_empty is False and selection output is empty (after filtering),
    generator can decide a fallback (re-prompt or force one).
    """
    allow_empty: bool = True
    include_features: bool = True

    # LLM response constraints
    require_json_only: bool = True
    max_selected_soft: Optional[int] = None  # operational hint in prompt; not a hard constraint

    # Include raw text in SelectionResult (debugging)
    include_raw_text: bool = True

    # Optional few-shot exemplar override used only when prompting_strategy == "few_shot".
    # If absent, built-in few-shot prompting should remain general.
    #
    # Expected shape:
    # {
    #   "intro": "Given products about craft beverages, a respondent might select:",
    #   "response": {
    #       "selected_product_ids": ["__FIRST_SHOWN__", "__THIRD_SHOWN_IF_AVAILABLE__"],
    #       "traces": {"reasoning": "Selected based on personal taste preferences."}
    #   }
    # }
    #
    # selected_product_ids may contain either literal product_ids or reserved placeholders
    # to be resolved against ctx.products_shown at render time.
    custom_few_shot_example: Optional[Dict[str, Any]] = None    


@dataclass(frozen=True)
class ExecutionRules:
    """
    Generator-side operational rules (NOT panelist constraints).

    Applied after parsing requested_product_ids:
      - subset filtering
      - optional cap
      - empty fallback behavior
    """
    enforce_subset_of_choice_set: bool = True
    max_evals_per_panelist_per_t: Optional[int] = None  # None => unlimited
    allow_empty: bool = True  # if False, generator should choose a fallback if empty

    # If max_evals is set, keep strategy determines which items survive.
    # For v0: keep_first preserves the panelist's order.
    keep_strategy: str = "keep_first"  # future: "random", "rerank", etc.