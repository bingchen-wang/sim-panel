from __future__ import annotations

from typing import Any, Optional, Tuple

from sim_panel.analysis.regression.types import OutcomeSpec
from sim_panel.outcomes.specs import FieldSpec, QuestionnaireSpec


def get_outcome_field(questionnaire: QuestionnaireSpec, field_name: str) -> FieldSpec:
    """
    Return the outcome FieldSpec with the given name.

    Raises:
        ValueError: if the field is not found among questionnaire outcome fields.
    """
    for fs in questionnaire.outcome_fields:
        if fs.name == field_name:
            return fs
    raise ValueError(f"Outcome field '{field_name}' not found in questionnaire outcome_fields.")


def resolve_outcome_spec(field_spec: FieldSpec) -> OutcomeSpec:
    """
    Resolve a questionnaire FieldSpec into a regression-facing OutcomeSpec.

    Resolution priority:
    1. Use explicit FieldSpec.analysis_type if provided.
    2. Otherwise infer from legacy FieldSpec.type and choices metadata.

    Legacy inference defaults:
    - bool -> binary
    - categorical -> nominal
    - int/float -> continuous
    - text/json -> unsupported
    """
    analysis_type = field_spec.analysis_type or _infer_analysis_type(field_spec)

    if analysis_type == "continuous":
        return OutcomeSpec(
            field_name=field_spec.name,
            field_type=field_spec.type,
            analysis_type="continuous",
            categories=_tuple_or_none(field_spec.choices),
            choice_order=None,
            required=field_spec.required,
        )

    if analysis_type == "binary":
        return OutcomeSpec(
            field_name=field_spec.name,
            field_type=field_spec.type,
            analysis_type="binary",
            categories=_tuple_or_none(field_spec.choices),
            choice_order=None,
            required=field_spec.required,
        )

    if analysis_type == "nominal":
        return OutcomeSpec(
            field_name=field_spec.name,
            field_type=field_spec.type,
            analysis_type="nominal",
            categories=_tuple_or_none(field_spec.choices),
            choice_order=None,
            required=field_spec.required,
        )

    if analysis_type == "ordinal":
        return OutcomeSpec(
            field_name=field_spec.name,
            field_type=field_spec.type,
            analysis_type="ordinal",
            categories=_tuple_or_none(field_spec.choices),
            choice_order=_resolve_choice_order(field_spec),
            required=field_spec.required,
        )

    raise ValueError(
        f"Unsupported analysis_type '{analysis_type}' for outcome field '{field_spec.name}'."
    )


def resolve_outcome_from_questionnaire(
    questionnaire: QuestionnaireSpec,
    field_name: str,
) -> OutcomeSpec:
    """
    Convenience wrapper: fetch the field from the questionnaire, then resolve it.
    """
    field_spec = get_outcome_field(questionnaire, field_name)
    return resolve_outcome_spec(field_spec)


def _infer_analysis_type(field_spec: FieldSpec) -> str:
    """
    Infer analysis_type from legacy field metadata.

    This preserves backward compatibility for questionnaires created before
    analysis_type existed.
    """
    if field_spec.type == "bool":
        return "binary"

    if field_spec.type == "categorical":
        return "nominal"

    if field_spec.type in {"int", "float"}:
        return "continuous"

    raise ValueError(
        f"Cannot infer regression analysis_type for field '{field_spec.name}' "
        f"with field type '{field_spec.type}'. Please set analysis_type explicitly."
    )


def _resolve_choice_order(field_spec: FieldSpec) -> Tuple[Any, ...]:
    """
    Resolve the ordering for an ordinal outcome.

    Priority:
    1. FieldSpec.choice_order
    2. FieldSpec.choices

    Raises:
        ValueError: if neither is available.
    """
    if field_spec.choice_order is not None:
        return tuple(field_spec.choice_order)

    if field_spec.choices is not None:
        return tuple(field_spec.choices)

    raise ValueError(
        f"Ordinal outcome field '{field_spec.name}' requires choice_order or choices."
    )


def _tuple_or_none(values: Any) -> Optional[Tuple[Any, ...]]:
    if values is None:
        return None
    if isinstance(values, tuple):
        return values
    if isinstance(values, list):
        return tuple(values)
    raise ValueError(f"Expected list/tuple or None, got {type(values).__name__}.")