from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from sim_panel.utils.hashing import sha256_json, sha256_text


@dataclass
class PersonaRecord:
    """
    Canonical on-disk persona artifact (JSONL/CSV row).
    Evaluation needs persona_text; attributes are optional.

    Supports:
      - text-only personas (attributes=None)
      - spec-only personas (persona_text=None, attributes present)
      - both
    """
    persona_id: str
    persona_text: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None

    schema_version: str = "0.1.0"
    persona_text_variant: str = "default"

    # Derived IDs for dedupe / caching / provenance tracing.
    spec_key: Optional[str] = None     # hash of attributes (if present)
    text_key: Optional[str] = None     # hash of persona_text (if present)

    provenance: Dict[str, Any] = field(default_factory=dict)

    def compute_keys(self) -> None:
        """
        Compute stable keys from current fields (in-place).
        """
        if self.attributes is not None and self.spec_key is None:
            payload = {
                "schema_version": self.schema_version,
                "persona_id": self.persona_id,
                "attributes": self.attributes,
            }
            self.spec_key = sha256_json(payload)

        if self.persona_text is not None and self.text_key is None:
            self.text_key = sha256_text(self.persona_text)

    def to_dict(self) -> Dict[str, Any]:
        self.compute_keys()
        return {
            "persona_id": self.persona_id,
            "persona_text": self.persona_text,
            "attributes": self.attributes,
            "schema_version": self.schema_version,
            "persona_text_variant": self.persona_text_variant,
            "spec_key": self.spec_key,
            "text_key": self.text_key,
            "provenance": self.provenance,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "PersonaRecord":
        rec = PersonaRecord(
            persona_id=d["persona_id"],
            persona_text=d.get("persona_text"),
            attributes=d.get("attributes"),
            schema_version=d.get("schema_version", "0.1.0"),
            persona_text_variant=d.get("persona_text_variant", "default"),
            spec_key=d.get("spec_key"),
            text_key=d.get("text_key"),
            provenance=d.get("provenance") or {},
        )
        rec.compute_keys()
        return rec