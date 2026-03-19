from __future__ import annotations

from pathlib import Path

from sim_panel.io import (
    ensure_dir,
    write_data_dictionary_json,
    write_json_dict,
    write_jsonl_rows,
    write_metadata_json,
    write_persona_records_jsonl,
    write_product_records_jsonl,
)
from sim_panel.sources.types import SourceExportBundle


def export_amazon_reviews_2023_bundle(
    *,
    bundle: SourceExportBundle,
    output_dir: Path,
) -> None:
    """
    Write a transformed Amazon Reviews'23 source bundle to disk.

    Output files
    ------------
    - events.jsonl
    - products.jsonl
    - personas.jsonl
    - metadata.json
    - data_dictionary.json
    - stats.json
    """
    ensure_dir(output_dir)

    write_jsonl_rows(output_dir / "events.jsonl", bundle.events)
    write_product_records_jsonl(output_dir / "products.jsonl", bundle.products)
    write_persona_records_jsonl(output_dir / "personas.jsonl", bundle.personas)

    write_metadata_json(output_dir / "metadata.json", bundle.metadata)
    write_data_dictionary_json(output_dir / "data_dictionary.json", bundle.data_dictionary)
    write_json_dict(output_dir / "stats.json", bundle.stats.as_dict())