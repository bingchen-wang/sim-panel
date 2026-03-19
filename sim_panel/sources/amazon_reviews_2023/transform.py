from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, Mapping, Optional

from sim_panel.panelists.records import PersonaRecord
from sim_panel.products.records import ProductRecord
from sim_panel.sources.amazon_reviews_2023.config import AmazonReviews2023Config
from sim_panel.sources.types import SourceExportBundle, SourceRawBundle, SourceStats
from sim_panel.utils.hashing import sha256_json
from sim_panel.utils.time import utc_now_iso
from sim_panel.utils.progress import tqdm_wrap

JsonDict = Dict[str, Any]


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, list):
        parts = []
        for item in value:
            if item is None:
                continue
            item_text = str(item).strip()
            if item_text:
                parts.append(item_text)
        if not parts:
            return None
        return "\n\n".join(parts)
    text = str(value).strip()
    return text or None


def _clean_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item is not None]
    return [value]


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def _as_timestamp_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def _normalize_product_display_text(
    metadata_row: Mapping[str, Any],
    *,
    fallback_to_features: bool,
) -> Optional[str]:
    description = _clean_text(metadata_row.get("description"))
    if description is not None:
        return description
    if fallback_to_features:
        return _clean_text(metadata_row.get("features"))
    return None


def _build_product_attributes(metadata_row: Mapping[str, Any]) -> JsonDict:
    return {
        "main_category": metadata_row.get("main_category"),
        "store": metadata_row.get("store"),
        "price": _as_float(metadata_row.get("price")),
        "average_rating": _as_float(metadata_row.get("average_rating")),
        "rating_number": _as_int(metadata_row.get("rating_number")),
        "categories": _clean_list(metadata_row.get("categories")),
        "details": metadata_row.get("details") or {},
    }


def _build_product_meta(
    metadata_row: Mapping[str, Any],
    *,
    include_raw_product_meta: bool,
) -> JsonDict:
    meta: JsonDict = {
        "source": "amazon_reviews_2023",
        "source_product_id_field": "parent_asin",
    }

    if include_raw_product_meta:
        meta["raw"] = {
            "parent_asin": metadata_row.get("parent_asin"),
            "title": metadata_row.get("title"),
            "description": metadata_row.get("description"),
            "features": metadata_row.get("features"),
            "details": metadata_row.get("details"),
            "images": metadata_row.get("images"),
            "videos": metadata_row.get("videos"),
            "store": metadata_row.get("store"),
            "categories": metadata_row.get("categories"),
            "main_category": metadata_row.get("main_category"),
            "price": metadata_row.get("price"),
            "average_rating": metadata_row.get("average_rating"),
            "rating_number": metadata_row.get("rating_number"),
            "bought_together": metadata_row.get("bought_together"),
        }

    return meta


def _build_product_record(
    metadata_row: Mapping[str, Any],
    *,
    config: AmazonReviews2023Config,
    imported_at: str,
) -> Optional[ProductRecord]:
    product_id = metadata_row.get("parent_asin")
    if not product_id:
        return None

    product_id = str(product_id)
    attributes = _build_product_attributes(metadata_row)
    display_name = _clean_text(metadata_row.get("title")) or product_id
    display_text = _normalize_product_display_text(
        metadata_row,
        fallback_to_features=config.product_description_fallback_to_features,
    )
    meta = _build_product_meta(
        metadata_row,
        include_raw_product_meta=config.include_raw_product_meta,
    )

    return ProductRecord(
        product_id=product_id,
        attributes=attributes,
        display_name=display_name,
        display_text=display_text,
        schema_version="0.1.0",
        display_variant="default",
        meta=meta,
        provenance={
            "source": "amazon_reviews_2023",
            "source_id": product_id,
            "imported_at": imported_at,
        },
    )


def _build_trace_payload(
    review_row: Mapping[str, Any],
    *,
    trace_field_map: Mapping[str, str],
    include_raw_review_meta: bool,
) -> Optional[JsonDict]:
    traces: JsonDict = {}

    for source_key, trace_key in trace_field_map.items():
        value = _clean_text(review_row.get(source_key))
        if value is not None:
            traces[trace_key] = value

    source_payload: JsonDict = {}
    asin = review_row.get("asin")
    timestamp = review_row.get("timestamp")

    if asin is not None:
        source_payload["child_asin"] = asin
    if timestamp is not None:
        source_payload["timestamp"] = timestamp

    if include_raw_review_meta:
        source_payload["raw"] = {
            "asin": review_row.get("asin"),
            "parent_asin": review_row.get("parent_asin"),
            "title": review_row.get("title"),
            "text": review_row.get("text"),
            "rating": review_row.get("rating"),
            "helpful_vote": review_row.get("helpful_vote"),
            "helpful_votes": review_row.get("helpful_votes"),
            "verified_purchase": review_row.get("verified_purchase"),
            "timestamp": review_row.get("timestamp"),
        }

    if source_payload:
        traces["source"] = source_payload

    return traces or None


