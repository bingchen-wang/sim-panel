from __future__ import annotations

import os
from dataclasses import dataclass


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


@dataclass(frozen=True)
class RunFilenames:
    events_jsonl: str = "events.jsonl"
    events_csv: str = "events.csv"
    metadata_json: str = "metadata.json"
    data_dictionary_json: str = "data_dictionary.json"


def default_run_filenames() -> RunFilenames:
    return RunFilenames()