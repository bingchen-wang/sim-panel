from __future__ import annotations

from typing import Iterable, List

from sim_panel.panelists.records import PersonaRecord
from sim_panel.products.records import ProductRecord
from sim_panel.panelists.io import save_persona_records
from sim_panel.products.io import save_product_records


def write_personas_jsonl(path: str, records: Iterable[PersonaRecord]) -> None:
    save_persona_records(path, records)


def write_products_jsonl(path: str, records: Iterable[ProductRecord]) -> None:
    save_product_records(path, records)