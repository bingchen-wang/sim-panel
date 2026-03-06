from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple


def extract_json_object(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Extract a JSON object from model output.

    Expected: JSON only. But we defensively attempt to find the first '{' and last '}'.
    Returns (obj, error).
    """
    if text is None:
        return None, "No text to parse."
    s = text.strip()
    if not s:
        return None, "Empty text."

    # Fast path: pure JSON
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj, None
        return None, f"Top-level JSON must be an object/dict, got {type(obj).__name__}."
    except Exception:
        pass

    # Fallback: extract substring between outer braces
    i = s.find("{")
    j = s.rfind("}")
    if i == -1 or j == -1 or j <= i:
        return None, "Could not find JSON object braces in output."

    candidate = s[i : j + 1]
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj, None
        return None, f"Top-level JSON must be an object/dict, got {type(obj).__name__}."
    except Exception as e:
        return None, f"JSON parse error: {type(e).__name__}: {e}"


def safe_excerpt(text: str, max_chars: int = 800) -> str:
    s = (text or "").strip()
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + "…"