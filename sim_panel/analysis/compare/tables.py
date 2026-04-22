from __future__ import annotations

from typing import Any, Dict, List

from sim_panel.analysis.compare.types import ConditionMetrics


def build_flat_table(metrics: List[ConditionMetrics]) -> List[Dict[str, Any]]:
    """One row per condition with all metrics."""
    rows: List[Dict[str, Any]] = []
    for m in metrics:
        rows.append(
            {
                "label": m.label,
                "model": m.model,
                "strategy": m.strategy,
                "n_evaluations": m.n_evaluations,
                "n_with_outcome": m.n_with_outcome,
                "rating_mean": m.rating_mean,
                "rating_std": m.rating_std,
                "rating_median": m.rating_median,
                "rating_entropy": m.rating_entropy,
                "rating_normalized_entropy": m.rating_normalized_entropy,
                "panelist_mean_variance": m.panelist_mean_variance,
                "mean_pairwise_panelist_distance": m.mean_pairwise_panelist_distance,
                "product_mean_variance": m.product_mean_variance,
            }
        )
    return rows


def build_pivot_table(
    metrics: List[ConditionMetrics],
    metric_name: str,
) -> Dict[str, Dict[str, Any]]:
    """Build model (rows) x strategy (columns) pivot for a single metric."""
    table: Dict[str, Dict[str, Any]] = {}
    for m in metrics:
        table.setdefault(m.model, {})[m.strategy] = getattr(m, metric_name, None)
    return table