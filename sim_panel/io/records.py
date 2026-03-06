from __future__ import annotations

from typing import List

from sim_panel.io.jsonl import read_jsonl_dicts, write_jsonl_dicts
from sim_panel.panelists.records import PersonaRecord
from sim_panel.products.records import ProductRecord


def read_persona_records_jsonl(path: str) -> List[PersonaRecord]:
    rows = read_jsonl_dicts(path)
    return [PersonaRecord.from_dict(r) for r in rows]


def read_product_records_jsonl(path: str) -> List[ProductRecord]:
    rows = read_jsonl_dicts(path)
    return [ProductRecord.from_dict(r) for r in rows]


def write_persona_records_jsonl(path: str, records: List[PersonaRecord]) -> None:
    write_jsonl_dicts(path, (r.to_dict() for r in records))


def write_product_records_jsonl(path: str, records: List[ProductRecord]) -> None:
    write_jsonl_dicts(path, (r.to_dict() for r in records))