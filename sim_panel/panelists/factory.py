from __future__ import annotations

from typing import List, Optional

from sim_panel.backends import Backend

from .panelist import Panelist, EvalSettings, SelectSettings
from .records import PersonaRecord



def build_panelists(
    records: List[PersonaRecord],
    *,
    backend: Optional[Backend] = None,
    variant: str = "default",
    eval_settings: Optional[EvalSettings] = None,
    select_settings: Optional[SelectSettings] = None,
) -> List[Panelist]:
    """
    Build runtime Panelist objects from PersonaRecord rows.

    Parameters
    ----------
    records:
        PersonaRecord list (typically loaded from personas.jsonl).
    backend:
        Optional Backend instance. Required if you intend to call Panelist.evaluate().
    variant:
        Which persona_text_variant to use (default: "default").
    eval_settings:
        YAML-governed default evaluation settings applied to each Panelist.
        If None, Panelist will use its internal defaults.
    select_settings:
        YAML-governed default selection settings applied to each Panelist.
        If None, Panelist will use its internal defaults.
    """
    panelists: List[Panelist] = []
    for r in records:
        if r.persona_text_variant != variant:
            continue
        if r.persona_text is None or not r.persona_text.strip():
            raise ValueError(
                f"persona_text missing for persona_id={r.persona_id} variant={variant}"
            )
        panelists.append(
            Panelist(
                panelist_id=r.persona_id,
                persona_text=r.persona_text,
                attributes=dict(r.attributes) if r.attributes is not None else None,
                backend=backend,
                eval_settings=eval_settings,
                select_settings=select_settings,
            )
        )
    return panelists