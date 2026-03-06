from __future__ import annotations

from typing import Any, Dict, List

from sim_panel.backends import Backend
from sim_panel.backends.types import Message
from sim_panel.products.records import ProductRecord

from sim_panel.data_gen.parsing import extract_json, safe_excerpt
from sim_panel.data_gen.settings import LLMGenSettings
from sim_panel.data_gen.prompts.products_beer_v1 import render_beer_products_prompt


def generate_beer_product_records_llm(
    *,
    backend: Backend,
    n_products: int,
    seed: int,
    variant: str = "default",
    settings: LLMGenSettings = LLMGenSettings(),
    schema_version: str = "0.1.0",
    product_id_prefix: str = "prod",
) -> List[ProductRecord]:
    """
    Generate beer ProductRecords using an LLM backend.

    - display_text is left as None (enrich later).
    - display_name + attributes must be present.
    """
    if n_products <= 0:
        return []

    batch_size = max(1, settings.batch_size)
    out: List[ProductRecord] = []
    cursor = 0
    batch_idx = 0

    while cursor < n_products:
        k = min(batch_size, n_products - cursor)
        batch_seed = seed + 10_000 + batch_idx
        payload = _call_products_batch(
            backend=backend,
            n=k,
            seed=batch_seed,
            settings=settings,
        )
        products = _parse_products_payload(payload, k_expected=k)

        for j, item in enumerate(products):
            name = item.get("display_name")
            attrs = item.get("attributes")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Product item missing display_name: {item!r}")
            if not isinstance(attrs, dict):
                raise ValueError(f"Product item missing attributes dict: {item!r}")

            product_id = f"{product_id_prefix}_{cursor + j + 1:04d}"
            rec = ProductRecord(
                product_id=product_id,
                attributes=attrs,
                display_name=name.strip(),
                display_text=None,
                schema_version=schema_version,
                display_variant=variant,
            )
            rec.compute_keys()
            out.append(rec)

        cursor += k
        batch_idx += 1

    return out


def _call_products_batch(*, backend: Backend, n: int, seed: int, settings: LLMGenSettings) -> str:
    prompt = render_beer_products_prompt(n=n)
    md = {} if settings.metadata is None else dict(settings.metadata)
    md.setdefault("module", "data_gen.products_beer")
    md.setdefault("seed", seed)
    md.setdefault("batch_size", n)

    messages: List[Message] = [
        {"role": "system", "content": prompt["system"]},
        {"role": "user", "content": prompt["user"]},
    ]

    last_err: Exception | None = None
    for attempt in range(settings.max_retries + 1):
        try:
            res = backend.chat(
                messages,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
                metadata=md,
            )
            return res.content
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Product batch generation failed after retries: {last_err}")


def _parse_products_payload(raw: str, *, k_expected: int) -> List[Dict[str, Any]]:
    obj, err = extract_json(raw)
    if err is not None or obj is None:
        raise ValueError(f"Failed to parse product JSON: {err}. Excerpt: {safe_excerpt(raw)}")

    if not isinstance(obj, dict) or "products" not in obj:
        raise ValueError("Product JSON must be an object with key 'products'.")

    products = obj["products"]
    if not isinstance(products, list):
        raise ValueError("Product JSON field 'products' must be a list.")

    if len(products) != k_expected:
        raise ValueError(f"Expected {k_expected} products, got {len(products)}.")

    out: List[Dict[str, Any]] = []
    for i, item in enumerate(products):
        if not isinstance(item, dict):
            raise ValueError(f"Product item at index {i} must be object/dict.")
        out.append(item)
    return out