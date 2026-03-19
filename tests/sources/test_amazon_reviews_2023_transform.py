from __future__ import annotations

from pathlib import Path

from sim_panel.panelists.records import PersonaRecord
from sim_panel.products.records import ProductRecord
from sim_panel.sources.amazon_reviews_2023.config import AmazonReviews2023Config
from sim_panel.sources.amazon_reviews_2023.transform import transform_amazon_reviews_2023
from sim_panel.sources.types import SourceRawBundle
from sim_panel.schema.versions.v0_1_0 import EventV0_1_0


def _make_config(**overrides) -> AmazonReviews2023Config:
    base = dict(
        name="amazon_reviews_2023",
        reviews_path=Path("dummy_reviews.jsonl"),
        metadata_path=Path("dummy_meta.jsonl"),
        category="Grocery_and_Gourmet_Food",
        require_metadata_match_for_events=False,
        trace_field_map={"title": "review_title", "text": "review_text"},
        time_index_mode="panelist_sequence",
        product_description_fallback_to_features=True,
        include_raw_product_meta=True,
        include_raw_review_meta=False,
        min_reviews_per_persona=1,
    )
    base.update(overrides)
    return AmazonReviews2023Config(**base)


def test_transform_builds_typed_product_and_persona_records() -> None:
    raw = SourceRawBundle(
        reviews=[
            {
                "user_id": "u1",
                "parent_asin": "p1",
                "asin": "c1",
                "title": "Nice",
                "text": "Very good.",
                "rating": 5,
                "verified_purchase": True,
                "helpful_vote": 3,
                "timestamp": 100,
            }
        ],
        products=[
            {
                "parent_asin": "p1",
                "title": "Coffee Beans",
                "description": "Rich and smooth medium roast.",
                "features": ["Whole bean", "12 oz"],
                "main_category": "Grocery",
                "store": "Acme",
                "price": 12.99,
                "average_rating": 4.7,
                "rating_number": 123,
                "categories": ["Coffee", "Beans"],
                "details": {"Roast": "Medium"},
            }
        ],
    )

    bundle = transform_amazon_reviews_2023(raw=raw, config=_make_config())

    assert len(bundle.products) == 1
    assert len(bundle.personas) == 1

    assert isinstance(bundle.products[0], ProductRecord)
    assert isinstance(bundle.personas[0], PersonaRecord)

    product = bundle.products[0]
    persona = bundle.personas[0]

    assert product.product_id == "p1"
    assert product.display_name == "Coffee Beans"
    assert product.display_text == "Rich and smooth medium roast."

    assert persona.persona_id == "u1"
    assert persona.attributes is not None
    assert persona.attributes["n_reviews"] == 1


def test_product_display_text_falls_back_to_features() -> None:
    raw = SourceRawBundle(
        reviews=[],
        products=[
            {
                "parent_asin": "p1",
                "title": "Protein Bar",
                "description": None,
                "features": ["High protein", "Chocolate flavor"],
                "main_category": "Grocery",
                "store": "Acme",
                "price": 2.5,
                "average_rating": 4.1,
                "rating_number": 10,
                "categories": ["Snacks"],
                "details": {},
            }
        ],
    )

    bundle = transform_amazon_reviews_2023(raw=raw, config=_make_config())
    product = bundle.products[0]

    assert product.display_name == "Protein Bar"
    assert product.display_text == "High protein\n\nChocolate flavor"


def test_duplicate_metadata_rows_deduplicate_on_parent_asin() -> None:
    raw = SourceRawBundle(
        reviews=[],
        products=[
            {
                "parent_asin": "p1",
                "title": "Item A",
                "description": "First row",
                "features": ["A1"],
            },
            {
                "parent_asin": "p1",
                "title": "Item A duplicate",
                "description": "Second row should be ignored",
                "features": ["A2"],
            },
        ],
    )

    bundle = transform_amazon_reviews_2023(raw=raw, config=_make_config())

    assert len(bundle.products) == 1
    assert bundle.products[0].product_id == "p1"
    assert bundle.products[0].display_text == "First row"


def test_event_copies_panelist_and_product_features_and_trace_mapping() -> None:
    raw = SourceRawBundle(
        reviews=[
            {
                "user_id": "u1",
                "parent_asin": "p1",
                "asin": "child-1",
                "title": "Loved it",
                "text": "Tasty and fresh.",
                "rating": 4,
                "verified_purchase": True,
                "helpful_vote": 7,
                "timestamp": 101,
            }
        ],
        products=[
            {
                "parent_asin": "p1",
                "title": "Granola",
                "description": "Crunchy granola with honey.",
                "features": ["Crunchy", "Honey"],
                "main_category": "Grocery",
                "store": "Acme",
                "price": 6.5,
                "average_rating": 4.3,
                "rating_number": 21,
                "categories": ["Breakfast"],
                "details": {"Flavor": "Honey"},
            }
        ],
    )

    bundle = transform_amazon_reviews_2023(raw=raw, config=_make_config())
    event = bundle.events[0]

    persona = bundle.personas[0]
    product = bundle.products[0]

    assert event["panelist_features"] == persona.attributes
    assert event["product_features"] == product.attributes
    assert event["product_display"] == product.display_text

    assert event["traces"]["review_title"] == "Loved it"
    assert event["traces"]["review_text"] == "Tasty and fresh."
    assert event["traces"]["source"]["child_asin"] == "child-1"
    assert event["outcomes"]["rating"] == 4
    assert event["outcomes"]["verified_purchase"] is True
    assert event["outcomes"]["helpful_vote"] == 7


