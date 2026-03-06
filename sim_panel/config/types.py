from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sim_panel.generators.pipeline import EventGenerator
from sim_panel.generators.types import GeneratorConfig
from sim_panel.panelists.panelist import Panelist
from sim_panel.products.product import Product


@dataclass(frozen=True)
class RunConfig:
    """
    Normalized run configuration extracted from YAML.
    Note: YAML is the source of truth; this is a convenience snapshot.
    """
    generator: GeneratorConfig

    personas_path: str
    products_path: str
    persona_variant: str = "default"
    product_variant: str = "default"

    # Optional; CLI can override
    output_dir: Optional[str] = None


@dataclass(frozen=True)
class RunBundle:
    """
    Fully built, ready-to-run bundle.
    """
    generator: EventGenerator
    panelists: List[Panelist]
    products: List[Product]
    config_snapshot: Dict[str, Any]
    run_config: RunConfig