def _make_event_id(
    *,
    panelist_id: str,
    product_id: str,
    t: int,
    source_child_asin: Optional[str],
    timestamp: Any,
) -> str:
    payload = {
        "panelist_id": panelist_id,
        "product_id": product_id,
        "t": t,
        "source_child_asin": source_child_asin,
        "timestamp": timestamp,
    }
    return f"evt_{sha256_json(payload)[:16]}"


def _normalize_helpful_vote(review_row: Mapping[str, Any]) -> Any:
    if "helpful_vote" in review_row:
        return review_row.get("helpful_vote")
    if "helpful_votes" in review_row:
        return review_row.get("helpful_votes")
    return None


def _build_event_record(
    review_row: Mapping[str, Any],
    *,
    config: AmazonReviews2023Config,
    known_product_ids: set[str],
    product_lookup: Mapping[str, ProductRecord],
    persona_lookup: Mapping[str, PersonaRecord],
    t_value: int,
) -> tuple[Optional[JsonDict], bool]:
    panelist_id = review_row.get("user_id")
    product_id = review_row.get("parent_asin")

    if not panelist_id or not product_id:
        return None, False

    panelist_id = str(panelist_id)
    product_id = str(product_id)
    matched_metadata = product_id in known_product_ids

    if config.require_metadata_match_for_events and not matched_metadata:
        return None, matched_metadata

    product_record = product_lookup.get(product_id)
    persona_record = persona_lookup.get(panelist_id)

    product_display = ""
    product_features: JsonDict = {}
    if product_record is not None:
        product_display = product_record.display_text or product_record.display_name or ""
        product_features = dict(product_record.attributes or {})

    panelist_features: JsonDict = {}
    if persona_record is not None:
        panelist_features = dict(persona_record.attributes or {})

    trace_payload = _build_trace_payload(
        review_row,
        trace_field_map=config.trace_field_map,
        include_raw_review_meta=config.include_raw_review_meta,
    )

    event: JsonDict = {
        "schema_version": "0.1.0",
        "event_id": _make_event_id(
            panelist_id=panelist_id,
            product_id=product_id,
            t=t_value,
            source_child_asin=review_row.get("asin"),
            timestamp=review_row.get("timestamp"),
        ),
        "event_type": "evaluation",
        "policy": "manual",
        "panelist_id": panelist_id,
        "t": t_value,
        "selection_id": None,
        "product_id": product_id,
        "product_display": product_display,
        "panelist_features": panelist_features,
        "product_features": product_features,
        "outcomes": {
            "rating": review_row.get("rating"),
            "verified_purchase": review_row.get("verified_purchase"),
            "helpful_vote": _normalize_helpful_vote(review_row),
        },
        "traces": trace_payload,
    }

    return event, matched_metadata


def _summarize_persona_rows(review_rows: Iterable[Mapping[str, Any]]) -> JsonDict:
    rows = list(review_rows)
    ratings = [_as_float(row.get("rating")) for row in rows]
    ratings = [x for x in ratings if x is not None]

    verified_count = sum(1 for row in rows if bool(row.get("verified_purchase")))
    unique_parent_asins = {
        str(row.get("parent_asin"))
        for row in rows
        if row.get("parent_asin") is not None
    }

    summary: JsonDict = {
        "n_reviews": len(rows),
        "n_unique_products": len(unique_parent_asins),
        "n_verified_purchase_reviews": verified_count,
    }

    if ratings:
        summary["mean_rating"] = sum(ratings) / len(ratings)

    return summary


def _build_persona_record(
    *,
    panelist_id: str,
    review_rows: Iterable[Mapping[str, Any]],
    imported_at: str,
) -> PersonaRecord:
    attributes = _summarize_persona_rows(review_rows)
    return PersonaRecord(
        persona_id=str(panelist_id),
        persona_text=None,
        attributes=attributes,
        schema_version="0.1.0",
        persona_text_variant="default",
        provenance={
            "source": "amazon_reviews_2023",
            "source_id": str(panelist_id),
            "derived_from": "review_history",
            "imported_at": imported_at,
        },
    )


