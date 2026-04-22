from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal


@dataclass(frozen=True)
class ConditionSpec:
    label: str
    model: str
    strategy: str
    run_dir: str
    condition_type: str = "synthetic"
    events_filename: str = "events.jsonl"

    @property
    def is_real(self) -> bool:
        return self.condition_type == "real"

@dataclass(frozen=True)
class CompareConfig:
    output_dir: str
    outcome_field: str  # e.g. "rating"
    conditions: List[ConditionSpec]
    rating_scale: Optional[List[int]] = None  # e.g. [1..10]; inferred if None
    benchmark_top_k_products: int = 20

@dataclass
class ConditionMetrics:
    label: str
    model: str
    strategy: str

    n_evaluations: int = 0
    n_with_outcome: int = 0

    rating_mean: Optional[float] = None
    rating_std: Optional[float] = None
    rating_median: Optional[float] = None

    # Persona consistency: do different personas give different ratings?
    panelist_mean_variance: Optional[float] = None
    mean_pairwise_panelist_distance: Optional[float] = None

    # Product differentiation: do different products get different ratings?
    product_mean_variance: Optional[float] = None

    # Distribution shape
    rating_entropy: Optional[float] = None
    rating_normalized_entropy: Optional[float] = None

    # Raw distribution for cross-condition comparisons
    rating_distribution: Dict[Any, int] = field(default_factory=dict)

    # All numeric values for pairwise computations
    _values: List[float] = field(default_factory=list, repr=False)

@dataclass(frozen=True)
class CompareMode:
    kind: Literal["cross", "benchmark"]
    reference_label: Optional[str] = None

