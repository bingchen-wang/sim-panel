from __future__ import annotations

import os
from typing import Any, Dict, Optional

from sim_panel.analysis.regression.summarize import (
    filter_coefficient_table,
    dropped_columns_to_dataframe,
)
from sim_panel.analysis.regression.types import RegressionResult
from sim_panel.analysis.types import RunAnalysis


def build_markdown_report(run: RunAnalysis) -> str:
    """
    Build a markdown report for a single analyzed run.

    Sections:
    - Run overview
    - Quality metrics
    - Outcome summary
    - Diversity metrics
    - Panelist/product differentiation
    - Selection behavior
    - Regression analysis
    - Plot artifacts
    - Notes
    """
    lines: list[str] = []

    run_summary = run.artifacts.get("run_summary", {})
    quality_metrics = run.artifacts.get("quality_metrics", {})
    outcome_summary = run.artifacts.get("outcome_summary", {})
    diversity_metrics = run.artifacts.get("diversity_metrics", {})
    persona_metrics = run.artifacts.get("persona_metrics", {})
    selection_metrics = run.artifacts.get("selection_metrics", {})
    regression = run.artifacts.get("regression", {})
    plots = run.artifacts.get("plots", {})

    # ---- title ----
    lines.append(f"# Analysis report: {run_summary.get('run_name', 'run')}")
    lines.append("")

    # ---- run overview ----
    _section_run_overview(lines, run_summary)

    # ---- quality ----
    if isinstance(quality_metrics, dict) and quality_metrics:
        _section_quality(lines, quality_metrics)

    # ---- outcome summary ----
    if isinstance(outcome_summary, dict) and outcome_summary:
        _section_outcome_summary(lines, outcome_summary)

    # ---- diversity ----
    if isinstance(diversity_metrics, dict) and diversity_metrics:
        _section_diversity(lines, diversity_metrics)

    # ---- persona/product differentiation ----
    if isinstance(persona_metrics, dict) and persona_metrics:
        _section_persona(lines, persona_metrics)

    # ---- selection ----
    if isinstance(selection_metrics, dict) and selection_metrics:
        _section_selection(lines, selection_metrics)

    # ---- regression ----
    if isinstance(regression, dict) and regression:
        _section_regression(lines, regression, output_dir=run.output_dir)

    # ---- plots ----
    if isinstance(plots, dict) and plots:
        _section_plots(lines, plots, output_dir=run.output_dir)

    # ---- notes ----
    lines.append("## Notes")
    lines.append("")
    lines.append("- Detailed machine-readable artifacts are saved under `summary/`, `metrics/`, `plots/`, and `regression/`.")
    lines.append("- This report is intended as a lightweight overview; see JSON/CSV outputs for full data.")
    lines.append("")

    return "\n".join(lines)


# ======================================================================
# Section builders
# ======================================================================

def _section_run_overview(lines: list[str], summary: Dict[str, Any]) -> None:
    lines.append("## Run overview")
    lines.append("")
    lines.extend(_kv_table(summary, keys=[
        ("run_name", "Run name"),
        ("policy", "Policy"),
        ("schema_version", "Schema version"),
        ("seed", "Seed"),
        ("generated_at_utc", "Generated at (UTC)"),
        ("backend_name", "Backend"),
        ("backend_model", "Model"),
        ("outcomes_model_name", "Outcomes model"),
        ("outcomes_temperature", "Outcomes temperature"),
    ]))
    lines.append("")

    lines.extend(_kv_table(summary, keys=[
        ("n_events", "Events"),
        ("n_evaluation_rows", "Evaluation rows"),
        ("n_selection_rows", "Selection rows"),
        ("n_unique_panelists_observed", "Unique panelists"),
        ("n_unique_products_evaluated", "Unique products"),
        ("n_unique_periods_observed", "Periods"),
    ]))
    lines.append("")


def _section_quality(lines: list[str], metrics: Dict[str, Any]) -> None:
    lines.append("## Quality metrics")
    lines.append("")
    lines.extend(_kv_table(metrics, keys=[
        ("rows_with_any_outcome_rate", "Outcome coverage rate"),
        ("rows_with_any_trace_rate", "Trace coverage rate"),
        ("panelist_feature_coverage_rate", "Panelist feature coverage"),
        ("product_feature_coverage_rate", "Product feature coverage"),
        ("selection_link_rate", "Selection link rate"),
    ]))
    lines.append("")


