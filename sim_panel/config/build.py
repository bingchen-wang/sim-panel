from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple
from dataclasses import replace

from sim_panel.config.types import RunBundle, RunConfig
from sim_panel.config.yaml_loader import load_yaml

from sim_panel.generators.pipeline import EventGenerator
from sim_panel.generators.types import GeneratorConfig, ExecutionConfig

from sim_panel.policies.base import PolicyConfig
from sim_panel.decisions.types import SelectionConfig, ExecutionRules
from sim_panel.outcomes.registry import outcome_config_from_yaml_dict

from sim_panel.panelists.factory import build_panelists
from sim_panel.panelists.panelist import EvalSettings, SelectSettings
from sim_panel.panelists.io import load_persona_records, save_persona_records
from sim_panel.panelists.enrich import ensure_persona_text, PersonaTextGenSettings

from sim_panel.products.io import load_product_records, save_product_records
from sim_panel.products.product import Product
from sim_panel.products.factory import build_products
from sim_panel.products.enrich import ensure_display_text, ProductDisplayTextGenSettings

from sim_panel.backends import Backend
from sim_panel.io.manual_schedule import load_manual_schedule


def build_run_from_yaml(path: str) -> RunBundle:
    d = load_yaml(path)
    return build_run_from_dict(d, config_path=path)


