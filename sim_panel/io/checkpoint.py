from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional


CHECKPOINT_EVENTS = "events.checkpoint.jsonl"
CHECKPOINT_STATE = "checkpoint_state.json"


def config_fingerprint(cfg_snapshot: Dict[str, Any]) -> str:
    """Stable hash of the run config so we can detect config drift on resume."""
    canonical = json.dumps(cfg_snapshot, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# -- state file --

def read_checkpoint_state(checkpoint_dir: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(checkpoint_dir, CHECKPOINT_STATE)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_checkpoint_state(checkpoint_dir: str, state: Dict[str, Any]) -> None:
    path = os.path.join(checkpoint_dir, CHECKPOINT_STATE)
    os.makedirs(checkpoint_dir, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


# -- event rows --

def read_checkpoint_rows(checkpoint_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(checkpoint_dir, CHECKPOINT_EVENTS)
    if not os.path.isfile(path):
        return []
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_checkpoint_rows(checkpoint_dir: str, rows: List[Dict[str, Any]]) -> None:
    """Append rows to the checkpoint JSONL (not atomic — we want incremental appends)."""
    path = os.path.join(checkpoint_dir, CHECKPOINT_EVENTS)
    os.makedirs(checkpoint_dir, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def clear_checkpoint(checkpoint_dir: str) -> None:
    """Remove checkpoint files after successful finalization."""
    for name in (CHECKPOINT_EVENTS, CHECKPOINT_STATE):
        path = os.path.join(checkpoint_dir, name)
        if os.path.isfile(path):
            os.remove(path)
