from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from .records import ProductRecord
from sim_panel.io.jsonl import read_jsonl_dicts, write_jsonl_dicts

def read_jsonl(path: str | Path) -> List[Dict]:
    p = Path(path)
    if not p.exists():
        return []
    return read_jsonl_dicts(str(p))

def write_jsonl_atomic(path: str | Path, rows: Iterable[Dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Delegate to shared JSONL writer (atomic write with fsync) for robustness.
    write_jsonl_dicts(str(p), rows)


def load_product_records(path: str | Path) -> List[ProductRecord]:
    return [ProductRecord.from_dict(r) for r in read_jsonl(path)]


def save_product_records(path: str | Path, records: Iterable[ProductRecord]) -> None:
    recs = sorted(records, key=lambda r: (r.product_id, r.display_variant))
    write_jsonl_atomic(path, (r.to_dict() for r in recs))


def merge_product_records(
    base: List[ProductRecord],
    incoming: List[ProductRecord],
    *,
    prefer_incoming_attributes: bool = True,
    prefer_incoming_display: bool = False,
) -> List[ProductRecord]:
    """
    Merge by (product_id, display_variant).

    - attributes: prefer incoming by default
    - display fields: prefer base by default unless prefer_incoming_display=True
    """
    index: Dict[tuple[str, str], ProductRecord] = {}
    for r in base:
        index[(r.product_id, r.display_variant)] = r

    for r in incoming:
        key = (r.product_id, r.display_variant)
        if key not in index:
            index[key] = r
            continue

        existing = index[key]

        if prefer_incoming_attributes:
            existing.attributes = r.attributes or existing.attributes
            existing.spec_key = None  # recompute

        if prefer_incoming_display:
            if r.display_name is not None:
                existing.display_name = r.display_name
            if r.display_text is not None:
                existing.display_text = r.display_text
                existing.text_key = None

        if r.meta:
            existing.meta = {**existing.meta, **r.meta}
        if r.provenance:
            existing.provenance = {**existing.provenance, **r.provenance}

    out = list(index.values())
    for r in out:
        r.compute_keys()
    return out