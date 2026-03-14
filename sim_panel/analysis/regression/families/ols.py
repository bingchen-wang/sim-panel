from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm

from sim_panel.analysis.regression.types import (
    CoefficientStat,
    RegressionOptions,
    RegressionResult,
)


def fit_ols_model(
    *,
    X: pd.DataFrame,
    y: pd.Series,
    design: str,
    outcome_field: str,
    options: RegressionOptions,
    cov_type: Optional[str] = None,
    cov_kwds: Optional[Dict[str, Any]] = None,
) -> RegressionResult:
    """
    Fit OLS via statsmodels and return a standardized RegressionResult.

    Supports:
    - nonrobust
    - HC1
    - one-way clustered covariance
    - two-way clustered covariance
    """
    model = sm.OLS(y, X)
    base_fitted = model.fit()

    fitted = _apply_robust_covariance(
        fitted=base_fitted,
        cov_type=cov_type,
        cov_kwds=cov_kwds,
    )

    term_names = list(X.columns)
    params = _to_1d_array(fitted.params)

    coefficients = {
        str(name): float(value)
        for name, value in zip(term_names, params)
        if name != "const"
    }
    intercept = _extract_intercept(term_names, params)

    metrics: Dict[str, Any] = {
        "r2": float(base_fitted.rsquared),
        "adj_r2": float(base_fitted.rsquared_adj),
        "aic": float(base_fitted.aic),
        "bic": float(base_fitted.bic),
        "log_likelihood": float(base_fitted.llf),
        "rmse": float(((base_fitted.resid ** 2).mean()) ** 0.5),
        "mae": float(base_fitted.resid.abs().mean()),
    }

    coefficient_table: List[CoefficientStat] = []
    if options.include_inference:
        coefficient_table = _build_inference_table(
            fitted=fitted,
            term_names=term_names,
            confidence_level=options.confidence_level,
        )

    metadata: Dict[str, Any] = {
        "converged": True,
        "model_class": type(model).__name__,
        "covariance_type": cov_type or "nonrobust",
    }

    return RegressionResult(
        family="ols",
        design=design,
        outcome_field=outcome_field,
        n_obs=int(len(y)),
        n_features=int(X.shape[1]),
        coefficients=coefficients,
        intercept=intercept,
        metrics=metrics,
        coefficient_table=coefficient_table,
        metadata=metadata,
    )


def _apply_robust_covariance(
    *,
    fitted: Any,
    cov_type: Optional[str],
    cov_kwds: Optional[Dict[str, Any]],
) -> Any:
    if cov_type is None:
        return fitted

    if cov_type == "HC1":
        return fitted.get_robustcov_results(cov_type="HC1")

    if cov_type == "cluster":
        kwds = cov_kwds or {}
        groups = kwds.get("groups")
        if groups is None:
            raise ValueError("cluster covariance requires 'groups'.")
        return fitted.get_robustcov_results(
            cov_type="cluster",
            groups=np.asarray(groups),
            use_correction=True,
            df_correction=True,
        )

    if cov_type == "cluster_two_way":
        kwds = cov_kwds or {}
        g1 = kwds.get("groups_panelist")
        g2 = kwds.get("groups_product")
        if g1 is None or g2 is None:
            raise ValueError(
                "cluster_two_way covariance requires both groups_panelist and groups_product."
            )

        groups = np.column_stack([np.asarray(g1), np.asarray(g2)])
        return fitted.get_robustcov_results(
            cov_type="cluster",
            groups=groups,
            use_correction=True,
            df_correction=True,
        )

    raise ValueError(f"Unsupported OLS covariance type '{cov_type}'.")


def _build_inference_table(
    *,
    fitted: Any,
    term_names: List[str],
    confidence_level: float,
) -> List[CoefficientStat]:
    alpha = 1.0 - confidence_level
    conf = fitted.conf_int(alpha=alpha)

    params = _to_1d_array(fitted.params)
    bse = _to_1d_array(fitted.bse)
    tvalues = _to_1d_array(fitted.tvalues)
    pvalues = _to_1d_array(fitted.pvalues)
    conf_arr = _to_2d_array(conf)

    rows: List[CoefficientStat] = []
    for i, term in enumerate(term_names):
        ci_low = conf_arr[i, 0] if conf_arr is not None and i < conf_arr.shape[0] else None
        ci_high = conf_arr[i, 1] if conf_arr is not None and i < conf_arr.shape[0] else None

        rows.append(
            CoefficientStat(
                term=str(term),
                estimate=_safe_float(params[i]),
                std_error=_safe_float(bse[i]) if i < len(bse) else None,
                statistic=_safe_float(tvalues[i]) if i < len(tvalues) else None,
                p_value=_safe_float(pvalues[i]) if i < len(pvalues) else None,
                ci_low=_safe_float(ci_low),
                ci_high=_safe_float(ci_high),
                param_type="intercept" if term == "const" else "slope",
            )
        )
    return rows


def _extract_intercept(term_names: List[str], params: np.ndarray) -> Optional[float]:
    if "const" in term_names:
        idx = term_names.index("const")
        return float(params[idx])
    return None


def _to_1d_array(value: Any) -> np.ndarray:
    if isinstance(value, pd.Series):
        return value.to_numpy()
    if isinstance(value, pd.DataFrame):
        arr = value.to_numpy().reshape(-1)
        return np.asarray(arr)
    return np.asarray(value).reshape(-1)


def _to_2d_array(value: Any) -> Optional[np.ndarray]:
    if value is None:
        return None
    if isinstance(value, pd.DataFrame):
        return value.to_numpy()
    arr = np.asarray(value)
    if arr.ndim == 1:
        if len(arr) % 2 == 0:
            return arr.reshape(-1, 2)
        return None
    return arr


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return None