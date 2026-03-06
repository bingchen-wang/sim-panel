from __future__ import annotations

from typing import Any, Dict, Optional


def render_persona_text_prompt(
    attributes: Dict[str, Any],
    *,
    prompt_version: str = "v1",
    style: str = "concise",
) -> Dict[str, str]:
    """
    Returns a {system, user} prompt pair for generating persona_text.

    The backend call should use:
      - system: instructions for the persona-writer
      - user: the structured attributes + formatting constraints
    """
    system = (
        "You write a descriptive persona to be used as a SYSTEM PROMPT for an LLM agent.\n"
        "The persona must be consistent with the provided structured attributes, provided in Attributes (JSON).\n"
        "Ensure the description is coherent and stays true to the attributes.\n"
        "Output ONLY the persona text, with no preface, disclaimers, or quotes."
    )

    if prompt_version != "v1":
        # Later can branch by prompt_version.
        pass

    user = (
        f"Attributes (JSON): {attributes}\n\n"
    )

    return {"system": system, "user": user}