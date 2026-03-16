from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from sim_panel.analysis.types import RunAnalysis
from sim_panel.outcomes.specs import QuestionnaireSpec

from sim_panel.analysis.regression.design import build_design_matrix
from sim_panel.analysis.regression.preprocess import preprocess_design_matrix
from sim_panel.analysis.regression.families import fit_discrete_model, fit_ols_model
from sim_panel.analysis.regression.types import (
    RegressionOptions,
    RegressionResult,
    RegressionSpec,
)
from sim_panel.analysis.regression.validate import validate_regression_spec


def run_regression(
    *,
    run: RunAnalysis,
    questionnaire: QuestionnaireSpec,
    spec: RegressionSpec,
    options: RegressionOptions | None = None,
) -> RegressionResult:
    """
    End-to-end regression runner for a single RegressionSpec.
    """
    if options is None:
        options = RegressionOptions()

    outcome = validate_regression_spec(questionnaire, spec)

    raw_design = build_design_matrix(
        run=run,
        design=spec.design,
        outcome_field=spec.outcome_field,
    )

    processed_design = preprocess_design_matrix(
        design_matrix=raw_design,
        outcome=outcome,
        options=options,
    )

    # ------------------------------------------------------------------
    # Pre-fit check: skip degenerate targets that cannot be estimated.
    # ------------------------------------------------------------------
    skip_reason = _check_degenerate_target(
        y=processed_design.y,
        family=spec.family,
        outcome_field=spec.outcome_field,
    )
    if skip_reason is not None:
        return RegressionResult(
            family=spec.family,
            design=spec.design,
            outcome_field=spec.outcome_field,
            n_obs=int(len(processed_design.y)),
            n_features=int(processed_design.X.shape[1]),
            coefficients={},
            intercept=None,
            metrics={},
            coefficient_table=[],
            metadata={
                "converged": False,
                "skip_reason": skip_reason,
                **{
                    k: v
                    for k, v in processed_design.metadata.items()
                    if k != "converged"
                },
            },
        )

    cov_type, cov_kwds = resolve_covariance_settings(
        options=options,
        metadata=processed_design.metadata,
    )

    if spec.family == "ols":
        result = fit_ols_model(
            X=processed_design.X,
            y=processed_design.y,
            design=spec.design,
            outcome_field=spec.outcome_field,
            options=options,
            cov_type=cov_type,
            cov_kwds=cov_kwds,
        )
    else:
        if options.covariance_type == "cluster_two_way":
            raise ValueError(
                "covariance_type='cluster_two_way' is currently supported for OLS only."
            )

        try:
            result = fit_discrete_model(
                family=spec.family,
                X=processed_design.X,
                y=processed_design.y,
                outcome=outcome,
                design=spec.design,
                outcome_field=spec.outcome_field,
                options=options,
                cov_type=cov_type,
                cov_kwds=cov_kwds,
            )
        except (np.linalg.LinAlgError, ValueError) as exc:
            result = RegressionResult(
                family=spec.family,
                design=spec.design,
                outcome_field=spec.outcome_field,
                n_obs=int(len(processed_design.y)),
                n_features=int(processed_design.X.shape[1]),
                coefficients={},
                intercept=None,
                metrics={},
                coefficient_table=[],
                metadata={
                    "converged": False,
                    "fit_error": f"{type(exc).__name__}: {exc}",
                },
            )

    result.metadata.update(
        {
            "panelist_ids": processed_design.metadata.get("panelist_ids"),
            "product_ids": processed_design.metadata.get("product_ids"),
            "dropped_constant_columns": processed_design.metadata.get("dropped_constant_columns", []),
            "dropped_duplicate_columns": processed_design.metadata.get("dropped_duplicate_columns", []),
            "dropped_rank_deficient_columns": processed_design.metadata.get("dropped_rank_deficient_columns", []),
            "n_rows_processed": processed_design.metadata.get("n_rows_processed"),
            "n_features_processed": processed_design.metadata.get("n_features_processed"),
        }
    )
    return result

def _check_degenerate_target(
    *,
    y: Any,
    family: str,
    outcome_field: str,
) -> Optional[str]:
    """
    Return a skip reason string if the target is degenerate, else None.

    Family-specific checks:

    - All families: zero observations or constant target (n_unique <= 1).
    - logit / probit: need both binary classes present (n_unique >= 2).
    - multinomial_logit: need at least 2 observed classes.
    - ordered_logit / ordered_probit: need at least 2 observed ordered categories.

    Notes
    -----
    This helper is intentionally conservative about truly degenerate targets,
    but it should not encode stronger model-policy choices than necessary.
    In particular, ordered models are only skipped when fewer than 2 observed
    categories remain after preprocessing; they are not required to use every
    declared category in `choice_order`.
    """
    y_series = pd.Series(y)
    y_nonmissing = y_series.dropna()

    if len(y_nonmissing) == 0:
        return "no observations after preprocessing"

    unique_values = pd.unique(y_nonmissing)

    n_unique = len(unique_values)

    if n_unique <= 1:
        if family in {"logit", "probit"}:
            return (
                f"binary target '{outcome_field}' has only one class present; "
                f"logit/probit requires observations in both classes"
            )
        return (
            f"target '{outcome_field}' has no variation "
            f"({n_unique} unique value(s)); model cannot be estimated"
        )

    return None


def resolve_covariance_settings(
    *,
    options: RegressionOptions,
    metadata: Dict[str, Any],
) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Translate high-level covariance options into fit settings.

    For cluster_two_way, we pass a dedicated marker through cov_type so the OLS
    fitter can handle it explicitly.
    """
    cov = options.covariance_type

    if cov == "nonrobust":
        return None, None

    if cov == "HC1":
        return "HC1", None

    if cov == "cluster_panelist":
        groups = metadata.get("panelist_ids")
        if not isinstance(groups, list) or len(groups) == 0:
            raise ValueError(
                "cluster_panelist covariance requested, but no panelist_ids are available."
            )
        return "cluster", {"groups": groups}

    if cov == "cluster_product":
        groups = metadata.get("product_ids")
        if not isinstance(groups, list) or len(groups) == 0:
            raise ValueError(
                "cluster_product covariance requested, but no product_ids are available."
            )
        return "cluster", {"groups": groups}

    if cov == "cluster_two_way":
        panelist_groups = metadata.get("panelist_ids")
        product_groups = metadata.get("product_ids")

        if not isinstance(panelist_groups, list) or len(panelist_groups) == 0:
            raise ValueError(
                "cluster_two_way covariance requested, but no panelist_ids are available."
            )
        if not isinstance(product_groups, list) or len(product_groups) == 0:
            raise ValueError(
                "cluster_two_way covariance requested, but no product_ids are available."
            )
        if len(panelist_groups) != len(product_groups):
            raise ValueError(
                "cluster_two_way covariance requires aligned panelist_ids and product_ids."
            )

        return "cluster_two_way", {
            "groups_panelist": panelist_groups,
            "groups_product": product_groups,
        }

    raise ValueError(f"Unsupported covariance_type '{cov}'.")