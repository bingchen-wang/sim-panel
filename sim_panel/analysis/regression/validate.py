from __future__ import annotations

from sim_panel.analysis.regression.registry import (
    allowed_analysis_types,
    is_supported_family,
)
from sim_panel.analysis.regression.resolve import (
    get_outcome_field,
    resolve_outcome_from_questionnaire,
)
from sim_panel.analysis.regression.types import OutcomeSpec, RegressionSpec
from sim_panel.outcomes.specs import QuestionnaireSpec


def validate_regression_spec(
    questionnaire: QuestionnaireSpec,
    spec: RegressionSpec,
) -> OutcomeSpec:
    """
    Validate a regression request against the questionnaire and return the
    resolved OutcomeSpec if valid.

    This is the main fail-fast entrypoint for regression config validation.
    """
    if not is_supported_family(spec.family):
        raise ValueError(f"Unsupported regression family '{spec.family}'.")

    get_outcome_field(questionnaire, spec.outcome_field)

    outcome = resolve_outcome_from_questionnaire(questionnaire, spec.outcome_field)

    _validate_family_compatibility(spec.family, outcome)
    _validate_outcome_semantics(outcome)

    return outcome


def _validate_family_compatibility(family: str, outcome: OutcomeSpec) -> None:
    allowed_types = allowed_analysis_types(family)
    if outcome.analysis_type not in allowed_types:
        raise ValueError(
            f"Regression family '{family}' is not compatible with outcome field "
            f"'{outcome.field_name}' (analysis_type='{outcome.analysis_type}')."
        )


def _validate_outcome_semantics(outcome: OutcomeSpec) -> None:
    """
    Validate resolved outcome semantics independent of the requested family.
    """
    if outcome.analysis_type == "binary":
        if outcome.categories is not None and len(outcome.categories) != 2:
            raise ValueError(
                f"Binary outcome field '{outcome.field_name}' must have exactly 2 categories "
                f"when categories are declared, got {len(outcome.categories)}."
            )

    if outcome.analysis_type == "ordinal":
        if outcome.choice_order is None:
            raise ValueError(
                f"Ordinal outcome field '{outcome.field_name}' requires a resolved choice order."
            )