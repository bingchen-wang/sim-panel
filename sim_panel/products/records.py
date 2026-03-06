from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from sim_panel.utils.hashing import sha256_json, sha256_text


@dataclass
class ProductRecord:
    """
    Canonical product/intervention artifact (JSONL row).

    - product_id is internal/stable and should NOT be shown to panelists.
    - display_name is panelist-facing (short).
    - display_text is panelist-facing (longer), optional and can be LLM-enriched.
    - attributes are structured features used for policies/outcomes and for rendering.

    Variants allow multiple display_text realizations (e.g., different campaigns).
    """
    product_id: str
    attributes: Dict[str, Any]

    display_name: Optional[str] = None
    display_text: Optional[str] = None

    schema_version: str = "0.1.0"
    display_variant: str = "default"

    spec_key: Optional[str] = None     # hash of attributes + id + schema_version
    text_key: Optional[str] = None     # hash of display_text (if present)

    meta: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def compute_keys(self) -> None:
        if self.spec_key is None:
            payload = {
                "schema_version": self.schema_version,
                "product_id": self.product_id,
                "attributes": self.attributes,
            }
            self.spec_key = sha256_json(payload)

        if self.display_text is not None and self.text_key is None:
            self.text_key = sha256_text(self.display_text)

    def to_dict(self) -> Dict[str, Any]:
        self.compute_keys()
        return {
            "product_id": self.product_id,
            "attributes": self.attributes,
            "display_name": self.display_name,
            "display_text": self.display_text,
            "schema_version": self.schema_version,
            "display_variant": self.display_variant,
            "spec_key": self.spec_key,
            "text_key": self.text_key,
            "meta": self.meta,
            "provenance": self.provenance,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ProductRecord":
        rec = ProductRecord(
            product_id=d["product_id"],
            attributes=d.get("attributes") or {},
            display_name=d.get("display_name"),
            display_text=d.get("display_text"),
            schema_version=d.get("schema_version", "0.1.0"),
            display_variant=d.get("display_variant", "default"),
            spec_key=d.get("spec_key"),
            text_key=d.get("text_key"),
            meta=d.get("meta") or {},
            provenance=d.get("provenance") or {},
        )
        rec.compute_keys()
        return rec