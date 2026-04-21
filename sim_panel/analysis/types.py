from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sim_panel.analysis.regression.types import RegressionOptions, RegressionSpec


@dataclass(frozen=True)
class LoadConfig:
    """
    Controls how a run is loaded for analysis.
    """

    resolve_sources: bool = True
    prefer_extra_paths: bool = True
    strict_source_resolution: bool = False


@dataclass(frozen=True)
class SummaryConfig:
    """
    Toggles for summary-table generation.
    """

    run: bool = True
    outcomes: bool = True
    traces: bool = True
    selections: bool = True


@dataclass(frozen=True)
class MetricConfig:
    """
    Toggles for metric families.
    """

    quality: bool = True
    diversity: bool = True
    persona: bool = True
    selection: bool = False


@dataclass(frozen=True)
class OutcomeDistributionPlotConfig:
    """
    Options for outcome distribution plots.
    """

    enabled: bool = True
    normalize_to_share: bool = False
    fields: Optional[List[str]] = None
    figsize: tuple[float, float] = (7.0, 4.5)


@dataclass(frozen=True)
class SummaryBarPlotConfig:
    """
    Options for panelist/product summary bar plots.
    """

    enabled: bool = False
    outcome_field: str = "rating"
    metrics: List[str] = field(default_factory=lambda: ["mean", "variance"])
    max_items: int = 30
    sort_by: str = "label_asc"
    horizontal: bool = False


@dataclass(frozen=True)
class SelectionConcentrationPlotConfig:
    """
    Options for selection concentration plots.
    """

    enabled: bool = False
    modes: List[str] = field(default_factory=lambda: ["executed", "requested"])
    top_k: int = 15
    horizontal: bool = True


@dataclass(frozen=True)
class PlotConfig:
    """
    Plot family configuration.
    """

    outcome_distributions: OutcomeDistributionPlotConfig = field(
        default_factory=OutcomeDistributionPlotConfig
    )
    panelist_summary: SummaryBarPlotConfig = field(
        default_factory=SummaryBarPlotConfig
    )
    product_summary: SummaryBarPlotConfig = field(
        default_factory=SummaryBarPlotConfig
    )
    selection_concentration: SelectionConcentrationPlotConfig = field(
        default_factory=SelectionConcentrationPlotConfig
    )


@dataclass(frozen=True)
class ExportConfig:
    """
    Controls artifact export.
    """

    csv: bool = True
    json: bool = True
    markdown: bool = True
    overwrite: bool = True


@dataclass(frozen=True)
class RegressionConfig:
    """
    Controls optional regression analysis.
    """

    enabled: bool = False
    specs: List[RegressionSpec] = field(default_factory=list)
    options: RegressionOptions = field(default_factory=RegressionOptions)
    save_results: bool = True
    output_subdir: str = "regression"


@dataclass(frozen=True)
class AnalysisConfig:
    """
    Normalized analysis configuration extracted from YAML.
    """

    run_dir: str
    output_dir: str

    load: LoadConfig = field(default_factory=LoadConfig)
    summaries: SummaryConfig = field(default_factory=SummaryConfig)
    metrics: MetricConfig = field(default_factory=MetricConfig)
    plots: PlotConfig = field(default_factory=PlotConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    regression: RegressionConfig = field(default_factory=RegressionConfig)


@dataclass
class RunAnalysis:
    """
    In-memory representation of a single analyzed run.

    Notes
    -----
    - `events` contains all rows from events.jsonl.
    - `selection_rows` and `evaluation_rows` are split views for convenience.
    - `personas` / `products` are optional linked source artifacts resolved from metadata.
    - `artifacts` stores computed summaries / metrics / plot paths.
    """

    run_dir: str
    output_dir: str

    events: List[Dict[str, Any]]
    selection_rows: List[Dict[str, Any]]
    evaluation_rows: List[Dict[str, Any]]

    metadata: Dict[str, Any]
    metadata_flat: Dict[str, Any]

    personas: Optional[List[Dict[str, Any]]] = None
    products: Optional[List[Dict[str, Any]]] = None

    artifacts: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Compare Config
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Compare per-condition metrics
# ---------------------------------------------------------------------------

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
