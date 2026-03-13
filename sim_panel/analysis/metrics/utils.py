from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional


def safe_mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def safe_variance(values: List[float]) -> Optional[float]:
    if len(values) < 2:
        return None
    mu = sum(values) / len(values)
    return sum((x - mu) ** 2 for x in values) / len(values)


def support_size(values: Iterable[Any]) -> int:
    return len(set(values))


def entropy_from_counts(counts: Mapping[Any, int]) -> Optional[float]:
    total = sum(counts.values())
    if total <= 0:
        return None

    h = 0.0
    for n in counts.values():
        if n <= 0:
            continue
        p = n / total
        h -= p * math.log(p, 2)
    return h


def normalized_entropy_full_support(
    counts: Mapping[Any, int],
    *,
    n_support: int,
) -> Optional[float]:
    """
    Entropy normalized by the full allowed support size.

    Example:
    - rating choices declared as [1,2,3,4,5] => n_support = 5
    """
    h = entropy_from_counts(counts)
    if h is None or n_support <= 1:
        return None
    return h / math.log(n_support, 2)


def normalized_entropy_observed_support(
    counts: Mapping[Any, int],
) -> Optional[float]:
    """
    Entropy normalized by the number of observed positive-count categories.
    """
    h = entropy_from_counts(counts)
    k_observed = len([n for n in counts.values() if n > 0])
    if h is None or k_observed <= 1:
        return None
    return h / math.log(k_observed, 2)


def value_counts(values: Iterable[Any]) -> Dict[Any, int]:
    return dict(Counter(values))


def get_declared_outcome_fields(metadata: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    cfg = metadata.get("config_snapshot") or {}
    questionnaire = cfg.get("questionnaire") or {}
    outcomes = questionnaire.get("outcomes") or {}
    fields = outcomes.get("fields") or {}
    return fields if isinstance(fields, dict) else {}


def get_declared_trace_fields(metadata: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    cfg = metadata.get("config_snapshot") or {}
    questionnaire = cfg.get("questionnaire") or {}
    traces = questionnaire.get("traces") or {}
    fields = traces.get("fields") or {}
    return fields if isinstance(fields, dict) else {}


def extract_outcome_values(
    evaluation_rows: List[Dict[str, Any]],
    field_name: str,
) -> List[Any]:
    values: List[Any] = []
    for row in evaluation_rows:
        outcomes = row.get("outcomes")
        if isinstance(outcomes, dict) and field_name in outcomes and outcomes[field_name] is not None:
            values.append(outcomes[field_name])
    return values


def extract_trace_values(
    rows: List[Dict[str, Any]],
    field_name: str,
) -> List[Any]:
    values: List[Any] = []
    for row in rows:
        traces = row.get("traces")
        if isinstance(traces, dict) and field_name in traces and traces[field_name] is not None:
            values.append(traces[field_name])
    return values


def group_numeric_outcome_by_field(
    evaluation_rows: List[Dict[str, Any]],
    *,
    group_field: str,
    outcome_field: str,
) -> Dict[Any, List[float]]:
    grouped: Dict[Any, List[float]] = defaultdict(list)

    for row in evaluation_rows:
        group_value = row.get(group_field)
        outcomes = row.get("outcomes")
        if not isinstance(outcomes, dict):
            continue
        value = outcomes.get(outcome_field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            grouped[group_value].append(float(value))

    return dict(grouped)


def group_numeric_outcome_by_two_fields(
    evaluation_rows: List[Dict[str, Any]],
    *,
    outer_field: str,
    inner_field: str,
    outcome_field: str,
) -> Dict[Any, Dict[Any, List[float]]]:
    grouped: Dict[Any, Dict[Any, List[float]]] = defaultdict(lambda: defaultdict(list))

    for row in evaluation_rows:
        outer_value = row.get(outer_field)
        inner_value = row.get(inner_field)
        outcomes = row.get("outcomes")
        if not isinstance(outcomes, dict):
            continue
        value = outcomes.get(outcome_field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            grouped[outer_value][inner_value].append(float(value))

    return {k: dict(v) for k, v in grouped.items()}