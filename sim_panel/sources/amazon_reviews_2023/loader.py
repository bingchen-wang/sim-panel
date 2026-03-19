from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, TextIO

from sim_panel.sources.amazon_reviews_2023.config import AmazonReviews2023Config
from sim_panel.sources.types import SourceRawBundle
from sim_panel.utils.progress import tqdm_wrap


def _open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def _iter_jsonl(path: Path) -> Iterator[Mapping[str, Any]]:
    with _open_text(path) as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def load_amazon_reviews_2023_raw(config: AmazonReviews2023Config) -> SourceRawBundle:
    """
    Load raw review rows and raw metadata rows from Amazon Reviews'23.

    This function performs no schema projection. It only ingests source
    artifacts into a generic raw bundle for downstream transformation.
    """
    reviews: list[Mapping[str, Any]] = []
    products: list[Mapping[str, Any]] = []

    review_iter = tqdm_wrap(
        _iter_jsonl(config.reviews_path),
        desc="Load reviews",
        enabled=True,
    )
    for idx, row in enumerate(review_iter):
        reviews.append(row)
        if config.max_reviews is not None and idx + 1 >= config.max_reviews:
            break

    product_iter = tqdm_wrap(
        _iter_jsonl(config.metadata_path),
        desc="Load metadata",
        enabled=True,
    )
    for idx, row in enumerate(product_iter):
        products.append(row)
        if config.max_metadata_rows is not None and idx + 1 >= config.max_metadata_rows:
            break

    aux: Dict[str, Any] = {
        "category": config.category,
        "reviews_path": str(config.reviews_path),
        "metadata_path": str(config.metadata_path),
        "product_id_field": config.product_id_field,
        "trace_field_map": dict(config.trace_field_map),
    }

    return SourceRawBundle(
        reviews=reviews,
        products=products,
        aux=aux,
    )