from __future__ import annotations

import os
from collections import Counter
from typing import Any, Dict, List

import matplotlib.pyplot as plt

from sim_panel.analysis.compare.types import ConditionSpec
from sim_panel.io.paths import ensure_dir


def save_benchmark_rating_bar_charts(
    *,
    eval_rows_by_label: Dict[str, List[Dict[str, Any]]],
    conditions: List[ConditionSpec],
    outcome_field: str,
    reference_label: str,
    output_dir: str,
    filename: str = "benchmark_rating_bar_charts.png",
) -> str:
    """
    Save a single-row panel of overall rating bar charts for benchmark mode.

    Ordering:
    - synthetic conditions first, preserving config order
    - reference condition last

    Each panel shows the normalized rating distribution (share) for one
    condition over the full set of that condition's evaluation rows.
    """
    ensure_dir(output_dir)

    ordered_conditions = _order_conditions_for_benchmark_plot(
        conditions=conditions,
        reference_label=reference_label,
    )
    if not ordered_conditions:
        raise ValueError("No conditions available for benchmark rating bar charts.")

    distributions_by_label = {
        cond.label: _build_rating_count_distribution(
            eval_rows_by_label.get(cond.label, []),
            outcome_field=outcome_field,
        )
        for cond in ordered_conditions
    }

    support = sorted(
        {
            rating
            for counts in distributions_by_label.values()
            for rating in counts.keys()
        }
    )
    if not support:
        raise ValueError(
            f"No numeric outcomes found for outcome_field={outcome_field!r}."
        )

    n_panels = len(ordered_conditions)
    fig_width = max(4.0 * n_panels, 8.0)
    fig, axes = plt.subplots(1, n_panels, figsize=(fig_width, 4.5), squeeze=False)
    axes_row = list(axes[0])

    max_share = 0.0
    shares_by_label: Dict[str, Dict[float, float]] = {}
    for cond in ordered_conditions:
        counts = distributions_by_label[cond.label]
        shares = _normalize_count_dict(counts)
        shares_by_label[cond.label] = shares
        if shares:
            max_share = max(max_share, max(shares.values()))

    y_max = max_share * 1.1 if max_share > 0 else 1.0

    for i, (ax, cond) in enumerate(zip(axes_row, ordered_conditions)):
        label = cond.label
        shares = shares_by_label[label]
        y_values = [shares.get(rating, 0.0) for rating in support]

        ax.bar(support, y_values)
        ax.set_title(label, fontsize=10)
        ax.set_xlabel(outcome_field)
        if i == 0:
            ax.set_ylabel("share")
        else:
            ax.set_ylabel("")
        ax.set_xticks(support)
        ax.set_ylim(0.0, y_max)

    fig.suptitle("Benchmark rating bar charts", y=1.02)
    fig.tight_layout()

    out_path = os.path.join(output_dir, filename)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return out_path


def _order_conditions_for_benchmark_plot(
    *,
    conditions: List[ConditionSpec],
    reference_label: str,
) -> List[ConditionSpec]:
    synthetic_conditions = [
        cond for cond in conditions if cond.label != reference_label
    ]
    reference_conditions = [
        cond for cond in conditions if cond.label == reference_label
    ]

    if len(reference_conditions) != 1:
        raise ValueError(
            "Expected exactly one reference condition when building benchmark plot; "
            f"found {len(reference_conditions)} for label {reference_label!r}."
        )

    return synthetic_conditions + reference_conditions


def _build_rating_count_distribution(
    rows: List[Dict[str, Any]],
    *,
    outcome_field: str,
) -> Dict[float, int]:
    counts: Counter[float] = Counter()

    for row in rows:
        outcomes = row.get("outcomes")
        if not isinstance(outcomes, dict):
            continue

        value = outcomes.get(outcome_field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue

        counts[float(value)] += 1

    return dict(sorted(counts.items(), key=lambda kv: kv[0]))


def _normalize_count_dict(counts: Dict[float, int]) -> Dict[float, float]:
    total = sum(counts.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in counts.items()}