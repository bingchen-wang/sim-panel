from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt

from sim_panel.analysis.metadata import get_questionnaire_outcome_fields
from sim_panel.analysis.metrics.utils import extract_outcome_values
from sim_panel.analysis.types import PlotConfig, RunAnalysis
from sim_panel.io.paths import ensure_dir


def generate_plots(
    run: RunAnalysis,
    *,
    plot_cfg: PlotConfig,
) -> Dict[str, str]:
    """
    Generate plots for a single run from PlotConfig.
    """
    plots_dir = ensure_dir(os.path.join(run.output_dir, "plots"))
    paths: Dict[str, str] = {}

    if plot_cfg.outcome_distributions.enabled:
        paths.update(
            plot_outcome_distributions(
                run,
                output_dir=plots_dir,
                fields=plot_cfg.outcome_distributions.fields,
                normalize_to_share=plot_cfg.outcome_distributions.normalize_to_share,
                figsize=plot_cfg.outcome_distributions.figsize,
            )
        )

    if plot_cfg.panelist_summary.enabled:
        for metric in plot_cfg.panelist_summary.metrics:
            paths.update(
                plot_panelist_summary(
                    run,
                    output_dir=plots_dir,
                    outcome_field=plot_cfg.panelist_summary.outcome_field,
                    metric=metric,
                    max_items=plot_cfg.panelist_summary.max_items,
                    sort_by=plot_cfg.panelist_summary.sort_by,
                    horizontal=plot_cfg.panelist_summary.horizontal,
                )
            )

    if plot_cfg.product_summary.enabled:
        for metric in plot_cfg.product_summary.metrics:
            paths.update(
                plot_product_summary(
                    run,
                    output_dir=plots_dir,
                    outcome_field=plot_cfg.product_summary.outcome_field,
                    metric=metric,
                    max_items=plot_cfg.product_summary.max_items,
                    sort_by=plot_cfg.product_summary.sort_by,
                    horizontal=plot_cfg.product_summary.horizontal,
                )
            )

    if plot_cfg.selection_concentration.enabled:
        for mode in plot_cfg.selection_concentration.modes:
            use_executed = mode == "executed"
            paths.update(
                plot_selection_concentration(
                    run,
                    output_dir=plots_dir,
                    use_executed=use_executed,
                    top_k=plot_cfg.selection_concentration.top_k,
                    horizontal=plot_cfg.selection_concentration.horizontal,
                )
            )

    return paths


