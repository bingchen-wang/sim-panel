"""
Cross-condition comparison for multi-run experiments.

Loads evaluation rows from multiple run directories, computes per-condition
metrics, and builds models x strategies comparison tables.
"""
from __future__ import annotations

import json
import math
import os
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from sim_panel.analysis.metrics.utils import (
    extract_outcome_values,
    group_numeric_outcome_by_field,
    group_numeric_outcome_by_two_fields,
    safe_mean,
    safe_variance,
)
from sim_panel.io.jsonl import read_jsonl_dicts
from sim_panel.io.paths import ensure_dir


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConditionSpec:
    label: str
    model: str
    strategy: str
    run_dir: str


@dataclass(frozen=True)
class CompareConfig:
    output_dir: str
    outcome_field: str  # e.g. "rating"
    conditions: List[ConditionSpec]
    rating_scale: Optional[List[int]] = None  # e.g. [1..10]; inferred if None


def build_compare_config_from_dict(d: Mapping[str, Any]) -> CompareConfig:
    output_dir = d.get("output_dir")
    if not isinstance(output_dir, str) or not output_dir:
        raise ValueError("compare config requires 'output_dir'")

    outcome_field = str(d.get("outcome_field", "rating"))

    raw_conditions = d.get("conditions")
    if not isinstance(raw_conditions, list) or not raw_conditions:
        raise ValueError("compare config requires a non-empty 'conditions' list")

    conditions: List[ConditionSpec] = []
    for i, c in enumerate(raw_conditions):
        if not isinstance(c, Mapping):
            raise ValueError(f"conditions[{i}] must be a mapping")
        conditions.append(ConditionSpec(
            label=str(c.get("label", f"cond_{i}")),
            model=str(c.get("model", "")),
            strategy=str(c.get("strategy", "")),
            run_dir=str(c["run_dir"]),
        ))

    rating_scale = d.get("rating_scale")
    if isinstance(rating_scale, list):
        rating_scale = [int(x) for x in rating_scale]

    return CompareConfig(
        output_dir=output_dir,
        outcome_field=outcome_field,
        conditions=conditions,
        rating_scale=rating_scale,
    )


def build_compare_config_from_yaml(path: str) -> CompareConfig:
    from sim_panel.config.yaml_loader import load_yaml
    return build_compare_config_from_dict(load_yaml(path))


# ---------------------------------------------------------------------------
# Per-condition metrics
# ---------------------------------------------------------------------------

