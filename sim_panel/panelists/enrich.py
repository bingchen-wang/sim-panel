from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from sim_panel.utils.time import utc_now_iso
from .records import PersonaRecord
from .render import render_persona_text_prompt


class ChatBackend(Protocol):
    """
    Minimal protocol expected from backends.
    """
    def chat(self, *, system: str, user: str, temperature: float = 0.2) -> str:
        ...


@dataclass(frozen=True)
class PersonaTextGenSettings:
    prompt_version: str = "v1"
    temperature: float = 0.2
    model_name: Optional[str] = None  # optional metadata only


def ensure_persona_text(
    records: List[PersonaRecord],
    *,
    backend: ChatBackend,
    settings: PersonaTextGenSettings,
    variant: str = "default",
    overwrite: bool = False,
) -> List[PersonaRecord]:
    """
    For each record of the given variant:
      - if persona_text missing (or overwrite=True), generate from attributes
      - write provenance fields

    Requires attributes to be present for generation.
    """
    out: List[PersonaRecord] = []
    for r in records:
        if r.persona_text_variant != variant:
            out.append(r)
            continue

        needs_text = overwrite or (r.persona_text is None or not r.persona_text.strip())
        if not needs_text:
            out.append(r)
            continue

        if r.attributes is None:
            raise ValueError(
                f"Cannot generate persona_text for persona_id={r.persona_id}: attributes is None."
            )

        prompt = render_persona_text_prompt(
            r.attributes, prompt_version=settings.prompt_version
        )
        persona_text = backend.chat(
            system=prompt["system"],
            user=prompt["user"],
            temperature=settings.temperature,
        ).strip()

        r.persona_text = persona_text
        r.text_key = None  # recompute
        r.compute_keys()

        r.provenance = {
            **r.provenance,
            "persona_text": {
                "generated_at": utc_now_iso(),
                "prompt_version": settings.prompt_version,
                "temperature": settings.temperature,
                "model_name": settings.model_name,
            },
        }

        out.append(r)

    return out