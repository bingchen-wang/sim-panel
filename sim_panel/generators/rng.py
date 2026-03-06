from __future__ import annotations

import hashlib
from typing import Any, Dict

import numpy as np


def make_rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def stable_event_id(namespace: str, payload: Dict[str, Any]) -> str:
    """
    Deterministic event id from a namespace + canonicalized payload.
    """
    items = []
    for k in sorted(payload.keys()):
        items.append(f"{k}={_stable_repr(payload[k])}")
    msg = (namespace + "|" + "|".join(items)).encode("utf-8")
    return hashlib.blake2b(msg, digest_size=16).hexdigest()


def _stable_repr(x: Any) -> str:
    if x is None:
        return "null"
    if isinstance(x, (str, int, float, bool)):
        return repr(x)
    if isinstance(x, list):
        return "[" + ",".join(_stable_repr(v) for v in x) + "]"
    if isinstance(x, dict):
        return "{" + ",".join(f"{k}:{_stable_repr(x[k])}" for k in sorted(x.keys())) + "}"
    return f"<{type(x).__name__}:{repr(x)}>"