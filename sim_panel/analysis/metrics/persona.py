from __future__ import annotations

from typing import Any, Dict, List, Tuple

from sim_panel.analysis.metrics.utils import (
    extract_outcome_values,
    get_declared_outcome_fields,
    group_numeric_outcome_by_field,
    group_numeric_outcome_by_two_fields,
    safe_mean,
    safe_variance,
)
from sim_panel.analysis.types import RunAnalysis


def compute_persona_metrics(
    run: RunAnalysis,
    *,
    outcome_field: str = "rating",
) -> Dict[str, Any]:
    """
    Compute simple persona-differentiation metrics for a numeric outcome field.

    v0 focuses on:
    - variance of persona means
    - variance of product means
    - mean variance across panelists within product
    - mean variance across products within panelist
    - mean pairwise distance between panelist profiles
    - mean pairwise distance between product profiles
    """
    declared = get_declared_outcome_fields(run.metadata)
    spec = declared.get(outcome_field, {})
    dtype = spec.get("type")

    if dtype not in {"int", "float"}:
        return {
            "outcome_field": outcome_field,
            "supported": False,
            "reason": f"Outcome field {outcome_field!r} is not declared as numeric (int or float).",
        }

    all_values = extract_outcome_values(run.evaluation_rows, outcome_field)
    numeric_values = [
        float(v)
        for v in all_values
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    ]

    by_panelist = group_numeric_outcome_by_field(
        run.evaluation_rows,
        group_field="panelist_id",
        outcome_field=outcome_field,
    )
    by_product = group_numeric_outcome_by_field(
        run.evaluation_rows,
        group_field="product_id",
        outcome_field=outcome_field,
    )
    by_product_then_panelist = group_numeric_outcome_by_two_fields(
        run.evaluation_rows,
        outer_field="product_id",
        inner_field="panelist_id",
        outcome_field=outcome_field,
    )

    by_panelist_then_product = group_numeric_outcome_by_two_fields(
        run.evaluation_rows,
        outer_field="panelist_id",
        inner_field="product_id",
        outcome_field=outcome_field,
    )

    panelist_means = {
        panelist_id: safe_mean(values)
        for panelist_id, values in by_panelist.items()
        if values
    }
    product_means = {
        product_id: safe_mean(values)
        for product_id, values in by_product.items()
        if values
    }

    return {
        "outcome_field": outcome_field,
        "supported": True,
        "n_observed": len(numeric_values),
        "overall_variance": safe_variance(numeric_values),
        "n_panelists_observed": len(panelist_means),
        "n_products_observed": len(product_means),
        "panelist_mean_variance": _variance_of_optional_values(list(panelist_means.values())),
        "product_mean_variance": _variance_of_optional_values(list(product_means.values())),
        "mean_within_product_panelist_variance": _mean_within_product_panelist_variance(
            by_product_then_panelist
        ),
        "mean_within_panelist_product_variance": _mean_within_panelist_product_variance(
            by_panelist_then_product
        ),
        "mean_pairwise_panelist_distance": _mean_pairwise_panelist_distance(
            by_product_then_panelist
        ),
        "mean_pairwise_product_distance": _mean_pairwise_product_distance(
            by_panelist_then_product
        ),
    }


def _mean_within_product_panelist_variance(
    grouped: Dict[Any, Dict[Any, List[float]]],
) -> float | None:
    """
    For each product, compute the variance of panelist mean outcomes.
    Then average that variance across products.
    """
    vars_: List[float] = []

    for _, inner in grouped.items():
        panelist_means: List[float] = []
        for _, values in inner.items():
            mu = safe_mean(values)
            if mu is not None:
                panelist_means.append(mu)

        var = safe_variance(panelist_means)
        if var is not None:
            vars_.append(var)

    return safe_mean(vars_)


def _mean_within_panelist_product_variance(
    grouped: Dict[Any, Dict[Any, List[float]]],
) -> float | None:
    """
    For each panelist, compute the variance of product mean outcomes.
    Then average that variance across panelists.
    """
    vars_: List[float] = []

    for _, inner in grouped.items():
        product_means: List[float] = []
        for _, values in inner.items():
            mu = safe_mean(values)
            if mu is not None:
                product_means.append(mu)

        var = safe_variance(product_means)
        if var is not None:
            vars_.append(var)

    return safe_mean(vars_)


def _mean_pairwise_panelist_distance(
    grouped: Dict[Any, Dict[Any, List[float]]],
) -> float | None:
    """
    Build panelist profiles over products using mean outcome per product,
    then compute average L1 distance over overlapping products.

    Input grouping:
        product_id -> panelist_id -> [values]
    """
    panelist_to_product_mean: Dict[Any, Dict[Any, float]] = {}

    for product_id, inner in grouped.items():
        for panelist_id, values in inner.items():
            mu = safe_mean(values)
            if mu is None:
                continue
            panelist_to_product_mean.setdefault(panelist_id, {})[product_id] = mu

    panelists = list(panelist_to_product_mean.keys())
    if len(panelists) < 2:
        return None

    distances: List[float] = []
    for i in range(len(panelists)):
        for j in range(i + 1, len(panelists)):
            p_i = panelist_to_product_mean[panelists[i]]
            p_j = panelist_to_product_mean[panelists[j]]
            overlap = sorted(set(p_i.keys()) & set(p_j.keys()))
            if not overlap:
                continue
            dist = sum(abs(p_i[pid] - p_j[pid]) for pid in overlap) / len(overlap)
            distances.append(dist)

    return safe_mean(distances)


def _mean_pairwise_product_distance(
    grouped: Dict[Any, Dict[Any, List[float]]],
) -> float | None:
    """
    Build product profiles over panelists using mean outcome per panelist,
    then compute average L1 distance over overlapping panelists.

    Input grouping:
        panelist_id -> product_id -> [values]
    """
    product_to_panelist_mean: Dict[Any, Dict[Any, float]] = {}

    for panelist_id, inner in grouped.items():
        for product_id, values in inner.items():
            mu = safe_mean(values)
            if mu is None:
                continue
            product_to_panelist_mean.setdefault(product_id, {})[panelist_id] = mu

    products = list(product_to_panelist_mean.keys())
    if len(products) < 2:
        return None

    distances: List[float] = []
    for i in range(len(products)):
        for j in range(i + 1, len(products)):
            p_i = product_to_panelist_mean[products[i]]
            p_j = product_to_panelist_mean[products[j]]
            overlap = sorted(set(p_i.keys()) & set(p_j.keys()))
            if not overlap:
                continue
            dist = sum(abs(p_i[pid] - p_j[pid]) for pid in overlap) / len(overlap)
            distances.append(dist)

    return safe_mean(distances)


def _variance_of_optional_values(values: List[float | None]) -> float | None:
    xs = [v for v in values if v is not None]
    return safe_variance(xs)