def build_run_from_dict(d: Mapping[str, Any], *, config_path: Optional[str] = None) -> RunBundle:
    """
    Build a complete run bundle from a YAML-parsed dict.

    Required YAML sections:
      panelists:
        source: path/to/personas.jsonl
        variant: default
        enrich: (optional)
      products:
        source: path/to/products.jsonl
        variant: default
        enrich: (optional)
      policy:
        name: random | manual | self_selection

    Optional sections:
      generator, selection, execution, outcomes_model, questionnaire, backend, output_dir
    """
    cfg_snapshot: Dict[str, Any] = dict(d)

    # --- required source sections ---
    panel_cfg = _require_mapping(d, "panelists")
    prod_cfg = _require_mapping(d, "products")

    personas_path = _require_str(panel_cfg, "source")
    products_path = _require_str(prod_cfg, "source")
    persona_variant = _get_str(panel_cfg, "variant", default="default") or "default"
    product_variant = _get_str(prod_cfg, "variant", default="default") or "default"

    output_dir = _get_str(d, "output_dir", default=None)

    # --- generator basics ---
    gen_cfg_raw = _get_mapping(d, "generator", default={})
    schema_version = _get_str(gen_cfg_raw, "schema_version", default="0.1.0")
    seed = _get_int(gen_cfg_raw, "seed", default=0)
    n_periods = _get_int(gen_cfg_raw, "n_periods", default=1)
    validate_on_finish = _get_bool(gen_cfg_raw, "validate_on_finish", default=True)
    max_errors = _get_int(gen_cfg_raw, "max_errors", default=50)
    event_namespace = _get_str(gen_cfg_raw, "event_namespace", default="sim_panel.v0")
    max_workers = _get_int(gen_cfg_raw, "max_workers", default=1)
    prompting_strategy = _get_str(gen_cfg_raw, "prompting_strategy", default="persona") or "persona"

    # --- policy config (required) ---
    policy_cfg_raw = _require_mapping(d, "policy")
    policy_cfg = _build_policy_config(policy_cfg_raw)

    # --- selection config ---
    selection_cfg_raw = _get_mapping(d, "selection", default={})
    selection_cfg = SelectionConfig(
        allow_empty=_get_bool(selection_cfg_raw, "allow_empty", default=True),
        # NOTE: SelectionConfig uses `include_features` (product features only).
        # Keep YAML key `include_product_features` for readability/back-compat.
        include_features=_get_bool(selection_cfg_raw, "include_product_features", default=True),
        require_json_only=_get_bool(selection_cfg_raw, "require_json_only", default=True),
        max_selected_soft=_get_optional_int(selection_cfg_raw, "max_selected_soft", default=None),
        include_raw_text=_get_bool(selection_cfg_raw, "include_raw_text", default=True),
    )

    # --- execution rules ---
    exec_cfg_raw = _get_mapping(d, "execution", default={})
    rules = ExecutionRules(
        enforce_subset_of_choice_set=_get_bool(exec_cfg_raw, "enforce_subset_of_choice_set", default=True),
        max_evals_per_panelist_per_t=_get_optional_int(exec_cfg_raw, "max_evals_per_panelist_per_t", default=None),
        allow_empty=_get_bool(exec_cfg_raw, "allow_empty", default=True),
        keep_strategy=_get_str(exec_cfg_raw, "keep_strategy", default="keep_first"),
    )
    execution_cfg = ExecutionConfig(rules=rules)

    # --- outcomes (optional) ---
    outcome_cfg = None
    if "questionnaire" in d or "outcomes_model" in d:
        outcome_cfg = outcome_config_from_yaml_dict(d)

    # --- backend (optional unless enrichment or llm outcomes enabled) ---
    backend_cfg = _get_mapping(d, "backend", default=None)
    backend: Optional[Backend] = None
    if backend_cfg is not None:
        backend = _build_backend(backend_cfg)

    # --- load records ---
    persona_records = load_persona_records(personas_path)
    product_records = load_product_records(products_path)

    # --- persisted enrichment (optional) ---
    persona_records, personas_path = _maybe_enrich_personas(
        persona_records,
        source_path=personas_path,
        section=panel_cfg,
        variant=persona_variant,
        backend=backend,
    )

    product_records, products_path = _maybe_enrich_products(
        product_records,
        source_path=products_path,
        section=prod_cfg,
        variant=product_variant,
        backend=backend,
    )

 
    # --- manual policy mapping injection (optional; required if policy.name == "manual") ---
    if policy_cfg.name == "manual":
        manual_section = policy_cfg_raw.get("manual")
        if not isinstance(manual_section, Mapping):
            raise ValueError("policy.name=manual requires a 'policy.manual' mapping section.")

        # Validate against IDs available for the selected variants (post-enrichment).
        panelist_ids = [
            r.persona_id for r in persona_records
            if getattr(r, "persona_text_variant", "default") == persona_variant
        ]
        product_ids = [
            r.product_id for r in product_records
            if getattr(r, "display_variant", "default") == product_variant
        ]

        fmt = _require_str(manual_section, "format")
        path = _require_str(manual_section, "path")
        on_unknown = _get_str(manual_section, "on_unknown", default="error") or "error"

        schedule = load_manual_schedule(
            path=path,
            format=fmt,
            panelist_ids=panelist_ids,
            product_ids=product_ids,
            on_unknown=on_unknown,
            panelist_id_col=_get_str(manual_section, "panelist_id_col", default="panelist_id") or "panelist_id",
            product_id_col=_get_str(manual_section, "product_id_col", default="product_id") or "product_id",
            t_col=_get_str(manual_section, "t_col", default="t") or "t",
            default_t=_get_int(manual_section, "default_t", default=0),
        )
        policy_cfg = replace(policy_cfg, manual_assignment_fn=schedule.to_fn(on_unknown=on_unknown))

    # --- panelist runtime settings ---
    eval_settings = _build_eval_settings(panel_cfg.get("eval_settings"))
    select_settings = _build_select_settings(panel_cfg.get("select_settings"))

    # If outcomes model is LLM, require backend
    if outcome_cfg is not None and outcome_cfg.name == "llm" and backend is None:
        raise ValueError("outcomes_model.name=llm requires a backend configuration.")

    # --- build runtime objects ---
    panelists = build_panelists(
        persona_records,
        backend=backend,
        variant=persona_variant,
        eval_settings=eval_settings,
        select_settings=select_settings,
    )
    products = build_products(product_records, variant=product_variant)

    gen_cfg = GeneratorConfig(
        schema_version=schema_version,
        seed=seed,
        n_periods=n_periods,
        policy=policy_cfg,
        selection=selection_cfg,
        execution=execution_cfg,
        outcome=outcome_cfg,
        validate_on_finish=validate_on_finish,
        max_errors=max_errors,
        event_namespace=event_namespace,
        max_workers=max_workers,
        prompting_strategy=prompting_strategy,
    )

    generator = EventGenerator(gen_cfg)

    run_cfg = RunConfig(
        generator=gen_cfg,
        personas_path=personas_path,
        products_path=products_path,
        persona_variant=persona_variant,
        product_variant=product_variant,
        output_dir=output_dir,
    )

    return RunBundle(
        generator=generator,
        panelists=panelists,
        products=products,
        config_snapshot=cfg_snapshot,
        run_config=run_cfg,
    )


