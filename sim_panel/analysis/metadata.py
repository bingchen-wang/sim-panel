from __future__ import annotations

import os
from typing import Any, Dict, Optional


def flatten_run_metadata(metadata: Dict[str, Any], *, run_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Flatten nested run metadata into a compact analysis-facing summary record.
    """
    counts = metadata.get("counts") or {}
    config_snapshot = metadata.get("config_snapshot") or {}
    backend = config_snapshot.get("backend") or {}
    outcomes_model = config_snapshot.get("outcomes_model") or {}
    extra = metadata.get("extra") or {}

    flat: Dict[str, Any] = {
        "run_dir": run_dir,
        "run_name": os.path.basename(run_dir) if run_dir else None,
        "generated_at_utc": metadata.get("generated_at_utc"),
        "schema_version": metadata.get("schema_version"),
        "policy": metadata.get("policy"),
        "seed": metadata.get("seed"),
        "config_hash_sha256": metadata.get("config_hash_sha256"),
        "n_rows": counts.get("rows"),
        "n_panelists": counts.get("panelists"),
        "n_products": counts.get("products"),
        "n_periods": counts.get("periods"),
        "backend_name": backend.get("name"),
        "backend_model": backend.get("model"),
        "outcomes_model_name": outcomes_model.get("name"),
        "outcomes_temperature": outcomes_model.get("temperature"),
        "config_path": extra.get("config_path"),
        "personas_path": extra.get("personas_path"),
        "products_path": extra.get("products_path"),
        "persona_variant": extra.get("persona_variant"),
        "product_variant": extra.get("product_variant"),
    }

    return flat


def get_questionnaire_outcome_fields(metadata: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Return questionnaire.outcomes.fields if present, else {}.
    """
    config_snapshot = metadata.get("config_snapshot") or {}
    questionnaire = config_snapshot.get("questionnaire") or {}
    outcomes = questionnaire.get("outcomes") or {}
    fields = outcomes.get("fields") or {}
    return fields if isinstance(fields, dict) else {}


def get_questionnaire_trace_fields(metadata: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Return questionnaire.traces.fields if present, else {}.
    """
    config_snapshot = metadata.get("config_snapshot") or {}
    questionnaire = config_snapshot.get("questionnaire") or {}
    traces = questionnaire.get("traces") or {}
    fields = traces.get("fields") or {}
    return fields if isinstance(fields, dict) else {}