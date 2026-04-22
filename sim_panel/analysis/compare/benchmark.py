from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sim_panel.analysis.compare.cross import _jensen_shannon_divergence
from sim_panel.analysis.compare.tables import build_flat_table, build_pivot_table
from sim_panel.analysis.compare.types import CompareConfig, ConditionMetrics


def build_benchmark_comparison_artifacts(
    *,
    config: CompareConfig,
    metrics: List[ConditionMetrics],
    eval_rows_by_label: Dict[str, List[Dict[str, Any]]],
    reference_label: str,
) -> Dict[str, Any]:
    """
    Build artifacts for benchmark mode, where one real condition acts as the
    reference and each synthetic condition is benchmarked against it.

    Main outputs:
    - condition_metrics: per-condition descriptive metrics
    - benchmark_summary: one row per synthetic condition
    - benchmark_product_diagnostics_topk: best/worst K products per condition
    - pivot_tables: synthetic-only pivots for descriptive metrics
    """
    flat_table = build_flat_table(metrics)
    reference_rows = eval_rows_by_label.get(reference_label, [])

    synthetic_metrics = [m for m in metrics if m.label != reference_label]

    #-----------------------------------------------------------------------------
    # Per-condition Summary
    #-----------------------------------------------------------------------------

    pivot_metrics = [
        "rating_mean",
        "rating_std",
        "panelist_mean_variance",
        "mean_pairwise_panelist_distance",
        "product_mean_variance",
        "rating_normalized_entropy",
    ]
    pivot_tables = {
        name: build_pivot_table(synthetic_metrics, name)
        for name in pivot_metrics
    }

    #-----------------------------------------------------------------------------
    # Benchmark Summary
    #-----------------------------------------------------------------------------
    benchmark_summary: List[Dict[str, Any]] = []
    diagnostics_topk: List[Dict[str, Any]] = []

    reference_product_ids = _get_product_id_set(reference_rows)
    reference_product_count_map = _build_product_review_count_map(reference_rows)

    for condition_metric in synthetic_metrics:
        condition_rows = eval_rows_by_label.get(condition_metric.label, [])
        condition_product_ids = _get_product_id_set(condition_rows)
        shared_product_ids = reference_product_ids & condition_product_ids

        #-----------------------------------------------------------------------------
        # Step 1: Calculate product overlap rates
        #-----------------------------------------------------------------------------

        overlap_stats = _compute_product_overlap_stats(
            reference_product_ids=reference_product_ids,
            condition_product_ids=condition_product_ids,
            shared_product_ids=shared_product_ids,
        )

        #-----------------------------------------------------------------------------
        # Step 2: Review distribution comparison over shared products
        #-----------------------------------------------------------------------------

        review_distribution_stats = _compute_review_distribution_stats(
            reference_rows=reference_rows,
            condition_rows=condition_rows,
            shared_product_ids=shared_product_ids,
        )

        #-----------------------------------------------------------------------------
        # Step 3: Overall rating distribution comparison over shared products
        #-----------------------------------------------------------------------------

        overall_rating_stats = _compute_overall_rating_stats(
            reference_rows=reference_rows,
            condition_rows=condition_rows,
            shared_product_ids=shared_product_ids,
            outcome_field=config.outcome_field,
        )

        #-----------------------------------------------------------------------------
        # Step 4: Rating comparison over shared products
        #-----------------------------------------------------------------------------

        product_rating_rows = _build_product_rating_diagnostics(
            reference_rows=reference_rows,
            condition_rows=condition_rows,
            shared_product_ids=shared_product_ids,
            outcome_field=config.outcome_field,
            reference_label=reference_label,
            condition_metric=condition_metric,
        )

        rating_jsd_egalitarian = _aggregate_product_metric(
            product_rows=product_rating_rows,
            metric_key="product_js_divergence",
            weighting="egalitarian",
            reference_product_count_map=reference_product_count_map,
        )
        rating_jsd_utilitarian = _aggregate_product_metric(
            product_rows=product_rating_rows,
            metric_key="product_js_divergence",
            weighting="utilitarian",
            reference_product_count_map=reference_product_count_map,
        )
        rating_emd_egalitarian = _aggregate_product_metric(
            product_rows=product_rating_rows,
            metric_key="product_emd",
            weighting="egalitarian",
            reference_product_count_map=reference_product_count_map,
        )
        rating_emd_utilitarian = _aggregate_product_metric(
            product_rows=product_rating_rows,
            metric_key="product_emd",
            weighting="utilitarian",
            reference_product_count_map=reference_product_count_map,
        )

        benchmark_summary.append(
            {
                "reference_label": reference_label,
                "label": condition_metric.label,
                "model": condition_metric.model,
                "strategy": condition_metric.strategy,
                "n_reference_products": overlap_stats["n_reference_products"],
                "n_condition_products": overlap_stats["n_condition_products"],
                "n_shared_products": overlap_stats["n_shared_products"],
                "product_overlap_rate_vs_reference": overlap_stats["product_overlap_rate_vs_reference"],
                "product_jaccard_overlap": overlap_stats["product_jaccard_overlap"],
                "n_reference_reviews_on_shared_products": review_distribution_stats["n_reference_reviews_on_shared_products"],
                "n_condition_reviews_on_shared_products": review_distribution_stats["n_condition_reviews_on_shared_products"],
                "shared_product_review_js_divergence": review_distribution_stats["shared_product_review_js_divergence"],
                "shared_product_review_l1_distance": review_distribution_stats["shared_product_review_l1_distance"],
                "overall_rating_js_divergence": overall_rating_stats["overall_rating_js_divergence"],
                "overall_rating_emd": overall_rating_stats["overall_rating_emd"],
                "rating_jsd_egalitarian": rating_jsd_egalitarian,
                "rating_jsd_utilitarian": rating_jsd_utilitarian,
                "rating_emd_egalitarian": rating_emd_egalitarian,
                "rating_emd_utilitarian": rating_emd_utilitarian,
            }
        )

        diagnostics_topk.extend(
            _select_topk_product_diagnostics(
                product_rows=product_rating_rows,
                top_k=config.benchmark_top_k_products,
            )
        )

    return {
        "mode": "benchmark",
        "reference_label": reference_label,
        "condition_metrics": flat_table,
        "benchmark_summary": benchmark_summary,
        "benchmark_product_diagnostics_topk": diagnostics_topk,
        "pivot_tables": pivot_tables,
    }


