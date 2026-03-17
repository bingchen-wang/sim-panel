from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple


RegressionFamily = Literal[
    "ols",
    "logit",
    "probit",
    "multinomial_logit",
    "ordered_logit",
    "ordered_probit",
]

AnalysisType = Literal["continuous", "binary", "nominal", "ordinal"]

CovarianceType = Literal[
    "nonrobust",
    "HC1",
    "cluster_panelist",
    "cluster_product",
    "cluster_two_way",
]


@dataclass(frozen=True)
class OutcomeSpec:
    """
    Regression-facing description of a questionnaire outcome field.
    """
    field_name: str
    field_type: str
    analysis_type: AnalysisType
    categories: Optional[Tuple[Any, ...]] = None
    choice_order: Optional[Tuple[Any, ...]] = None
    required: bool = True

    def is_continuous(self) -> bool:
        return self.analysis_type == "continuous"

    def is_binary(self) -> bool:
        return self.analysis_type == "binary"

    def is_nominal(self) -> bool:
        return self.analysis_type == "nominal"

    def is_ordinal(self) -> bool:
        return self.analysis_type == "ordinal"

    def is_categorical(self) -> bool:
        return self.analysis_type in {"nominal", "ordinal"}


@dataclass(frozen=True)
class RegressionSpec:
    """
    A single requested regression run.
    """
    family: RegressionFamily
    design: str
    outcome_field: str


@dataclass(frozen=True)
class RegressionOptions:
    """
    Shared fitting/preprocessing options.
    """
    drop_missing: bool = True
    standardize_numeric: bool = False
    add_intercept: bool = True
    max_iter: int = 200
    include_inference: bool = True
    confidence_level: float = 0.95
    covariance_type: CovarianceType = "cluster_two_way"


@dataclass(frozen=True)
class CoefficientStat:
    """
    One row of a regression coefficient table.
    """
    term: str
    estimate: float
    std_error: Optional[float] = None
    statistic: Optional[float] = None
    p_value: Optional[float] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    class_label: Optional[str] = None
    param_type: Optional[str] = None


@dataclass
class DesignMatrix:
    """
    Regression-ready design bundle.
    """
    X: Any
    y: Any
    feature_names: List[str]
    row_ids: List[int]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegressionResult:
    """
    Standardized fitted-result container returned by the regression layer.
    """
    family: str
    design: str
    outcome_field: str
    n_obs: int
    n_features: int
    coefficients: Dict[str, float]
    intercept: Optional[float]
    metrics: Dict[str, Any] = field(default_factory=dict)
    coefficient_table: List[CoefficientStat] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)