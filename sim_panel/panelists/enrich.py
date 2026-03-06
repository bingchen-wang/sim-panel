from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


from sim_panel.utils.time import utc_now_iso
from sim_panel.utils.progress import tqdm_wrap
from sim_panel.backends import Backend
from sim_panel.backends.types import Message

from .records import PersonaRecord
from .render import render_persona_text_prompt


@dataclass(frozen=True)
class PersonaTextGenSettings:
    prompt_version: str = "v1"
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None  # passed to backend.chat(), optional


def ensure_persona_text(
    records: List[PersonaRecord],
    *,
    backend: Backend,
    settings: PersonaTextGenSettings,
    variant: str = "default",
    overwrite: bool = False,
    progress: bool = True,
) -> List[PersonaRecord]:
    """
    For each record of the given variant:
      - if persona_text missing (or overwrite=True), generate from attributes
      - write provenance fields

    Requires attributes to be present for generation.
    """
    out: List[PersonaRecord] = []

    # Best-effort progress info: only meaningful when we will actually generate.
    n_total = 0
    n_to_generate = 0
    for r in records:
        if r.persona_text_variant != variant:
            continue
        n_total += 1
        needs_text = overwrite or (r.persona_text is None or not r.persona_text.strip())
        if needs_text:
            n_to_generate += 1

    desc = f"Enrich personas ({n_to_generate}/{n_total})"

    for r in tqdm_wrap(records, total=len(records), desc=desc, enabled=progress):
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
        persona_text = res.content.strip()

        r.persona_text = persona_text
        r.text_key = None  # recompute
        r.compute_keys()

        r.provenance = {
            **r.provenance,
            "persona_text": {
                "generated_at": utc_now_iso(),
                "prompt_version": settings.prompt_version,
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