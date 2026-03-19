from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from sim_panel.panelists.records import PersonaRecord
from sim_panel.products.records import ProductRecord


JsonDict = Dict[str, Any]


@dataclass(slots=True)
class SourceConfig:
    """
    Generic source-layer configuration.

    Source-specific config classes may subclass this and add extra fields.
    """

    name: str
    output_dir: Optional[Path] = None
    seed: int = 0
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceStats:
    """
    Lightweight summary statistics for a source import run.
    """

    n_raw_reviews: int = 0
    n_raw_products: int = 0
    n_events: int = 0
    n_products: int = 0
    n_personas: int = 0
    n_reviews_missing_product_metadata: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> JsonDict:
        return {
            "n_raw_reviews": self.n_raw_reviews,
            "n_raw_products": self.n_raw_products,
            "n_events": self.n_events,
            "n_products": self.n_products,
            "n_personas": self.n_personas,
            "n_reviews_missing_product_metadata": self.n_reviews_missing_product_metadata,
            "extra": dict(self.extra),
        }


@dataclass(slots=True)
class SourceRawBundle:
    """
    Raw source artifacts loaded from external files, before canonical projection.
    """

    reviews: Sequence[Mapping[str, Any]] = field(default_factory=list)
    products: Sequence[Mapping[str, Any]] = field(default_factory=list)
    aux: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceExportBundle:
    """
    Canonical export payload produced by a source importer.

    Events remain schema-valid row dicts.
    Products and personas are typed on-disk records.
    """

    events: List[JsonDict] = field(default_factory=list)
    products: List[ProductRecord] = field(default_factory=list)
    personas: List[PersonaRecord] = field(default_factory=list)
    metadata: JsonDict = field(default_factory=dict)
    data_dictionary: JsonDict = field(default_factory=dict)
    stats: SourceStats = field(default_factory=SourceStats)

    def is_empty(self) -> bool:
        return not (self.events or self.products or self.personas)

    def as_dict(self) -> JsonDict:
        return {
            "events": self.events,
            "products": [p.to_dict() for p in self.products],
            "personas": [p.to_dict() for p in self.personas],
            "metadata": self.metadata,
            "data_dictionary": self.data_dictionary,
            "stats": self.stats.as_dict(),
        }