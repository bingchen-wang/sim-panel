from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from sim_panel.sources.types import SourceConfig


@dataclass(slots=True)
class AmazonReviews2023Config(SourceConfig):
    """
    Configuration for the Amazon Reviews'23 source importer.

    Design choices for v0
    ---------------------
    - products.jsonl is built from the item metadata file
    - product_id is the parent/family identifier: parent_asin
    - events.jsonl may still retain child asin as source provenance
    - all rows in the provided metadata file are exported as products
    - textual review content is mapped into the single event-level `traces` dict
    - `t` is derived from timestamps, defaulting to within-panelist sequence order

    Time index modes
    ----------------
    - panelist_sequence: default and recommended; assigns t = 0, 1, ... within each
      panelist after chronological sorting of that panelist's reviews
    - raw_timestamp: uses the source timestamp directly
    - global_sequence: assigns a corpus-wide chronological sequence; supported in
      in-memory mode but not yet in streaming mode
    """

    reviews_path: Path = Path()
    metadata_path: Path = Path()
    category: Optional[str] = None

    import_mode: Literal["in_memory", "streaming"] = "in_memory"

    require_metadata_match_for_events: bool = False

    trace_field_map: Dict[str, str] = field(
        default_factory=lambda: {
            "title": "review_title",
            "text": "review_text",
        }
    )

    time_index_mode: Literal["panelist_sequence", "global_sequence", "raw_timestamp"] = (
        "panelist_sequence"
    )

    product_description_fallback_to_features: bool = True
    include_raw_product_meta: bool = True
    include_raw_review_meta: bool = True

    min_reviews_per_persona: int = 1
    max_reviews: Optional[int] = None
    max_metadata_rows: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.name:
            self.name = "amazon_reviews_2023"

    @property
    def product_id_field(self) -> str:
        return "parent_asin"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AmazonReviews2023Config":
        payload = dict(data)

        payload["reviews_path"] = Path(payload["reviews_path"])
        payload["metadata_path"] = Path(payload["metadata_path"])

        if "output_dir" in payload and payload["output_dir"] is not None:
            payload["output_dir"] = Path(payload["output_dir"])

        if "trace_field_map" in payload and payload["trace_field_map"] is not None:
            payload["trace_field_map"] = dict(payload["trace_field_map"])

        return cls(**payload)