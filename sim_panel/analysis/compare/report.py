from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


def build_cross_markdown_report(
    *,
    artifacts: Dict[str, Any],
    outcome_field: str,
) -> str:
    """
    Build the markdown report for cross-comparison mode.
    """
    flat_table = artifacts.get("condition_metrics", [])
    pivot_tables = artifacts.get("pivot_tables", {})
    js_matrix = artifacts.get("js_divergence_matrix", {})
    rmse_matrix = artifacts.get("pairwise_rmse_matrix", {})

    lines: List[str] = []
    lines.append("# Cross-condition comparison report")
    lines.append("")
    lines.append("Mode: `cross`")
    lines.append("")
    lines.append(f"Outcome field: `{outcome_field}`")
    lines.append("")

    lines.extend(
        _render_flat_table_section(
            title="## Per-condition metrics",
            rows=flat_table,
        )
    )

    for metric_name, pivot in pivot_tables.items():
        lines.extend(
            _render_pivot_section(
                title=f"## {metric_name} (model x strategy)",
                pivot=pivot,
            )
        )

    lines.extend(
        _render_matrix_section(
            title="## Jensen-Shannon divergence (distribution overlap)",
            matrix=js_matrix,
        )
    )

    lines.extend(
        _render_matrix_section(
            title="## Pairwise RMSE (over shared panelist-product pairs)",
            matrix=rmse_matrix,
        )
    )

    return "\n".join(lines)


def build_benchmark_markdown_report(
    *,
    artifacts: Dict[str, Any],
    outcome_field: str,
    reference_label: str,
) -> str:
    """
    Build the markdown report for benchmark mode.
    """
    flat_table = artifacts.get("condition_metrics", [])
    benchmark_summary = artifacts.get("benchmark_summary", [])
    diagnostics_topk = artifacts.get("benchmark_product_diagnostics_topk", [])
    pivot_tables = artifacts.get("pivot_tables", {})

    lines: List[str] = []
    lines.append("# Benchmark comparison report")
    lines.append("")
    lines.append("Mode: `benchmark`")
    lines.append("")
    lines.append(f"Outcome field: `{outcome_field}`")
    lines.append("")
    lines.append(f"Reference condition: `{reference_label}`")
    lines.append("")

    lines.extend(
        _render_flat_table_section(
            title="## Per-condition metrics",
            rows=flat_table,
        )
    )

    bar_chart_path = artifacts.get("benchmark_rating_bar_chart_path")

    lines.append("## Overall rating bar charts")
    lines.append("")

    if isinstance(bar_chart_path, str) and bar_chart_path:
        image_name = os.path.basename(bar_chart_path)
        lines.append(f"![Benchmark rating bar charts]({image_name})")
    else:
        lines.append("_No chart available._")

    lines.append("")

    lines.extend(
        _render_flat_table_section(
            title="## Benchmark summary",
            rows=benchmark_summary,
        )
    )

    for metric_name, pivot in pivot_tables.items():
        lines.extend(
            _render_pivot_section(
                title=f"## {metric_name} (model x strategy)",
                pivot=pivot,
            )
        )

    lines.extend(
        _render_flat_table_section(
            title="## Product diagnostics (best/worst K by EMD)",
            rows=diagnostics_topk,
        )
    )

    return "\n".join(lines)


def _fmt(v: Any) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


def _render_flat_table_section(
    *,
    title: str,
    rows: List[Dict[str, Any]],
) -> List[str]:
    lines: List[str] = [title, ""]

    if not rows:
        lines.append("_No rows available._")
        lines.append("")
        return lines

    cols = list(rows[0].keys())
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join("---" for _ in cols) + " |")

    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(col)) for col in cols) + " |")

    lines.append("")
    return lines


def _render_pivot_section(
    *,
    title: str,
    pivot: Dict[str, Dict[str, Any]],
) -> List[str]:
    lines: List[str] = [title, ""]

    if not pivot:
        lines.append("_No rows available._")
        lines.append("")
        return lines

    strategies = sorted({strategy for row in pivot.values() for strategy in row.keys()})
    lines.append("| model | " + " | ".join(strategies) + " |")
    lines.append("| --- | " + " | ".join("---" for _ in strategies) + " |")

    for model in sorted(pivot.keys()):
        vals = [_fmt(pivot[model].get(strategy)) for strategy in strategies]
        lines.append(f"| {model} | " + " | ".join(vals) + " |")

    lines.append("")
    return lines


def _render_matrix_section(
    *,
    title: str,
    matrix: Dict[str, Dict[str, Optional[float]]],
) -> List[str]:
    lines: List[str] = [title, ""]

    if not matrix:
        lines.append("_No rows available._")
        lines.append("")
        return lines

    labels = list(matrix.keys())
    lines.append("| | " + " | ".join(labels) + " |")
    lines.append("| --- | " + " | ".join("---" for _ in labels) + " |")

    for label in labels:
        vals = [_fmt(matrix[label].get(other)) for other in labels]
        lines.append(f"| {label} | " + " | ".join(vals) + " |")

    lines.append("")
    return lines