def _sort_key_for_review(row: Mapping[str, Any]) -> tuple[int, str, str]:
    ts = _as_timestamp_int(row.get("timestamp"))
    ts_key = ts if ts is not None else -1

    asin = "" if row.get("asin") is None else str(row.get("asin"))
    parent_asin = "" if row.get("parent_asin") is None else str(row.get("parent_asin"))
    return (ts_key, parent_asin, asin)


def _build_products(
    raw_products: Iterable[Mapping[str, Any]],
    *,
    config: AmazonReviews2023Config,
    imported_at: str,
) -> list[ProductRecord]:
    product_map: Dict[str, ProductRecord] = {}

    for row in tqdm_wrap(raw_products, desc="Build products", enabled=True):
        record = _build_product_record(row, config=config, imported_at=imported_at)
        if record is None:
            continue
        if record.product_id not in product_map:
            product_map[record.product_id] = record

    return list(product_map.values())


def _iter_reviews_with_t(
    raw_reviews: Iterable[Mapping[str, Any]],
    *,
    time_index_mode: str,
) -> Iterable[tuple[Mapping[str, Any], int]]:
    rows = list(raw_reviews)

    if time_index_mode == "raw_timestamp":
        for row in rows:
            ts = _as_timestamp_int(row.get("timestamp"))
            yield row, 0 if ts is None or ts < 0 else ts
        return

    if time_index_mode == "global_sequence":
        sorted_rows = sorted(rows, key=_sort_key_for_review)
        for idx, row in enumerate(sorted_rows):
            yield row, idx
        return

    if time_index_mode == "panelist_sequence":
        by_user: Dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        missing_user_rows: list[Mapping[str, Any]] = []

        for row in rows:
            user_id = row.get("user_id")
            if user_id is None:
                missing_user_rows.append(row)
            else:
                by_user[str(user_id)].append(row)

        for _, user_rows in by_user.items():
            sorted_rows = sorted(user_rows, key=_sort_key_for_review)
            for idx, row in enumerate(sorted_rows):
                yield row, idx

        for row in missing_user_rows:
            yield row, 0
        return

    raise ValueError(f"Unsupported time_index_mode: {time_index_mode}")


def _build_events(
    raw_reviews: Iterable[Mapping[str, Any]],
    *,
    config: AmazonReviews2023Config,
    known_product_ids: set[str],
    product_lookup: Mapping[str, ProductRecord],
    persona_lookup: Mapping[str, PersonaRecord],
) -> tuple[list[JsonDict], int]:
    events: list[JsonDict] = []
    n_missing_product_metadata = 0

    review_iter = tqdm_wrap(
        _iter_reviews_with_t(
            raw_reviews,
            time_index_mode=config.time_index_mode,
        ),
        desc="Build events",
        enabled=True,
    )

    for row, t_value in review_iter:
        event, matched_metadata = _build_event_record(
            review_row=row,
            config=config,
            known_product_ids=known_product_ids,
            product_lookup=product_lookup,
            persona_lookup=persona_lookup,
            t_value=t_value,
        )
        if not matched_metadata:
            n_missing_product_metadata += 1
        if event is not None:
            events.append(event)

    return events, n_missing_product_metadata


def _build_personas(
    raw_reviews: Iterable[Mapping[str, Any]],
    *,
    min_reviews_per_persona: int,
    imported_at: str,
) -> list[PersonaRecord]:
    by_user: Dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in tqdm_wrap(raw_reviews, desc="Group personas", enabled=True):
        user_id = row.get("user_id")
        if user_id is None:
            continue
        by_user[str(user_id)].append(row)

    personas: list[PersonaRecord] = []
    for panelist_id, rows in tqdm_wrap(
        by_user.items(),
        desc="Build personas",
        enabled=True,
    ):
        if len(rows) < min_reviews_per_persona:
            continue
        personas.append(
            _build_persona_record(
                panelist_id=panelist_id,
                review_rows=rows,
                imported_at=imported_at,
            )
        )

    return personas


