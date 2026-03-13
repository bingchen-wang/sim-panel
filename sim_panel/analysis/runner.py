from __future__ import annotations

import json
import os
from typing import Any, Dict

from sim_panel.analysis.run import analyze_run
from sim_panel.analysis.types import AnalysisConfig, RunAnalysis
from sim_panel.io.paths import ensure_dir


def run_analysis(config: AnalysisConfig) -> RunAnalysis:
    """
    Top-level analysis entry point.

    Current responsibilities:
    - load and analyze a single run
    - write structured analysis artifacts to disk

    Artifact layout:
        <output_dir>/
          summary/
          metrics/
          plots/
          report/
    """
    run = analyze_run(config)
    _write_artifacts(
        run,
        write_json=config.export.json,
        write_csv=config.export.csv,
        write_markdown=config.export.markdown,
        overwrite=config.export.overwrite,
    )
    return run


def _write_artifacts(
    run: RunAnalysis,
    *,
    write_json: bool,
    write_csv: bool,
    write_markdown: bool,
    overwrite: bool,
) -> None:
    base_dir = ensure_dir(run.output_dir)
    summary_dir = ensure_dir(os.path.join(base_dir, "summary"))
    metrics_dir = ensure_dir(os.path.join(base_dir, "metrics"))
    plots_dir = ensure_dir(os.path.join(base_dir, "plots"))
    report_dir = ensure_dir(os.path.join(base_dir, "report"))

    for name, payload in run.artifacts.items():
        if name == "plots":
            if write_json:
                _write_json(
                    os.path.join(plots_dir, "plot_index.json"),
                    payload,
                    overwrite=overwrite,
                )
            continue

        target_dir = _artifact_target_dir(
            name,
            summary_dir=summary_dir,
            metrics_dir=metrics_dir,
            report_dir=report_dir,
        )

        if write_json:
            _write_json(
                os.path.join(target_dir, f"{name}.json"),
                payload,
                overwrite=overwrite,
            )

        if write_csv:
            rows = _payload_to_csv_rows(name, payload)
            if rows is not None:
                _write_csv(
                    os.path.join(target_dir, f"{name}.csv"),
                    rows,
                    overwrite=overwrite,
                )

    if write_markdown:
        report_md = build_markdown_report(run)
        _write_text(
            os.path.join(report_dir, "report.md"),
            report_md,
            overwrite=overwrite,
        )


def _artifact_target_dir(
    artifact_name: str,
    *,
    summary_dir: str,
    metrics_dir: str,
    report_dir: str,
) -> str:
    if artifact_name.endswith("_summary"):
        return summary_dir
    if artifact_name.endswith("_metrics"):
        return metrics_dir
    return report_dir


def _write_json(path: str, payload: Any, *, overwrite: bool) -> None:
    if not overwrite and os.path.exists(path):
        return
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _write_text(path: str, text: str, *, overwrite: bool) -> None:
    if not overwrite and os.path.exists(path):
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _write_csv(path: str, rows: list[dict[str, Any]], *, overwrite: bool) -> None:
    if not rows:
        return
    if not overwrite and os.path.exists(path):
        return

    import csv

    fieldnames = _collect_fieldnames(rows)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _csv_safe_value(v) for k, v in row.items()})


def _collect_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    seen: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.append(key)
    return seen


def _csv_safe_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def _payload_to_csv_rows(name: str, payload: Any) -> list[dict[str, Any]] | None:
    """
    Convert known artifact payloads into CSV-friendly row lists.

    v0 strategy:
    - dict[str, scalar] -> one-row table
    - specific nested summaries/metrics -> flattened row lists
    """
    if isinstance(payload, dict):
        if _is_scalar_dict(payload):
            return [payload]

        if name == "outcome_summary":
            return _flatten_outcome_summary(payload)

        if name == "trace_summary":
            return _flatten_trace_summary(payload)

        if name == "diversity_metrics":
            return _flatten_diversity_metrics(payload)

        if name == "quality_metrics":
            return _flatten_quality_metrics(payload)

        if name == "persona_metrics":
            return [payload]

        if name == "selection_metrics":
            return [payload]

        if name == "selection_summary":
            return [payload]

        if name == "run_summary":
            return [payload]

    return None


def _is_scalar_dict(d: Dict[str, Any]) -> bool:
    scalar_types = (str, int, float, bool, type(None))
    return all(isinstance(v, scalar_types) for v in d.values())


