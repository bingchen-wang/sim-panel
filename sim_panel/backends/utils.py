from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .types import Message


def normalize_messages(messages: Sequence[Message]) -> list[dict[str, Any]]:
    """
    Ensure messages are plain dicts with stable key ordering (for hashing/determinism).
    """
    out: list[dict[str, Any]] = []
    for m in messages:
        out.append(
            {
                "role": m.get("role"),
                "content": m.get("content", ""),
                **({"name": m["name"]} if "name" in m else {}),
                **({"tool_call_id": m["tool_call_id"]} if "tool_call_id" in m else {}),
            }
        )
    return out


def stable_hash(payload: Mapping[str, Any]) -> str:
    """
    Stable SHA256 over JSON canonical form.
    """
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()