def _build_data_dictionary() -> JsonDict:
    return {
        "products": {
            "product_id": "Canonical product identifier built from metadata parent_asin.",
            "display_name": "Human-facing product title from metadata title.",
            "display_text": "Human-facing product text from metadata description, with optional fallback to features.",
            "attributes": "Structured product metadata used for policies, outcomes, and event product_features.",
            "meta": "Source-specific auxiliary metadata and optional raw payload.",
            "provenance": "Source lineage for the imported product record.",
            "spec_key": "Stable hash of schema_version, product_id, and attributes.",
            "text_key": "Stable hash of display_text, when present.",
        },
        "personas": {
            "persona_id": "Canonical persona identifier built from Amazon user_id.",
            "persona_text": "Optional runtime persona prompt; left null for source-derived records.",
            "attributes": "Derived behavioral summaries from review history; copied into event panelist_features.",
            "provenance": "Source lineage for the imported persona record.",
            "spec_key": "Stable hash of schema_version, persona_id, and attributes, when present.",
            "text_key": "Stable hash of persona_text, when present.",
        },
        "events": {
            "event_id": "Deterministic event identifier.",
            "event_type": "Always 'evaluation' for imported review events.",
            "policy": "Set to 'manual' for observational imported events in v0.",
            "panelist_id": "Imported Amazon user_id.",
            "t": "Timestamp-derived integer time index. Default is within-panelist chronological sequence.",
            "product_id": "Canonical product identifier linked by parent_asin.",
            "product_display": "Panelist-facing stimulus text, defaulting to product display_text or display_name.",
            "panelist_features": "Persona attributes copied from the imported PersonaRecord.",
            "product_features": "Product attributes copied from the imported ProductRecord.",
            "outcomes": "Observed review-side outcomes, including rating, verified_purchase, and helpful_vote.",
            "traces": "Mapped review text fields plus optional structured source payload such as child asin.",
        },
    }


def transform_amazon_reviews_2023(
    *,
    raw: SourceRawBundle,
    config: AmazonReviews2023Config,
) -> SourceExportBundle:
    """
    Transform raw Amazon Reviews'23 rows into canonical internal records.

    v0 contract
    -----------
    - products are built from the metadata file and keyed by parent_asin
    - product display_name defaults to metadata title
    - product display_text defaults to metadata description, with optional
      fallback to features
    - products are emitted as ProductRecord objects
    - personas are derived from user review histories and emitted as PersonaRecord objects
    - events are built from review rows and linked to parent_asin
    - event product_display defaults to product display_text or display_name
    - event product_features mirror ProductRecord.attributes
    - event panelist_features mirror PersonaRecord.attributes
    - `t` is derived from source timestamps according to config.time_index_mode
    - child asin is retained under traces['source']
    - review text fields are mapped into the single event-level `traces` dict
      according to `config.trace_field_map`
    """
    imported_at = utc_now_iso()

    products = _build_products(raw.products, config=config, imported_at=imported_at)
    product_lookup = {record.product_id: record for record in products}
    known_product_ids = set(product_lookup.keys())

    personas = _build_personas(
        raw.reviews,
        min_reviews_per_persona=config.min_reviews_per_persona,
        imported_at=imported_at,
    )
    persona_lookup = {record.persona_id: record for record in personas}

    events, n_missing_product_metadata = _build_events(
        raw_reviews=raw.reviews,
        config=config,
        known_product_ids=known_product_ids,
        product_lookup=product_lookup,
        persona_lookup=persona_lookup,
    )

    stats = SourceStats(
        n_raw_reviews=len(raw.reviews),
        n_raw_products=len(raw.products),
        n_events=len(events),
        n_products=len(products),
        n_personas=len(personas),
        n_reviews_missing_product_metadata=n_missing_product_metadata,
        extra={
            "trace_field_map": dict(config.trace_field_map),
            "require_metadata_match_for_events": config.require_metadata_match_for_events,
            "time_index_mode": config.time_index_mode,
        },
    )

    metadata: JsonDict = {
        "source_name": config.name,
        "category": config.category,
        "reviews_path": str(config.reviews_path),
        "metadata_path": str(config.metadata_path),
        "product_id_field": config.product_id_field,
        "products_built_from": "metadata_file",
        "events_linked_by": "parent_asin",
        "child_asin_retained_in_traces": True,
        "trace_field_map": dict(config.trace_field_map),
        "time_index_mode": config.time_index_mode,
        "imported_at": imported_at,
    }

    return SourceExportBundle(
        events=events,
        products=products,
        personas=personas,
        metadata=metadata,
        data_dictionary=_build_data_dictionary(),
        stats=stats,
    )