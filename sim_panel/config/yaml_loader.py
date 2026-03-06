from __future__ import annotations

from typing import Any, Dict

import yaml


def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        obj = yaml.safe_load(f)

    if obj is None:
        return {}
    if not isinstance(obj, dict):
        raise ValueError(f"YAML root must be a mapping/dict, got {type(obj).__name__}")
    return obj