from __future__ import annotations

import json
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Mapping

from sim_panel.io import ensure_dir, write_data_dictionary_json, write_json_dict, write_metadata_json
from sim_panel.panelists.records import PersonaRecord
from sim_panel.products.records import ProductRecord
from sim_panel.sources.amazon_reviews_2023.config import AmazonReviews2023Config
from sim_panel.sources.amazon_reviews_2023.loader import (
    iter_amazon_metadata_rows,
    iter_amazon_reviews_rows,
)
from sim_panel.sources.amazon_reviews_2023.transform import (
    _build_data_dictionary,
    _build_event_record,
    _build_persona_record,
    _build_product_record,
    _sort_key_for_review,
    _as_timestamp_int,
)
from sim_panel.sources.types import JsonDict, SourceExportBundle, SourceStats
from sim_panel.utils.hashing import sha256_json
from sim_panel.utils.progress import tqdm_wrap
from sim_panel.utils.time import utc_now_iso

AMAZON_PRODUCTS_BUILT_FROM = "metadata_file"
AMAZON_EVENTS_LINKED_BY = "parent_asin"
AMAZON_CHILD_ASIN_RETAINED_IN_TRACES = True


def _write_jsonl_append(path: Path, row: Mapping[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def _stable_shard_id(user_id: str, n_shards: int) -> int:
    digest = sha256_json({"user_id": user_id})
    return int(digest[:8], 16) % n_shards


def _choose_n_shards(config: AmazonReviews2023Config) -> int:
    """
    Heuristic shard count for streaming review processing.

    We keep this simple for v0. The goal is bounded shard size, not perfect tuning.
    """
    if config.max_reviews is not None:
        if config.max_reviews <= 100_000:
            return 8
        if config.max_reviews <= 1_000_000:
            return 32
        return 64
    return 256


def _build_products_and_lookup(
    *,
    config: AmazonReviews2023Config,
    imported_at: str,
    products_path: Path,
) -> tuple[Dict[str, ProductRecord], int]:
    """
    Stream metadata, write products.jsonl incrementally, and retain a compact
    product lookup in memory for event construction.
    """
    product_lookup: Dict[str, ProductRecord] = {}
    n_products = 0

    for row in iter_amazon_metadata_rows(config):
        record = _build_product_record(row, config=config, imported_at=imported_at)
        if record is None:
            continue
        if record.product_id in product_lookup:
            continue

        product_lookup[record.product_id] = record
        _write_jsonl_append(products_path, record.to_dict())
        n_products += 1

    return product_lookup, n_products


def _shard_reviews_by_user(
    *,
    config: AmazonReviews2023Config,
    shard_dir: Path,
    n_shards: int,
) -> int:
    """
    Stream reviews once and shard them to disk by user_id.

    All rows for a given user_id are guaranteed to land in the same shard.
    Rows with missing user_id are routed to shard 0.
    """
    ensure_dir(shard_dir)

    shard_paths = [shard_dir / f"reviews_shard_{idx:04d}.jsonl" for idx in range(n_shards)]
    shard_fps = [path.open("w", encoding="utf-8") for path in shard_paths]

    n_raw_reviews = 0
    try:
        for row in iter_amazon_reviews_rows(config):
            user_id = row.get("user_id")
            if user_id is None:
                shard_id = 0
            else:
                shard_id = _stable_shard_id(str(user_id), n_shards)

            shard_fps[shard_id].write(json.dumps(row, ensure_ascii=False) + "\n")
            n_raw_reviews += 1
    finally:
        for fp in shard_fps:
            fp.close()

    return n_raw_reviews


def _load_jsonl_rows(path: Path) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _t_value_for_raw_timestamp(row: Mapping[str, Any]) -> int:
    ts = _as_timestamp_int(row.get("timestamp"))
    return 0 if ts is None or ts < 0 else ts


def _process_review_shards(
    *,
    config: AmazonReviews2023Config,
    shard_dir: Path,
    n_shards: int,
    imported_at: str,
    product_lookup: Mapping[str, ProductRecord],
    personas_path: Path,
    events_path: Path,
) -> tuple[int, int, int]:
    """
    Process each review shard independently.

    Returns
    -------
    tuple
        (n_personas, n_events, n_reviews_missing_product_metadata)
    """
    known_product_ids = set(product_lookup.keys())

    n_personas = 0
    n_events = 0
    n_reviews_missing_product_metadata = 0

    shard_iter = tqdm_wrap(
        range(n_shards),
        desc="Process review shards",
        enabled=True,
    )

    for shard_idx in shard_iter:
        shard_path = shard_dir / f"reviews_shard_{shard_idx:04d}.jsonl"
        rows = _load_jsonl_rows(shard_path)
        if not rows:
            continue

        by_user: Dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        missing_user_rows: list[Mapping[str, Any]] = []

        for row in rows:
            user_id = row.get("user_id")
            if user_id is None:
                missing_user_rows.append(row)
            else:
                by_user[str(user_id)].append(row)

        persona_lookup: Dict[str, PersonaRecord] = {}
        for panelist_id, user_rows in by_user.items():
            if len(user_rows) < config.min_reviews_per_persona:
                continue
            persona = _build_persona_record(
                panelist_id=panelist_id,
                review_rows=user_rows,
                imported_at=imported_at,
            )
            persona_lookup[panelist_id] = persona
            _write_jsonl_append(personas_path, persona.to_dict())
            n_personas += 1

        if config.time_index_mode == "panelist_sequence":
            for panelist_id, user_rows in by_user.items():
                sorted_rows = sorted(user_rows, key=_sort_key_for_review)
                for t_value, row in enumerate(sorted_rows):
                    event, matched_metadata = _build_event_record(
                        review_row=row,
                        config=config,
                        known_product_ids=known_product_ids,
                        product_lookup=product_lookup,
                        persona_lookup=persona_lookup,
                        t_value=t_value,
                    )
                    if not matched_metadata:
                        n_reviews_missing_product_metadata += 1
                    if event is not None:
                        _write_jsonl_append(events_path, event)
                        n_events += 1

            for row in missing_user_rows:
                event, matched_metadata = _build_event_record(
                    review_row=row,
                    config=config,
                    known_product_ids=known_product_ids,
                    product_lookup=product_lookup,
                    persona_lookup={},
                    t_value=0,
                )
                if not matched_metadata:
                    n_reviews_missing_product_metadata += 1
                if event is not None:
                    _write_jsonl_append(events_path, event)
                    n_events += 1

        elif config.time_index_mode == "raw_timestamp":
            for panelist_id, user_rows in by_user.items():
                for row in user_rows:
                    event, matched_metadata = _build_event_record(
                        review_row=row,
                        config=config,
                        known_product_ids=known_product_ids,
                        product_lookup=product_lookup,
                        persona_lookup=persona_lookup,
                        t_value=_t_value_for_raw_timestamp(row),
                    )
                    if not matched_metadata:
                        n_reviews_missing_product_metadata += 1
                    if event is not None:
                        _write_jsonl_append(events_path, event)
                        n_events += 1

            for row in missing_user_rows:
                event, matched_metadata = _build_event_record(
                    review_row=row,
                    config=config,
                    known_product_ids=known_product_ids,
                    product_lookup=product_lookup,
                    persona_lookup={},
                    t_value=_t_value_for_raw_timestamp(row),
                )
                if not matched_metadata:
                    n_reviews_missing_product_metadata += 1
                if event is not None:
                    _write_jsonl_append(events_path, event)
                    n_events += 1

        else:
            raise ValueError(
                "Streaming mode supports only time_index_mode='panelist_sequence' "
                "or 'raw_timestamp'."
            )

    return n_personas, n_events, n_reviews_missing_product_metadata


def _build_metadata_payload(
    *,
    config: AmazonReviews2023Config,
    imported_at: str,
) -> JsonDict:
    return {
        "source_name": config.name,
        "category": config.category,
        "reviews_path": str(config.reviews_path),
        "metadata_path": str(config.metadata_path),
        "product_id_field": config.product_id_field,
        "products_built_from": AMAZON_PRODUCTS_BUILT_FROM,
        "events_linked_by": AMAZON_EVENTS_LINKED_BY,
        "child_asin_retained_in_traces": AMAZON_CHILD_ASIN_RETAINED_IN_TRACES,
        "trace_field_map": dict(config.trace_field_map),
        "time_index_mode": config.time_index_mode,
        "import_mode": config.import_mode,
        "imported_at": imported_at,
    }


def export_amazon_reviews_2023_streaming(
    *,
    config: AmazonReviews2023Config,
    output_dir: Path,
) -> SourceExportBundle:
    """
    Streaming importer for Amazon Reviews'23.

    Design notes
    ------------
    - products are streamed from metadata and written incrementally
    - reviews are first sharded to disk by user_id
    - each shard is processed independently to derive personas and events
    - events are written incrementally; no full in-memory event list is built
    """
    if config.time_index_mode == "global_sequence":
        raise ValueError(
            "Streaming mode does not support time_index_mode='global_sequence'. "
            "Use 'panelist_sequence' or 'raw_timestamp', or switch to in_memory mode."
        )

    ensure_dir(output_dir)

    events_path = output_dir / "events.jsonl"
    products_path = output_dir / "products.jsonl"
    personas_path = output_dir / "personas.jsonl"

    # Truncate output files if they already exist.
    for path in (events_path, products_path, personas_path):
        path.write_text("", encoding="utf-8")

    imported_at = utc_now_iso()

    print("[import] streaming metadata and writing products...")
    product_lookup, n_products = _build_products_and_lookup(
        config=config,
        imported_at=imported_at,
        products_path=products_path,
    )

    n_shards = _choose_n_shards(config)

    print("[import] sharding reviews by panelist...")
    with tempfile.TemporaryDirectory(prefix="sim_panel_amazon_reviews_") as tmpdir:
        shard_dir = Path(tmpdir) / "review_shards"
        n_raw_reviews = _shard_reviews_by_user(
            config=config,
            shard_dir=shard_dir,
            n_shards=n_shards,
        )

        print("[import] processing review shards into personas and events...")
        n_personas, n_events, n_missing_product_metadata = _process_review_shards(
            config=config,
            shard_dir=shard_dir,
            n_shards=n_shards,
            imported_at=imported_at,
            product_lookup=product_lookup,
            personas_path=personas_path,
            events_path=events_path,
        )

    metadata = _build_metadata_payload(
        config=config,
        imported_at=imported_at,
    )
    data_dictionary = _build_data_dictionary()

    stats = SourceStats(
        n_raw_reviews=n_raw_reviews,
        n_raw_products=n_products,
        n_events=n_events,
        n_products=n_products,
        n_personas=n_personas,
        n_reviews_missing_product_metadata=n_missing_product_metadata,
        extra={
            "trace_field_map": dict(config.trace_field_map),
            "require_metadata_match_for_events": config.require_metadata_match_for_events,
            "time_index_mode": config.time_index_mode,
            "import_mode": config.import_mode,
            "n_review_shards": n_shards,
        },
    )

    write_metadata_json(output_dir / "metadata.json", metadata)
    write_data_dictionary_json(output_dir / "data_dictionary.json", data_dictionary)
    write_json_dict(output_dir / "stats.json", stats.as_dict())

    return SourceExportBundle(
        events=[],
        products=[],
        personas=[],
        metadata=metadata,
        data_dictionary=data_dictionary,
        stats=stats,
    )