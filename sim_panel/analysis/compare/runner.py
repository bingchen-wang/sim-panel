from __future__ import annotations

import csv
import json
import os
from typing import Any, Dict, List, Tuple

from sim_panel.analysis.compare.benchmark import build_benchmark_comparison_artifacts
from sim_panel.analysis.compare.cross import build_cross_comparison_artifacts
from sim_panel.analysis.compare.metrics import _compute_condition_metrics
from sim_panel.analysis.compare.plot import save_benchmark_rating_bar_charts
from sim_panel.analysis.compare.report import (
    build_cross_markdown_report,
    build_benchmark_markdown_report,
)
from sim_panel.analysis.compare.resolve import resolve_compare_mode
from sim_panel.analysis.compare.types import CompareConfig, ConditionMetrics
from sim_panel.io.jsonl import read_jsonl_dicts
from sim_panel.io.paths import ensure_dir


def run_comparison(config: CompareConfig) -> Dict[str, Any]:
    """
    Load all conditions, compute shared per-condition metrics, dispatch to the 
    appropriate comparison mode, write artifacts, and return the artifact dict.

    Returns the full artifact dict.
    """
    ensure_dir(config.output_dir)

    mode = resolve_compare_mode(config.conditions)
    all_metrics, eval_rows_by_label = _load_condition_data(config)

    if mode.kind == "cross":
        artifacts = build_cross_comparison_artifacts(
            config=config,
            metrics=all_metrics,
            eval_rows_by_label=eval_rows_by_label,
        )
        report = build_cross_markdown_report(
            artifacts=artifacts,
            outcome_field=config.outcome_field,
        )
    elif mode.kind == "benchmark":
        if mode.reference_label is None:
            raise ValueError("benchmark mode requires a reference_label")

        artifacts = build_benchmark_comparison_artifacts(
            config=config,
            metrics=all_metrics,
            eval_rows_by_label=eval_rows_by_label,
            reference_label=mode.reference_label,
        )
        bar_chart_path = save_benchmark_rating_bar_charts(
            eval_rows_by_label=eval_rows_by_label,
            conditions=config.conditions,
            outcome_field=config.outcome_field,
            reference_label=mode.reference_label,
            output_dir=config.output_dir,
        )
        artifacts["benchmark_rating_bar_chart_path"] = bar_chart_path
        report = build_benchmark_markdown_report(
            artifacts=artifacts,
            outcome_field=config.outcome_field,
            reference_label=mode.reference_label,
        )
    else:
        raise ValueError(f"Unsupported compare mode: {mode.kind!r}")

    _write_artifacts(config.output_dir, artifacts, report)
    return artifacts


def _load_condition_data(
    config: CompareConfig,
) -> Tuple[List[ConditionMetrics], Dict[str, List[Dict[str, Any]]]]:
    """
    Load evaluation rows for each condition and compute shared per-condition
    metrics.

    Returns:
        (
            all_metrics,
            eval_rows_by_label,
        )
    """
    all_metrics: List[ConditionMetrics] = []
    eval_rows_by_label: Dict[str, List[Dict[str, Any]]] = {}

    for cond in config.conditions:
        events_path = os.path.join(cond.run_dir, cond.events_filename)
        if not os.path.isfile(events_path):
            raise FileNotFoundError(
                f"Events file not found for condition '{cond.label}': {events_path}"
            )

        events = read_jsonl_dicts(events_path)
        eval_rows = [row for row in events if row.get("event_type") == "evaluation"]
        eval_rows_by_label[cond.label] = eval_rows

        metrics = _compute_condition_metrics(
            eval_rows,
            outcome_field=config.outcome_field,
            label=cond.label,
            model=cond.model,
            strategy=cond.strategy,
            rating_scale=config.rating_scale,
        )
        all_metrics.append(metrics)

    return all_metrics, eval_rows_by_label


def _write_artifacts(
    output_dir: str,
    artifacts: Dict[str, Any],
    report: str,
) -> None:
    """
    Write compare artifacts to disk.

    Conventions:
    - dict payloads -> JSON
    - list payloads -> JSON
    - list[dict] payloads -> JSON + CSV
    - report -> comparison_report.md
    """
    for name, payload in artifacts.items():
        if name in {"mode", "benchmark_rating_bar_chart_path"}:
            continue

        json_path = os.path.join(output_dir, f"{name}.json")
        _write_json(json_path, payload)

        if _is_list_of_dicts(payload):
            csv_path = os.path.join(output_dir, f"{name}.csv")
            _write_csv(csv_path, payload)

    report_path = os.path.join(output_dir, "comparison_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)


def _is_list_of_dicts(payload: Any) -> bool:
    return (
        isinstance(payload, list)
        and bool(payload)
        and all(isinstance(item, dict) for item in payload)
    )


def _write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            payload,
            f,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
        f.write("\n")


def _write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    fieldnames: List[str] = []
    for row in rows:
        for k in row:
            if k not in fieldnames:
                fieldnames.append(k)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _csv_val(v) for k, v in row.items()})


def _csv_val(v: Any) -> Any:
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return v