def _get_product_id_set(rows: List[Dict[str, Any]]) -> set[Any]:
    return {
        row.get("product_id")
        for row in rows
        if row.get("product_id") is not None
    }


def _compute_product_overlap_stats(
    *,
    reference_product_ids: set[Any],
    condition_product_ids: set[Any],
    shared_product_ids: set[Any],
) -> Dict[str, Optional[float]]:
    n_reference_products = len(reference_product_ids)
    n_condition_products = len(condition_product_ids)
    n_shared_products = len(shared_product_ids)
    n_union_products = len(reference_product_ids | condition_product_ids)

    product_overlap_rate_vs_reference = None
    if n_reference_products > 0:
        product_overlap_rate_vs_reference = n_shared_products / n_reference_products

    product_jaccard_overlap = None
    if n_union_products > 0:
        product_jaccard_overlap = n_shared_products / n_union_products

    return {
        "n_reference_products": n_reference_products,
        "n_condition_products": n_condition_products,
        "n_shared_products": n_shared_products,
        "product_overlap_rate_vs_reference": product_overlap_rate_vs_reference,
        "product_jaccard_overlap": product_jaccard_overlap,
    }


def _compute_review_distribution_stats(
    *,
    reference_rows: List[Dict[str, Any]],
    condition_rows: List[Dict[str, Any]],
    shared_product_ids: set[Any],
) -> Dict[str, Optional[float]]:
    reference_counts = _build_product_review_count_map(
        reference_rows,
        allowed_product_ids=shared_product_ids,
    )
    condition_counts = _build_product_review_count_map(
        condition_rows,
        allowed_product_ids=shared_product_ids,
    )

    n_reference_reviews = sum(reference_counts.values())
    n_condition_reviews = sum(condition_counts.values())

    return {
        "n_reference_reviews_on_shared_products": n_reference_reviews,
        "n_condition_reviews_on_shared_products": n_condition_reviews,
        "shared_product_review_js_divergence": _jensen_shannon_divergence(
            reference_counts,
            condition_counts,
        ),
        "shared_product_review_l1_distance": _l1_distance_from_counts(
            reference_counts,
            condition_counts,
        ),
    }


