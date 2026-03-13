from __future__ import annotations

from typing import Any, Mapping, Optional

from sim_panel.analysis.types import (
    AnalysisConfig,
    ExportConfig,
    LoadConfig,
    MetricConfig,
    OutcomeDistributionPlotConfig,
    PlotConfig,
    SelectionConcentrationPlotConfig,
    SummaryBarPlotConfig,
    SummaryConfig,
)
from sim_panel.config.yaml_loader import load_yaml


def build_analysis_config_from_yaml(path: str) -> AnalysisConfig:
    d = load_yaml(path)
    return build_analysis_config_from_dict(d)


def build_analysis_config_from_dict(d: Mapping[str, Any]) -> AnalysisConfig:
    """
    Build an AnalysisConfig from a YAML-parsed dict.

    Minimal YAML:
        run_dir: outputs/run_beer_demo_large_self_selection
        output_dir: outputs/run_beer_demo_large_self_selection/analysis

    Optional sections:
        load:
        summaries:
        metrics:
        plots:
        export:
    """
    run_dir = _require_str(d, "run_dir")
    output_dir = _require_str(d, "output_dir")

    load_raw = _get_mapping(d, "load", default={})
    summaries_raw = _get_mapping(d, "summaries", default={})
    metrics_raw = _get_mapping(d, "metrics", default={})
    plots_raw = _get_mapping(d, "plots", default={})
    export_raw = _get_mapping(d, "export", default={})

    load_cfg = LoadConfig(
        resolve_sources=_get_bool(load_raw, "resolve_sources", default=True),
        prefer_extra_paths=_get_bool(load_raw, "prefer_extra_paths", default=True),
        strict_source_resolution=_get_bool(load_raw, "strict_source_resolution", default=False),
    )

    summaries_cfg = SummaryConfig(
        run=_get_bool(summaries_raw, "run", default=True),
        outcomes=_get_bool(summaries_raw, "outcomes", default=True),
        traces=_get_bool(summaries_raw, "traces", default=True),
        selections=_get_bool(summaries_raw, "selections", default=True),
    )

    metrics_cfg = MetricConfig(
        quality=_get_bool(metrics_raw, "quality", default=True),
        diversity=_get_bool(metrics_raw, "diversity", default=True),
        persona=_get_bool(metrics_raw, "persona", default=True),
        selection=_get_bool(metrics_raw, "selection", default=False),
    )

    outcome_plot_raw = _get_mapping(plots_raw, "outcome_distributions", default={})
    panelist_plot_raw = _get_mapping(plots_raw, "panelist_summary", default={})
    product_plot_raw = _get_mapping(plots_raw, "product_summary", default={})
    selection_plot_raw = _get_mapping(plots_raw, "selection_concentration", default={})

    outcome_plot_cfg = OutcomeDistributionPlotConfig(
        enabled=_get_bool(outcome_plot_raw, "enabled", default=True),
        normalize_to_share=_get_bool(outcome_plot_raw, "normalize_to_share", default=False),
        fields=_get_optional_str_list(outcome_plot_raw, "fields", default=None),
        figsize=_get_float_pair(outcome_plot_raw, "figsize", default=(7.0, 4.5)),
    )

    panelist_plot_cfg = SummaryBarPlotConfig(
        enabled=_get_bool(panelist_plot_raw, "enabled", default=False),
        outcome_field=_get_str(panelist_plot_raw, "outcome_field", default="rating") or "rating",
        metrics=_get_str_list(panelist_plot_raw, "metrics", default=["mean", "variance"]),
        max_items=_get_int(panelist_plot_raw, "max_items", default=30),
        sort_by=_get_str(panelist_plot_raw, "sort_by", default="label_asc") or "label_asc",
        horizontal=_get_bool(panelist_plot_raw, "horizontal", default=False),
    )

    product_plot_cfg = SummaryBarPlotConfig(
        enabled=_get_bool(product_plot_raw, "enabled", default=False),
        outcome_field=_get_str(product_plot_raw, "outcome_field", default="rating") or "rating",
        metrics=_get_str_list(product_plot_raw, "metrics", default=["mean", "variance"]),
        max_items=_get_int(product_plot_raw, "max_items", default=30),
        sort_by=_get_str(product_plot_raw, "sort_by", default="label_asc") or "label_asc",
        horizontal=_get_bool(product_plot_raw, "horizontal", default=False),
    )

    selection_plot_cfg = SelectionConcentrationPlotConfig(
        enabled=_get_bool(selection_plot_raw, "enabled", default=False),
        modes=_get_str_list(selection_plot_raw, "modes", default=["executed", "requested"]),
        top_k=_get_int(selection_plot_raw, "top_k", default=15),
        horizontal=_get_bool(selection_plot_raw, "horizontal", default=True),
    )

    plots_cfg = PlotConfig(
        outcome_distributions=outcome_plot_cfg,
        panelist_summary=panelist_plot_cfg,
        product_summary=product_plot_cfg,
        selection_concentration=selection_plot_cfg,
    )

    export_cfg = ExportConfig(
        csv=_get_bool(export_raw, "csv", default=True),
        json=_get_bool(export_raw, "json", default=True),
        markdown=_get_bool(export_raw, "markdown", default=True),
        overwrite=_get_bool(export_raw, "overwrite", default=True),
    )

    return AnalysisConfig(
        run_dir=run_dir,
        output_dir=output_dir,
        load=load_cfg,
        summaries=summaries_cfg,
        metrics=metrics_cfg,
        plots=plots_cfg,
        export=export_cfg,
    )


