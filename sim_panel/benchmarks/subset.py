from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Optional

from sim_panel.benchmarks.config import BenchmarkSubsetConfig
from sim_panel.utils.hashing import sha256_json
from sim_panel.utils.progress import tqdm_wrap


BENCHMARK_CONTRACT_VERSION = "0.1.0"
BENCHMARK_BUILDER_VERSION = "0.1.0"


def build_benchmark_subset(config: BenchmarkSubsetConfig) -> Dict[str, Any]:
    """
    Build a frozen benchmark subset directory from imported real-data artifacts.

    Writes the following files into ``config.output_dir``:
    - events.jsonl
    - products.jsonl
    - metadata.json
    - stats.json

    Design
    ------
    This is a streaming two-pass builder over events.jsonl:
    1. pass 1 counts rating-bearing events per product
    2. pass 2 writes events for the selected products

    This avoids loading the full events table into memory.
    """
    import_dir = Path(config.import_dir)
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    events_path = import_dir / "events.jsonl"
    products_path = import_dir / "products.jsonl"

    if not events_path.exists():
        raise FileNotFoundError(f"Missing import events file: {events_path}")
    if config.require_product_record and not products_path.exists():
        raise FileNotFoundError(
            f"Benchmark subset requires products.jsonl, but it was not found: {products_path}"
        )

    known_product_ids = (
        _load_product_ids(products_path) if products_path.exists() else None
    )

    review_counts = _count_reviews_by_product(
        events_path=events_path,
        known_product_ids=known_product_ids if config.require_product_record else None,
    )

    selected_product_ids = _select_product_ids(
        review_counts=review_counts,
        known_product_ids=known_product_ids,
        config=config,
    )
    selected_product_id_set = set(selected_product_ids)

    exported_products = _write_selected_products(
        products_path=products_path,
        output_path=output_dir / "products.jsonl",
        selected_product_ids=selected_product_id_set,
    )

    export_stats = _write_selected_events(
        events_path=events_path,
        output_path=output_dir / "events.jsonl",
        selected_product_ids=selected_product_id_set,
    )

    stats = {
        "builder_version": BENCHMARK_BUILDER_VERSION,
        "benchmark_contract_version": BENCHMARK_CONTRACT_VERSION,
        "n_selected_products": len(selected_product_ids),
        "n_selected_products_written": exported_products,
        "n_selected_events": export_stats["n_events"],
        "n_unique_panelists": export_stats["n_unique_panelists"],
        "rating_histogram": export_stats["rating_histogram"],
        "selected_product_review_counts": {
            product_id: review_counts[product_id] for product_id in selected_product_ids
        },
        "min_reviews_per_product": config.min_reviews_per_product,
        "max_products": config.max_products,
    }

    metadata = {
        "artifact_type": "benchmark_subset",
        "benchmark_contract_version": BENCHMARK_CONTRACT_VERSION,
        "builder_version": BENCHMARK_BUILDER_VERSION,
        "source_import_dir": str(import_dir.resolve()),
        "source_events_path": str(events_path.resolve()),
        "source_products_path": str(products_path.resolve()) if products_path.exists() else None,
        "selection_unit": "product",
        "selection_basis": "rating_event_count",
        "seed": config.seed,
        "config": asdict(config),
        "config_hash_sha256": sha256_json(asdict(config)),
        "files": {
            "events": "events.jsonl",
            "products": "products.jsonl",
            "metadata": "metadata.json",
            "stats": "stats.json",
        },
    }

    _write_json(output_dir / "metadata.json", metadata)
    _write_json(output_dir / "stats.json", stats)

    return {
        "metadata": metadata,
        "stats": stats,
        "selected_product_ids": selected_product_ids,
    }


def _count_reviews_by_product(
    *,
    events_path: Path,
    known_product_ids: Optional[set[str]],
) -> Dict[str, int]:
    """
    First pass over events.jsonl.

    Count rating-bearing events per product, optionally restricting to products
    known to exist in products.jsonl.
    """
    counts: Counter[str] = Counter()

    for row in tqdm_wrap(
        _iter_jsonl(events_path),
        desc="Count reviews by product",
        enabled=True,
    ):
        product_id = _extract_product_id(row)
        rating = _extract_rating(row)

        if product_id is None or rating is None:
            continue
        if known_product_ids is not None and product_id not in known_product_ids:
            continue

        counts[product_id] += 1

    return dict(counts)