def _section_outcome_summary(lines: list[str], summary: Dict[str, Any]) -> None:
    field_summaries = summary.get("outcome_field_summaries", {})
    if not isinstance(field_summaries, dict) or not field_summaries:
        return

    lines.append("## Outcome summary")
    lines.append("")

    rows: list[dict[str, Any]] = []
    for name, info in field_summaries.items():
        if not isinstance(info, dict):
            continue
        sub = info.get("summary", {})
        row: dict[str, Any] = {"field": name, "type": info.get("type")}
        row["n"] = info.get("n_observed")
        row["missing"] = info.get("n_missing")

        if isinstance(sub, dict):
            if "mean" in sub:
                row["mean"] = sub["mean"]
            if "min" in sub:
                row["min"] = sub["min"]
            if "max" in sub:
                row["max"] = sub["max"]
            if "n_unique" in sub:
                row["n_unique"] = sub["n_unique"]

        rows.append(row)

    if rows:
        cols = [c for c in ["field", "type", "n", "missing", "mean", "min", "max", "n_unique"]
                if any(c in r for r in rows)]
        lines.extend(_markdown_table(rows, cols))
        lines.append("")


def _section_diversity(lines: list[str], metrics: Dict[str, Any]) -> None:
    fields = metrics.get("fields", {})
    if not isinstance(fields, dict) or not fields:
        return

    lines.append("## Outcome diversity")
    lines.append("")
    lines.append("`norm_entropy` is relative to the declared support. `observed`/`declared` show how many distinct values appeared vs. how many the questionnaire allows.")
    lines.append("")

    rows: list[dict[str, Any]] = []
    for name, info in fields.items():
        if not isinstance(info, dict):
            continue
        rows.append({
            "field": name,
            "entropy": info.get("entropy"),
            "norm_entropy": info.get("normalized_entropy_full_support"),
            "observed": info.get("support_size_observed"),
            "declared": info.get("support_size_allowed"),
        })

    if rows:
        cols = ["field", "entropy", "norm_entropy", "observed", "declared"]
        lines.extend(_markdown_table(rows, cols))
        lines.append("")


def _section_persona(lines: list[str], metrics: Dict[str, Any]) -> None:
    lines.append("## Panelist/product differentiation")
    lines.append("")

    field = metrics.get("outcome_field")
    if field:
        lines.append(f"Outcome field: `{field}`")
        lines.append("")

    lines.extend(_kv_table(metrics, keys=[
        ("overall_variance", "Overall variance"),
        ("panelist_mean_variance", "Variance of panelist means"),
        ("product_mean_variance", "Variance of product means"),
        ("mean_within_product_panelist_variance", "Mean within-product panelist variance"),
        ("mean_within_panelist_product_variance", "Mean within-panelist product variance"),
        ("mean_pairwise_panelist_distance", "Mean pairwise panelist distance"),
        ("mean_pairwise_product_distance", "Mean pairwise product distance"),
    ]))
    lines.append("")


def _section_selection(lines: list[str], metrics: Dict[str, Any]) -> None:
    lines.append("## Selection behavior")
    lines.append("")
    lines.extend(_kv_table(metrics, keys=[
        ("n_selection_rows", "Selection events"),
        ("avg_choice_set_size", "Avg choice set size"),
        ("avg_requested_size", "Avg requested"),
        ("avg_executed_size", "Avg executed"),
        ("avg_dropped_size", "Avg dropped"),
        ("empty_request_rate", "Empty request rate"),
        ("empty_execution_rate", "Empty execution rate"),
        ("request_to_execution_ratio", "Request-to-execution ratio"),
        ("drop_rate_over_requested", "Drop rate"),
    ]))
    lines.append("")

    lines.extend(_kv_table(metrics, keys=[
        ("requested_product_entropy", "Requested entropy"),
        ("requested_product_normalized_entropy_full_support", "Requested norm entropy (full)"),
        ("executed_product_entropy", "Executed entropy"),
        ("executed_product_normalized_entropy_full_support", "Executed norm entropy (full)"),
        ("n_unique_requested_products", "Unique requested products"),
        ("n_unique_executed_products", "Unique executed products"),
    ]))
    lines.append("")


def _section_regression(
    lines: list[str],
    regression: Dict[str, Any],
    *,
    output_dir: str,
) -> None:
    lines.append("## Regression analysis")
    lines.append("")
    lines.append(f"Models fitted: {regression.get('n_models', 0)}")
    lines.append("")
    lines.append("> Caution: coefficient estimates can be useful diagnostically, but standard errors, p-values, and confidence intervals should be interpreted carefully in small synthetic runs with grouped observations.")
    lines.append("")
    lines.append("> Significance markers: `*` p < 0.10, `**` p < 0.05, `***` p < 0.01.")
    lines.append("")

    for item in regression.get("results", []):
        if not isinstance(item, dict):
            continue
        _render_regression_item(lines, item, output_dir=output_dir)