# ----------------------------
# Enrichment orchestrators
# ----------------------------

def _maybe_enrich_personas(
    records,
    *,
    source_path: str,
    section: Mapping[str, Any],
    variant: str,
    backend: Optional[Backend],
):
    enrich = section.get("enrich")
    if not isinstance(enrich, Mapping):
        return records, source_path

    enabled = bool(enrich.get("enabled", False))
    if not enabled:
        return records, source_path

    if backend is None:
        raise ValueError("panelists.enrich.enabled=true requires a backend configuration.")

    overwrite = bool(enrich.get("overwrite", False))
    save_target = enrich.get("save", "in_place")
    save_path = _resolve_save_path(source_path, save_target)

    settings_raw = enrich.get("settings", {})
    if not isinstance(settings_raw, Mapping):
        raise ValueError("panelists.enrich.settings must be a mapping if provided.")

    settings = PersonaTextGenSettings(
        prompt_version=str(settings_raw.get("prompt_version", "v1")),
        temperature=float(settings_raw.get("temperature", 0.2)),
        max_tokens=settings_raw.get("max_tokens"),
        metadata=settings_raw.get("metadata"),
        max_workers=max(1, int(settings_raw.get("max_workers", 1))),
    )

    updated = ensure_persona_text(
        records,
        backend=backend,
        settings=settings,
        variant=variant,
        overwrite=overwrite,
    )

    save_persona_records(save_path, updated)
    return updated, save_path


def _maybe_enrich_products(
    records,
    *,
    source_path: str,
    section: Mapping[str, Any],
    variant: str,
    backend: Optional[Backend],
):
    enrich = section.get("enrich")
    if not isinstance(enrich, Mapping):
        return records, source_path

    enabled = bool(enrich.get("enabled", False))
    if not enabled:
        return records, source_path

    if backend is None:
        raise ValueError("products.enrich.enabled=true requires a backend configuration.")

    overwrite = bool(enrich.get("overwrite", False))
    save_target = enrich.get("save", "in_place")
    save_path = _resolve_save_path(source_path, save_target)

    settings_raw = enrich.get("settings", {})
    if not isinstance(settings_raw, Mapping):
        raise ValueError("products.enrich.settings must be a mapping if provided.")

    settings = ProductDisplayTextGenSettings(
        prompt_version=str(settings_raw.get("prompt_version", "v1")),
        temperature=float(settings_raw.get("temperature", 0.2)),
        max_tokens=settings_raw.get("max_tokens"),
        metadata=settings_raw.get("metadata"),
        campaign=settings_raw.get("campaign"),
        tone=str(settings_raw.get("tone", "neutral")),
        length=str(settings_raw.get("length", "short")),
        max_workers=max(1, int(settings_raw.get("max_workers", 1))),
    )

    updated = ensure_display_text(
        records,
        backend=backend,
        settings=settings,
        variant=variant,
        overwrite=overwrite,
    )

    save_product_records(save_path, updated)
    return updated, save_path


def _resolve_save_path(source_path: str, save: Any) -> str:
    """
    save can be:
      - "in_place" (default): overwrite source_path
      - {"path": "..."}: write to explicit path
    """
    if save is None:
        return source_path
    if isinstance(save, str):
        if save == "in_place":
            return source_path
        raise ValueError("enrich.save must be 'in_place' or a mapping with {path: ...}")
    if isinstance(save, Mapping):
        p = save.get("path")
        if not isinstance(p, str) or not p:
            raise ValueError("enrich.save.path must be a non-empty string")
        return p
    raise ValueError("enrich.save must be 'in_place' or a mapping with {path: ...}")