def _select_product_ids(
    *,
    review_counts: Mapping[str, int],
    known_product_ids: Optional[set[str]],
    config: BenchmarkSubsetConfig,
) -> list[str]:
    """
    Select eligible product IDs reproducibly.

    Eligibility:
    - has at least min_reviews_per_product rating-bearing events
    - if require_product_record=True, must also exist in products.jsonl
    """
    eligible = [
        product_id
        for product_id, count in review_counts.items()
        if count >= config.min_reviews_per_product
        and (
            not config.require_product_record
            or known_product_ids is None
            or product_id in known_product_ids
        )
    ]
    eligible.sort()

    rng = random.Random(config.seed)
    rng.shuffle(eligible)

    if config.max_products is None:
        return eligible
    return eligible[: config.max_products]


def _write_selected_events(
    *,
    events_path: Path,
    output_path: Path,
    selected_product_ids: set[str],
) -> Dict[str, Any]:
    """
    Second pass over events.jsonl.

    Stream matching rows directly to events.jsonl and accumulate a few
    lightweight benchmark stats.
    """
    n_events = 0
    panelist_ids: set[str] = set()
    rating_histogram: Counter[str] = Counter()

    with output_path.open("w", encoding="utf-8") as fp:
        for row in tqdm_wrap(
            _iter_jsonl(events_path),
            desc="Write subset events",
            enabled=True,
        ):
            product_id = _extract_product_id(row)
            rating = _extract_rating(row)

            if product_id is None or rating is None:
                continue
            if product_id not in selected_product_ids:
                continue

            fp.write(json.dumps(row, ensure_ascii=False) + "\n")
            n_events += 1

            panelist_id = row.get("panelist_id") or row.get("user_id")
            if panelist_id is not None:
                panelist_ids.add(str(panelist_id))

            rating_histogram[_rating_bucket(rating)] += 1

    return {
        "n_events": n_events,
        "n_unique_panelists": len(panelist_ids),
        "rating_histogram": dict(
            sorted(rating_histogram.items(), key=lambda kv: float(kv[0]))
        ),
    }


def _write_selected_products(
    *,
    products_path: Path,
    output_path: Path,
    selected_product_ids: set[str],
) -> int:
    """
    Stream products.jsonl and keep only products referenced by the selected subset.
    """
    if not products_path.exists():
        output_path.write_text("", encoding="utf-8")
        return 0

    n_products = 0
    with output_path.open("w", encoding="utf-8") as fp:
        for row in tqdm_wrap(
            _iter_jsonl(products_path),
            desc="Write subset products",
            enabled=True,
        ):
            product_id = _extract_product_id(row)
            if product_id is None or product_id not in selected_product_ids:
                continue
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")
            n_products += 1

    return n_products


def _load_product_ids(products_path: Path) -> set[str]:
    """
    Load only product IDs from products.jsonl.

    This is much cheaper than loading all products as full records, and is enough
    for benchmark subset eligibility filtering.
    """
    product_ids: set[str] = set()
    for row in tqdm_wrap(
        _iter_jsonl(products_path),
        desc="Load product ids",
        enabled=True,
    ):
        product_id = _extract_product_id(row)
        if product_id is not None:
            product_ids.add(product_id)
    return product_ids


def _extract_product_id(row: Mapping[str, Any]) -> Optional[str]:
    """
    Extract product ID from either imported real-data rows or imported product rows.

    For Amazon-derived imports this should usually be product_id, with parent_asin
    kept as a fallback for robustness.
    """
    product_id = row.get("product_id") or row.get("parent_asin")
    if product_id is None:
        return None
    return str(product_id)


def _extract_rating(row: Mapping[str, Any]) -> Optional[float]:
    """
    Extract rating from either:
    - top-level rating
    - outcomes.rating
    """
    rating: Any
    outcomes = row.get("outcomes")
    if isinstance(outcomes, Mapping) and "rating" in outcomes:
        rating = outcomes.get("rating")
    else:
        rating = row.get("rating")

    if rating is None:
        return None

    try:
        return float(rating)
    except (TypeError, ValueError):
        return None


def _iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _rating_bucket(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:g}"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2, sort_keys=True)
        fp.write("\n")