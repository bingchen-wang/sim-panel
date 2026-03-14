from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.miscmodels.ordinal_model import OrderedModel

from sim_panel.analysis.regression.types import (
    CoefficientStat,
    OutcomeSpec,
    RegressionOptions,
    RegressionResult,
)


def fit_discrete_model(
    *,
    family: str,
    X: pd.DataFrame,
    y: pd.Series,
    outcome: OutcomeSpec,
    design: str,
    outcome_field: str,
    options: RegressionOptions,
    cov_type: Optional[str] = None,
    cov_kwds: Optional[Dict[str, Any]] = None,
) -> RegressionResult:
    """
    Fit a discrete regression family via statsmodels.

    Supported:
    - logit
    - probit
    - multinomial_logit
    - ordered_logit
    - ordered_probit

    Robust covariance is used where the underlying statsmodels fit supports it.
    Two-way clustered covariance is intentionally not enabled here yet.
    """
    if cov_type == "cluster_two_way":
        raise ValueError(
            "Two-way clustered covariance is currently supported for OLS only."
        )

    if family == "logit":
        model = sm.Logit(y, X)
        fitted = _fit_likelihood_model(
            model=model,
            max_iter=options.max_iter,
            cov_type=cov_type,
            cov_kwds=cov_kwds,
        )
        return _standardize_binary_result(
            fitted=fitted,
            family=family,
            X=X,
            y=y,
            design=design,
            outcome_field=outcome_field,
            options=options,
            covariance_type=cov_type or "nonrobust",
        )

    if family == "probit":
        model = sm.Probit(y, X)
        fitted = _fit_likelihood_model(
            model=model,
            max_iter=options.max_iter,
            cov_type=cov_type,
            cov_kwds=cov_kwds,
        )
        return _standardize_binary_result(
            fitted=fitted,
            family=family,
            X=X,
            y=y,
            design=design,
            outcome_field=outcome_field,
            options=options,
            covariance_type=cov_type or "nonrobust",
        )

    if family == "multinomial_logit":
        codes = y.cat.codes if hasattr(y, "cat") else y
        model = sm.MNLogit(codes, X)
        fitted = _fit_likelihood_model(
            model=model,
            max_iter=options.max_iter,
            cov_type=cov_type,
            cov_kwds=cov_kwds,
        )
        return _standardize_multinomial_result(
            fitted=fitted,
            family=family,
            X=X,
            y=y,
            design=design,
            outcome_field=outcome_field,
            options=options,
            covariance_type=cov_type or "nonrobust",
        )

    if family in {"ordered_logit", "ordered_probit"}:
        if outcome.choice_order is None:
            raise ValueError(
                f"Ordered family '{family}' requires choice_order for outcome '{outcome_field}'."
            )

        distr = "logit" if family == "ordered_logit" else "probit"
        ordered_y = y.cat.codes if hasattr(y, "cat") else y

        exog = X.drop(columns=["const"], errors="ignore")
        model = OrderedModel(ordered_y, exog, distr=distr)
        fitted = _fit_likelihood_model(
            model=model,
            max_iter=options.max_iter,
            cov_type=cov_type,
            cov_kwds=cov_kwds,
        )

        return _standardize_ordered_result(
            fitted=fitted,
            family=family,
            X=exog,
            y=y,
            design=design,
            outcome_field=outcome_field,
            options=options,
            covariance_type=cov_type or "nonrobust",
        )

    raise ValueError(f"Unsupported discrete family '{family}'.")


def _fit_likelihood_model(
    *,
    model: Any,
    max_iter: int,
    cov_type: Optional[str],
    cov_kwds: Optional[Dict[str, Any]],
) -> Any:
    fit_kwargs: Dict[str, Any] = {
        "disp": False,
        "maxiter": max_iter,
    }

    if cov_type is not None:
        fit_kwargs["cov_type"] = cov_type
        fit_kwargs["cov_kwds"] = cov_kwds or {}

    if isinstance(model, OrderedModel):
        fit_kwargs["method"] = "bfgs"

    return model.fit(**fit_kwargs)


