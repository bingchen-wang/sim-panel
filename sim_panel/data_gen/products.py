from __future__ import annotations

import concurrent.futures
from typing import Any, Dict, List, Optional, Tuple

from sim_panel.data_gen.nonce import make_nonce
from sim_panel.utils.progress import tqdm_wrap
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
    progress: bool = True,
) -> List[ProductRecord]:
    """
    Generate beer ProductRecords using an LLM backend.

    - display_text is left as None (enrich later).
    - display_name + attributes must be present.
    """
    if n_products <= 0:
        return []

    batch_size = max(1, settings.batch_size)
    batch_specs: List[Tuple[int, int, int, int]] = []

    total_batches = (n_products + batch_size - 1) // batch_size
    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        if start >= n_products:
            break
        k = min(batch_size, n_products - start)
        batch_seed = seed + 10_000 + batch_idx
        batch_specs.append((batch_idx, start, k, batch_seed))

    ordered_payloads: List[Optional[str]] = [None] * len(batch_specs)
    use_parallel = settings.max_workers > 1 and len(batch_specs) > 1

    if use_parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.max_workers) as pool:
            future_to_meta = {
                pool.submit(
                    _call_products_batch,
                    backend=backend,
                    n=k,
                    seed=batch_seed,
                    base_seed=seed,
                    batch_idx=batch_idx,
                    settings=settings,
                ): (i, batch_idx)
                for i, (batch_idx, start, k, batch_seed) in enumerate(batch_specs)
            }

            for future in tqdm_wrap(
                concurrent.futures.as_completed(future_to_meta),
                total=len(future_to_meta),
                desc="Generate products",
                enabled=progress,
            ):
                i, batch_idx = future_to_meta[future]
                try:
                    ordered_payloads[i] = future.result()
                except Exception as exc:
                    raise RuntimeError(
                        f"Product batch generation failed at batch_idx={batch_idx}"
                    ) from exc
    else:
        for i, (batch_idx, start, k, batch_seed) in enumerate(
            tqdm_wrap(batch_specs, total=len(batch_specs), desc="Generate products", enabled=progress)
        ):
            ordered_payloads[i] = _call_products_batch(
                backend=backend,
                n=k,
                seed=batch_seed,
                base_seed=seed,
                batch_idx=batch_idx,
                settings=settings,
            )

    out: List[ProductRecord] = []
    for i, (batch_idx, start, k, batch_seed) in enumerate(batch_specs):
        payload = ordered_payloads[i]
        if payload is None:
            raise RuntimeError("Product generation finished with a missing batch payload.")

        products = _parse_products_payload(payload, k_expected=k)

        for j, item in enumerate(products):
            name = item.get("display_name")
            attrs = item.get("attributes")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Product item missing display_name: {item!r}")
            if not isinstance(attrs, dict):
                raise ValueError(f"Product item missing attributes dict: {item!r}")

            product_id = f"{product_id_prefix}_{start + j + 1:04d}"
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

    return out


def _call_products_batch(
    *,
    backend: Backend,
    n: int,
    seed: int,
    base_seed: int,
    batch_idx: int,
    settings: LLMGenSettings,
) -> str:
    # Backward-compatible: nonce is optional and controlled by settings.use_nonce (default False).
    nonce = make_nonce(kind="products_beer", seed=base_seed, batch_idx=batch_idx) if getattr(settings, "use_nonce", False) else None
    prompt = render_beer_products_prompt(n=n, nonce=nonce)

    md = {} if settings.metadata is None else dict(settings.metadata)
    md.setdefault("module", "data_gen.products_beer")
    md.setdefault("seed", seed)
    md.setdefault("base_seed", base_seed)
    md.setdefault("batch_idx", batch_idx)    
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