def test_panelist_sequence_time_index_is_assigned_within_user() -> None:
    raw = SourceRawBundle(
        reviews=[
            {
                "user_id": "u1",
                "parent_asin": "p1",
                "asin": "c1",
                "title": "Second",
                "text": "Later review",
                "rating": 5,
                "verified_purchase": True,
                "helpful_vote": 1,
                "timestamp": 200,
            },
            {
                "user_id": "u1",
                "parent_asin": "p2",
                "asin": "c2",
                "title": "First",
                "text": "Earlier review",
                "rating": 3,
                "verified_purchase": False,
                "helpful_vote": 0,
                "timestamp": 100,
            },
            {
                "user_id": "u2",
                "parent_asin": "p1",
                "asin": "c3",
                "title": "Other user",
                "text": "Another review",
                "rating": 4,
                "verified_purchase": True,
                "helpful_vote": 2,
                "timestamp": 150,
            },
        ],
        products=[
            {"parent_asin": "p1", "title": "Item 1", "description": "Desc 1"},
            {"parent_asin": "p2", "title": "Item 2", "description": "Desc 2"},
        ],
    )

    bundle = transform_amazon_reviews_2023(raw=raw, config=_make_config())
    events = bundle.events

    u1_events = [e for e in events if e["panelist_id"] == "u1"]
    u2_events = [e for e in events if e["panelist_id"] == "u2"]

    assert len(u1_events) == 2
    assert sorted(e["t"] for e in u1_events) == [0, 1]
    assert u2_events[0]["t"] == 0

    earlier_u1 = next(e for e in u1_events if e["product_id"] == "p2")
    later_u1 = next(e for e in u1_events if e["product_id"] == "p1")

    assert earlier_u1["t"] == 0
    assert later_u1["t"] == 1


def test_require_metadata_match_for_events_drops_unmatched_events() -> None:
    raw = SourceRawBundle(
        reviews=[
            {
                "user_id": "u1",
                "parent_asin": "p_missing",
                "asin": "c1",
                "title": "Unmatched",
                "text": "No metadata row",
                "rating": 2,
                "verified_purchase": False,
                "helpful_vote": 0,
                "timestamp": 100,
            }
        ],
        products=[
            {
                "parent_asin": "p1",
                "title": "Item 1",
                "description": "Desc 1",
            }
        ],
    )

    bundle = transform_amazon_reviews_2023(
        raw=raw,
        config=_make_config(require_metadata_match_for_events=True),
    )

    assert len(bundle.events) == 0
    assert bundle.stats.n_reviews_missing_product_metadata == 1


def test_min_reviews_per_persona_threshold_is_respected() -> None:
    raw = SourceRawBundle(
        reviews=[
            {
                "user_id": "u1",
                "parent_asin": "p1",
                "asin": "c1",
                "title": "Only review",
                "text": "Single review",
                "rating": 4,
                "verified_purchase": True,
                "helpful_vote": 1,
                "timestamp": 100,
            }
        ],
        products=[
            {
                "parent_asin": "p1",
                "title": "Item 1",
                "description": "Desc 1",
            }
        ],
    )

    bundle = transform_amazon_reviews_2023(
        raw=raw,
        config=_make_config(min_reviews_per_persona=2),
    )

    assert len(bundle.personas) == 0
    assert len(bundle.events) == 1
    assert bundle.events[0]["panelist_features"] == {}


def test_event_rows_validate_against_v0_1_0_schema() -> None:
    raw = SourceRawBundle(
        reviews=[
            {
                "user_id": "u1",
                "parent_asin": "p1",
                "asin": "c1",
                "title": "Good",
                "text": "Works well",
                "rating": 5,
                "verified_purchase": True,
                "helpful_vote": 2,
                "timestamp": 100,
            }
        ],
        products=[
            {
                "parent_asin": "p1",
                "title": "Item 1",
                "description": "Desc 1",
                "main_category": "Grocery",
                "store": "Acme",
                "price": 9.9,
                "average_rating": 4.8,
                "rating_number": 30,
                "categories": ["Cat"],
                "details": {},
            }
        ],
    )

    bundle = transform_amazon_reviews_2023(raw=raw, config=_make_config())

    assert len(bundle.events) == 1
    validated = EventV0_1_0(**bundle.events[0])

    assert validated.event_type == "evaluation"
    assert validated.policy == "manual"
    assert validated.product_id == "p1"
    assert validated.product_display == "Desc 1"