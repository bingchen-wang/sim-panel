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
    3. transforming them into canonical internal records, and
    4. optionally exporting them to disk.
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
        """
        raise NotImplementedError

    @abstractmethod
    def transform(self, raw: SourceRawBundle) -> SourceExportBundle:
        """
        Convert raw source artifacts into canonical internal records.
        """
        raise NotImplementedError

    def run(self) -> SourceExportBundle:
        """
        End-to-end source import: validate, load, transform.
        """
        raw = self.load_raw()
        return self.transform(raw)
    
    def export_streaming(self, output_dir: Path | None = None) -> None:
        raise NotImplementedError(f"{self.__class__.__name__} does not implement streaming import.")