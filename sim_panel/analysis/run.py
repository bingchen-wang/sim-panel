from __future__ import annotations

import os
from typing import Any, Dict, List

from sim_panel.analysis.metadata import flatten_run_metadata
from sim_panel.analysis.resolve import load_resolved_sources
from sim_panel.analysis.tables import (
    build_outcome_summary,
    build_run_summary,
    build_selection_summary,
    build_trace_summary,
)
from sim_panel.analysis.metrics import (
    compute_diversity_metrics,
    compute_persona_metrics,
    compute_quality_metrics,
    compute_selection_metrics,
)
from sim_panel.analysis.plots import generate_plots
from sim_panel.analysis.types import AnalysisConfig, RunAnalysis
from sim_panel.io import default_run_filenames, read_jsonl_dicts
from sim_panel.config.yaml_loader import load_yaml


def load_run_analysis(config: AnalysisConfig) -> RunAnalysis:
    """
    Load a single run and optional linked sources into a RunAnalysis object.
    """
    filenames = default_run_filenames()

    events_path = os.path.join(config.run_dir, filenames.events_jsonl)
    metadata_path = os.path.join(config.run_dir, filenames.metadata_json)

    events = read_jsonl_dicts(events_path)
    metadata = load_yaml(metadata_path)
    metadata_flat = flatten_run_metadata(metadata, run_dir=config.run_dir)

    selection_rows = get_selection_rows(events)
    evaluation_rows = get_evaluation_rows(events)

    personas = None
    products = None
    if config.load.resolve_sources:
        personas, products = load_resolved_sources(
            metadata,
            prefer_extra_paths=config.load.prefer_extra_paths,
            strict=config.load.strict_source_resolution,
        )

    return RunAnalysis(
        run_dir=config.run_dir,
        output_dir=config.output_dir,
        events=events,
        selection_rows=selection_rows,
        evaluation_rows=evaluation_rows,
        metadata=metadata,
        metadata_flat=metadata_flat,
        personas=personas,
        products=products,
    )


def analyze_run(config: AnalysisConfig) -> RunAnalysis:
    """
    Load a run and compute requested summary artifacts.

    Metric / plot execution will be added incrementally.
    """
    run = load_run_analysis(config)

    if config.summaries.run:
        run.artifacts["run_summary"] = build_run_summary(run)

    if config.summaries.outcomes:
        run.artifacts["outcome_summary"] = build_outcome_summary(run)

    if config.summaries.traces:
        run.artifacts["trace_summary"] = build_trace_summary(run)

    if config.summaries.selections:
        run.artifacts["selection_summary"] = build_selection_summary(run)

    if config.metrics.quality:
        run.artifacts["quality_metrics"] = compute_quality_metrics(run)

    if config.metrics.diversity:
        run.artifacts["diversity_metrics"] = compute_diversity_metrics(run)

    if config.metrics.persona:
        run.artifacts["persona_metrics"] = compute_persona_metrics(run)

    if config.metrics.selection:
        run.artifacts["selection_metrics"] = compute_selection_metrics(run)

    if _any_plot_enabled(config):
        run.artifacts["plots"] = generate_plots(
            run,
            plot_cfg=config.plots,
        )

    return run


def get_selection_rows(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [row for row in events if row.get("event_type") == "selection"]


def get_evaluation_rows(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [row for row in events if row.get("event_type") == "evaluation"]


def _any_plot_enabled(config: AnalysisConfig) -> bool:
    return any(
        [
            config.plots.outcome_distributions.enabled,
            config.plots.panelist_summary.enabled,
            config.plots.product_summary.enabled,
            config.plots.selection_concentration.enabled,
        ]
    )