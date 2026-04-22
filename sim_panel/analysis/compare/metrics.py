from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Optional

from sim_panel.analysis.compare.types import ConditionMetrics
from sim_panel.analysis.metrics.utils import (
    extract_outcome_values,
    group_numeric_outcome_by_field,
    group_numeric_outcome_by_two_fields,
    safe_mean,
    safe_variance,
)


def _compute_condition_metrics(
    evaluation_rows: List[Dict[str, Any]],
    *,
    outcome_field: str,
    label: str,
    model: str,
    strategy: str,
    rating_scale: Optional[List[int]],
) -> ConditionMetrics:
    m = ConditionMetrics(label=label, model=model, strategy=strategy)
    m.n_evaluations = len(evaluation_rows)

    values_raw = extract_outcome_values(evaluation_rows, outcome_field)
    values = [
        float(v)
        for v in values_raw
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    ]
    m.n_with_outcome = len(values)
    m._values = values

    if not values:
        return m

    m.rating_mean = safe_mean(values)
    var = safe_variance(values)
    m.rating_std = math.sqrt(var) if var is not None else None
    m.rating_median = float(sorted(values)[len(values) // 2])

    counts = dict(Counter(values_raw))
    m.rating_distribution = counts

    total = sum(counts.values())
    if total > 0:
        h = 0.0
        for n in counts.values():
            if n > 0:
                p = n / total
                h -= p * math.log(p, 2)
        m.rating_entropy = h

        n_support = len(rating_scale) if rating_scale else len(counts)
        if n_support > 1:
            m.rating_normalized_entropy = h / math.log(n_support, 2)

    by_panelist = group_numeric_outcome_by_field(
        evaluation_rows,
        group_field="panelist_id",
        outcome_field=outcome_field,
    )
    panelist_means = [safe_mean(v) for v in by_panelist.values() if v]
    panelist_means_clean = [x for x in panelist_means if x is not None]
    m.panelist_mean_variance = safe_variance(panelist_means_clean)

    by_product_then_panelist = group_numeric_outcome_by_two_fields(
        evaluation_rows,
        outer_field="product_id",
        inner_field="panelist_id",
        outcome_field=outcome_field,
    )
    m.mean_pairwise_panelist_distance = _mean_pairwise_distance(
        by_product_then_panelist
    )

    by_product = group_numeric_outcome_by_field(
        evaluation_rows,
        group_field="product_id",
        outcome_field=outcome_field,
    )
    product_means = [safe_mean(v) for v in by_product.values() if v]
    product_means_clean = [x for x in product_means if x is not None]
    m.product_mean_variance = safe_variance(product_means_clean)

    return m


def _mean_pairwise_distance(
    grouped: Dict[Any, Dict[Any, List[float]]],
) -> Optional[float]:
    """Average L1 distance between entity profiles over overlapping items."""
    entity_profiles: Dict[Any, Dict[Any, float]] = {}
    for outer_id, inner in grouped.items():
        for inner_id, values in inner.items():
            mu = safe_mean(values)
            if mu is not None:
                entity_profiles.setdefault(inner_id, {})[outer_id] = mu

    entities = list(entity_profiles.keys())
    if len(entities) < 2:
        return None

    distances: List[float] = []
    for i in range(len(entities)):
        for j in range(i + 1, len(entities)):
            p_i = entity_profiles[entities[i]]
            p_j = entity_profiles[entities[j]]
            overlap = set(p_i.keys()) & set(p_j.keys())
            if not overlap:
                continue
            dist = sum(abs(p_i[k] - p_j[k]) for k in overlap) / len(overlap)
            distances.append(dist)

    return safe_mean(distances)