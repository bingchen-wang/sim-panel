from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml


@dataclass(frozen=True)
class BenchmarkSubsetConfig:
    """
    Configuration for exporting a benchmark-ready real-data subset.

    Parameters
    ----------
    import_dir
        Directory containing imported source artifacts, expected to include
        at least ``events.jsonl`` and usually ``products.jsonl``.
    output_dir
        Directory to write the frozen benchmark subset.
    seed
        Random seed for reproducible product sampling.
    min_reviews_per_product
        Minimum number of rating-bearing events a product must have to be
        eligible for the subset.
    max_products
        Maximum number of products to keep. If None, keep all eligible products.
    require_product_record
        If True, only keep products that also appear in ``products.jsonl``.
    """

    import_dir: str
    output_dir: str
    seed: int = 0
    min_reviews_per_product: int = 25
    max_products: Optional[int] = 100
    require_product_record: bool = True


def load_benchmark_subset_config(path: str | Path) -> BenchmarkSubsetConfig:
    """
    Load a benchmark subset config from YAML.

    Accepts either:
    - a top-level mapping containing benchmark_subset: {...}
    - or the benchmark_subset fields directly at the top level
    """
    raw = _read_yaml(path)
    section = raw.get("benchmark_subset", raw)

    return BenchmarkSubsetConfig(
        import_dir=_required_str(section, "import_dir"),
        output_dir=_required_str(section, "output_dir"),
        seed=_coerce_int(section.get("seed", 0), field_name="seed"),
        min_reviews_per_product=_coerce_int(
            section.get("min_reviews_per_product", 25),
            field_name="min_reviews_per_product",
        ),
        max_products=_coerce_optional_int(
            section.get("max_products", 100),
            field_name="max_products",
        ),
        require_product_record=_coerce_bool(
            section.get("require_product_record", True),
            field_name="require_product_record",
        ),
    )


def _read_yaml(path: str | Path) -> Mapping[str, Any]:
    yaml_path = Path(path)
    with yaml_path.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    if not isinstance(data, Mapping):
        raise ValueError(f"Expected YAML mapping at {yaml_path}, got: {type(data).__name__}")
    return data


def _required_str(section: Mapping[str, Any], key: str) -> str:
    value = section.get(key)
    if value is None:
        raise ValueError(f"Missing required benchmark subset config field: {key}")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Field {key} must be a non-empty string.")
    return value


def _coerce_int(value: Any, *, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Field {field_name} must be an integer.") from exc


def _coerce_optional_int(value: Any, *, field_name: str) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Field {field_name} must be an integer or null.") from exc


def _coerce_bool(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"Field {field_name} must be a boolean.")