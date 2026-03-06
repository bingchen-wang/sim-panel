from __future__ import annotations

from typing import Any, Dict, List

from sim_panel.backends import Backend
from sim_panel.backends.types import Message
from sim_panel.panelists.records import PersonaRecord

from sim_panel.data_gen.parsing import extract_json, safe_excerpt
from sim_panel.data_gen.settings import LLMGenSettings
from sim_panel.data_gen.prompts.personas_beer_v1 import render_personas_prompt


def generate_persona_records_llm(
    *,
    backend: Backend,
    n_personas: int,
    seed: int,
    variant: str = "default",
    settings: LLMGenSettings = LLMGenSettings(),
    schema_version: str = "0.1.0",
    persona_id_prefix: str = "p",
) -> List[PersonaRecord]:
    """
    Generate spec-only PersonaRecords using an LLM backend.

    - persona_text is left as None (enrich later).
    - attributes must be present.
    """
    if n_personas <= 0:
        return []

    batch_size = max(1, settings.batch_size)
    out: List[PersonaRecord] = []
    cursor = 0
    batch_idx = 0

    while cursor < n_personas:
        k = min(batch_size, n_personas - cursor)
        batch_seed = seed + batch_idx
        payload = _call_personas_batch(
            backend=backend,
            n=k,
            seed=batch_seed,
            settings=settings,
        )
        personas = _parse_personas_payload(payload, k_expected=k)

        for j, item in enumerate(personas):
            attrs = item.get("attributes")
            if not isinstance(attrs, dict):
                raise ValueError(f"Persona item missing attributes dict: {item!r}")

            persona_id = f"{persona_id_prefix}{cursor + j + 1:04d}"
            rec = PersonaRecord(
                persona_id=persona_id,
                persona_text=None,
                attributes=attrs,
                schema_version=schema_version,
                persona_text_variant=variant,
            )
            rec.compute_keys()
            out.append(rec)

        cursor += k
        batch_idx += 1

    return out


def _call_personas_batch(*, backend: Backend, n: int, seed: int, settings: LLMGenSettings) -> str:
    prompt = render_personas_prompt(n=n)
    md = {} if settings.metadata is None else dict(settings.metadata)
    md.setdefault("module", "data_gen.personas")
    md.setdefault("seed", seed)
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
    raise RuntimeError(f"Persona batch generation failed after retries: {last_err}")


def _parse_personas_payload(raw: str, *, k_expected: int) -> List[Dict[str, Any]]:
    obj, err = extract_json(raw)
    if err is not None or obj is None:
        raise ValueError(f"Failed to parse persona JSON: {err}. Excerpt: {safe_excerpt(raw)}")

    if not isinstance(obj, dict) or "personas" not in obj:
        raise ValueError(f"Persona JSON must be an object with key 'personas'. Got: {type(obj).__name__}")

    personas = obj["personas"]
    if not isinstance(personas, list):
        raise ValueError("Persona JSON field 'personas' must be a list.")

    if len(personas) != k_expected:
        # Not fatal, but keep it strict for now.
        raise ValueError(f"Expected {k_expected} personas, got {len(personas)}.")

    out: List[Dict[str, Any]] = []
    for i, item in enumerate(personas):
        if not isinstance(item, dict):
            raise ValueError(f"Persona item at index {i} must be object/dict.")
        out.append(item)
    return out