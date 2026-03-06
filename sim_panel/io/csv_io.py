from __future__ import annotations

import csv
import json
from typing import Any, Dict, Iterable, List, Optional

from sim_panel.io.atomic import atomic_write_text


def _to_cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (str, int, float, bool)):
        return str(v)
    # JSON-serialize nested structures for CSV compatibility
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def write_csv_rows(path: str, rows: Iterable[Dict[str, Any]], *, fieldnames: Optional[List[str]] = None) -> None:
    """
    Write dict rows to CSV. Nested values are JSON-serialized strings.

    Note: CSV is a secondary output format; JSONL is the primary.
    """
    rows_list = list(rows)
    if not rows_list:
        atomic_write_text(path, "")
        return

    if fieldnames is None:
        # Deterministic: union keys then sort
        keys = set()
        for r in rows_list:
            keys.update(r.keys())
        fieldnames = sorted(keys)

    # Use csv module to generate text, then atomic-write.
    from io import StringIO
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in rows_list:
        writer.writerow({k: _to_cell(r.get(k)) for k in fieldnames})
    atomic_write_text(path, buf.getvalue())