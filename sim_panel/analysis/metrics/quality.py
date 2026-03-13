from __future__ import annotations

from typing import Any, Dict

from sim_panel.analysis.metrics.utils import (
    get_declared_outcome_fields,
    get_declared_trace_fields,
)
from sim_panel.analysis.types import RunAnalysis


def compute_quality_metrics(run: RunAnalysis) -> Dict[str, Any]:
    """
    Compute operational / completeness diagnostics for a single run.
    """
    n_events = len(run.events)
    n_selection_rows = len(run.selection_rows)
    n_evaluation_rows = len(run.evaluation_rows)

    rows_with_any_outcome = 0
    rows_with_any_trace = 0
    rows_with_panelist_features = 0
    rows_with_product_features = 0
    selection_linked_rows = 0

    for row in run.evaluation_rows:
        outcomes = row.get("outcomes")
        traces = row.get("traces")
        panelist_features = row.get("panelist_features")
        product_features = row.get("product_features")

        if isinstance(outcomes, dict) and len(outcomes) > 0:
            rows_with_any_outcome += 1
        if isinstance(traces, dict) and len(traces) > 0:
            rows_with_any_trace += 1
        if isinstance(panelist_features, dict) and len(panelist_features) > 0:
            rows_with_panelist_features += 1
        if isinstance(product_features, dict) and len(product_features) > 0:
            rows_with_product_features += 1
        if isinstance(row.get("selection_id"), str) and row.get("selection_id"):
            selection_linked_rows += 1

    outcome_missing_rates = _compute_outcome_missing_rates(run)
    trace_missing_rates = _compute_trace_missing_rates(run)

    return {
        "n_events": n_events,
        "n_selection_rows": n_selection_rows,
        "n_evaluation_rows": n_evaluation_rows,
        "rows_with_any_outcome_rate": _safe_rate(rows_with_any_outcome, n_evaluation_rows),
        "rows_with_any_trace_rate": _safe_rate(rows_with_any_trace, n_evaluation_rows),
        "panelist_feature_coverage_rate": _safe_rate(rows_with_panelist_features, n_evaluation_rows),
        "product_feature_coverage_rate": _safe_rate(rows_with_product_features, n_evaluation_rows),
        "selection_link_rate": _safe_rate(selection_linked_rows, n_evaluation_rows),
        "outcome_field_missing_rates": outcome_missing_rates,
        "trace_field_missing_rates": trace_missing_rates,
    }


def _compute_outcome_missing_rates(run: RunAnalysis) -> Dict[str, float]:
    declared = get_declared_outcome_fields(run.metadata)
    field_names = list(declared.keys())
    n = len(run.evaluation_rows)

    rates: Dict[str, float] = {}
    for field_name in field_names:
        missing = 0
        for row in run.evaluation_rows:
            outcomes = row.get("outcomes")
            if not isinstance(outcomes, dict) or field_name not in outcomes or outcomes[field_name] is None:
                missing += 1
        rates[field_name] = _safe_rate(missing, n)
    return rates


def _compute_trace_missing_rates(run: RunAnalysis) -> Dict[str, float]:
    declared = get_declared_trace_fields(run.metadata)
    field_names = list(declared.keys())
    n = len(run.events)

    rates: Dict[str, float] = {}
    for field_name in field_names:
        missing = 0
        for row in run.events:
            traces = row.get("traces")
            if not isinstance(traces, dict) or field_name not in traces or traces[field_name] is None:
                missing += 1
        rates[field_name] = _safe_rate(missing, n)
    return rates


def _safe_rate(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return num / den