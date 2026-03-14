from __future__ import annotations

from typing import Dict, Set

from sim_panel.analysis.regression.types import AnalysisType, RegressionFamily


SUPPORTED_FAMILIES: Dict[RegressionFamily, dict] = {
    "ols": {
        "analysis_types": {"continuous"},
    },
    "logit": {
        "analysis_types": {"binary"},
    },
    "probit": {
        "analysis_types": {"binary"},
    },
    "multinomial_logit": {
        "analysis_types": {"nominal"},
    },
    "ordered_logit": {
        "analysis_types": {"ordinal"},
    },
    "ordered_probit": {
        "analysis_types": {"ordinal"},
    },
}


def is_supported_family(family: str) -> bool:
    return family in SUPPORTED_FAMILIES


def get_family_spec(family: str) -> dict:
    if family not in SUPPORTED_FAMILIES:
        raise ValueError(f"Unsupported regression family '{family}'.")
    return SUPPORTED_FAMILIES[family]  # type: ignore[index]


def allowed_analysis_types(family: str) -> Set[AnalysisType]:
    spec = get_family_spec(family)
    return set(spec["analysis_types"])