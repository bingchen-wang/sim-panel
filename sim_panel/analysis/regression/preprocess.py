from __future__ import annotations

from typing import Any, List

import numpy as np
import pandas as pd
import statsmodels.api as sm

from sim_panel.analysis.regression.types import DesignMatrix, OutcomeSpec, RegressionOptions


def preprocess_design_matrix(
    *,
    design_matrix: DesignMatrix,
    outcome: OutcomeSpec,
    options: RegressionOptions,
) -> DesignMatrix:
    """
    Apply shared preprocessing before model-family-specific fitting.

    Steps:
    - drop rows with missing target / regressors if requested
    - coerce target according to outcome semantics
    - encode regressors into numeric columns with reference-category coding
    - optionally standardize numeric regressors
    - optionally add an intercept column
    - drop constant / duplicate / rank-deficient columns
    - keep cluster group labels aligned with retained rows
    """
    X = _as_dataframe(design_matrix.X).copy()
    y = _as_series(design_matrix.y).copy()
    row_ids = list(design_matrix.row_ids)
    metadata = dict(design_matrix.metadata)

    panelist_ids = metadata.get("panelist_ids")
    product_ids = metadata.get("product_ids")

    if options.drop_missing:
        keep_mask = ~(X.isna().any(axis=1) | y.isna())
        X = X.loc[keep_mask].reset_index(drop=True)
        y = y.loc[keep_mask].reset_index(drop=True)
        row_ids = [rid for rid, keep in zip(row_ids, keep_mask.tolist()) if keep]

        if isinstance(panelist_ids, list):
            panelist_ids = [gid for gid, keep in zip(panelist_ids, keep_mask.tolist()) if keep]
        if isinstance(product_ids, list):
            product_ids = [gid for gid, keep in zip(product_ids, keep_mask.tolist()) if keep]

    y = _coerce_target(y, outcome=outcome)
    X = _encode_regressors(X)

    dropped_constant = _find_constant_columns(X)
    X = X.drop(columns=dropped_constant, errors="ignore")

    dropped_duplicate = _find_duplicate_columns(X)
    X = X.drop(columns=dropped_duplicate, errors="ignore")

    if options.standardize_numeric:
        X = _standardize_numeric_columns(X)

    if options.add_intercept:
        X = sm.add_constant(X, has_constant="add")

    X, dropped_rank_deficient = _drop_rank_deficient_columns(X)

    metadata.update(
        {
            "panelist_ids": panelist_ids,
            "product_ids": product_ids,
            "n_rows_processed": int(len(X)),
            "n_features_processed": int(X.shape[1]),
            "dropped_constant_columns": dropped_constant,
            "dropped_duplicate_columns": dropped_duplicate,
            "dropped_rank_deficient_columns": dropped_rank_deficient,
        }
    )

    return DesignMatrix(
        X=X,
        y=y,
        feature_names=list(X.columns),
        row_ids=row_ids,
        metadata=metadata,
    )


def _coerce_target(y: pd.Series, *, outcome: OutcomeSpec) -> pd.Series:
    if outcome.is_continuous():
        return pd.to_numeric(y, errors="raise")

    if outcome.is_binary():
        if outcome.categories is not None:
            mapping = {cat: i for i, cat in enumerate(outcome.categories)}
            mapped = y.map(mapping)
            if mapped.isna().any():
                bad = y[mapped.isna()].unique().tolist()
                raise ValueError(
                    f"Binary outcome contains undeclared categories: {bad}"
                )
            return mapped.astype(int)

        return pd.to_numeric(y, errors="raise").astype(int)

    if outcome.is_nominal():
        return y.astype("category")

    if outcome.is_ordinal():
        if outcome.choice_order is None:
            raise ValueError(
                f"Ordinal outcome '{outcome.field_name}' requires choice_order."
            )
        dtype = pd.CategoricalDtype(
            categories=list(outcome.choice_order),
            ordered=True,
        )
        return y.astype(dtype)

    raise ValueError(
        f"Unsupported analysis_type '{outcome.analysis_type}' for target coercion."
    )


def _encode_regressors(X: pd.DataFrame) -> pd.DataFrame:
    """
    Convert regressors into a numeric design matrix.

    Rules:
    - bool columns become 0/1
    - object/category columns are one-hot encoded with drop_first=True
    - numeric columns are kept as-is
    """
    if X.empty:
        return X

    X = X.copy()

    bool_cols = [c for c in X.columns if pd.api.types.is_bool_dtype(X[c])]
    for col in bool_cols:
        X[col] = X[col].astype(int)

    categorical_cols = [
        c
        for c in X.columns
        if pd.api.types.is_object_dtype(X[c])
        or isinstance(X[c].dtype, pd.CategoricalDtype)
    ]

    if categorical_cols:
        X = pd.get_dummies(
            X,
            columns=categorical_cols,
            drop_first=True,
            dtype=float,
        )

    return X


def _find_constant_columns(X: pd.DataFrame) -> List[str]:
    dropped: List[str] = []
    for col in X.columns:
        if X[col].nunique(dropna=False) <= 1:
            dropped.append(col)
    return dropped


def _find_duplicate_columns(X: pd.DataFrame) -> List[str]:
    dropped: List[str] = []
    cols = list(X.columns)

    for i, col_i in enumerate(cols):
        if col_i in dropped:
            continue
        for col_j in cols[i + 1 :]:
            if col_j in dropped:
                continue
            if X[col_i].equals(X[col_j]):
                dropped.append(col_j)

    return dropped


def _drop_rank_deficient_columns(X: pd.DataFrame) -> tuple[pd.DataFrame, List[str]]:
    """
    Drop columns that do not increase matrix rank, preserving earlier columns.
    """
    if X.empty:
        return X, []

    kept_cols: List[str] = []
    dropped_cols: List[str] = []
    current_rank = 0

    for col in X.columns:
        candidate_cols = kept_cols + [col]
        candidate = X.loc[:, candidate_cols]

        rank = np.linalg.matrix_rank(candidate.to_numpy(dtype=float))
        if rank > current_rank:
            kept_cols.append(col)
            current_rank = rank
        else:
            dropped_cols.append(col)

    return X.loc[:, kept_cols].copy(), dropped_cols


def _standardize_numeric_columns(X: pd.DataFrame) -> pd.DataFrame:
    X = X.copy()
    for col in X.columns:
        if col == "const":
            continue
        if pd.api.types.is_numeric_dtype(X[col]):
            std = X[col].std()
            if std is not None and std > 0:
                X[col] = (X[col] - X[col].mean()) / std
    return X


def _as_dataframe(X: Any) -> pd.DataFrame:
    if isinstance(X, pd.DataFrame):
        return X
    raise ValueError(f"Expected pandas DataFrame for X, got {type(X).__name__}.")


def _as_series(y: Any) -> pd.Series:
    if isinstance(y, pd.Series):
        return y
    raise ValueError(f"Expected pandas Series for y, got {type(y).__name__}.")