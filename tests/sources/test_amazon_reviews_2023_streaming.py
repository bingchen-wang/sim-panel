from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import pytest

from sim_panel.sources.amazon_reviews_2023 import streaming as amazon_streaming
from sim_panel.sources.amazon_reviews_2023.config import AmazonReviews2023Config
from sim_panel.sources.amazon_reviews_2023.source import AmazonReviews2023Source


def _write_jsonl_gz(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _sorted_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda r: (
            r["panelist_id"],
            r["t"],
            r["product_id"],
            r["event_id"],
        ),
    )


def _sorted_products(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: r["product_id"])


def _sorted_personas(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: r["persona_id"])


def _make_config(
    *,
    tmp_path: Path,
    reviews_path: Path,
    metadata_path: Path,
    output_dir_name: str,
    import_mode: str,
    time_index_mode: str = "panelist_sequence",
    min_reviews_per_persona: int = 1,
) -> AmazonReviews2023Config:
    return AmazonReviews2023Config(
        name="amazon_reviews_2023",
        output_dir=tmp_path / output_dir_name,
        reviews_path=reviews_path,
        metadata_path=metadata_path,
        category="test_category",
        import_mode=import_mode,
        require_metadata_match_for_events=False,
        trace_field_map={"title": "review_title", "text": "review_text"},
        time_index_mode=time_index_mode,
        product_description_fallback_to_features=True,
        include_raw_product_meta=True,
        include_raw_review_meta=False,
        min_reviews_per_persona=min_reviews_per_persona,
        max_reviews=None,
        max_metadata_rows=None,
    )


@pytest.fixture
def amazon_small_fixture(tmp_path: Path) -> dict[str, Path]:
    reviews = [
        {
            "user_id": "u2",
            "parent_asin": "p2",
            "asin": "c2a",
            "timestamp": 300,
            "rating": 5,
            "verified_purchase": True,
            "helpful_vote": 2,
            "title": "great",
            "text": "really good",
        },
        {
            "user_id": "u1",
            "parent_asin": "p1",
            "asin": "c1a",
            "timestamp": 200,
            "rating": 4,
            "verified_purchase": False,
            "helpful_vote": 1,
            "title": "nice",
            "text": "pretty nice",
        },
        {
            "user_id": "u1",
            "parent_asin": "p2",
            "asin": "c2b",
            "timestamp": 100,
            "rating": 3,
            "verified_purchase": True,
            "helpful_vote": 0,
            "title": "ok",
            "text": "it was ok",
        },
        {
            "user_id": "u3",
            "parent_asin": "p3",
            "asin": "c3a",
            "timestamp": 250,
            "rating": 2,
            "verified_purchase": False,
            "helpful_vote": 0,
            "title": "bad",
            "text": "not great",
        },
    ]

    metadata = [
        {
            "parent_asin": "p1",
            "title": "Product 1",
            "description": "Desc 1",
            "features": ["F1"],
            "details": {"brand": "A"},
            "store": "Store A",
            "main_category": "Cat",
            "categories": ["Cat", "Sub1"],
            "price": 10.0,
            "average_rating": 4.2,
            "rating_number": 10,
        },
        {
            "parent_asin": "p2",
            "title": "Product 2",
            "description": None,
            "features": ["Feature 2A", "Feature 2B"],
            "details": {"brand": "B"},
            "store": "Store B",
            "main_category": "Cat",
            "categories": ["Cat", "Sub2"],
            "price": 20.0,
            "average_rating": 4.8,
            "rating_number": 20,
        },
        {
            "parent_asin": "p3",
            "title": "Product 3",
            "description": "Desc 3",
            "features": [],
            "details": {"brand": "C"},
            "store": "Store C",
            "main_category": "Cat",
            "categories": ["Cat", "Sub3"],
            "price": 30.0,
            "average_rating": 3.0,
            "rating_number": 5,
        },
    ]

    reviews_path = tmp_path / "reviews.jsonl.gz"
    metadata_path = tmp_path / "metadata.jsonl.gz"
    _write_jsonl_gz(reviews_path, reviews)
    _write_jsonl_gz(metadata_path, metadata)

    return {
        "reviews_path": reviews_path,
        "metadata_path": metadata_path,
    }


