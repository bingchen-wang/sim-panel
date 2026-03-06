from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from sim_panel.data_gen.settings import LLMGenSettings


@dataclass(frozen=True)
class OutputConfig:
    personas_path: str
    products_path: str


@dataclass(frozen=True)
class PersonasConfig:
    n: int
    seed: int
    persona_text_variant: str = "default"
    persona_id_prefix: str = "p"
    llm: LLMGenSettings = LLMGenSettings()


@dataclass(frozen=True)
class ProductsConfig:
    kind: str = "beer"
    n: int = 0
    seed: int = 0
    display_variant: str = "default"
    product_id_prefix: str = "prod"
    llm: LLMGenSettings = LLMGenSettings()


@dataclass(frozen=True)
class EnrichAfterConfig:
    enabled: bool = False
    panelists: Optional[Dict[str, Any]] = None
    products: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class DataGenConfig:
    backend: Dict[str, Any]
    output: OutputConfig
    personas: PersonasConfig
    products: ProductsConfig
    enrich_after: EnrichAfterConfig = EnrichAfterConfig()


def datagen_config_from_dict(d: Mapping[str, Any]) -> DataGenConfig:
    backend = _require_mapping(d, "backend")
    output = _require_mapping(d, "output")
    personas = _require_mapping(d, "personas")
    products = _require_mapping(d, "products")

    out_cfg = OutputConfig(
        personas_path=_require_str(output, "personas_path"),
        products_path=_require_str(output, "products_path"),
    )

    persona_cfg = PersonasConfig(
        n=_require_int(personas, "n"),
        seed=_require_int(personas, "seed"),
        persona_text_variant=_get_str(personas, "persona_text_variant", "default"),
        persona_id_prefix=_get_str(personas, "persona_id_prefix", "p"),
        llm=_llm_settings_from_dict(_get_mapping(personas, "llm", {})),
    )

    prod_cfg = ProductsConfig(
        kind=_get_str(products, "kind", "beer"),
        n=_require_int(products, "n"),
        seed=_require_int(products, "seed"),
        display_variant=_get_str(products, "display_variant", "default"),
        product_id_prefix=_get_str(products, "product_id_prefix", "prod"),
        llm=_llm_settings_from_dict(_get_mapping(products, "llm", {})),
    )

    enrich_raw = _get_mapping(d, "enrich_after", default={})
    enrich_cfg = EnrichAfterConfig(
        enabled=_get_bool(enrich_raw, "enabled", False),
        panelists=_get_mapping(enrich_raw, "panelists", default=None),
        products=_get_mapping(enrich_raw, "products", default=None),
    )

    return DataGenConfig(
        backend=dict(backend),
        output=out_cfg,
        personas=persona_cfg,
        products=prod_cfg,
        enrich_after=enrich_cfg,
    )


def _llm_settings_from_dict(d: Mapping[str, Any]) -> LLMGenSettings:
    return LLMGenSettings(
        prompt_version=_get_str(d, "prompt_version", "v1"),
        temperature=float(d.get("temperature", 0.2)),
        max_tokens=d.get("max_tokens", 1200),
        metadata=d.get("metadata"),
        batch_size=int(d.get("batch_size", 10)),
        max_retries=int(d.get("max_retries", 2)),
        require_json_only=bool(d.get("require_json_only", True)),
    )


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
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return v.strip()


def _get_str(d: Mapping[str, Any], key: str, default: str) -> str:
    v = d.get(key, default)
    if not isinstance(v, str):
        raise ValueError(f"{key} must be a string")
    return v


def _require_int(d: Mapping[str, Any], key: str) -> int:
    v = d.get(key)
    if not isinstance(v, int):
        raise ValueError(f"{key} must be an int")
    return v


def _get_bool(d: Mapping[str, Any], key: str, default: bool) -> bool:
    if key not in d or d.get(key) is None:
        return default
    v = d.get(key)
    if not isinstance(v, bool):
        raise ValueError(f"{key} must be a bool")
    return v