from __future__ import annotations

from typing import List

from .product import Product
from .records import ProductRecord


def build_products(
    records: List[ProductRecord],
    *,
    variant: str = "default",
) -> List[Product]:
    products: List[Product] = []
    for r in records:
        if r.display_variant != variant:
            continue
        products.append(Product(record=r))
    return products