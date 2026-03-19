from __future__ import annotations

from typing import Any, Dict

from sim_panel.sources import build_source
from sim_panel.sources.amazon_reviews_2023 import AmazonReviews2023Config


def build_source_from_yaml_dict(d: Dict[str, Any]):
    """
    Build a source instance from a parsed YAML dictionary.

    Expected shape:
        source:
          name: amazon_reviews_2023
          ...
    """
    source_cfg = d.get("source")
    if not isinstance(source_cfg, dict):
        raise ValueError("YAML must contain a top-level 'source' mapping.")

    name = source_cfg.get("name")
    if name == "amazon_reviews_2023":
        cfg = AmazonReviews2023Config.from_dict(source_cfg)
        return build_source(cfg)

    raise ValueError(f"Unsupported source name: {name!r}")