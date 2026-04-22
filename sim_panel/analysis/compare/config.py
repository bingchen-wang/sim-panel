from __future__ import annotations

from typing import Any, Mapping

from sim_panel.analysis.compare.types import CompareConfig, ConditionSpec
from sim_panel.config.yaml_loader import load_yaml


def build_compare_config_from_dict(d: Mapping[str, Any]) -> CompareConfig:
    output_dir = d.get("output_dir")
    if not isinstance(output_dir, str) or not output_dir:
        raise ValueError("compare config requires 'output_dir'")

    outcome_field = str(d.get("outcome_field", "rating"))

    raw_conditions = d.get("conditions")
    if not isinstance(raw_conditions, list) or not raw_conditions:
        raise ValueError("compare config requires a non-empty 'conditions' list")

    conditions: list[ConditionSpec] = []
    for i, c in enumerate(raw_conditions):
        if not isinstance(c, Mapping):
            raise ValueError(f"conditions[{i}] must be a mapping")

        condition_type = str(c.get("condition_type", "synthetic"))
        if condition_type not in {"synthetic", "real"}:
            raise ValueError(
                f"conditions[{i}].condition_type must be 'synthetic' or 'real', "
                f"got {condition_type!r}"
            )

        events_filename = c.get("events_filename", "events.jsonl")
        if not isinstance(events_filename, str) or not events_filename:
            raise ValueError(
                f"conditions[{i}].events_filename must be a non-empty string"
            )

        run_dir = c.get("run_dir")
        if not isinstance(run_dir, str) or not run_dir:
            raise ValueError(f"conditions[{i}].run_dir must be a non-empty string")

        conditions.append(
            ConditionSpec(
                label=str(c.get("label", f"cond_{i}")),
                model=str(c.get("model", "")),
                strategy=str(c.get("strategy", "")),
                run_dir=run_dir,
                condition_type=condition_type,
                events_filename=events_filename,
            )
        )

    rating_scale = d.get("rating_scale")
    if isinstance(rating_scale, list):
        rating_scale = [int(x) for x in rating_scale]

    benchmark_top_k_products = d.get("benchmark_top_k_products", 20)
    if not isinstance(benchmark_top_k_products, int) or benchmark_top_k_products <= 0:
        raise ValueError("compare config 'benchmark_top_k_products' must be a positive int")

    return CompareConfig(
        output_dir=output_dir,
        outcome_field=outcome_field,
        conditions=conditions,
        rating_scale=rating_scale,
        benchmark_top_k_products = benchmark_top_k_products,
    )


def build_compare_config_from_yaml(path: str) -> CompareConfig:
    return build_compare_config_from_dict(load_yaml(path))