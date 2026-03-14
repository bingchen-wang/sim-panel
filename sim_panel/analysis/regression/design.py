from __future__ import annotations

from typing import List

from sim_panel.analysis.regression.types import DesignMatrix
from sim_panel.analysis.tables import build_evaluation_dataframe
from sim_panel.analysis.types import RunAnalysis


SUPPORTED_DESIGNS = {
    "panelist_features",
    "product_features",
    "panelist_plus_product_features",
    "panelist_id_fe",
    "product_id_fe",
    "two_way_fe",
    "features_plus_two_way_fe",
}


def build_design_matrix(
    *,
    run: RunAnalysis,
    design: str,
    outcome_field: str,
) -> DesignMatrix:
    """
    Build a regression design matrix from RunAnalysis.evaluation_rows.
    """
    if design not in SUPPORTED_DESIGNS:
        raise ValueError(
            f"Unsupported regression design '{design}'. "
            f"Supported designs: {sorted(SUPPORTED_DESIGNS)}."
        )

    df = build_evaluation_dataframe(run)

    if outcome_field not in df.columns:
        raise ValueError(
            f"Outcome field '{outcome_field}' not found in evaluation dataframe."
        )

    X = _select_design_columns(df, design=design)
    y = df[outcome_field].copy()
    row_ids = df["_row_ix"].astype(int).tolist()

    metadata = {
        "design": design,
        "outcome_field": outcome_field,
        "n_rows_raw": int(len(df)),
        "n_features_raw": int(X.shape[1]),
        "panelist_ids": df["panelist_id"].tolist() if "panelist_id" in df.columns else None,
        "product_ids": df["product_id"].tolist() if "product_id" in df.columns else None,
    }

    return DesignMatrix(
        X=X,
        y=y,
        feature_names=list(X.columns),
        row_ids=row_ids,
        metadata=metadata,
    )


def _select_design_columns(df, *, design: str):
    panelist_feature_cols = sorted(
        c for c in df.columns if c.startswith("panelist.")
    )
    product_feature_cols = sorted(
        c for c in df.columns if c.startswith("product.")
    )
    feature_cols = panelist_feature_cols + product_feature_cols

    if design == "panelist_features":
        cols: List[str] = panelist_feature_cols
    elif design == "product_features":
        cols = product_feature_cols
    elif design == "panelist_plus_product_features":
        cols = feature_cols
    elif design == "panelist_id_fe":
        cols = ["panelist_id"]
    elif design == "product_id_fe":
        cols = ["product_id"]
    elif design == "two_way_fe":
        cols = ["panelist_id", "product_id"]
    elif design == "features_plus_two_way_fe":
        # Put FE identifiers first so rank-based dropping keeps FE first.
        cols = ["panelist_id", "product_id"] + feature_cols
    else:
        raise ValueError(f"Unsupported design '{design}'.")

    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"Design '{design}' requested missing columns: {missing}"
        )

    if not cols:
        raise ValueError(
            f"Design '{design}' produced no feature columns. "
            "Check whether the run contains the required attributes."
        )

    return df.loc[:, cols].copy()