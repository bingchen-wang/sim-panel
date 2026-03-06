from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .records import ProductRecord
from .render import render_product_display


@dataclass(frozen=True)
class Product:
    """
    Runtime convenience wrapper.
    """
    record: ProductRecord

    @property
    def product_id(self) -> str:
        return self.record.product_id

    @property
    def display_name(self) -> Optional[str]:
        return self.record.display_name

    @property
    def display_text(self) -> Optional[str]:
        return self.record.display_text

    @property
    def attributes(self) -> Mapping[str, Any]:
        return self.record.attributes

    def display(self) -> str:
        return render_product_display(self.record)