def _standardize_binary_result(
    *,
    fitted: Any,
    family: str,
    X: pd.DataFrame,
    y: pd.Series,
    design: str,
    outcome_field: str,
    options: RegressionOptions,
    covariance_type: str,
) -> RegressionResult:
    term_names = list(X.columns)
    params = _to_1d_array(fitted.params)

    coefficients = {
        str(name): float(value)
        for name, value in zip(term_names, params)
        if name != "const"
    }
    intercept = _extract_intercept(term_names, params)

    pred_prob = np.asarray(fitted.predict(X)).reshape(-1)
    pred_label = (pred_prob >= 0.5).astype(int)
    accuracy = float((pred_label == np.asarray(y)).mean())

    metrics: Dict[str, Any] = {
        "aic": float(fitted.aic),
        "bic": float(fitted.bic),
        "log_likelihood": float(fitted.llf),
        "pseudo_r2": float(getattr(fitted, "prsquared", float("nan"))),
        "accuracy": accuracy,
    }

    coefficient_table: List[CoefficientStat] = []
    if options.include_inference:
        coefficient_table = _build_single_index_inference_table(
            fitted=fitted,
            term_names=term_names,
            confidence_level=options.confidence_level,
        )

    metadata: Dict[str, Any] = {
        "converged": bool(getattr(fitted, "mle_retvals", {}).get("converged", True)),
        "model_class": type(fitted.model).__name__,
        "covariance_type": covariance_type,
    }

    return RegressionResult(
        family=family,
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


def _standardize_multinomial_result(
    *,
    fitted: Any,
    family: str,
    X: pd.DataFrame,
    y: pd.Series,
    design: str,
    outcome_field: str,
    options: RegressionOptions,
    covariance_type: str,
) -> RegressionResult:
    params_df = _coerce_params_frame(fitted.params, row_names=list(X.columns))

    flat_coefficients: Dict[str, float] = {}
    coefficient_table: List[CoefficientStat] = []

    bse_df = _coerce_optional_frame(getattr(fitted, "bse", None), like=params_df)
    pvalues_df = _coerce_optional_frame(getattr(fitted, "pvalues", None), like=params_df)
    tvalues_df = _coerce_optional_frame(getattr(fitted, "tvalues", None), like=params_df)

    conf = None
    if options.include_inference:
        try:
            conf = fitted.conf_int(alpha=1.0 - options.confidence_level)
        except Exception:
            conf = None

    for class_label in params_df.columns:
        for term in params_df.index:
            estimate = params_df.loc[term, class_label]
            key = f"class={class_label}:{term}"
            flat_coefficients[key] = float(estimate)

            if options.include_inference:
                se = _frame_lookup(bse_df, term, class_label)
                stat = _frame_lookup(tvalues_df, term, class_label)
                pval = _frame_lookup(pvalues_df, term, class_label)
                ci_low, ci_high = _extract_multinomial_conf_int(
                    conf=conf,
                    term=term,
                    class_label=class_label,
                )

                coefficient_table.append(
                    CoefficientStat(
                        term=str(term),
                        estimate=float(estimate),
                        std_error=_safe_float(se),
                        statistic=_safe_float(stat),
                        p_value=_safe_float(pval),
                        ci_low=_safe_float(ci_low),
                        ci_high=_safe_float(ci_high),
                        class_label=str(class_label),
                        param_type="intercept" if term == "const" else "slope",
                    )
                )

    metrics: Dict[str, Any] = {
        "aic": float(fitted.aic),
        "bic": float(fitted.bic),
        "log_likelihood": float(fitted.llf),
        "pseudo_r2": float(getattr(fitted, "prsquared", float("nan"))),
    }

    metadata: Dict[str, Any] = {
        "converged": bool(getattr(fitted, "mle_retvals", {}).get("converged", True)),
        "model_class": type(fitted.model).__name__,
        "covariance_type": covariance_type,
        "conf_int_layout": _describe_conf_layout(conf),
    }

    return RegressionResult(
        family=family,
        design=design,
        outcome_field=outcome_field,
        n_obs=int(len(y)),
        n_features=int(X.shape[1]),
        coefficients=flat_coefficients,
        intercept=None,
        metrics=metrics,
        coefficient_table=coefficient_table,
        metadata=metadata,
    )


def _standardize_ordered_result(
    *,
    fitted: Any,
    family: str,
    X: pd.DataFrame,
    y: pd.Series,
    design: str,
    outcome_field: str,
    options: RegressionOptions,
    covariance_type: str,
) -> RegressionResult:
    term_names = _extract_ordered_term_names(fitted=fitted, exog_columns=list(X.columns))
    params = _to_1d_array(fitted.params)

    coefficients = {
        str(name): float(value)
        for name, value in zip(term_names, params)
        if "/" not in str(name)
    }

    threshold_params = {
        str(name): float(value)
        for name, value in zip(term_names, params)
        if "/" in str(name)
    }

    coefficient_table: List[CoefficientStat] = []
    if options.include_inference:
        coefficient_table = _build_ordered_inference_table(
            fitted=fitted,
            term_names=term_names,
            confidence_level=options.confidence_level,
        )

    metrics: Dict[str, Any] = {
        "aic": float(fitted.aic),
        "bic": float(fitted.bic),
        "log_likelihood": float(fitted.llf),
    }

    metadata: Dict[str, Any] = {
        "converged": bool(getattr(fitted, "mle_retvals", {}).get("converged", True)),
        "model_class": type(fitted.model).__name__,
        "covariance_type": covariance_type,
        "thresholds": threshold_params,
    }

    return RegressionResult(
        family=family,
        design=design,
        outcome_field=outcome_field,
        n_obs=int(len(y)),
        n_features=int(X.shape[1]),
        coefficients=coefficients,
        intercept=None,
        metrics=metrics,
        coefficient_table=coefficient_table,
        metadata=metadata,
    )


def _build_single_index_inference_table(
    *,
    fitted: Any,
    term_names: List[str],
    confidence_level: float,
) -> List[CoefficientStat]:
    alpha = 1.0 - confidence_level
    conf = fitted.conf_int(alpha=alpha)

    params = _to_1d_array(fitted.params)
    bse = _to_1d_array(fitted.bse)
    tvalues = _to_1d_array(getattr(fitted, "tvalues", None))
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


def _build_ordered_inference_table(
    *,
    fitted: Any,
    term_names: List[str],
    confidence_level: float,
) -> List[CoefficientStat]:
    alpha = 1.0 - confidence_level
    conf = fitted.conf_int(alpha=alpha)

    params = _to_1d_array(fitted.params)
    bse = _to_1d_array(fitted.bse)
    tvalues = _to_1d_array(getattr(fitted, "tvalues", None))
    pvalues = _to_1d_array(fitted.pvalues)
    conf_arr = _to_2d_array(conf)

    rows: List[CoefficientStat] = []
    for i, term in enumerate(term_names):
        ci_low = conf_arr[i, 0] if conf_arr is not None and i < conf_arr.shape[0] else None
        ci_high = conf_arr[i, 1] if conf_arr is not None and i < conf_arr.shape[0] else None
        param_type = "threshold" if "/" in str(term) else "slope"

        rows.append(
            CoefficientStat(
                term=str(term),
                estimate=_safe_float(params[i]),
                std_error=_safe_float(bse[i]) if i < len(bse) else None,
                statistic=_safe_float(tvalues[i]) if i < len(tvalues) else None,
                p_value=_safe_float(pvalues[i]) if i < len(pvalues) else None,
                ci_low=_safe_float(ci_low),
                ci_high=_safe_float(ci_high),
                param_type=param_type,
            )
        )
    return rows


def _extract_intercept(term_names: List[str], params: np.ndarray) -> Optional[float]:
    if "const" in term_names:
        idx = term_names.index("const")
        return float(params[idx])
    return None


def _extract_ordered_term_names(
    *,
    fitted: Any,
    exog_columns: List[str],
) -> List[str]:
    """
    OrderedModel results typically return slope parameters followed by thresholds.
    Use exog column names first, then infer remaining threshold names from the
    original index when available.
    """
    params_obj = fitted.params

    if isinstance(params_obj, pd.Series):
        return [str(x) for x in params_obj.index]

    params = _to_1d_array(params_obj)
    n_total = len(params)
    n_exog = len(exog_columns)

    if n_total <= n_exog:
        return list(exog_columns[:n_total])

    threshold_names = [f"threshold_{i}" for i in range(n_total - n_exog)]
    return list(exog_columns) + threshold_names


def _coerce_params_frame(params: Any, row_names: List[str]) -> pd.DataFrame:
    """
    Coerce multinomial parameter output into a DataFrame with:
    - index = term names
    - columns = class labels
    """
    if isinstance(params, pd.DataFrame):
        return params.copy()

    arr = np.asarray(params)
    if arr.ndim != 2:
        raise ValueError(
            f"Expected 2D parameter array for multinomial model, got shape {arr.shape}."
        )

    if arr.shape[0] == len(row_names):
        return pd.DataFrame(arr, index=row_names)

    if arr.shape[1] == len(row_names):
        return pd.DataFrame(arr.T, index=row_names)

    raise ValueError(
        "Could not align multinomial parameter array with regressor names."
    )


def _coerce_optional_frame(value: Any, *, like: pd.DataFrame) -> Optional[pd.DataFrame]:
    if value is None:
        return None

    if isinstance(value, pd.DataFrame):
        return value.copy()

    arr = np.asarray(value)
    if arr.ndim != 2:
        return None

    if arr.shape == like.shape:
        return pd.DataFrame(arr, index=like.index, columns=like.columns)

    if arr.T.shape == like.shape:
        return pd.DataFrame(arr.T, index=like.index, columns=like.columns)

    return None


def _frame_lookup(frame: Optional[pd.DataFrame], row_key: Any, col_key: Any) -> Any:
    if frame is None:
        return None
    if row_key in frame.index and col_key in frame.columns:
        return frame.loc[row_key, col_key]
    return None


def _extract_multinomial_conf_int(
    *,
    conf: Any,
    term: Any,
    class_label: Any,
) -> Tuple[Any, Any]:
    """
    Try several plausible statsmodels layouts for MNLogit conf_int output.
    """
    if conf is None:
        return None, None

    if isinstance(conf, pd.DataFrame) and isinstance(conf.columns, pd.MultiIndex):
        try:
            return conf.loc[term, (class_label, 0)], conf.loc[term, (class_label, 1)]
        except Exception:
            pass

    if isinstance(conf, pd.DataFrame) and isinstance(conf.index, pd.MultiIndex):
        try:
            low = conf.loc[(term, class_label, 0)]
            high = conf.loc[(term, class_label, 1)]
            return _squeeze_scalar(low), _squeeze_scalar(high)
        except Exception:
            pass

    if isinstance(conf, pd.Series) and isinstance(conf.index, pd.MultiIndex):
        try:
            return conf.loc[(term, class_label, 0)], conf.loc[(term, class_label, 1)]
        except Exception:
            pass

    arr = _to_2d_array(conf)
    return None, None


def _describe_conf_layout(conf: Any) -> Optional[str]:
    if conf is None:
        return None
    if isinstance(conf, pd.DataFrame):
        return f"DataFrame[index={type(conf.index).__name__}, columns={type(conf.columns).__name__}]"
    if isinstance(conf, pd.Series):
        return f"Series[index={type(conf.index).__name__}]"
    return type(conf).__name__


def _squeeze_scalar(value: Any) -> Any:
    if isinstance(value, pd.Series) and len(value) == 1:
        return value.iloc[0]
    if isinstance(value, pd.DataFrame) and value.shape == (1, 1):
        return value.iloc[0, 0]
    return value


def _to_1d_array(value: Any) -> np.ndarray:
    if value is None:
        return np.asarray([])
    if isinstance(value, pd.Series):
        return value.to_numpy()
    if isinstance(value, pd.DataFrame):
        return value.to_numpy().reshape(-1)
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