@dataclass
class ConditionMetrics:
    label: str
    model: str
    strategy: str

    n_evaluations: int = 0
    n_with_outcome: int = 0

    rating_mean: Optional[float] = None
    rating_std: Optional[float] = None
    rating_median: Optional[float] = None

    # Persona consistency: do different personas give different ratings?
    panelist_mean_variance: Optional[float] = None
    mean_pairwise_panelist_distance: Optional[float] = None

    # Product differentiation: do different products get different ratings?
    product_mean_variance: Optional[float] = None

    # Distribution shape
    rating_entropy: Optional[float] = None
    rating_normalized_entropy: Optional[float] = None

    # Raw distribution for cross-condition comparisons
    rating_distribution: Dict[Any, int] = field(default_factory=dict)

    # All numeric values for pairwise computations
    _values: List[float] = field(default_factory=list, repr=False)


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
    values = [float(v) for v in values_raw if isinstance(v, (int, float)) and not isinstance(v, bool)]
    m.n_with_outcome = len(values)
    m._values = values

    if not values:
        return m

    m.rating_mean = safe_mean(values)
    var = safe_variance(values)
    m.rating_std = math.sqrt(var) if var is not None else None
    m.rating_median = float(sorted(values)[len(values) // 2])

    # Distribution
    counts = dict(Counter(values_raw))
    m.rating_distribution = counts

    # Entropy
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

    # Persona consistency
    by_panelist = group_numeric_outcome_by_field(
        evaluation_rows, group_field="panelist_id", outcome_field=outcome_field,
    )
    panelist_means = [safe_mean(v) for v in by_panelist.values() if v]
    panelist_means_clean = [x for x in panelist_means if x is not None]
    m.panelist_mean_variance = safe_variance(panelist_means_clean)

    # Pairwise panelist distance
    by_product_then_panelist = group_numeric_outcome_by_two_fields(
        evaluation_rows, outer_field="product_id", inner_field="panelist_id",
        outcome_field=outcome_field,
    )
    m.mean_pairwise_panelist_distance = _mean_pairwise_distance(by_product_then_panelist)

    # Product differentiation
    by_product = group_numeric_outcome_by_field(
        evaluation_rows, group_field="product_id", outcome_field=outcome_field,
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


# ---------------------------------------------------------------------------
# Cross-condition metrics
# ---------------------------------------------------------------------------

def _jensen_shannon_divergence(
    dist_a: Dict[Any, int],
    dist_b: Dict[Any, int],
) -> Optional[float]:
    """Symmetric JS divergence (bits) between two count distributions."""
    all_keys = set(dist_a.keys()) | set(dist_b.keys())
    if not all_keys:
        return None

    total_a = sum(dist_a.values())
    total_b = sum(dist_b.values())
    if total_a == 0 or total_b == 0:
        return None

    # Convert to probabilities
    p = {k: dist_a.get(k, 0) / total_a for k in all_keys}
    q = {k: dist_b.get(k, 0) / total_b for k in all_keys}
    m = {k: (p[k] + q[k]) / 2 for k in all_keys}

    def _kl(a: Dict, b: Dict) -> float:
        return sum(
            a[k] * math.log(a[k] / b[k], 2)
            for k in all_keys
            if a[k] > 0 and b[k] > 0
        )

    return (_kl(p, m) + _kl(q, m)) / 2


def _pairwise_rmse(
    rows_a: List[Dict[str, Any]],
    rows_b: List[Dict[str, Any]],
    outcome_field: str,
) -> Optional[float]:
    """
    RMSE between two conditions computed over shared (panelist, product) pairs.
    Each pair's value is the mean outcome for that (panelist, product) in each condition.
    """
    def _build_profile(rows: List[Dict[str, Any]]) -> Dict[tuple, float]:
        from collections import defaultdict
        accum: Dict[tuple, List[float]] = defaultdict(list)
        for row in rows:
            outcomes = row.get("outcomes")
            if not isinstance(outcomes, dict):
                continue
            v = outcomes.get(outcome_field)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            key = (row.get("panelist_id"), row.get("product_id"))
            accum[key].append(float(v))
        return {k: sum(vs) / len(vs) for k, vs in accum.items() if vs}

    prof_a = _build_profile(rows_a)
    prof_b = _build_profile(rows_b)
    shared = set(prof_a.keys()) & set(prof_b.keys())

    if not shared:
        return None

    sse = sum((prof_a[k] - prof_b[k]) ** 2 for k in shared)
    return math.sqrt(sse / len(shared))


# ---------------------------------------------------------------------------
# Comparison tables
# ---------------------------------------------------------------------------

def _build_flat_table(metrics: List[ConditionMetrics]) -> List[Dict[str, Any]]:
    """One row per condition with all metrics."""
    rows: List[Dict[str, Any]] = []
    for m in metrics:
        rows.append({
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
        })
    return rows


def _build_pivot_table(
    metrics: List[ConditionMetrics],
    metric_name: str,
) -> Dict[str, Dict[str, Any]]:
    """Build model (rows) x strategy (columns) pivot for a single metric."""
    table: Dict[str, Dict[str, Any]] = {}
    for m in metrics:
        table.setdefault(m.model, {})[m.strategy] = getattr(m, metric_name, None)
    return table


def _build_js_divergence_matrix(
    metrics: List[ConditionMetrics],
) -> Dict[str, Dict[str, Optional[float]]]:
    """Pairwise Jensen-Shannon divergence between all conditions."""
    matrix: Dict[str, Dict[str, Optional[float]]] = {}
    for i, a in enumerate(metrics):
        row: Dict[str, Optional[float]] = {}
        for j, b in enumerate(metrics):
            if i == j:
                row[b.label] = 0.0
            else:
                row[b.label] = _jensen_shannon_divergence(
                    a.rating_distribution, b.rating_distribution,
                )
        matrix[a.label] = row
    return matrix


def _build_rmse_matrix(
    metrics: List[ConditionMetrics],
    eval_rows_by_label: Dict[str, List[Dict[str, Any]]],
    outcome_field: str,
) -> Dict[str, Dict[str, Optional[float]]]:
    """Pairwise RMSE between all conditions over shared (panelist, product) pairs."""
    matrix: Dict[str, Dict[str, Optional[float]]] = {}
    for a in metrics:
        row: Dict[str, Optional[float]] = {}
        for b in metrics:
            if a.label == b.label:
                row[b.label] = 0.0
            else:
                row[b.label] = _pairwise_rmse(
                    eval_rows_by_label[a.label],
                    eval_rows_by_label[b.label],
                    outcome_field,
                )
        matrix[a.label] = row
    return matrix


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def _fmt(v: Any) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


def _build_markdown_report(
    flat_table: List[Dict[str, Any]],
    pivot_tables: Dict[str, Dict[str, Dict[str, Any]]],
    js_matrix: Dict[str, Dict[str, Optional[float]]],
    rmse_matrix: Dict[str, Dict[str, Optional[float]]],
    outcome_field: str,
) -> str:
    lines: List[str] = []
    lines.append("# Cross-condition comparison report")
    lines.append("")

    # Flat table
    lines.append("## Per-condition metrics")
    lines.append("")
    if flat_table:
        cols = list(flat_table[0].keys())
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join("---" for _ in cols) + " |")
        for row in flat_table:
            lines.append("| " + " | ".join(_fmt(row.get(c)) for c in cols) + " |")
        lines.append("")

    # Pivot tables
    for metric_name, pivot in pivot_tables.items():
        lines.append(f"## {metric_name} (model x strategy)")
        lines.append("")
        strategies = sorted({s for row in pivot.values() for s in row.keys()})
        lines.append("| model | " + " | ".join(strategies) + " |")
        lines.append("| --- | " + " | ".join("---" for _ in strategies) + " |")
        for model in sorted(pivot.keys()):
            vals = [_fmt(pivot[model].get(s)) for s in strategies]
            lines.append(f"| {model} | " + " | ".join(vals) + " |")
        lines.append("")

    # JS divergence matrix
    lines.append("## Jensen-Shannon divergence (distribution overlap)")
    lines.append("")
    labels = list(js_matrix.keys())
    lines.append("| | " + " | ".join(labels) + " |")
    lines.append("| --- | " + " | ".join("---" for _ in labels) + " |")
    for label in labels:
        vals = [_fmt(js_matrix[label].get(l)) for l in labels]
        lines.append(f"| {label} | " + " | ".join(vals) + " |")
    lines.append("")

    # RMSE matrix
    lines.append("## Pairwise RMSE (over shared panelist-product pairs)")
    lines.append("")
    labels = list(rmse_matrix.keys())
    lines.append("| | " + " | ".join(labels) + " |")
    lines.append("| --- | " + " | ".join("---" for _ in labels) + " |")
    for label in labels:
        vals = [_fmt(rmse_matrix[label].get(l)) for l in labels]
        lines.append(f"| {label} | " + " | ".join(vals) + " |")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_comparison(config: CompareConfig) -> Dict[str, Any]:
    """
    Load all conditions, compute metrics, build tables, write artifacts.

    Returns the full artifact dict.
    """
    ensure_dir(config.output_dir)

    all_metrics: List[ConditionMetrics] = []
    eval_rows_by_label: Dict[str, List[Dict[str, Any]]] = {}

    for cond in config.conditions:
        events_path = os.path.join(cond.run_dir, "events.jsonl")
        if not os.path.isfile(events_path):
            raise FileNotFoundError(f"Events file not found for condition '{cond.label}': {events_path}")

        events = read_jsonl_dicts(events_path)
        eval_rows = [r for r in events if r.get("event_type") == "evaluation"]
        eval_rows_by_label[cond.label] = eval_rows

        m = _compute_condition_metrics(
            eval_rows,
            outcome_field=config.outcome_field,
            label=cond.label,
            model=cond.model,
            strategy=cond.strategy,
            rating_scale=config.rating_scale,
        )
        all_metrics.append(m)

    # Build tables
    flat_table = _build_flat_table(all_metrics)

    pivot_metrics = [
        "rating_mean", "rating_std",
        "panelist_mean_variance", "mean_pairwise_panelist_distance",
        "product_mean_variance", "rating_normalized_entropy",
    ]
    pivot_tables = {
        name: _build_pivot_table(all_metrics, name) for name in pivot_metrics
    }

    js_matrix = _build_js_divergence_matrix(all_metrics)
    rmse_matrix = _build_rmse_matrix(all_metrics, eval_rows_by_label, config.outcome_field)

    # Build markdown
    report = _build_markdown_report(
        flat_table, pivot_tables, js_matrix, rmse_matrix, config.outcome_field,
    )

    # Write artifacts
    artifacts = {
        "condition_metrics": flat_table,
        "pivot_tables": pivot_tables,
        "js_divergence_matrix": js_matrix,
        "pairwise_rmse_matrix": rmse_matrix,
    }

    _write_json(os.path.join(config.output_dir, "condition_metrics.json"), flat_table)
    _write_json(os.path.join(config.output_dir, "pivot_tables.json"), pivot_tables)
    _write_json(os.path.join(config.output_dir, "js_divergence_matrix.json"), js_matrix)
    _write_json(os.path.join(config.output_dir, "pairwise_rmse_matrix.json"), rmse_matrix)

    # CSV of flat table
    _write_csv(os.path.join(config.output_dir, "condition_metrics.csv"), flat_table)

    # Markdown report
    report_path = os.path.join(config.output_dir, "comparison_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return artifacts


def _write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, sort_keys=True, indent=2, default=str)
        f.write("\n")


def _write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    import csv
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
