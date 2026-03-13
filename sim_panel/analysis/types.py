from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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