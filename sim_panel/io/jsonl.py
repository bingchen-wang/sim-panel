from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Iterator, List, Optional

from sim_panel.io.atomic import atomic_write_text


def read_jsonl_dicts(path: str) -> List[Dict[str, Any]]:
    """
    Read a JSONL file into a list of dicts.
    """
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {i} in {path}: {e}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"Expected JSON object on line {i} in {path}, got {type(obj).__name__}")
            out.append(obj)
    return out


def write_jsonl_dicts(path: str, rows: Iterable[Dict[str, Any]]) -> None:
    """
    Write an iterable of dicts to JSONL (atomic write).
    """
    lines: List[str] = []
    for row in rows:
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
    text = "\n".join(lines) + ("\n" if lines else "")
    atomic_write_text(path, text)


def write_jsonl_rows(path: str, rows: Iterable[Dict[str, Any]]) -> None:
    """
    Alias for write_jsonl_dicts; kept for semantic clarity.
    """
    write_jsonl_dicts(path, rows)