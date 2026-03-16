from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from sim_panel.analysis.regression.families.discrete import fit_discrete_model
from sim_panel.analysis.regression.preprocess import preprocess_design_matrix
from sim_panel.analysis.regression.types import (
    DesignMatrix,
    OutcomeSpec,
    RegressionOptions,
)


def _base_options(**overrides) -> RegressionOptions:
    kwargs = {
        "drop_missing": True,
        "standardize_numeric": False,
        "add_intercept": True,
        "max_iter": 200,
        "include_inference": True,
        "confidence_level": 0.95,
        "covariance_type": "nonrobust",
    }
    kwargs.update(overrides)
    return RegressionOptions(**kwargs)


def _assert_has_some_inference(result) -> None:
    assert result.coefficient_table, "Expected non-empty coefficient_table"

    has_std = any(
        row.std_error is not None and math.isfinite(row.std_error)
        for row in result.coefficient_table
    )
    has_p = any(
        row.p_value is not None and math.isfinite(row.p_value)
        for row in result.coefficient_table
    )

    assert has_std, "Expected at least one finite std_error"
    assert has_p, "Expected at least one finite p_value"


def _make_design_matrix(
    X: pd.DataFrame,
    y: pd.Series,
) -> DesignMatrix:
    return DesignMatrix(
        X=X,
        y=y,
        feature_names=list(X.columns),
        row_ids=list(range(len(y))),
        metadata={},
    )


def _make_binary_data(n: int = 300, seed: int = 7) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    x3 = rng.binomial(1, 0.4, size=n)

    eta = -0.3 + 1.1 * x1 - 0.8 * x2 + 0.6 * x3
    p = 1.0 / (1.0 + np.exp(-eta))
    y = rng.binomial(1, p, size=n)

    X = pd.DataFrame(
        {
            "x1": x1,
            "x2": x2,
            "x3": x3,
        }
    )
    return X, pd.Series(y, name="y")


def _make_ordered_data(
    n: int = 400,
    seed: int = 11,
) -> tuple[pd.DataFrame, pd.Series, tuple[str, ...]]:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)

    latent = 0.7 * x1 - 0.5 * x2 + rng.normal(scale=0.9, size=n)
    y_num = np.digitize(latent, bins=[-0.5, 0.8])

    order = ("low", "medium", "high")
    labels = np.array(order, dtype=object)
    y = pd.Series(labels[y_num], name="y")

    X = pd.DataFrame(
        {
            "x1": x1,
            "x2": x2,
        }
    )
    return X, y, order


def _make_multinomial_data(
    n: int = 500,
    seed: int = 19,
) -> tuple[pd.DataFrame, pd.Series, tuple[str, ...]]:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)

    eta1 = 0.8 * x1 - 0.4 * x2
    eta2 = -0.5 * x1 + 0.9 * x2

    logits = np.column_stack([np.zeros(n), eta1, eta2])
    logits = logits - logits.max(axis=1, keepdims=True)
    probs = np.exp(logits)
    probs = probs / probs.sum(axis=1, keepdims=True)

    draws = np.array([rng.choice(3, p=probs[i]) for i in range(n)])
    cats = ("A", "B", "C")
    labels = np.array(cats, dtype=object)
    y = pd.Series(labels[draws], name="y")

    X = pd.DataFrame(
        {
            "x1": x1,
            "x2": x2,
        }
    )
    return X, y, cats


@pytest.mark.parametrize("family", ["logit", "probit"])
def test_binary_module_path_returns_inference(family: str) -> None:
    X_raw, y_raw = _make_binary_data()

    outcome = OutcomeSpec(
        field_name="y",
        field_type="categorical",
        analysis_type="binary",
        categories=(0, 1),
        required=True,
    )
    options = _base_options()

    design = _make_design_matrix(X_raw, y_raw)
    processed = preprocess_design_matrix(
        design_matrix=design,
        outcome=outcome,
        options=options,
    )

    result = fit_discrete_model(
        family=family,
        X=processed.X,
        y=processed.y,
        outcome=outcome,
        design="synthetic_binary",
        outcome_field="y",
        options=options,
    )

    assert result.family == family
    assert result.n_obs == len(y_raw)
    assert "log_likelihood" in result.metrics
    assert "accuracy" in result.metrics
    _assert_has_some_inference(result)


