from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from .records import ProductRecord


def _format_kv(attributes: Dict[str, Any], *, keys: Optional[Iterable[str]] = None) -> str:
    if keys is None:
        keys = sorted(attributes.keys())
    parts = []
    for k in keys:
        v = attributes.get(k)
        parts.append(f"{k}={v}")
    return ", ".join(parts)


def render_product_display(
    product: ProductRecord,
    *,
    include_attributes: bool = True,
    attribute_keys: Optional[list[str]] = None,
) -> str:
    """
    Returns the human-facing product/intervention stimulus.
    Never includes product_id by default.

    Priority:
      1) display_text if present
      2) display_name (+ attributes summary if include_attributes)
      3) attributes summary only
    """
    if product.display_text and product.display_text.strip():
        return product.display_text.strip()

    name = (product.display_name or "").strip()
    attrs = product.attributes or {}

    if include_attributes and attrs:
        kv = _format_kv(attrs, keys=attribute_keys)
        if name:
            return f"{name}\n({kv})"
        return kv

    if name:
        return name

    # last resort
    return "Unnamed item"