def _flatten_outcome_summary(payload: Dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    field_summaries = payload.get("outcome_field_summaries", {})
    n_eval = payload.get("n_evaluation_rows")

    if not isinstance(field_summaries, dict):
        return rows

    for field_name, info in field_summaries.items():
        if not isinstance(info, dict):
            continue
        row = {
            "field_name": field_name,
            "n_evaluation_rows": n_eval,
            "type": info.get("type"),
            "n_observed": info.get("n_observed"),
            "n_missing": info.get("n_missing"),
        }
        summary = info.get("summary")
        if isinstance(summary, dict):
            for k, v in summary.items():
                row[f"summary__{k}"] = v
        rows.append(row)

    return rows


def _flatten_trace_summary(payload: Dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    field_summaries = payload.get("trace_field_summaries", {})
    n_trace_rows = payload.get("n_trace_rows_observed")

    if not isinstance(field_summaries, dict):
        return rows

    for field_name, info in field_summaries.items():
        if not isinstance(info, dict):
            continue
        row = {
            "field_name": field_name,
            "n_trace_rows_observed": n_trace_rows,
            "type": info.get("type"),
            "n_observed": info.get("n_observed"),
            "n_missing": info.get("n_missing"),
        }
        summary = info.get("summary")
        if isinstance(summary, dict):
            for k, v in summary.items():
                row[f"summary__{k}"] = v
        rows.append(row)

    return rows


def _flatten_diversity_metrics(payload: Dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fields = payload.get("fields", {})
    n_eval = payload.get("n_evaluation_rows")

    if not isinstance(fields, dict):
        return rows

    for field_name, info in fields.items():
        if not isinstance(info, dict):
            continue
        row = {
            "field_name": field_name,
            "n_evaluation_rows": n_eval,
        }
        for k, v in info.items():
            row[k] = v
        rows.append(row)

    return rows


def _flatten_quality_metrics(payload: Dict[str, Any]) -> list[dict[str, Any]]:
    base: dict[str, Any] = {}
    outcome_missing = payload.get("outcome_field_missing_rates", {})
    trace_missing = payload.get("trace_field_missing_rates", {})

    for k, v in payload.items():
        if k not in {"outcome_field_missing_rates", "trace_field_missing_rates"}:
            base[k] = v

    if isinstance(outcome_missing, dict):
        for field_name, rate in outcome_missing.items():
            base[f"outcome_missing_rate__{field_name}"] = rate

    if isinstance(trace_missing, dict):
        for field_name, rate in trace_missing.items():
            base[f"trace_missing_rate__{field_name}"] = rate

    return [base]


def build_markdown_report(run: RunAnalysis) -> str:
    """
    Build a minimal markdown report for a single run.

    v0 goal:
    - compact human-readable overview
    - point the reader to JSON/CSV/plot artifacts
    """
    lines: list[str] = []

    run_summary = run.artifacts.get("run_summary", {})
    quality_metrics = run.artifacts.get("quality_metrics", {})
    persona_metrics = run.artifacts.get("persona_metrics", {})
    selection_metrics = run.artifacts.get("selection_metrics", {})
    plots = run.artifacts.get("plots", {})

    lines.append(f"# Analysis report: {run_summary.get('run_name', 'run')}")
    lines.append("")
    lines.append("## Run overview")
    lines.append("")
    lines.extend(_kv_lines(run_summary, keys=[
        "run_name",
        "run_dir",
        "policy",
        "schema_version",
        "seed",
        "generated_at_utc",
        "backend_name",
        "backend_model",
        "outcomes_model_name",
        "outcomes_temperature",
        "n_events",
        "n_selection_rows",
        "n_evaluation_rows",
        "n_unique_panelists_observed",
        "n_unique_products_evaluated",
        "n_unique_periods_observed",
        "personas_path",
        "products_path",
        "config_path",
    ]))
    lines.append("")

    if isinstance(quality_metrics, dict) and quality_metrics:
        lines.append("## Quality metrics")
        lines.append("")
        lines.extend(_kv_lines(quality_metrics, keys=[
            "n_events",
            "n_selection_rows",
            "n_evaluation_rows",
            "rows_with_any_outcome_rate",
            "rows_with_any_trace_rate",
            "panelist_feature_coverage_rate",
            "product_feature_coverage_rate",
            "selection_link_rate",
        ]))
        lines.append("")

    if isinstance(persona_metrics, dict) and persona_metrics:
        lines.append("## Panelist/product differentiation")
        lines.append("")
        lines.extend(_kv_lines(persona_metrics, keys=[
            "outcome_field",
            "supported",
            "n_observed",
            "overall_variance",
            "n_panelists_observed",
            "n_products_observed",
            "panelist_mean_variance",
            "product_mean_variance",
            "mean_within_product_panelist_variance",
            "mean_within_panelist_product_variance",
            "mean_pairwise_panelist_distance",
            "mean_pairwise_product_distance",
        ]))
        lines.append("")

    if isinstance(selection_metrics, dict) and selection_metrics:
        lines.append("## Selection behavior")
        lines.append("")
        lines.extend(_kv_lines(selection_metrics, keys=[
            "n_selection_rows",
            "support_size_allowed",
            "avg_choice_set_size",
            "avg_requested_size",
            "avg_executed_size",
            "avg_dropped_size",
            "empty_request_rate",
            "empty_execution_rate",
            "request_to_execution_ratio",
            "drop_rate_over_requested",
            "requested_product_entropy",
            "requested_product_normalized_entropy_full_support",
            "requested_product_normalized_entropy_observed_support",
            "executed_product_entropy",
            "executed_product_normalized_entropy_full_support",
            "executed_product_normalized_entropy_observed_support",
            "n_unique_requested_products",
            "n_unique_executed_products",
        ]))
        lines.append("")

    if isinstance(plots, dict) and plots:
        lines.append("## Plot artifacts")
        lines.append("")
        for name, path in sorted(plots.items()):
            rel_path = os.path.relpath(path, run.output_dir)
            lines.append(f"- `{name}`: `{rel_path}`")
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- Detailed machine-readable artifacts are saved under `summary/`, `metrics/`, and `plots/`.")
    lines.append("- This report is intentionally lightweight and is meant to complement, not replace, the JSON/CSV outputs.")
    lines.append("")

    return "\n".join(lines)


def _kv_lines(d: Dict[str, Any], *, keys: list[str]) -> list[str]:
    lines: list[str] = []
    for key in keys:
        if key in d:
            lines.append(f"- **{key}**: `{d[key]}`")
    return lines