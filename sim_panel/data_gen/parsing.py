from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple


def extract_json(text: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    Parse JSON from model output.

    - Fast path: JSON-only
    - Fallback: find outermost {...} or [...] and parse that slice
    """
    if text is None:
        return None, "No text to parse."
    s = text.strip()
    if not s:
        return None, "Empty text."

    try:
        return json.loads(s), None
    except Exception:
        pass

    # Try object slice
    obj, err = _slice_parse(s, "{", "}")
    if err is None:
        return obj, None

    # Try array slice
    arr, err2 = _slice_parse(s, "[", "]")
    if err2 is None:
        return arr, None

    return None, f"JSON parse failed. object_err={err}; array_err={err2}"


def _slice_parse(s: str, l: str, r: str) -> Tuple[Optional[Any], Optional[str]]:
    i = s.find(l)
    j = s.rfind(r)
    if i == -1 or j == -1 or j <= i:
        return None, f"Could not find JSON slice {l}...{r}"
    candidate = s[i : j + 1]
    try:
        return json.loads(candidate), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def safe_excerpt(text: str, max_chars: int = 800) -> str:
    s = (text or "").strip()
    return s if len(s) <= max_chars else s[:max_chars] + "…"