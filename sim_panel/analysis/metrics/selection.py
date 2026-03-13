from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from sim_panel.analysis.metrics.utils import (
    entropy_from_counts,
    normalized_entropy_full_support,
    normalized_entropy_observed_support,
    safe_mean,
    value_counts,
)
from sim_panel.analysis.types import RunAnalysis


def compute_selection_metrics(run: RunAnalysis) -> Dict[str, Any]:
    """
    Compute metrics for selection rows.

    These are most relevant for self_selection runs, but safe for any run.

    Entropy metrics are reported in three forms:
    - raw entropy
    - normalized by full allowed product support
    - normalized by observed support
    """
    rows = run.selection_rows
    n_rows = len(rows)

    n_support_allowed = _resolve_selection_support_size(run)

    if n_rows == 0:
        return {
            "n_selection_rows": 0,
            "support_size_allowed": n_support_allowed,
            "avg_choice_set_size": None,
            "avg_requested_size": None,
            "avg_executed_size": None,
            "avg_dropped_size": None,
            "empty_request_rate": None,
            "empty_execution_rate": None,
            "request_to_execution_ratio": None,
            "drop_rate_over_requested": None,
            "requested_product_entropy": None,
            "requested_product_normalized_entropy_full_support": None,
            "requested_product_normalized_entropy_observed_support": None,
            "executed_product_entropy": None,
            "executed_product_normalized_entropy_full_support": None,
            "executed_product_normalized_entropy_observed_support": None,
            "n_unique_requested_products": 0,
            "n_unique_executed_products": 0,
        }

    choice_sizes: List[float] = []
    requested_sizes: List[float] = []
    executed_sizes: List[float] = []
    dropped_sizes: List[float] = []

    total_requested = 0
    total_executed = 0
    total_dropped = 0

    n_empty_request = 0
    n_empty_execution = 0

    requested_products: List[str] = []
    executed_products: List[str] = []

    for row in rows:
        choice_set = row.get("choice_set")
        selected = row.get("selected_product_ids")
        traces = row.get("traces") if isinstance(row.get("traces"), dict) else {}

        executed = traces.get("executed_product_ids", [])
        dropped = traces.get("dropped_product_ids", [])

        choice_size = len(choice_set) if isinstance(choice_set, list) else 0
        requested_size = len(selected) if isinstance(selected, list) else 0
        executed_size = len(executed) if isinstance(executed, list) else 0
        dropped_size = len(dropped) if isinstance(dropped, list) else 0

        choice_sizes.append(float(choice_size))
        requested_sizes.append(float(requested_size))
        executed_sizes.append(float(executed_size))
        dropped_sizes.append(float(dropped_size))

        total_requested += requested_size
        total_executed += executed_size
        total_dropped += dropped_size

        if requested_size == 0:
            n_empty_request += 1
        if executed_size == 0:
            n_empty_execution += 1

        if isinstance(selected, list):
            requested_products.extend(pid for pid in selected if isinstance(pid, str))
        if isinstance(executed, list):
            executed_products.extend(pid for pid in executed if isinstance(pid, str))

    requested_counts = value_counts(requested_products)
    executed_counts = value_counts(executed_products)

    return {
        "n_selection_rows": n_rows,
        "support_size_allowed": n_support_allowed,
        "avg_choice_set_size": safe_mean(choice_sizes),
        "avg_requested_size": safe_mean(requested_sizes),
        "avg_executed_size": safe_mean(executed_sizes),
        "avg_dropped_size": safe_mean(dropped_sizes),
        "empty_request_rate": n_empty_request / n_rows,
        "empty_execution_rate": n_empty_execution / n_rows,
        "request_to_execution_ratio": _safe_ratio(total_executed, total_requested),
        "drop_rate_over_requested": _safe_ratio(total_dropped, total_requested),
        "requested_product_entropy": entropy_from_counts(requested_counts),
        "requested_product_normalized_entropy_full_support": (
            normalized_entropy_full_support(requested_counts, n_support=n_support_allowed)
            if isinstance(n_support_allowed, int)
            else None
        ),
        "requested_product_normalized_entropy_observed_support": (
            normalized_entropy_observed_support(requested_counts)
        ),
        "executed_product_entropy": entropy_from_counts(executed_counts),
        "executed_product_normalized_entropy_full_support": (
            normalized_entropy_full_support(executed_counts, n_support=n_support_allowed)
            if isinstance(n_support_allowed, int)
            else None
        ),
        "executed_product_normalized_entropy_observed_support": (
            normalized_entropy_observed_support(executed_counts)
        ),
        "n_unique_requested_products": len(requested_counts),
        "n_unique_executed_products": len(executed_counts),
    }


def _resolve_selection_support_size(run: RunAnalysis) -> Optional[int]:
    """
    Resolve the full allowed product support size for selection entropy normalization.

    Preference order:
    1. metadata_flat["n_products"]
    2. unique products observed in selection choice sets
    3. None
    """
    n_products_meta = run.metadata_flat.get("n_products")
    if isinstance(n_products_meta, int) and n_products_meta > 0:
        return n_products_meta

    product_ids: Set[str] = set()
    for row in run.selection_rows:
        choice_set = row.get("choice_set")
        if isinstance(choice_set, list):
            product_ids.update(pid for pid in choice_set if isinstance(pid, str))

    if product_ids:
        return len(product_ids)

    return None


def _safe_ratio(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return num / den