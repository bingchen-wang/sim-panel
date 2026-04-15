from __future__ import annotations

import pandas as pd
from collections import Counter
from typing import Any, Dict, List, Optional, Mapping

from sim_panel.analysis.metadata import (
    get_questionnaire_outcome_fields,
    get_questionnaire_trace_fields,
)

from sim_panel.analysis.types import RunAnalysis, ConditionMetrics


def build_run_summary(run: RunAnalysis) -> Dict[str, Any]:
    """
    Build a compact single-run summary.

    This is the top-level diagnostic record for one run.
    """
    selection_rows = run.selection_rows
    evaluation_rows = run.evaluation_rows

    event_type_counts = Counter(row.get("event_type") for row in run.events)
    policy_counts = Counter(row.get("policy") for row in run.events)

    unique_panelists = sorted(
        {
            row["panelist_id"]
            for row in run.events
            if isinstance(row.get("panelist_id"), str)
        }
    )
    unique_products = sorted(
        {
            row["product_id"]
            for row in evaluation_rows
            if isinstance(row.get("product_id"), str)
        }
    )
    unique_periods = sorted(
        {
            row["t"]
            for row in run.events
            if isinstance(row.get("t"), int)
        }
    )

    return {
        "run_name": run.metadata_flat.get("run_name"),
        "run_dir": run.run_dir,
        "policy": run.metadata_flat.get("policy"),
        "schema_version": run.metadata_flat.get("schema_version"),
        "seed": run.metadata_flat.get("seed"),
        "generated_at_utc": run.metadata_flat.get("generated_at_utc"),
        "backend_name": run.metadata_flat.get("backend_name"),
        "backend_model": run.metadata_flat.get("backend_model"),
        "outcomes_model_name": run.metadata_flat.get("outcomes_model_name"),
        "outcomes_temperature": run.metadata_flat.get("outcomes_temperature"),
        "n_events": len(run.events),
        "n_selection_rows": len(selection_rows),
        "n_evaluation_rows": len(evaluation_rows),
        "event_type_counts": dict(event_type_counts),
        "policy_counts": dict(policy_counts),
        "n_unique_panelists_observed": len(unique_panelists),
        "n_unique_products_evaluated": len(unique_products),
        "n_unique_periods_observed": len(unique_periods),
        "periods_observed": unique_periods,
        "metadata_n_rows": run.metadata_flat.get("n_rows"),
        "metadata_n_panelists": run.metadata_flat.get("n_panelists"),
        "metadata_n_products": run.metadata_flat.get("n_products"),
        "metadata_n_periods": run.metadata_flat.get("n_periods"),
        "personas_path": run.metadata_flat.get("personas_path"),
        "products_path": run.metadata_flat.get("products_path"),
        "config_path": run.metadata_flat.get("config_path"),
    }


def build_outcome_summary(run: RunAnalysis) -> Dict[str, Any]:
    """
    Summarize outcome fields observed in evaluation rows.

    Returns a dict with:
    - outcome_fields_declared
    - outcome_field_summaries
    """
    declared_fields = get_questionnaire_outcome_fields(run.metadata)
    field_names = list(declared_fields.keys())

    observed_values: Dict[str, List[Any]] = {name: [] for name in field_names}
    missing_counts: Dict[str, int] = {name: 0 for name in field_names}

    for row in run.evaluation_rows:
        outcomes = row.get("outcomes")
        if not isinstance(outcomes, dict):
            for name in field_names:
                missing_counts[name] += 1
            continue

        for name in field_names:
            if name in outcomes and outcomes[name] is not None:
                observed_values[name].append(outcomes[name])
            else:
                missing_counts[name] += 1

    summaries: Dict[str, Dict[str, Any]] = {}
    for name in field_names:
        spec = declared_fields.get(name, {})
        dtype = spec.get("type")
        values = observed_values[name]

        summaries[name] = {
            "type": dtype,
            "n_observed": len(values),
            "n_missing": missing_counts[name],
            "summary": summarize_values(values, dtype=dtype),
        }

    return {
        "outcome_fields_declared": field_names,
        "n_evaluation_rows": len(run.evaluation_rows),
        "outcome_field_summaries": summaries,
    }


