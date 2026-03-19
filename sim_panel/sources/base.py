from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from sim_panel.sources.types import SourceConfig, SourceExportBundle, SourceRawBundle


class BaseSource(ABC):
    """
    Abstract base class for external data sources.

    A source is responsible for:
    1. validating its configuration,
    2. loading raw source artifacts,
    3. transforming them into canonical internal records,
    4. exporting materialized bundles when applicable, and
    5. optionally supporting a streaming import/export path.
    """

    name: str

    def __init__(self, config: SourceConfig) -> None:
        self.config = config
        self.validate_config()

    @abstractmethod
    def validate_config(self) -> None:
        """
        Validate the source configuration and raise a helpful error if invalid.
        """
        raise NotImplementedError

    @abstractmethod
    def load_raw(self) -> SourceRawBundle:
        """
        Load raw source artifacts from disk or other local inputs.

        Sources that only support streaming may raise a RuntimeError here.
        """
        raise NotImplementedError

    @abstractmethod
    def transform(self, raw: SourceRawBundle) -> SourceExportBundle:
        """
        Convert raw source artifacts into canonical internal records.

        Sources that only support streaming may raise a RuntimeError here.
        """
        raise NotImplementedError

    @abstractmethod
    def export(
        self,
        bundle: SourceExportBundle,
        output_dir: Path | None = None,
    ) -> None:
        """
        Write a materialized source export bundle to disk.
        """
        raise NotImplementedError

    def run(self) -> SourceExportBundle:
        """
        End-to-end in-memory source import: validate, load, transform.
        """
        raw = self.load_raw()
        return self.transform(raw)

    def export_streaming(self, output_dir: Path | None = None) -> SourceExportBundle:
        """
        Streaming source import/export path.

        Implementations may write artifacts incrementally to disk and return a
        lightweight bundle carrying metadata and stats only.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement streaming import."
        )