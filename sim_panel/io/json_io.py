from __future__ import annotations

import json
from typing import Any, Dict

from sim_panel.io.atomic import atomic_write_text


def write_json_dict(path: str, payload: Dict[str, Any]) -> None:
    """
    Write a JSON dictionary atomically with stable formatting.
    """
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    atomic_write_text(path, text)