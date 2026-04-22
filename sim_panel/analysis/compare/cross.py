from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Optional

from sim_panel.analysis.compare.tables import build_flat_table, build_pivot_table
from sim_panel.analysis.compare.types import ConditionMetrics, CompareConfig


def build_cross_comparison_artifacts(
    *,
    config: CompareConfig,
    metrics: List[ConditionMetrics],
    eval_rows_by_label: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Build artifacts for synthetic-vs-synthetic cross comparison mode.
    """
    flat_table = build_flat_table(metrics)

    pivot_metrics = [
        "rating_mean",
        "rating_std",
        "panelist_mean_variance",
        "mean_pairwise_panelist_distance",
        "product_mean_variance",
        "rating_normalized_entropy",
    ]
    pivot_tables = {
        name: build_pivot_table(metrics, name)
        for name in pivot_metrics
    }

    js_matrix = _build_js_divergence_matrix(metrics)
    rmse_matrix = _build_rmse_matrix(
        metrics,
        eval_rows_by_label,
        config.outcome_field,
    )

    return {
        "mode": "cross",
        "condition_metrics": flat_table,
        "pivot_tables": pivot_tables,
        "js_divergence_matrix": js_matrix,
        "pairwise_rmse_matrix": rmse_matrix,
    }

def _jensen_shannon_divergence(
    dist_a: Dict[Any, int],
    dist_b: Dict[Any, int],
) -> Optional[float]:
    """Symmetric JS divergence (bits) between two count distributions."""
    all_keys = set(dist_a.keys()) | set(dist_b.keys())
    if not all_keys:
        return None

    total_a = sum(dist_a.values())
    total_b = sum(dist_b.values())
    if total_a == 0 or total_b == 0:
        return None

    p = {k: dist_a.get(k, 0) / total_a for k in all_keys}
    q = {k: dist_b.get(k, 0) / total_b for k in all_keys}
    m = {k: (p[k] + q[k]) / 2 for k in all_keys}

    def _kl(a: Dict[Any, float], b: Dict[Any, float]) -> float:
        return sum(
            a[k] * math.log(a[k] / b[k], 2)
            for k in all_keys
            if a[k] > 0 and b[k] > 0
        )

    return (_kl(p, m) + _kl(q, m)) / 2


def _pairwise_rmse(
    rows_a: List[Dict[str, Any]],
    rows_b: List[Dict[str, Any]],
    outcome_field: str,
) -> Optional[float]:
    """
    RMSE between two conditions computed over shared (panelist, product) pairs.
    Each pair's value is the mean outcome for that (panelist, product) in each condition.
    """

    def _build_profile(rows: List[Dict[str, Any]]) -> Dict[tuple[Any, Any], float]:
        accum: Dict[tuple[Any, Any], List[float]] = defaultdict(list)
        for row in rows:
            outcomes = row.get("outcomes")
            if not isinstance(outcomes, dict):
                continue
            v = outcomes.get(outcome_field)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            key = (row.get("panelist_id"), row.get("product_id"))
            accum[key].append(float(v))
        return {k: sum(vs) / len(vs) for k, vs in accum.items() if vs}

    prof_a = _build_profile(rows_a)
    prof_b = _build_profile(rows_b)
    shared = set(prof_a.keys()) & set(prof_b.keys())

    if not shared:
        return None

    sse = sum((prof_a[k] - prof_b[k]) ** 2 for k in shared)
    return math.sqrt(sse / len(shared))


def _build_js_divergence_matrix(
    metrics: List[ConditionMetrics],
) -> Dict[str, Dict[str, Optional[float]]]:
    """Pairwise Jensen-Shannon divergence between all conditions."""
    matrix: Dict[str, Dict[str, Optional[float]]] = {}
    for i, a in enumerate(metrics):
        row: Dict[str, Optional[float]] = {}
        for j, b in enumerate(metrics):
            if i == j:
                row[b.label] = 0.0
            else:
                row[b.label] = _jensen_shannon_divergence(
                    a.rating_distribution,
                    b.rating_distribution,
                )
        matrix[a.label] = row
    return matrix


def _build_rmse_matrix(
    metrics: List[ConditionMetrics],
    eval_rows_by_label: Dict[str, List[Dict[str, Any]]],
    outcome_field: str,
) -> Dict[str, Dict[str, Optional[float]]]:
    """Pairwise RMSE between all conditions over shared (panelist, product) pairs."""
    matrix: Dict[str, Dict[str, Optional[float]]] = {}
    for a in metrics:
        row: Dict[str, Optional[float]] = {}
        for b in metrics:
            if a.label == b.label:
                row[b.label] = 0.0
            else:
                row[b.label] = _pairwise_rmse(
                    eval_rows_by_label[a.label],
                    eval_rows_by_label[b.label],
                    outcome_field,
                )
        matrix[a.label] = row
    return matrix