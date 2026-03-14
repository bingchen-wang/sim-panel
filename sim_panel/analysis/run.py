from __future__ import annotations

import os
from typing import Any, Dict, List, Mapping, Optional

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
from sim_panel.analysis.regression.fit import run_regression
from sim_panel.analysis.regression.io import save_regression_result
from sim_panel.analysis.regression.summarize import regression_result_to_summary_row
from sim_panel.analysis.types import AnalysisConfig, RunAnalysis
from sim_panel.config.yaml_loader import load_yaml
from sim_panel.io import default_run_filenames, read_jsonl_dicts
from sim_panel.outcomes.specs import QuestionnaireSpec


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

    if config.regression.enabled:
        run.artifacts["regression"] = _run_regressions(run, config)

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


def _run_regressions(run: RunAnalysis, config: AnalysisConfig) -> Dict[str, Any]:
    questionnaire = _load_questionnaire_spec(run)

    results: List[Dict[str, Any]] = []
    output_root = os.path.join(config.output_dir, config.regression.output_subdir)

    for i, spec in enumerate(config.regression.specs):
        result = run_regression(
            run=run,
            questionnaire=questionnaire,
            spec=spec,
            options=config.regression.options,
        )

        entry: Dict[str, Any] = {
            "spec_index": i,
            "family": spec.family,
            "design": spec.design,
            "outcome_field": spec.outcome_field,
            "summary": regression_result_to_summary_row(result),
            "result": result,
        }

        if config.regression.save_results:
            os.makedirs(output_root, exist_ok=True)
            prefix = f"{i:02d}_{spec.family}_{spec.design}_{spec.outcome_field}"
            entry["paths"] = save_regression_result(
                result=result,
                output_dir=output_root,
                prefix=prefix,
            )

        results.append(entry)

    return {
        "n_models": len(results),
        "results": results,
    }


def _load_questionnaire_spec(run: RunAnalysis) -> QuestionnaireSpec:
    candidate = _find_questionnaire_candidate(run.metadata)
    if candidate is not None:
        return QuestionnaireSpec.from_config_dict(candidate)

    config_path = _resolve_config_path(run)
    if config_path is not None and os.path.exists(config_path):
        cfg = load_yaml(config_path)
        questionnaire = _find_questionnaire_candidate(cfg)
        if questionnaire is not None:
            return QuestionnaireSpec.from_config_dict(questionnaire)

    raise ValueError(
        "Could not locate questionnaire config in run metadata or referenced config file."
    )


def _find_questionnaire_candidate(obj: Any) -> Optional[Mapping[str, Any]]:
    if isinstance(obj, Mapping):
        if _looks_like_questionnaire_config(obj):
            return obj

        value = obj.get("questionnaire")
        if isinstance(value, Mapping) and _looks_like_questionnaire_config(value):
            return value

        for child in obj.values():
            found = _find_questionnaire_candidate(child)
            if found is not None:
                return found

    elif isinstance(obj, list):
        for item in obj:
            found = _find_questionnaire_candidate(item)
            if found is not None:
                return found

    return None


def _looks_like_questionnaire_config(obj: Mapping[str, Any]) -> bool:
    outcomes = obj.get("outcomes")
    if not isinstance(outcomes, Mapping):
        return False
    fields = outcomes.get("fields")
    return isinstance(fields, Mapping) and len(fields) > 0


def _resolve_config_path(run: RunAnalysis) -> Optional[str]:
    for source in (run.metadata_flat, run.metadata):
        if isinstance(source, Mapping):
            path = source.get("config_path")
            if isinstance(path, str) and path:
                return path
    return None