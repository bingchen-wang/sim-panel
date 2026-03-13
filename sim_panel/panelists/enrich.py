from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


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
    max_workers: int = 1


def _enrich_one_persona(
    r: PersonaRecord,
    *,
    backend: Backend,
    settings: PersonaTextGenSettings,
) -> Tuple[str, Dict[str, Any]]:
    """Generate persona_text for a single record. Returns (text, provenance_entry)."""
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

    prov = {
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
    }
    return persona_text, prov


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
    # Partition records: those needing generation vs pass-through.
    to_generate: List[Tuple[int, PersonaRecord]] = []
    out: List[Optional[PersonaRecord]] = [None] * len(records)

    for i, r in enumerate(records):
        if r.persona_text_variant != variant:
            out[i] = r
            continue
        needs_text = overwrite or (r.persona_text is None or not r.persona_text.strip())
        if not needs_text:
            out[i] = r
            continue
        to_generate.append((i, r))

    n_total = sum(1 for r in records if r.persona_text_variant == variant)
    desc = f"Enrich personas ({len(to_generate)}/{n_total})"

    use_parallel = settings.max_workers > 1 and len(to_generate) > 1

    if use_parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.max_workers) as pool:
            future_to_idx = {
                pool.submit(
                    _enrich_one_persona, r, backend=backend, settings=settings
                ): (i, r)
                for i, r in to_generate
            }

            for future in tqdm_wrap(
                concurrent.futures.as_completed(future_to_idx),
                total=len(future_to_idx),
                desc=desc,
                enabled=progress,
            ):
                i, r = future_to_idx[future]
                persona_text, prov = future.result()
                r.persona_text = persona_text
                r.text_key = None
                r.compute_keys()
                r.provenance = {**r.provenance, "persona_text": prov}
                out[i] = r
    else:
        for i, r in tqdm_wrap(to_generate, total=len(to_generate), desc=desc, enabled=progress):
            persona_text, prov = _enrich_one_persona(r, backend=backend, settings=settings)
            r.persona_text = persona_text
            r.text_key = None
            r.compute_keys()
            r.provenance = {**r.provenance, "persona_text": prov}
            out[i] = r

    return [r for r in out if r is not None]