def build_trace_summary(run: RunAnalysis) -> Dict[str, Any]:
    """
    Summarize trace fields from both selection and evaluation rows.

    For now this is lightweight:
    - declared trace fields
    - observed counts
    - missing counts
    - text length summaries for text-like traces
    """
    declared_fields = get_questionnaire_trace_fields(run.metadata)
    field_names = list(declared_fields.keys())

    observed_values: Dict[str, List[Any]] = {name: [] for name in field_names}
    missing_counts: Dict[str, int] = {name: 0 for name in field_names}

    trace_rows = [row for row in run.events if isinstance(row.get("traces"), dict)]

    for row in run.events:
        traces = row.get("traces")
        if not isinstance(traces, dict):
            for name in field_names:
                missing_counts[name] += 1
            continue

        for name in field_names:
            if name in traces and traces[name] is not None:
                observed_values[name].append(traces[name])
            else:
                missing_counts[name] += 1

    summaries: Dict[str, Dict[str, Any]] = {}
    for name in field_names:
        spec = declared_fields.get(name, {})
        dtype = spec.get("type")
        values = observed_values[name]

        summaries[name] = {
            "type": dtype,
            "n_observed": len(values),
            "n_missing": missing_counts[name],
            "summary": summarize_values(values, dtype=dtype),
        }

    return {
        "trace_fields_declared": field_names,
        "n_trace_rows_observed": len(trace_rows),
        "trace_field_summaries": summaries,
    }


def build_selection_summary(run: RunAnalysis) -> Dict[str, Any]:
    """
    Summarize selection behavior for runs with selection rows.

    Useful primarily for self_selection policy, but safe for any run.
    """
    rows = run.selection_rows
    n_rows = len(rows)

    if n_rows == 0:
        return {
            "n_selection_rows": 0,
            "avg_choice_set_size": None,
            "avg_requested_size": None,
            "avg_executed_size": None,
            "avg_dropped_size": None,
            "empty_request_rate": None,
            "empty_execution_rate": None,
            "top_requested_products": [],
            "top_executed_products": [],
        }

    choice_set_sizes: List[int] = []
    requested_sizes: List[int] = []
    executed_sizes: List[int] = []
    dropped_sizes: List[int] = []

    requested_counter: Counter[str] = Counter()
    executed_counter: Counter[str] = Counter()

    n_empty_request = 0
    n_empty_execution = 0

    for row in rows:
        choice_set = row.get("choice_set")
        selected = row.get("selected_product_ids")
        traces = row.get("traces") if isinstance(row.get("traces"), dict) else {}

        executed = traces.get("executed_product_ids", [])
        dropped = traces.get("dropped_product_ids", [])

        choice_size = len(choice_set) if isinstance(choice_set, list) else 0
        requested_size = len(selected) if isinstance(selected, list) else 0
        executed_size = len(executed) if isinstance(executed, list) else 0
        dropped_size = len(dropped) if isinstance(dropped, list) else 0

        choice_set_sizes.append(choice_size)
        requested_sizes.append(requested_size)
        executed_sizes.append(executed_size)
        dropped_sizes.append(dropped_size)

        if requested_size == 0:
            n_empty_request += 1
        if executed_size == 0:
            n_empty_execution += 1

        if isinstance(selected, list):
            requested_counter.update(pid for pid in selected if isinstance(pid, str))
        if isinstance(executed, list):
            executed_counter.update(pid for pid in executed if isinstance(pid, str))

    return {
        "n_selection_rows": n_rows,
        "avg_choice_set_size": safe_mean(choice_set_sizes),
        "avg_requested_size": safe_mean(requested_sizes),
        "avg_executed_size": safe_mean(executed_sizes),
        "avg_dropped_size": safe_mean(dropped_sizes),
        "empty_request_rate": n_empty_request / n_rows,
        "empty_execution_rate": n_empty_execution / n_rows,
        "top_requested_products": requested_counter.most_common(10),
        "top_executed_products": executed_counter.most_common(10),
    }


