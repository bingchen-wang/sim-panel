from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ManualSchedule:
    """
    Mapping (panelist_id, t) -> list[product_id].
    """
    by_key: Dict[Tuple[str, int], List[str]]

    def get(self, panelist_id: str, t: int) -> List[str]:
        return list(self.by_key.get((panelist_id, t), []))

    def to_fn(self, *, on_unknown: str = "error"):
        """
        Create a ManualAssignmentFn compatible with PolicyConfig.manual_assignment_fn.
        Filters products to the provided catalog in the policy call (product_ids arg).
        """
        if on_unknown not in {"error", "drop"}:
            raise ValueError("on_unknown must be 'error' or 'drop'")

        def _fn(panelist_id: str, t: int, product_ids: Sequence[str]) -> List[str]:
            requested = self.get(panelist_id, t)
            if not requested:
                return []
            allowed = set(product_ids)
            kept = [p for p in requested if p in allowed]
            if on_unknown == "error":
                unknown = [p for p in requested if p not in allowed]
                if unknown:
                    raise ValueError(
                        f"ManualSchedule contains product_ids not in current catalog: {unknown}"
                    )
            return kept

        return _fn


def load_manual_schedule(
    *,
    path: str,
    format: str,
    panelist_ids: Optional[Sequence[str]] = None,
    product_ids: Optional[Sequence[str]] = None,
    on_unknown: str = "error",
    # csv_long options
    panelist_id_col: str = "panelist_id",
    product_id_col: str = "product_id",
    t_col: str = "t",
    default_t: int = 0,
) -> ManualSchedule:
    """
    Load a manual assignment schedule from disk.

    Parameters
    ----------
    path:
        File path to schedule.
    format:
        One of {"csv_long", "json"}.
    panelist_ids, product_ids:
        Optional allowed ID sets for validation. If provided, we validate during load.
    on_unknown:
        "error" (default) or "drop" unknown ids at load time.
    """
    if on_unknown not in {"error", "drop"}:
        raise ValueError("on_unknown must be 'error' or 'drop'")

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    allowed_panelists = set(panelist_ids) if panelist_ids is not None else None
    allowed_products = set(product_ids) if product_ids is not None else None

    if format == "csv_long":
        by_key = _load_csv_long(
            p,
            panelist_id_col=panelist_id_col,
            product_id_col=product_id_col,
            t_col=t_col,
            default_t=default_t,
            allowed_panelists=allowed_panelists,
            allowed_products=allowed_products,
            on_unknown=on_unknown,
        )
        return ManualSchedule(by_key=by_key)

    if format == "json":
        by_key = _load_json_mapping(
            p,
            allowed_panelists=allowed_panelists,
            allowed_products=allowed_products,
            on_unknown=on_unknown,
        )
        return ManualSchedule(by_key=by_key)

    raise ValueError(f"Unknown manual schedule format: {format!r}. Expected 'csv_long' or 'json'.")


def _load_csv_long(
    path: Path,
    *,
    panelist_id_col: str,
    product_id_col: str,
    t_col: str,
    default_t: int,
    allowed_panelists: Optional[set[str]],
    allowed_products: Optional[set[str]],
    on_unknown: str,
) -> Dict[Tuple[str, int], List[str]]:
    by_key: Dict[Tuple[str, int], List[str]] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{path} appears to have no header row.")
        if panelist_id_col not in reader.fieldnames:
            raise ValueError(f"Missing required column '{panelist_id_col}' in {path}.")
        if product_id_col not in reader.fieldnames:
            raise ValueError(f"Missing required column '{product_id_col}' in {path}.")
        # t_col is optional

        for i, row in enumerate(reader, start=2):  # header is line 1
            pid = (row.get(panelist_id_col) or "").strip()
            prid = (row.get(product_id_col) or "").strip()
            if not pid or not prid:
                raise ValueError(f"Empty {panelist_id_col} or {product_id_col} on line {i} in {path}.")

            t_raw = row.get(t_col)
            if t_raw is None or str(t_raw).strip() == "":
                t = default_t
            else:
                try:
                    t = int(str(t_raw).strip())
                except ValueError as e:
                    raise ValueError(f"Invalid int {t_col}={t_raw!r} on line {i} in {path}.") from e

            if allowed_panelists is not None and pid not in allowed_panelists:
                if on_unknown == "error":
                    raise ValueError(f"Unknown panelist_id={pid!r} on line {i} in {path}.")
                else:
                    continue

            if allowed_products is not None and prid not in allowed_products:
                if on_unknown == "error":
                    raise ValueError(f"Unknown product_id={prid!r} on line {i} in {path}.")
                else:
                    continue

            by_key.setdefault((pid, t), []).append(prid)

    # Deduplicate while preserving order
    for k, v in list(by_key.items()):
        by_key[k] = _dedupe_preserve_order(v)
    return by_key


def _load_json_mapping(
    path: Path,
    *,
    allowed_panelists: Optional[set[str]],
    allowed_products: Optional[set[str]],
    on_unknown: str,
) -> Dict[Tuple[str, int], List[str]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"JSON manual schedule must be an object/dict at top-level: {path}")

    by_key: Dict[Tuple[str, int], List[str]] = {}

    for panelist_id, v in obj.items():
        if not isinstance(panelist_id, str) or not panelist_id.strip():
            raise ValueError(f"Invalid panelist_id key in {path}: {panelist_id!r}")
        pid = panelist_id.strip()

        if allowed_panelists is not None and pid not in allowed_panelists:
            if on_unknown == "error":
                raise ValueError(f"Unknown panelist_id={pid!r} in {path}.")
            else:
                continue

        # Case A: panelist_id -> [product_id,...] (t=0)
        if isinstance(v, list):
            prods = _validate_product_list(v, path=path, allowed_products=allowed_products, on_unknown=on_unknown)
            by_key[(pid, 0)] = prods
            continue

        # Case B: panelist_id -> {t: [product_id,...]}
        if isinstance(v, dict):
            for t_key, prod_list in v.items():
                try:
                    t = int(t_key)
                except Exception as e:
                    raise ValueError(f"Manual schedule JSON has non-int t key {t_key!r} for {pid!r} in {path}.") from e
                if not isinstance(prod_list, list):
                    raise ValueError(f"Manual schedule JSON expects list at {pid}[{t_key}] in {path}.")
                prods = _validate_product_list(prod_list, path=path, allowed_products=allowed_products, on_unknown=on_unknown)
                by_key[(pid, t)] = prods
            continue

        raise ValueError(f"Manual schedule JSON value for panelist_id={pid!r} must be list or dict, got {type(v).__name__}.")

    # Deduplicate while preserving order
    for k, v in list(by_key.items()):
        by_key[k] = _dedupe_preserve_order(v)
    return by_key


def _validate_product_list(
    xs: List[Any],
    *,
    path: Path,
    allowed_products: Optional[set[str]],
    on_unknown: str,
) -> List[str]:
    out: List[str] = []
    for x in xs:
        if not isinstance(x, str) or not x.strip():
            raise ValueError(f"Manual schedule JSON contains invalid product_id value {x!r} in {path}.")
        pid = x.strip()
        if allowed_products is not None and pid not in allowed_products:
            if on_unknown == "error":
                raise ValueError(f"Unknown product_id={pid!r} in {path}.")
            else:
                continue
        out.append(pid)
    return _dedupe_preserve_order(out)


def _dedupe_preserve_order(xs: Sequence[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in xs:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out