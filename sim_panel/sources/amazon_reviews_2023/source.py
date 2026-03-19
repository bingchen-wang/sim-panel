from __future__ import annotations

from pathlib import Path

from sim_panel.sources.amazon_reviews_2023.config import AmazonReviews2023Config
from sim_panel.sources.amazon_reviews_2023.export import export_amazon_reviews_2023_bundle
from sim_panel.sources.amazon_reviews_2023.loader import load_amazon_reviews_2023_raw
from sim_panel.sources.amazon_reviews_2023.transform import transform_amazon_reviews_2023
from sim_panel.sources.base import BaseSource
from sim_panel.sources.registry import register_source
from sim_panel.sources.types import SourceExportBundle, SourceRawBundle


class AmazonReviews2023Source(BaseSource):
    """
    Source importer for Amazon Reviews'23.
    """

    name = "amazon_reviews_2023"

    config: AmazonReviews2023Config

    def __init__(self, config: AmazonReviews2023Config) -> None:
        if not isinstance(config, AmazonReviews2023Config):
            raise TypeError(
                "AmazonReviews2023Source requires AmazonReviews2023Config, "
                f"got {type(config).__name__}."
            )
        super().__init__(config)

    def validate_config(self) -> None:
        if self.config.name != self.name:
            raise ValueError(
                f"AmazonReviews2023Source expected config.name='{self.name}', "
                f"got '{self.config.name}'."
            )

        if not self.config.reviews_path:
            raise ValueError("reviews_path must be provided.")
        if not self.config.metadata_path:
            raise ValueError("metadata_path must be provided.")

        if not self.config.reviews_path.exists():
            raise FileNotFoundError(f"Review file not found: {self.config.reviews_path}")
        if not self.config.metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {self.config.metadata_path}")

        if self.config.min_reviews_per_persona < 1:
            raise ValueError("min_reviews_per_persona must be >= 1.")

        if self.config.max_reviews is not None and self.config.max_reviews < 1:
            raise ValueError("max_reviews must be >= 1 when provided.")

        if self.config.max_metadata_rows is not None and self.config.max_metadata_rows < 1:
            raise ValueError("max_metadata_rows must be >= 1 when provided.")

    def load_raw(self) -> SourceRawBundle:
        return load_amazon_reviews_2023_raw(self.config)

    def transform(self, raw: SourceRawBundle) -> SourceExportBundle:
        return transform_amazon_reviews_2023(raw=raw, config=self.config)

    def export(self, bundle: SourceExportBundle, output_dir: Path | None = None) -> None:
        target_dir = output_dir or self.config.output_dir
        if target_dir is None:
            raise ValueError("An output directory must be provided for export.")
        export_amazon_reviews_2023_bundle(bundle=bundle, output_dir=target_dir)


register_source(AmazonReviews2023Source.name, AmazonReviews2023Source)