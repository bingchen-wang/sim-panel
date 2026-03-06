from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .records import PersonaRecord
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


def load_persona_records(path: str | Path) -> List[PersonaRecord]:
    return [PersonaRecord.from_dict(r) for r in read_jsonl(path)]


def save_persona_records(path: str | Path, records: Iterable[PersonaRecord]) -> None:
    # stable order for reproducibility (persona_id, then variant)
    recs = sorted(records, key=lambda r: (r.persona_id, r.persona_text_variant))
    write_jsonl_atomic(path, (r.to_dict() for r in recs))


def merge_persona_records(
    base: List[PersonaRecord],
    incoming: List[PersonaRecord],
    *,
    prefer_incoming_attributes: bool = True,
    prefer_incoming_text: bool = True,
) -> List[PersonaRecord]:
    """
    Merge by (persona_id, persona_text_variant). Rewrite-friendly.

    - attributes: prefer incoming by default
    - persona_text: prefer incoming by default
    """
    index: Dict[tuple[str, str], PersonaRecord] = {}
    for r in base:
        index[(r.persona_id, r.persona_text_variant)] = r

    for r in incoming:
        key = (r.persona_id, r.persona_text_variant)
        if key not in index:
            index[key] = r
            continue

        existing = index[key]

        if prefer_incoming_attributes and r.attributes is not None:
            existing.attributes = r.attributes
            existing.spec_key = r.spec_key  # may be None; recomputed on to_dict()

        if prefer_incoming_text and r.persona_text is not None:
            existing.persona_text = r.persona_text
            existing.text_key = r.text_key

        # Merge provenance shallowly (incoming wins)
        if r.provenance:
            existing.provenance = {**existing.provenance, **r.provenance}

    # Ensure keys computed
    out = list(index.values())
    for r in out:
        r.compute_keys()
    return out