from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sim_panel.utils.time import utc_now_iso
from sim_panel.backends import Backend
from sim_panel.backends.types import Message

from .records import ProductRecord


@dataclass(frozen=True)
class ProductDisplayTextGenSettings:
    prompt_version: str = "v1"
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None  # passed to backend.chat(), optional

    # Campaign / experiment customization knobs
    campaign: Optional[str] = None
    tone: str = "neutral"            # e.g., neutral, enthusiastic, clinical
    length: str = "short"            # short|medium|long


def render_product_display_text_prompt(
    record: ProductRecord,
    *,
    prompt_version: str = "v1",
    campaign: Optional[str] = None,
    tone: str = "neutral",
    length: str = "short",
) -> Dict[str, str]:
    """
    Prompt to generate display_text tailored for a campaign/experiment.
    Output must be plain text (no quotes, no preface).
    """
    system = (
        "You write a human-facing product/intervention description that will be shown to a customer-like evaluator.\n"
        "It must be consistent with the structured attributes.\n"
        "Do not mention internal IDs. Do not mention that this is synthetic.\n"
        "Output ONLY the description text."
    )

    name = record.display_name or "Unnamed item"
    attrs = record.attributes

    length_rule = {
        "short": "60-120 words",
        "medium": "120-200 words",
        "long": "200-320 words",
    }.get(length, "60-120 words")

    campaign_line = f"Campaign/experiment context: {campaign}\n" if campaign else ""

    user = (
        f"{campaign_line}"
        f"Display name: {name}\n"
        f"Attributes (JSON): {attrs}\n\n"
        f"Tone: {tone}\n"
        f"Length: {length_rule}\n"
        "Write a clear description that a customer would see."
    )

    return {"system": system, "user": user}


def ensure_display_text(
    records: List[ProductRecord],
    *,
    backend: Backend,
    settings: ProductDisplayTextGenSettings,
    variant: str = "default",
    overwrite: bool = False,
) -> List[ProductRecord]:
    """
    For each record of the given display_variant:
      - if display_text missing (or overwrite=True), generate from attributes (+ display_name)
      - write provenance fields
    """
    out: List[ProductRecord] = []
    for r in records:
        if r.display_variant != variant:
            out.append(r)
            continue

        needs_text = overwrite or (r.display_text is None or not r.display_text.strip())
        if not needs_text:
            out.append(r)
            continue

        prompt = render_product_display_text_prompt(
            r,
            prompt_version=settings.prompt_version,
            campaign=settings.campaign,
            tone=settings.tone,
            length=settings.length,
        )

        messages: List[Message] = [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ]

        res = backend.chat(
            messages,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            metadata=settings.metadata,
        )
        text = res.content.strip()

        r.display_text = text
        r.text_key = None
        r.compute_keys()

        r.provenance = {
            **r.provenance,
            "display_text": {
                "generated_at": utc_now_iso(),
                "prompt_version": settings.prompt_version,
                "campaign": settings.campaign,
                "tone": settings.tone,
                "length": settings.length,
                "temperature": settings.temperature,
                "max_tokens": settings.max_tokens,
                "backend": {"name": backend.config.name, "model": res.model},
                "usage": (
                    {
                        "prompt_tokens": res.usage.prompt_tokens,
                        "completion_tokens": res.usage.completion_tokens,
                        "total_tokens": res.usage.total_tokens,
                    }
                    if backend.config.return_usage
                    else None
                ),
            },
        }

        out.append(r)

    return out