from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

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