# ----------------------------
# Builders
# ----------------------------

def _build_policy_config(d: Mapping[str, Any]) -> PolicyConfig:
    name = _require_str(d, "name")

    evals_per_period = _get_int(d, "evals_per_period", default=1)

    random_mode = _get_str(d, "random_mode", default="balanced_quota")
    product_probs = d.get("product_probs")
    if product_probs is not None and not isinstance(product_probs, dict):
        raise ValueError("policy.product_probs must be a mapping if provided.")

    choice_set_size = d.get("choice_set_size", None)
    if choice_set_size is not None and not isinstance(choice_set_size, int):
        raise ValueError("policy.choice_set_size must be int or null.")
    allow_empty_selection = _get_bool(d, "allow_empty_selection", default=True)

    # manual mapping injection handled later (io/manual_schedule)
    manual_assignment_fn = None

    return PolicyConfig(
        name=name,  # type: ignore[arg-type]
        evals_per_period=evals_per_period,
        random_mode=random_mode,  # type: ignore[arg-type]
        product_probs=product_probs,
        choice_set_size=choice_set_size,
        allow_empty_selection=allow_empty_selection,
        manual_assignment_fn=manual_assignment_fn,
    )


def _build_eval_settings(x: Any) -> Optional[EvalSettings]:
    if x is None:
        return None
    if not isinstance(x, Mapping):
        raise ValueError("panelists.eval_settings must be a mapping if provided.")
    return EvalSettings(
        temperature=float(x.get("temperature", 0.2)),
        max_tokens=x.get("max_tokens"),
        metadata=x.get("metadata"),
    )


def _build_select_settings(x: Any) -> Optional[SelectSettings]:
    if x is None:
        return None
    if not isinstance(x, Mapping):
        raise ValueError("panelists.select_settings must be a mapping if provided.")
    return SelectSettings(
        temperature=float(x.get("temperature", 0.2)),
        max_tokens=x.get("max_tokens"),
        metadata=x.get("metadata"),
    )


def _build_backend(d: Mapping[str, Any]) -> Backend:
    """
    Wire backend from YAML.

    Expects a registry builder at:
      sim_panel.backends.registry.build_backend_from_dict
    """
    try:
        from sim_panel.backends.registry import build_backend_from_dict  # type: ignore
    except Exception as e:
        raise NotImplementedError(
            "backend config provided, but sim_panel.backends.registry.build_backend_from_dict "
            "is not available. Implement that builder or omit 'backend' for deterministic runs."
        ) from e

    return build_backend_from_dict(d)


# ----------------------------
# Parsing helpers
# ----------------------------

def _require_mapping(d: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    if key not in d:
        raise ValueError(f"Missing required key: {key}")
    v = d[key]
    if not isinstance(v, Mapping):
        raise ValueError(f"{key} must be a mapping/dict, got {type(v).__name__}")
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


def _require_str(d: Mapping[str, Any], key: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v:
        raise ValueError(f"{key} must be a non-empty string")
    return v


def _get_str(d: Mapping[str, Any], key: str, default: Optional[str]) -> Optional[str]:
    if key not in d or d.get(key) is None:
        return default
    v = d.get(key)
    if not isinstance(v, str):
        raise ValueError(f"{key} must be a string")
    return v


def _get_int(d: Mapping[str, Any], key: str, default: int) -> int:
    if key not in d or d.get(key) is None:
        return default
    v = d.get(key)
    if not isinstance(v, int):
        raise ValueError(f"{key} must be an int")
    return v


def _get_optional_int(d: Mapping[str, Any], key: str, default: Optional[int]) -> Optional[int]:
    if key not in d or d.get(key) is None:
        return default
    v = d.get(key)
    if not isinstance(v, int):
        raise ValueError(f"{key} must be an int or null")
    return v


def _get_bool(d: Mapping[str, Any], key: str, default: bool) -> bool:
    if key not in d or d.get(key) is None:
        return default
    v = d.get(key)
    if not isinstance(v, bool):
        raise ValueError(f"{key} must be a bool")
    return v