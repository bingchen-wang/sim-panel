from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

import pandas as pd

from sim_panel.analysis.regression.types import CoefficientStat, RegressionResult


def regression_result_to_summary_row(result: RegressionResult) -> Dict[str, Any]:
    """
    Flatten a RegressionResult into a compact one-row summary suitable for
    dataframe aggregation or JSON export.
    """
    row: Dict[str, Any] = {
        "family": result.family,
        "design": result.design,
        "outcome_field": result.outcome_field,
        "n_obs": result.n_obs,
        "n_features": result.n_features,
        "covariance_type": result.metadata.get("covariance_type"),
        "n_unique_panelist_clusters": _count_unique(result.metadata.get("panelist_ids")),
        "n_unique_product_clusters": _count_unique(result.metadata.get("product_ids")),
        "n_dropped_constant_columns": len(result.metadata.get("dropped_constant_columns", []) or []),
        "n_dropped_duplicate_columns": len(result.metadata.get("dropped_duplicate_columns", []) or []),
        "n_dropped_rank_deficient_columns": len(result.metadata.get("dropped_rank_deficient_columns", []) or []),
    }
    row.update(result.metrics)
    return row


def coefficient_table_to_dataframe(result: RegressionResult) -> pd.DataFrame:
    """
    Convert coefficient_table into a dataframe.

    Returns an empty dataframe with stable columns if no coefficient table is present.
    """
    if not result.coefficient_table:
        return pd.DataFrame(
            columns=[
                "term",
                "estimate",
                "std_error",
                "statistic",
                "p_value",
                "ci_low",
                "ci_high",
                "class_label",
                "param_type",
            ]
        )

    return pd.DataFrame([asdict(row) for row in result.coefficient_table])


def filter_coefficient_table(
    result: RegressionResult,
    *,
    include_fixed_effects: bool = True,
    include_intercept: bool = True,
    include_thresholds: bool = True,
    attribute_only: bool = False,
) -> pd.DataFrame:
    """
    Build a clean coefficient table for inspection/export.

    Heuristics:
    - panelist_id_* and product_id_* dummy terms are treated as FE terms
    - const is treated as intercept
    - ordered-model slash terms are treated as thresholds if param_type is absent
    """
    df = coefficient_table_to_dataframe(result)
    if df.empty:
        return df

    term_series = df["term"].astype(str)

    is_intercept = term_series.eq("const") | df["param_type"].eq("intercept")
    is_threshold = df["param_type"].eq("threshold") | term_series.str.contains("/", regex=False)
    is_fe = (
        term_series.str.startswith("panelist_id_")
        | term_series.str.startswith("product_id_")
        | term_series.eq("panelist_id")
        | term_series.eq("product_id")
    )
    is_attribute = ~is_intercept & ~is_threshold & ~is_fe

    keep = pd.Series(True, index=df.index)

    if not include_fixed_effects:
        keep &= ~is_fe
    if not include_intercept:
        keep &= ~is_intercept
    if not include_thresholds:
        keep &= ~is_threshold
    if attribute_only:
        keep &= is_attribute

    out = df.loc[keep].copy()

    sort_cols: List[str] = []
    if "class_label" in out.columns and out["class_label"].notna().any():
        sort_cols.append("class_label")
    if "p_value" in out.columns:
        sort_cols.append("p_value")

    if sort_cols:
        out = out.sort_values(sort_cols, kind="stable")
    else:
        out = out.sort_values("term", kind="stable")

    return out.reset_index(drop=True)


def top_attribute_coefficients(
    result: RegressionResult,
    *,
    n: int = 20,
    by: str = "abs_estimate",
) -> pd.DataFrame:
    """
    Return the top attribute coefficients after excluding FE, intercepts, and thresholds.
    """
    df = filter_coefficient_table(
        result,
        include_fixed_effects=False,
        include_intercept=False,
        include_thresholds=False,
        attribute_only=True,
    )
    if df.empty:
        return df

    if by == "abs_estimate":
        df = df.assign(abs_estimate=df["estimate"].abs()).sort_values(
            "abs_estimate", ascending=False, kind="stable"
        )
    elif by == "p_value":
        if "p_value" not in df.columns:
            return df.head(n)
        df = df.sort_values("p_value", ascending=True, kind="stable")
    else:
        raise ValueError("by must be one of {'abs_estimate', 'p_value'}.")

    return df.head(n).reset_index(drop=True)


def regression_metadata_to_row(result: RegressionResult) -> Dict[str, Any]:
    """
    Flatten metadata that is especially useful for diagnostics/export.
    """
    return {
        "family": result.family,
        "design": result.design,
        "outcome_field": result.outcome_field,
        "covariance_type": result.metadata.get("covariance_type"),
        "model_class": result.metadata.get("model_class"),
        "converged": result.metadata.get("converged"),
        "n_unique_panelist_clusters": _count_unique(result.metadata.get("panelist_ids")),
        "n_unique_product_clusters": _count_unique(result.metadata.get("product_ids")),
        "dropped_constant_columns": result.metadata.get("dropped_constant_columns", []),
        "dropped_duplicate_columns": result.metadata.get("dropped_duplicate_columns", []),
        "dropped_rank_deficient_columns": result.metadata.get("dropped_rank_deficient_columns", []),
    }


def dropped_columns_to_dataframe(result: RegressionResult) -> pd.DataFrame:
    """
    Return a tidy dataframe of dropped columns and their reason.
    """
    rows: List[Dict[str, Any]] = []

    for col in result.metadata.get("dropped_constant_columns", []) or []:
        rows.append({"column": col, "reason": "constant"})

    for col in result.metadata.get("dropped_duplicate_columns", []) or []:
        rows.append({"column": col, "reason": "duplicate"})

    for col in result.metadata.get("dropped_rank_deficient_columns", []) or []:
        rows.append({"column": col, "reason": "rank_deficient"})

    if not rows:
        return pd.DataFrame(columns=["column", "reason"])

    return pd.DataFrame(rows)


def _count_unique(values: Any) -> Optional[int]:
    if not isinstance(values, list) or len(values) == 0:
        return None
    return len(set(values))