@pytest.mark.parametrize("family", ["ordered_logit", "ordered_probit"])
def test_ordered_module_path_returns_inference(family: str) -> None:
    X_raw, y_raw, order = _make_ordered_data()

    outcome = OutcomeSpec(
        field_name="y",
        field_type="categorical",
        analysis_type="ordinal",
        categories=order,
        choice_order=order,
        required=True,
    )
    options = _base_options()

    design = _make_design_matrix(X_raw, y_raw)
    processed = preprocess_design_matrix(
        design_matrix=design,
        outcome=outcome,
        options=options,
    )

    result = fit_discrete_model(
        family=family,
        X=processed.X,
        y=processed.y,
        outcome=outcome,
        design="synthetic_ordered",
        outcome_field="y",
        options=options,
    )

    assert result.family == family
    assert result.n_obs == len(y_raw)
    assert "log_likelihood" in result.metrics
    assert isinstance(result.metadata.get("thresholds"), dict)
    _assert_has_some_inference(result)

    has_threshold_row = any(
        row.param_type == "threshold" for row in result.coefficient_table
    )
    assert has_threshold_row, "Expected threshold rows for ordered model"


def test_multinomial_module_path_returns_inference() -> None:
    X_raw, y_raw, cats = _make_multinomial_data()

    outcome = OutcomeSpec(
        field_name="y",
        field_type="categorical",
        analysis_type="nominal",
        categories=cats,
        required=True,
    )
    options = _base_options()

    design = _make_design_matrix(X_raw, y_raw)
    processed = preprocess_design_matrix(
        design_matrix=design,
        outcome=outcome,
        options=options,
    )

    result = fit_discrete_model(
        family="multinomial_logit",
        X=processed.X,
        y=processed.y,
        outcome=outcome,
        design="synthetic_multinomial",
        outcome_field="y",
        options=options,
    )

    assert result.family == "multinomial_logit"
    assert result.n_obs == len(y_raw)
    assert "log_likelihood" in result.metrics
    assert result.coefficient_table

    assert any(row.class_label is not None for row in result.coefficient_table)

    has_std = any(
        row.std_error is not None and math.isfinite(row.std_error)
        for row in result.coefficient_table
    )
    has_p = any(
        row.p_value is not None and math.isfinite(row.p_value)
        for row in result.coefficient_table
    )

    assert has_std, "Expected at least one finite std_error for multinomial logit"
    assert has_p, "Expected at least one finite p_value for multinomial logit"


@pytest.mark.parametrize(
    "family,covariance_type",
    [
        ("logit", "HC1"),
        ("probit", "HC1"),
        ("logit", "cluster_panelist"),
        ("probit", "cluster_panelist"),
    ],
)
def test_binary_module_path_supports_requested_inference_modes(
    family: str,
    covariance_type: str,
) -> None:
    X_raw, y_raw = _make_binary_data()

    outcome = OutcomeSpec(
        field_name="y",
        field_type="categorical",
        analysis_type="binary",
        categories=(0, 1),
        required=True,
    )

    design = _make_design_matrix(X_raw, y_raw)
    design.metadata["panelist_ids"] = [f"p{i // 10:03d}" for i in range(len(y_raw))]
    design.metadata["product_ids"] = [f"prod{i % 7:03d}" for i in range(len(y_raw))]

    options = _base_options(covariance_type=covariance_type)
    processed = preprocess_design_matrix(
        design_matrix=design,
        outcome=outcome,
        options=options,
    )

    if covariance_type == "HC1":
        cov_type = "HC1"
        cov_kwds = None
    else:
        cov_type = "cluster"
        cov_kwds = {"groups": processed.metadata["panelist_ids"]}

    result = fit_discrete_model(
        family=family,
        X=processed.X,
        y=processed.y,
        outcome=outcome,
        design="synthetic_binary",
        outcome_field="y",
        options=options,
        cov_type=cov_type,
        cov_kwds=cov_kwds,
    )

    _assert_has_some_inference(result)


def test_discrete_models_reject_cluster_two_way() -> None:
    X_raw, y_raw = _make_binary_data()

    outcome = OutcomeSpec(
        field_name="y",
        field_type="categorical",
        analysis_type="binary",
        categories=(0, 1),
        required=True,
    )
    options = _base_options(covariance_type="cluster_two_way")

    design = _make_design_matrix(X_raw, y_raw)
    processed = preprocess_design_matrix(
        design_matrix=design,
        outcome=outcome,
        options=options,
    )

    with pytest.raises(ValueError, match="OLS only"):
        fit_discrete_model(
            family="logit",
            X=processed.X,
            y=processed.y,
            outcome=outcome,
            design="synthetic_binary",
            outcome_field="y",
            options=options,
            cov_type="cluster_two_way",
            cov_kwds={
                "groups_panelist": np.arange(len(y_raw)),
                "groups_product": np.arange(len(y_raw)),
            },
        )