def _compute_overall_rating_stats(
    *,
    reference_rows: List[Dict[str, Any]],
    condition_rows: List[Dict[str, Any]],
    shared_product_ids: set[Any],
    outcome_field: str,
) -> Dict[str, Optional[float]]:
    reference_rating_counts = _build_rating_count_distribution(
        reference_rows,
        outcome_field=outcome_field,
        allowed_product_ids=shared_product_ids,
    )
    condition_rating_counts = _build_rating_count_distribution(
        condition_rows,
        outcome_field=outcome_field,
        allowed_product_ids=shared_product_ids,
    )

    return {
        "overall_rating_js_divergence": _jensen_shannon_divergence(
            reference_rating_counts,
            condition_rating_counts,
        ),
        "overall_rating_emd": _wasserstein_distance_discrete(
            reference_rating_counts,
            condition_rating_counts,
        ),
    }


def _build_product_rating_diagnostics(
    *,
    reference_rows: List[Dict[str, Any]],
    condition_rows: List[Dict[str, Any]],
    shared_product_ids: set[Any],
    outcome_field: str,
    reference_label: str,
    condition_metric: ConditionMetrics,
) -> List[Dict[str, Any]]:
    reference_counts_by_product = _build_product_rating_distributions(
        reference_rows,
        outcome_field=outcome_field,
        allowed_product_ids=shared_product_ids,
    )
    condition_counts_by_product = _build_product_rating_distributions(
        condition_rows,
        outcome_field=outcome_field,
        allowed_product_ids=shared_product_ids,
    )

    reference_review_counts = _build_product_review_count_map(
        reference_rows,
        allowed_product_ids=shared_product_ids,
    )
    condition_review_counts = _build_product_review_count_map(
        condition_rows,
        allowed_product_ids=shared_product_ids,
    )

    shared_products_sorted = sorted(shared_product_ids, key=lambda x: str(x))
    rows: List[Dict[str, Any]] = []

    for product_id in shared_products_sorted:
        reference_dist = reference_counts_by_product.get(product_id, {})
        condition_dist = condition_counts_by_product.get(product_id, {})

        if not reference_dist or not condition_dist:
            continue

        rows.append(
            {
                "reference_label": reference_label,
                "label": condition_metric.label,
                "model": condition_metric.model,
                "strategy": condition_metric.strategy,
                "product_id": product_id,
                "n_reference_reviews": reference_review_counts.get(product_id, 0),
                "n_condition_reviews": condition_review_counts.get(product_id, 0),
                "product_js_divergence": _jensen_shannon_divergence(
                    reference_dist,
                    condition_dist,
                ),
                "product_emd": _wasserstein_distance_discrete(
                    reference_dist,
                    condition_dist,
                ),
                "reference_mean_rating": _mean_from_count_distribution(reference_dist),
                "condition_mean_rating": _mean_from_count_distribution(condition_dist),
            }
        )

    return rows


def _build_product_review_count_map(
    rows: List[Dict[str, Any]],
    allowed_product_ids: Optional[set[Any]] = None,
) -> Dict[Any, int]:
    counts: Counter[Any] = Counter()

    for row in rows:
        product_id = row.get("product_id")
        if product_id is None:
            continue
        if allowed_product_ids is not None and product_id not in allowed_product_ids:
            continue
        counts[product_id] += 1

    return dict(counts)