def test_streaming_matches_in_memory_panelist_sequence(
    tmp_path: Path,
    amazon_small_fixture: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reviews_path = amazon_small_fixture["reviews_path"]
    metadata_path = amazon_small_fixture["metadata_path"]

    in_memory_cfg = _make_config(
        tmp_path=tmp_path,
        reviews_path=reviews_path,
        metadata_path=metadata_path,
        output_dir_name="in_memory_out",
        import_mode="in_memory",
        time_index_mode="panelist_sequence",
    )
    streaming_cfg = _make_config(
        tmp_path=tmp_path,
        reviews_path=reviews_path,
        metadata_path=metadata_path,
        output_dir_name="streaming_out",
        import_mode="streaming",
        time_index_mode="panelist_sequence",
    )

    in_memory_source = AmazonReviews2023Source(in_memory_cfg)
    raw = in_memory_source.load_raw()
    in_memory_bundle = in_memory_source.transform(raw)

    streaming_source = AmazonReviews2023Source(streaming_cfg)

    monkeypatch.setattr(amazon_streaming, "_choose_n_shards", lambda config: 2)

    streaming_bundle = streaming_source.export_streaming()

    assert streaming_bundle.stats.n_events == in_memory_bundle.stats.n_events
    assert streaming_bundle.stats.n_products == in_memory_bundle.stats.n_products
    assert streaming_bundle.stats.n_personas == in_memory_bundle.stats.n_personas

    streamed_events = _read_jsonl(streaming_cfg.output_dir / "events.jsonl")
    streamed_products = _read_jsonl(streaming_cfg.output_dir / "products.jsonl")
    streamed_personas = _read_jsonl(streaming_cfg.output_dir / "personas.jsonl")

    expected_events = _sorted_events(in_memory_bundle.events)
    expected_products = _sorted_products([p.to_dict() for p in in_memory_bundle.products])
    expected_personas = _sorted_personas([p.to_dict() for p in in_memory_bundle.personas])

    assert _sorted_events(streamed_events) == expected_events
    assert _sorted_products(streamed_products) == expected_products
    assert _sorted_personas(streamed_personas) == expected_personas


def test_streaming_shard_processing_reconstructs_personas_correctly(
    tmp_path: Path,
    amazon_small_fixture: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _make_config(
        tmp_path=tmp_path,
        reviews_path=amazon_small_fixture["reviews_path"],
        metadata_path=amazon_small_fixture["metadata_path"],
        output_dir_name="streaming_out",
        import_mode="streaming",
        time_index_mode="panelist_sequence",
        min_reviews_per_persona=1,
    )
    source = AmazonReviews2023Source(cfg)

    monkeypatch.setattr(amazon_streaming, "_choose_n_shards", lambda config: 2)

    source.export_streaming()

    personas = _sorted_personas(_read_jsonl(cfg.output_dir / "personas.jsonl"))
    by_id = {row["persona_id"]: row for row in personas}

    assert set(by_id) == {"u1", "u2", "u3"}
    assert by_id["u1"]["attributes"]["n_reviews"] == 2
    assert by_id["u1"]["attributes"]["n_unique_products"] == 2
    assert by_id["u1"]["attributes"]["n_verified_purchase_reviews"] == 1
    assert by_id["u1"]["attributes"]["mean_rating"] == pytest.approx(3.5)
    assert by_id["u2"]["attributes"]["n_reviews"] == 1
    assert by_id["u3"]["attributes"]["n_reviews"] == 1


def test_streaming_panelist_sequence_assigns_within_user_t(
    tmp_path: Path,
    amazon_small_fixture: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _make_config(
        tmp_path=tmp_path,
        reviews_path=amazon_small_fixture["reviews_path"],
        metadata_path=amazon_small_fixture["metadata_path"],
        output_dir_name="streaming_out",
        import_mode="streaming",
        time_index_mode="panelist_sequence",
    )
    source = AmazonReviews2023Source(cfg)

    monkeypatch.setattr(amazon_streaming, "_choose_n_shards", lambda config: 2)

    source.export_streaming()

    events = _read_jsonl(cfg.output_dir / "events.jsonl")
    by_user: dict[str, list[dict[str, Any]]] = {}
    for row in events:
        by_user.setdefault(row["panelist_id"], []).append(row)

    for panelist_id, rows in by_user.items():
        rows_sorted = sorted(rows, key=lambda r: r["t"])
        t_values = [row["t"] for row in rows_sorted]
        assert t_values == list(range(len(rows_sorted))), panelist_id

    u1_rows = sorted(by_user["u1"], key=lambda r: r["t"])
    assert [row["product_id"] for row in u1_rows] == ["p2", "p1"]


def test_streaming_rejects_global_sequence(
    tmp_path: Path,
    amazon_small_fixture: dict[str, Path],
) -> None:
    cfg = _make_config(
        tmp_path=tmp_path,
        reviews_path=amazon_small_fixture["reviews_path"],
        metadata_path=amazon_small_fixture["metadata_path"],
        output_dir_name="streaming_out",
        import_mode="streaming",
        time_index_mode="global_sequence",
    )

    with pytest.raises(ValueError, match="global_sequence"):
        AmazonReviews2023Source(cfg)