def summarize_values(values: List[Any], *, dtype: Optional[str]) -> Dict[str, Any]:
    """
    Summarize a list of scalar values based on questionnaire dtype.

    Supported rough families:
    - int / float -> numeric summary
    - categorical -> frequency summary
    - text -> text-length summary
    - fallback -> frequency summary on repr
    """
    if dtype in {"int", "float"}:
        numeric_values = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
        return summarize_numeric(numeric_values)

    if dtype == "categorical":
        cats = [v for v in values if isinstance(v, (str, int, float, bool))]
        return summarize_categorical(cats)

    if dtype == "text":
        texts = [v for v in values if isinstance(v, str)]
        return summarize_text(texts)

    scalar_values = [v for v in values if isinstance(v, (str, int, float, bool))]
    return summarize_categorical(scalar_values)


def summarize_numeric(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {
            "n": 0,
            "mean": None,
            "min": None,
            "max": None,
            "value_counts": {},
        }

    counts = Counter(values)
    return {
        "n": len(values),
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
        "value_counts": dict(sorted(counts.items(), key=lambda kv: kv[0])),
    }


def summarize_categorical(values: List[Any]) -> Dict[str, Any]:
    if not values:
        return {
            "n": 0,
            "n_unique": 0,
            "value_counts": {},
            "top_values": [],
        }

    counts = Counter(values)
    return {
        "n": len(values),
        "n_unique": len(counts),
        "value_counts": dict(counts),
        "top_values": counts.most_common(10),
    }


def summarize_text(values: List[str]) -> Dict[str, Any]:
    if not values:
        return {
            "n": 0,
            "avg_length_chars": None,
            "min_length_chars": None,
            "max_length_chars": None,
        }

    lengths = [len(v) for v in values]
    return {
        "n": len(values),
        "avg_length_chars": sum(lengths) / len(lengths),
        "min_length_chars": min(lengths),
        "max_length_chars": max(lengths),
    }


def safe_mean(values: List[int]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)

def build_evaluation_dataframe(run: RunAnalysis) -> pd.DataFrame:
    """
    Build a flat evaluation-level dataframe from run.evaluation_rows.

    Included blocks:
    - identifiers / context:
        _row_ix, event_id, panelist_id, product_id, selection_id, t, policy
    - outcomes:
        one column per outcome field under event["outcomes"]
    - flattened panelist features:
        panelist.<...>
    - flattened product features:
        product.<...>

    Excluded in v0:
    - traces
    - product_display
    - arbitrary free text fields
    """
    rows: List[Dict[str, Any]] = []

    for row_ix, row in enumerate(run.evaluation_rows):
        if not isinstance(row, Mapping):
            continue

        if row.get("event_type") != "evaluation":
            continue

        out: Dict[str, Any] = {
            "_row_ix": row_ix,
            "event_id": row.get("event_id"),
            "panelist_id": row.get("panelist_id"),
            "product_id": row.get("product_id"),
            "selection_id": row.get("selection_id"),
            "t": row.get("t"),
            "policy": row.get("policy"),
        }

        outcomes = row.get("outcomes")
        if isinstance(outcomes, Mapping):
            for k, v in outcomes.items():
                out[k] = v

        panelist_features = row.get("panelist_features")
        if isinstance(panelist_features, Mapping):
            out.update(_flatten_feature_mapping(panelist_features, prefix="panelist"))

        product_features = row.get("product_features")
        if isinstance(product_features, Mapping):
            out.update(_flatten_feature_mapping(product_features, prefix="product"))

        rows.append(out)

    if not rows:
        raise ValueError("RunAnalysis contains no usable evaluation rows.")

    return pd.DataFrame(rows)


def _flatten_feature_mapping(
    obj: Mapping[str, Any],
    *,
    prefix: str,
) -> Dict[str, Any]:
    """
    Flatten a nested feature mapping into dotted columns.

    Rules:
    - nested dicts are recursively flattened
    - scalar leaves are kept
    - lists are skipped in v0
    - column names are namespaced with the provided prefix
    """
    out: Dict[str, Any] = {}

    def _walk(value: Any, path: List[str]) -> None:
        if isinstance(value, Mapping):
            for k, v in value.items():
                _walk(v, path + [str(k)])
            return

        if isinstance(value, list):
            return

        col = ".".join([prefix] + path)
        out[col] = value

    for key, value in obj.items():
        _walk(value, [str(key)])

    return out

# ---------------------------------------------------------------------------
# Compare tables
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