def _render_regression_item(
    lines: list[str],
    item: Dict[str, Any],
    *,
    output_dir: str,
) -> None:
    family = item.get("family", "?")
    design = item.get("design", "?")
    outcome_field = item.get("outcome_field", "?")

    lines.append(f"### {family} / {design} / {outcome_field}")
    lines.append("")

    result: Optional[RegressionResult] = item.get("result")
    summary = item.get("summary", {})

    # ---- skipped / failed ----
    if result is not None and isinstance(result.metadata, dict):
        skip_reason = result.metadata.get("skip_reason")
        fit_error = result.metadata.get("fit_error")

        if skip_reason:
            lines.append(f"**Skipped**: {skip_reason}")
            lines.append("")
            return

        if fit_error:
            lines.append(f"**Failed**: {fit_error}")
            lines.append("")
            return

    # ---- fit summary (table, not kv list) ----
    if isinstance(summary, dict) and summary:
        _render_fit_summary_table(lines, summary, family=family)

    # ---- coefficient table from in-memory result ----
    if result is not None:
        _render_coefficient_table(lines, result)
        _render_dropped_columns(lines, result)

    # ---- artifact paths ----
    paths = item.get("paths", {})
    if isinstance(paths, dict) and paths:
        lines.append("Artifacts:")
        for name, path in sorted(paths.items()):
            rel_path = os.path.relpath(path, output_dir)
            lines.append(f"- `{name}`: `{rel_path}`")
        lines.append("")


def _render_fit_summary_table(
    lines: list[str],
    summary: Dict[str, Any],
    *,
    family: str,
) -> None:
    """Render the fit metrics as a compact table, selecting keys by family."""
    common_keys = [
        ("n_obs", "N"),
        ("n_features", "Features"),
        ("covariance_type", "Covariance"),
        ("n_unique_panelist_clusters", "Panelist clusters"),
        ("n_unique_product_clusters", "Product clusters"),
    ]

    if family == "ols":
        metric_keys = [
            ("r2", "R2"),
            ("adj_r2", "Adj R2"),
            ("rmse", "RMSE"),
            ("mae", "MAE"),
            ("aic", "AIC"),
            ("bic", "BIC"),
        ]
    else:
        metric_keys = [
            ("pseudo_r2", "Pseudo R2"),
            ("accuracy", "Accuracy"),
            ("aic", "AIC"),
            ("bic", "BIC"),
            ("log_likelihood", "Log-lik"),
        ]

    lines.extend(_kv_table(summary, keys=common_keys + metric_keys))

    n_dropped = (
        (summary.get("n_dropped_constant_columns") or 0)
        + (summary.get("n_dropped_duplicate_columns") or 0)
        + (summary.get("n_dropped_rank_deficient_columns") or 0)
    )
    if n_dropped > 0:
        lines.append(f"Dropped columns: {n_dropped} (constant: {summary.get('n_dropped_constant_columns', 0)}, duplicate: {summary.get('n_dropped_duplicate_columns', 0)}, rank-deficient: {summary.get('n_dropped_rank_deficient_columns', 0)})")
    lines.append("")


def _render_coefficient_table(
    lines: list[str],
    result: RegressionResult,
    *,
    max_rows: int = 12,
) -> None:
    """Render the attribute coefficient table from the in-memory result."""
    df = filter_coefficient_table(
        result,
        include_fixed_effects=False,
        include_intercept=False,
        include_thresholds=False,
        attribute_only=True,
    )
    if df.empty:
        return

    df = df.head(max_rows)

    has_class_label = (
        "class_label" in df.columns and df["class_label"].notna().any()
    )

    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        est = _safe_float(r.get("estimate"))
        pval = r.get("p_value")
        row: dict[str, Any] = {"term": r.get("term", "")}
        if has_class_label:
            row["class"] = r.get("class_label", "")
        row.update({
            "estimate": _fmt_estimate(est, pval),
            "std_error": _fmt_float(r.get("std_error")),
            "p_value": _fmt_float(r.get("p_value")),
            "ci_low": _fmt_float(r.get("ci_low")),
            "ci_high": _fmt_float(r.get("ci_high")),
        })
        rows.append(row)

    if rows:
        cols = ["term"]
        if has_class_label:
            cols.append("class")
        cols.extend(["estimate", "std_error", "p_value", "ci_low", "ci_high"])

        lines.append("Attribute coefficients")
        lines.append("")
        lines.extend(_markdown_table(rows, cols))
        lines.append("")


def _render_dropped_columns(
    lines: list[str],
    result: RegressionResult,
    *,
    max_rows: int = 12,
) -> None:
    """Render the dropped columns table from the in-memory result."""
    df = dropped_columns_to_dataframe(result)
    if df.empty:
        return

    df = df.head(max_rows)

    rows = [{"column": r.get("column", ""), "reason": r.get("reason", "")}
            for _, r in df.iterrows()]

    if rows:
        lines.append("Dropped columns")
        lines.append("")
        lines.extend(_markdown_table(rows, ["column", "reason"]))
        lines.append("")