def plot_outcome_distributions(
    run: RunAnalysis,
    *,
    output_dir: str,
    fields: Optional[List[str]] = None,
    normalize_to_share: bool = False,
    figsize: Tuple[float, float] = (7, 4.5),
) -> Dict[str, str]:
    ensure_dir(output_dir)
    declared = get_questionnaire_outcome_fields(run.metadata)
    allowed_fields = set(fields) if fields is not None else None

    saved: Dict[str, str] = {}
    for field_name, spec in declared.items():
        if allowed_fields is not None and field_name not in allowed_fields:
            continue

        dtype = spec.get("type")
        values = extract_outcome_values(run.evaluation_rows, field_name)
        if not values:
            continue

        if dtype in {"int", "float", "categorical"}:
            fig, ax = plt.subplots(figsize=figsize)
            _plot_value_count_bars(
                ax=ax,
                values=values,
                title=f"{field_name} distribution",
                xlabel=field_name,
                ylabel="Share" if normalize_to_share else "Count",
                sort_numeric=(dtype in {"int", "float"}),
                normalize_to_share=normalize_to_share,
            )
            fig.tight_layout()

            suffix = "share" if normalize_to_share else "count"
            path = os.path.join(output_dir, f"outcome_distribution_{field_name}_{suffix}.png")
            fig.savefig(path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            saved[f"outcome_distribution_{field_name}_{suffix}"] = path

    return saved


def plot_panelist_summary(
    run: RunAnalysis,
    *,
    output_dir: str,
    outcome_field: str = "rating",
    metric: str = "mean",
    max_items: Optional[int] = 30,
    sort_by: str = "label_asc",
    horizontal: bool = False,
) -> Dict[str, str]:
    ensure_dir(output_dir)
    _validate_summary_metric(metric)

    grouped = _group_numeric_outcome_by_panelist(run, outcome_field=outcome_field)
    if not grouped:
        return {}

    stats: List[Tuple[str, float]] = []
    for panelist_id, values in grouped.items():
        if not values:
            continue

        val = _variance(values) if metric == "variance" else _mean(values)
        if val is not None:
            stats.append((panelist_id, val))

    if not stats:
        return {}

    stats = _sort_labeled_values(stats, sort_by=sort_by)

    if isinstance(max_items, int) and max_items > 0:
        stats = stats[:max_items]

    fig = _plot_labeled_bars(
        items=stats,
        title=f"{outcome_field}: {metric} by panelist",
        xlabel="Panelist",
        ylabel="Outcome variance" if metric == "variance" else "Mean outcome",
        horizontal=horizontal,
    )

    path = os.path.join(output_dir, f"panelist_{metric}_{outcome_field}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return {f"panelist_{metric}_{outcome_field}": path}


def plot_product_summary(
    run: RunAnalysis,
    *,
    output_dir: str,
    outcome_field: str = "rating",
    metric: str = "mean",
    max_items: Optional[int] = 30,
    sort_by: str = "label_asc",
    horizontal: bool = False,
) -> Dict[str, str]:
    ensure_dir(output_dir)
    _validate_summary_metric(metric)

    grouped = _group_numeric_outcome_by_product(run, outcome_field=outcome_field)
    if not grouped:
        return {}

    stats: List[Tuple[str, float]] = []
    for product_id, values in grouped.items():
        if not values:
            continue

        val = _variance(values) if metric == "variance" else _mean(values)
        if val is not None:
            stats.append((product_id, val))

    if not stats:
        return {}

    stats = _sort_labeled_values(stats, sort_by=sort_by)

    if isinstance(max_items, int) and max_items > 0:
        stats = stats[:max_items]

    fig = _plot_labeled_bars(
        items=stats,
        title=f"{outcome_field}: {metric} by product",
        xlabel="Product",
        ylabel="Outcome variance" if metric == "variance" else "Mean outcome",
        horizontal=horizontal,
    )

    path = os.path.join(output_dir, f"product_{metric}_{outcome_field}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return {f"product_{metric}_{outcome_field}": path}


def plot_selection_concentration(
    run: RunAnalysis,
    *,
    output_dir: str,
    use_executed: bool = True,
    top_k: Optional[int] = 15,
    horizontal: bool = True,
) -> Dict[str, str]:
    ensure_dir(output_dir)

    counts = _selection_product_counts(run, use_executed=use_executed)
    items = list(counts.items())
    items.sort(key=lambda x: x[1], reverse=True)

    if isinstance(top_k, int) and top_k > 0:
        items = items[:top_k]

    if not items:
        return {}

    mode = "executed" if use_executed else "requested"

    fig = _plot_labeled_bars(
        items=items,
        title=f"Selection concentration ({mode})",
        xlabel="Product",
        ylabel="Count",
        horizontal=horizontal,
    )

    path = os.path.join(output_dir, f"selection_concentration_{mode}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return {f"selection_concentration_{mode}": path}


def _plot_value_count_bars(
    *,
    ax,
    values: List[Any],
    title: str,
    xlabel: str,
    ylabel: str,
    sort_numeric: bool,
    normalize_to_share: bool,
) -> None:
    counts = _value_counts(values)

    if sort_numeric:
        items = sorted(counts.items(), key=lambda kv: kv[0])
    else:
        items = sorted(counts.items(), key=lambda kv: str(kv[0]))

    labels = [str(k) for k, _ in items]
    heights = [v for _, v in items]

    if normalize_to_share:
        total = sum(heights)
        if total > 0:
            heights = [h / total for h in heights]

    ax.bar(labels, heights)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)


def _plot_labeled_bars(
    *,
    items: List[Tuple[str, float]],
    title: str,
    xlabel: str,
    ylabel: str,
    horizontal: bool,
):
    n = len(items)
    width = max(8, n * 0.5) if not horizontal else 8
    height = 4.5 if not horizontal else max(4.5, n * 0.35)

    fig, ax = plt.subplots(figsize=(width, height))
    labels = [x[0] for x in items]
    values = [x[1] for x in items]

    if horizontal:
        ax.barh(labels, values)
        ax.set_ylabel(xlabel)
        ax.set_xlabel(ylabel)
    else:
        ax.bar(labels, values)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=45)

    ax.set_title(title)
    fig.tight_layout()
    return fig


def _group_numeric_outcome_by_panelist(
    run: RunAnalysis,
    *,
    outcome_field: str,
) -> Dict[str, List[float]]:
    grouped: Dict[str, List[float]] = {}

    for row in run.evaluation_rows:
        panelist_id = row.get("panelist_id")
        outcomes = row.get("outcomes")
        if not isinstance(panelist_id, str):
            continue
        if not isinstance(outcomes, dict):
            continue

        value = outcomes.get(outcome_field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            grouped.setdefault(panelist_id, []).append(float(value))

    return grouped


def _group_numeric_outcome_by_product(
    run: RunAnalysis,
    *,
    outcome_field: str,
) -> Dict[str, List[float]]:
    grouped: Dict[str, List[float]] = {}

    for row in run.evaluation_rows:
        product_id = row.get("product_id")
        outcomes = row.get("outcomes")
        if not isinstance(product_id, str):
            continue
        if not isinstance(outcomes, dict):
            continue

        value = outcomes.get(outcome_field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            grouped.setdefault(product_id, []).append(float(value))

    return grouped


def _selection_product_counts(run: RunAnalysis, *, use_executed: bool) -> Dict[str, int]:
    counts: Dict[str, int] = {}

    for row in run.selection_rows:
        traces = row.get("traces") if isinstance(row.get("traces"), dict) else {}
        if use_executed:
            product_ids = traces.get("executed_product_ids", [])
        else:
            product_ids = row.get("selected_product_ids", [])

        if isinstance(product_ids, list):
            for pid in product_ids:
                if isinstance(pid, str):
                    counts[pid] = counts.get(pid, 0) + 1

    return counts


def _sort_labeled_values(
    items: List[Tuple[str, float]],
    *,
    sort_by: str,
) -> List[Tuple[str, float]]:
    if sort_by == "label_desc":
        return sorted(items, key=lambda x: x[0], reverse=True)
    if sort_by == "value_asc":
        return sorted(items, key=lambda x: x[1])
    if sort_by == "value_desc":
        return sorted(items, key=lambda x: x[1], reverse=True)
    return sorted(items, key=lambda x: x[0])


def _validate_summary_metric(metric: str) -> None:
    if metric not in {"mean", "variance"}:
        raise ValueError(f"Unsupported metric {metric!r}. Expected 'mean' or 'variance'.")


def _value_counts(values: List[Any]) -> Dict[Any, int]:
    counts: Dict[Any, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return counts


def _mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def _variance(values: List[float]) -> Optional[float]:
    if len(values) < 2:
        return None
    mu = sum(values) / len(values)
    return sum((x - mu) ** 2 for x in values) / len(values)