def _build_rating_count_distribution(
    rows: List[Dict[str, Any]],
    *,
    outcome_field: str,
    allowed_product_ids: Optional[set[Any]] = None,
) -> Dict[float, int]:
    counts: Counter[float] = Counter()

    for row in rows:
        product_id = row.get("product_id")
        if allowed_product_ids is not None and product_id not in allowed_product_ids:
            continue

        outcomes = row.get("outcomes")
        if not isinstance(outcomes, dict):
            continue

        value = outcomes.get(outcome_field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue

        counts[float(value)] += 1

    return dict(sorted(counts.items(), key=lambda kv: kv[0]))


def _build_product_rating_distributions(
    rows: List[Dict[str, Any]],
    *,
    outcome_field: str,
    allowed_product_ids: Optional[set[Any]] = None,
) -> Dict[Any, Dict[float, int]]:
    counts_by_product: Dict[Any, Counter[float]] = defaultdict(Counter)

    for row in rows:
        product_id = row.get("product_id")
        if product_id is None:
            continue
        if allowed_product_ids is not None and product_id not in allowed_product_ids:
            continue

        outcomes = row.get("outcomes")
        if not isinstance(outcomes, dict):
            continue

        value = outcomes.get(outcome_field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue

        counts_by_product[product_id][float(value)] += 1

    out: Dict[Any, Dict[float, int]] = {}
    for product_id, counts in counts_by_product.items():
        out[product_id] = dict(sorted(counts.items(), key=lambda kv: kv[0]))
    return out


def _normalize_count_dict(counts: Dict[Any, int]) -> Dict[Any, float]:
    total = sum(counts.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in counts.items()}


def _l1_distance_from_counts(
    counts_a: Dict[Any, int],
    counts_b: Dict[Any, int],
) -> Optional[float]:
    probs_a = _normalize_count_dict(counts_a)
    probs_b = _normalize_count_dict(counts_b)

    all_keys = set(probs_a.keys()) | set(probs_b.keys())
    if not all_keys:
        return None

    return sum(abs(probs_a.get(k, 0.0) - probs_b.get(k, 0.0)) for k in all_keys)


def _wasserstein_distance_discrete(
    counts_a: Dict[float, int],
    counts_b: Dict[float, int],
) -> Optional[float]:
    """
    Wasserstein-1 distance for 1D discrete ordinal supports using count dicts.

    For discrete 1D distributions, W1 can be computed from the L1 gap between
    cumulative distributions across sorted support values.
    """
    total_a = sum(counts_a.values())
    total_b = sum(counts_b.values())
    if total_a <= 0 or total_b <= 0:
        return None

    support = sorted(set(counts_a.keys()) | set(counts_b.keys()))
    if len(support) <= 1:
        return 0.0

    probs_a = {k: counts_a.get(k, 0) / total_a for k in support}
    probs_b = {k: counts_b.get(k, 0) / total_b for k in support}

    cumulative_a = 0.0
    cumulative_b = 0.0
    distance = 0.0

    for i in range(len(support) - 1):
        x = support[i]
        next_x = support[i + 1]
        cumulative_a += probs_a[x]
        cumulative_b += probs_b[x]
        distance += abs(cumulative_a - cumulative_b) * (next_x - x)

    return distance


def _mean_from_count_distribution(
    counts: Dict[float, int],
) -> Optional[float]:
    total = sum(counts.values())
    if total <= 0:
        return None
    return sum(value * count for value, count in counts.items()) / total


def _aggregate_product_metric(
    *,
    product_rows: List[Dict[str, Any]],
    metric_key: str,
    weighting: str,
    reference_product_count_map: Dict[Any, int],
) -> Optional[float]:
    valid_rows = [
        row for row in product_rows
        if isinstance(row.get(metric_key), (int, float))
    ]
    if not valid_rows:
        return None

    if weighting == "egalitarian":
        values = [float(row[metric_key]) for row in valid_rows]
        return sum(values) / len(values)

    if weighting == "utilitarian":
        weighted_sum = 0.0
        weight_total = 0.0

        for row in valid_rows:
            product_id = row.get("product_id")
            weight = float(reference_product_count_map.get(product_id, 0))
            if weight <= 0:
                continue
            weighted_sum += float(row[metric_key]) * weight
            weight_total += weight

        if weight_total <= 0:
            return None
        return weighted_sum / weight_total

    raise ValueError(f"Unsupported weighting scheme: {weighting!r}")


def _select_topk_product_diagnostics(
    *,
    product_rows: List[Dict[str, Any]],
    top_k: int,
) -> List[Dict[str, Any]]:
    if top_k <= 0:
        return []

    ranked_rows = [
        row for row in product_rows
        if isinstance(row.get("product_emd"), (int, float))
    ]
    if not ranked_rows:
        return []

    ranked_rows = sorted(
        ranked_rows,
        key=lambda row: (float(row["product_emd"]), str(row.get("product_id"))),
    )

    best_rows = ranked_rows[:top_k]
    worst_rows = list(reversed(ranked_rows[-top_k:]))

    output_rows: List[Dict[str, Any]] = []

    for row in best_rows:
        output_rows.append(
            {
                **row,
                "diagnostic_bucket": "best_by_emd",
            }
        )

    for row in worst_rows:
        output_rows.append(
            {
                **row,
                "diagnostic_bucket": "worst_by_emd",
            }
        )

    return output_rows