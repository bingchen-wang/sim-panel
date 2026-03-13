from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from sim_panel.io import read_jsonl_dicts


def resolve_personas_path(
    metadata: Dict[str, Any],
    *,
    prefer_extra_paths: bool = True,
) -> Optional[str]:
    extra = metadata.get("extra") or {}
    cfg = metadata.get("config_snapshot") or {}
    panel_cfg = cfg.get("panelists") or {}

    candidates: List[Optional[str]]
    if prefer_extra_paths:
        candidates = [
            extra.get("personas_path"),
            panel_cfg.get("source"),
        ]
    else:
        candidates = [
            panel_cfg.get("source"),
            extra.get("personas_path"),
        ]

    for p in candidates:
        if isinstance(p, str) and p:
            return p
    return None


def resolve_products_path(
    metadata: Dict[str, Any],
    *,
    prefer_extra_paths: bool = True,
) -> Optional[str]:
    extra = metadata.get("extra") or {}
    cfg = metadata.get("config_snapshot") or {}
    prod_cfg = cfg.get("products") or {}

    candidates: List[Optional[str]]
    if prefer_extra_paths:
        candidates = [
            extra.get("products_path"),
            prod_cfg.get("source"),
        ]
    else:
        candidates = [
            prod_cfg.get("source"),
            extra.get("products_path"),
        ]

    for p in candidates:
        if isinstance(p, str) and p:
            return p
    return None


def load_resolved_sources(
    metadata: Dict[str, Any],
    *,
    prefer_extra_paths: bool = True,
    strict: bool = False,
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[List[Dict[str, Any]]]]:
    personas_path = resolve_personas_path(metadata, prefer_extra_paths=prefer_extra_paths)
    products_path = resolve_products_path(metadata, prefer_extra_paths=prefer_extra_paths)

    personas = _load_optional_jsonl(personas_path, strict=strict, label="personas")
    products = _load_optional_jsonl(products_path, strict=strict, label="products")
    return personas, products


def _load_optional_jsonl(
    path: Optional[str],
    *,
    strict: bool,
    label: str,
) -> Optional[List[Dict[str, Any]]]:
    if path is None:
        if strict:
            raise FileNotFoundError(f"Could not resolve {label} path from metadata.")
        return None

    if not os.path.exists(path):
        if strict:
            raise FileNotFoundError(f"Resolved {label} path does not exist: {path}")
        return None

    return read_jsonl_dicts(path)