def _section_plots(
    lines: list[str],
    plots: Dict[str, Any],
    *,
    output_dir: str,
) -> None:
    lines.append("## Plots")
    lines.append("")

    # Report lives at <output_dir>/report/report.md;
    # plots live at <output_dir>/plots/*.png.
    report_dir = os.path.join(output_dir, "report")

    groups = _group_plots(plots)

    for family, label, description in _PLOT_FAMILIES:
        items = groups.get(family, [])
        if not items:
            continue

        lines.append(f"### {label}")
        lines.append("")
        if description:
            lines.append(description)
            lines.append("")

        _render_plot_grid(lines, items, report_dir=report_dir)

    # Ungrouped plots (future-proofing).
    ungrouped = groups.get("_other", [])
    if ungrouped:
        lines.append("### Other plots")
        lines.append("")
        _render_plot_grid(lines, ungrouped, report_dir=report_dir)


def _render_plot_grid(
    lines: list[str],
    items: list[tuple[str, str]],
    *,
    report_dir: str,
) -> None:
    """
    Render plot images in an HTML table grid.

    Layout: 2 per row if 4 or fewer images, 3 per row otherwise.
    """
    cols = 2 if len(items) <= 4 else 3

    lines.append("<table>")
    for i in range(0, len(items), cols):
        chunk = items[i : i + cols]
        lines.append("<tr>")
        for name, path in chunk:
            rel_path = os.path.relpath(path, report_dir)
            lines.append(
                f'<td><img src="{rel_path}" width="400"/>'
                f"<br><sub>{name}</sub></td>"
            )
        lines.append("</tr>")
    lines.append("</table>")
    lines.append("")


# (family_prefix, heading, description)
_PLOT_FAMILIES = [
    (
        "outcome_distribution",
        "Outcome distributions",
        "Empirical distribution of each declared outcome field across evaluation rows.",
    ),
    (
        "panelist",
        "Panelist summaries",
        "Per-panelist summary statistics for the selected outcome field.",
    ),
    (
        "product",
        "Product summaries",
        "Per-product summary statistics for the selected outcome field.",
    ),
    (
        "selection_concentration",
        "Selection concentration",
        "How selection mass is distributed across products in self-selection runs.",
    ),
]


def _group_plots(
    plots: Dict[str, Any],
) -> Dict[str, list[tuple[str, str]]]:
    """
    Group plot artifacts by family prefix.

    Returns a dict mapping family prefix to a sorted list of (name, path) tuples.
    Unmatched plots go under '_other'.
    """
    groups: Dict[str, list[tuple[str, str]]] = {}

    for name, path in sorted(plots.items()):
        matched = False
        for family, _, _ in _PLOT_FAMILIES:
            if name.startswith(family):
                groups.setdefault(family, []).append((name, path))
                matched = True
                break
        if not matched:
            groups.setdefault("_other", []).append((name, path))

    return groups


# ======================================================================
# Formatting helpers
# ======================================================================

def _kv_table(
    d: Dict[str, Any],
    *,
    keys: list[tuple[str, str]],
) -> list[str]:
    """
    Render selected keys from a dict as a two-column markdown table.

    Each entry in `keys` is (dict_key, display_label).
    Keys not present in the dict are silently skipped.
    """
    rows: list[dict[str, Any]] = []
    for dict_key, label in keys:
        if dict_key in d:
            rows.append({"": label, " ": _format_value(d[dict_key])})

    if not rows:
        return []

    return _markdown_table(rows, ["", " "])


def _markdown_table(rows: list[dict[str, Any]], cols: list[str]) -> list[str]:
    header = "| " + " | ".join(cols) + " |"
    rule = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = [
        "| " + " | ".join(_markdown_cell(row.get(col)) for col in cols) + " |"
        for row in rows
    ]
    return [header, rule] + body


def _markdown_cell(value: Any) -> str:
    text = _format_value(value) if not isinstance(value, str) else value
    return text.replace("\n", " ").replace("|", "\\|")


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _fmt_float(value: Any) -> str:
    f = _safe_float(value)
    if f is None:
        return ""
    return f"{f:.4f}"


def _fmt_estimate(estimate: Optional[float], p_value: Any) -> str:
    if estimate is None:
        return ""
    return f"{estimate:.4f}{_significance_stars(p_value)}"


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        import math
        f = float(value)
        if math.isnan(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _significance_stars(p_value: Any) -> str:
    f = _safe_float(p_value)
    if f is None:
        return ""
    if f < 0.01:
        return "***"
    if f < 0.05:
        return "**"
    if f < 0.10:
        return "*"
    return ""