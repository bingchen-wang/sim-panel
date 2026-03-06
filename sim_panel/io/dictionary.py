from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional

from sim_panel.io.atomic import atomic_write_text
from sim_panel.utils.time import utc_now_iso


def _to_jsonable(obj: Any) -> Any:
    """
    Convert common config/spec dataclasses to JSON-serializable dicts.
    """
    if obj is None:
        return None
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, tuple):
        return [_to_jsonable(x) for x in obj]
    # last resort
    return repr(obj)


def build_data_dictionary(
    *,
    schema_version: str,
    generator_config: Optional[Any] = None,
    policy_config: Optional[Any] = None,
    selection_config: Optional[Any] = None,
    execution_rules: Optional[Any] = None,
    outcome_config: Optional[Any] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a data dictionary / contract artifact for the emitted dataset.

    This is intentionally "wide" rather than perfectly normalized: it exists to help
    downstream users understand what fields exist and how to interpret outcomes/traces.

    We store JSONable versions of the key configs/specs.
    """
    dd: Dict[str, Any] = {
        "generated_at_utc": utc_now_iso(),
        "schema_version": schema_version,
        "components": {
            "generator_config": _to_jsonable(generator_config),
            "policy_config": _to_jsonable(policy_config),
            "selection_config": _to_jsonable(selection_config),
            "execution_rules": _to_jsonable(execution_rules),
            "outcome_config": _to_jsonable(outcome_config),
        },
    }
    if notes:
        dd["notes"] = notes
    return dd


def write_data_dictionary_json(path: str, data_dictionary: Dict[str, Any]) -> None:
    text = json.dumps(data_dictionary, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    atomic_write_text(path, text)