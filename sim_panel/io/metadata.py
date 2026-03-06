from __future__ import annotations

import json
from typing import Any, Dict, Optional

from sim_panel.io.atomic import atomic_write_text
from sim_panel.utils.hashing import sha256_json
from sim_panel.utils.time import utc_now_iso


def build_metadata(
    *,
    schema_version: str,
    seed: int,
    n_rows: int,
    n_panelists: Optional[int] = None,
    n_products: Optional[int] = None,
    n_periods: Optional[int] = None,
    policy_name: Optional[str] = None,
    config_snapshot: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a small run metadata JSON payload.

    `config_snapshot` should be the parsed YAML (or a subset) to help reproducibility.
    We store a hash so downstream can quickly compare configs.
    """
    cfg = config_snapshot or {}
    meta: Dict[str, Any] = {
        "generated_at_utc": utc_now_iso(),
        "schema_version": schema_version,
        "seed": seed,
        "counts": {
            "rows": n_rows,
            "panelists": n_panelists,
            "products": n_products,
            "periods": n_periods,
        },
        "policy": policy_name,
        "config_hash_sha256": sha256_json(cfg) if cfg else None,
        "config_snapshot": cfg if cfg else None,
    }
    if extra:
        meta["extra"] = extra
    return meta


def write_metadata_json(path: str, metadata: Dict[str, Any]) -> None:
    text = json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    atomic_write_text(path, text)