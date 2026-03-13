from __future__ import annotations

from typing import Any, Dict

from sim_panel.analysis.metrics.utils import (
    entropy_from_counts,
    extract_outcome_values,
    get_declared_outcome_fields,
    normalized_entropy_full_support,
    normalized_entropy_observed_support,
    safe_mean,
    safe_variance,
    support_size,
    value_counts,
)
from sim_panel.analysis.types import RunAnalysis


def compute_diversity_metrics(run: RunAnalysis) -> Dict[str, Any]:
    """
    Compute field-level diversity metrics for declared outcome fields.
    """
    declared = get_declared_outcome_fields(run.metadata)

    result: Dict[str, Any] = {
        "n_evaluation_rows": len(run.evaluation_rows),
        "fields": {},
    }

    for field_name, spec in declared.items():
        dtype = spec.get("type")
        values = extract_outcome_values(run.evaluation_rows, field_name)
        counts = value_counts(values)

        choices = spec.get("choices")
        n_support_allowed = len(choices) if isinstance(choices, list) else None

        field_metrics: Dict[str, Any] = {
            "type": dtype,
            "n_observed": len(values),
            "support_size_observed": support_size(values),
            "support_size_allowed": n_support_allowed,
            "entropy": entropy_from_counts(counts),
            "normalized_entropy_full_support": (
                normalized_entropy_full_support(counts, n_support=n_support_allowed)
                if isinstance(n_support_allowed, int)
                else None
            ),
            "normalized_entropy_observed_support": normalized_entropy_observed_support(counts),
            "value_counts": counts,
        }

        if dtype in {"int", "float"}:
            numeric_values = [
                float(v)
                for v in values
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            field_metrics.update(
                {
                    "mean": safe_mean(numeric_values),
                    "variance": safe_variance(numeric_values),
                }
            )

        result["fields"][field_name] = field_metrics

    return result