from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping, Optional

from sim_panel.config.yaml_loader import load_yaml
from sim_panel.backends.registry import build_backend_from_dict
from sim_panel.backends import Backend

from sim_panel.data_gen.config import datagen_config_from_dict, DataGenConfig
from sim_panel.data_gen.personas import generate_persona_records_llm
from sim_panel.data_gen.products import generate_beer_product_records_llm
from sim_panel.data_gen.write import write_personas_jsonl, write_products_jsonl

from sim_panel.panelists.enrich import ensure_persona_text, PersonaTextGenSettings
from sim_panel.products.enrich import ensure_display_text, ProductDisplayTextGenSettings
from sim_panel.panelists.io import save_persona_records
from sim_panel.products.io import save_product_records


def run_datagen_from_yaml(path: str, *, disable_enrich_after: bool = False) -> None:
    d = load_yaml(path)
    cfg = datagen_config_from_dict(d)
    run_datagen(cfg, disable_enrich_after=disable_enrich_after)

def run_datagen(cfg: DataGenConfig, *, disable_enrich_after: bool = False) -> None:
    # Build two backend instances so their seeds can differ (if backend supports it).
    backend_personas = _build_backend_with_seed(cfg.backend, cfg.personas.seed)
    backend_products = _build_backend_with_seed(cfg.backend, cfg.products.seed)

    personas = generate_persona_records_llm(
        backend=backend_personas,
        n_personas=cfg.personas.n,
        seed=cfg.personas.seed,
        variant=cfg.personas.persona_text_variant,
        settings=cfg.personas.llm,
        persona_id_prefix=cfg.personas.persona_id_prefix,
    )
    write_personas_jsonl(cfg.output.personas_path, personas)

    if cfg.products.kind != "beer":
        raise ValueError(f"Unsupported products.kind={cfg.products.kind!r} in v0 (only 'beer').")

    products = generate_beer_product_records_llm(
        backend=backend_products,
        n_products=cfg.products.n,
        seed=cfg.products.seed,
        variant=cfg.products.display_variant,
        settings=cfg.products.llm,
        product_id_prefix=cfg.products.product_id_prefix,
    )
    write_products_jsonl(cfg.output.products_path, products)

    # Optional: enrich-after (persisted)
    if (not disable_enrich_after) and cfg.enrich_after.enabled:
        _run_enrich_after(cfg, backend_personas=backend_personas, backend_products=backend_products, personas=personas, products=products)


def _build_backend_with_seed(backend_cfg: Dict[str, Any], seed: int) -> Backend:
    d = dict(backend_cfg)
    d["seed"] = seed
    return build_backend_from_dict(d)


def _run_enrich_after(
    cfg: DataGenConfig,
    *,
    backend_personas: Backend,
    backend_products: Backend,
    personas,
    products,
) -> None:
    # Panelist text enrichment
    p_block = cfg.enrich_after.panelists or {}
    pr_overwrite = bool(p_block.get("overwrite", False))
    pr_save = p_block.get("save", {"path": cfg.output.personas_path})
    pr_save_path = _resolve_save_path(cfg.output.personas_path, pr_save)

    p_settings_raw = p_block.get("settings", {})
    p_settings = PersonaTextGenSettings(
        prompt_version=str(p_settings_raw.get("prompt_version", "v1")),
        temperature=float(p_settings_raw.get("temperature", 0.2)),
        max_tokens=p_settings_raw.get("max_tokens"),
        metadata=p_settings_raw.get("metadata"),
    )

    personas2 = ensure_persona_text(
        personas,
        backend=backend_personas,
        settings=p_settings,
        variant=cfg.personas.persona_text_variant,
        overwrite=pr_overwrite,
    )
    save_persona_records(pr_save_path, personas2)

    # Product display_text enrichment
    prod_block = cfg.enrich_after.products or {}
    pd_overwrite = bool(prod_block.get("overwrite", False))
    pd_save = prod_block.get("save", {"path": cfg.output.products_path})
    pd_save_path = _resolve_save_path(cfg.output.products_path, pd_save)

    prod_settings_raw = prod_block.get("settings", {})
    prod_settings = ProductDisplayTextGenSettings(
        prompt_version=str(prod_settings_raw.get("prompt_version", "v1")),
        temperature=float(prod_settings_raw.get("temperature", 0.2)),
        max_tokens=prod_settings_raw.get("max_tokens"),
        metadata=prod_settings_raw.get("metadata"),
        campaign=prod_settings_raw.get("campaign"),
        tone=str(prod_settings_raw.get("tone", "neutral")),
        length=str(prod_settings_raw.get("length", "short")),
    )

    products2 = ensure_display_text(
        products,
        backend=backend_products,
        settings=prod_settings,
        variant=cfg.products.display_variant,
        overwrite=pd_overwrite,
    )
    save_product_records(pd_save_path, products2)


def _resolve_save_path(source_path: str, save: Any) -> str:
    if save is None:
        return source_path
    if isinstance(save, str):
        if save == "in_place":
            return source_path
        raise ValueError("save must be 'in_place' or a mapping with {path: ...}")
    if isinstance(save, Mapping):
        p = save.get("path")
        if not isinstance(p, str) or not p:
            raise ValueError("save.path must be a non-empty string")
        return p
    raise ValueError("save must be 'in_place' or a mapping with {path: ...}")