def _require_str(d: Mapping[str, Any], key: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v:
        raise ValueError(f"{key} must be a non-empty string")
    return v


def _get_mapping(d: Mapping[str, Any], key: str, default: Any) -> Any:
    if key not in d:
        return default
    v = d[key]
    if v is None:
        return default
    if not isinstance(v, Mapping):
        raise ValueError(f"{key} must be a mapping/dict, got {type(v).__name__}")
    return v


def _get_bool(d: Mapping[str, Any], key: str, default: bool) -> bool:
    if key not in d or d.get(key) is None:
        return default
    v = d.get(key)
    if not isinstance(v, bool):
        raise ValueError(f"{key} must be a bool")
    return v

def _get_int(d: Mapping[str, Any], key: str, default: int) -> int:
    if key not in d or d.get(key) is None:
        return default
    v = d.get(key)
    if not isinstance(v, int):
        raise ValueError(f"{key} must be an int")
    return v


def _get_str(d: Mapping[str, Any], key: str, default: Optional[str]) -> Optional[str]:
    if key not in d or d.get(key) is None:
        return default
    v = d.get(key)
    if not isinstance(v, str):
        raise ValueError(f"{key} must be a string")
    return v


def _get_str_list(d: Mapping[str, Any], key: str, default: list[str]) -> list[str]:
    if key not in d or d.get(key) is None:
        return list(default)
    v = d.get(key)
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise ValueError(f"{key} must be a list of strings")
    return list(v)


def _get_optional_str_list(
    d: Mapping[str, Any],
    key: str,
    default: Optional[list[str]],
) -> Optional[list[str]]:
    if key not in d or d.get(key) is None:
        return default
    v = d.get(key)
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise ValueError(f"{key} must be a list of strings or null")
    return list(v)


def _get_float_pair(
    d: Mapping[str, Any],
    key: str,
    default: tuple[float, float],
) -> tuple[float, float]:
    if key not in d or d.get(key) is None:
        return default
    v = d.get(key)
    if (
        not isinstance(v, list)
        or len(v) != 2
        or not all(isinstance(x, (int, float)) for x in v)
    ):
        raise ValueError(f"{key} must be a 2-element numeric list")
    return (float(v[0]), float(v[1]))