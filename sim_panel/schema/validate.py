from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import ValidationError

from sim_panel.schema.registry import get_schema


@dataclass(frozen=True)
class RowError:
    index: int
    message: str


@dataclass(frozen=True)
class ValidationReport:
    schema_version: str
    n_rows: int
    n_valid: int
    n_invalid: int
    errors: List[RowError]
    warnings: List[str]

    @property
    def ok(self) -> bool:
        return self.n_invalid == 0


def validate_rows(
    rows: Iterable[Dict[str, Any]],
    schema_version: Optional[str] = None,
    *,
    max_errors: int = 50,
) -> ValidationReport:
    """
    Validate rows against a specific schema version.

    If schema_version is None, attempt to read it from each row's "schema_version".
    In that mode, rows with missing/unknown schema_version are marked invalid.
    """
    errors: List[RowError] = []
    warnings: List[str] = []

    n_rows = 0
    n_valid = 0

    for i, row in enumerate(rows):
        n_rows += 1

        row_version = schema_version or row.get("schema_version")
        if not isinstance(row_version, str) or not row_version:
            if len(errors) < max_errors:
                errors.append(RowError(index=i, message="Missing/invalid 'schema_version' in row."))
            continue

        try:
            spec = get_schema(row_version)
        except ValueError as e:
            if len(errors) < max_errors:
                errors.append(RowError(index=i, message=str(e)))
            continue

        try:
            spec.model.model_validate(row)
            n_valid += 1
        except ValidationError as e:
            if len(errors) < max_errors:
                errors.append(RowError(index=i, message=str(e)))

    # If caller pinned schema_version, warn if any rows disagree (when row contains a value)
    if schema_version is not None:
        # This is best-effort because rows is an iterable that may be consumed already.
        # We can't reliably re-scan without materializing, so we only warn generally here.
        warnings.append(
            "validate_rows(schema_version=...) does not check per-row schema_version mismatches unless the caller "
            "pre-checks or provides rows as a re-iterable."
        )

    return ValidationReport(
        schema_version=schema_version or "per-row",
        n_rows=n_rows,
        n_valid=n_valid,
        n_invalid=n_rows - n_valid,
        errors=errors,
        warnings=warnings,
    )


def validate_unique_event_id(rows: Iterable[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    seen = set()
    for i, row in enumerate(rows):
        eid = row.get("event_id")
        if eid in seen:
            return False, f"Duplicate event_id at row {i}: {eid!r}"
        seen.add(eid)
    return True, None


def validate_self_selection_links(rows: Iterable[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    Cross-row validation for v0.1.0 self-selection linkage rules:

    - Every selection row (event_type == "selection") defines a (panelist_id, t) -> event_id mapping.
    - Every self_selection evaluation row must have selection_id that references an existing selection event_id.
    - Additionally, selection_id should match the same (panelist_id, t) as the evaluation row (sanity).

    Returns (ok, problems).
    """
    problems: List[str] = []

    selection_by_event_id: Dict[str, Tuple[str, int]] = {}
    selection_by_key: Dict[Tuple[str, int], str] = {}

    # First pass: collect selection rows
    for i, row in enumerate(rows):
        if row.get("event_type") != "selection":
            continue
        eid = row.get("event_id")
        pid = row.get("panelist_id")
        t = row.get("t")
        if not isinstance(eid, str) or not isinstance(pid, str) or not isinstance(t, int):
            problems.append(f"Row {i}: malformed selection row identifiers (event_id/panelist_id/t).")
            continue

        selection_by_event_id[eid] = (pid, t)
        key = (pid, t)
        if key in selection_by_key and selection_by_key[key] != eid:
            problems.append(
                f"Multiple selection rows for same (panelist_id, t)={key}: "
                f"{selection_by_key[key]!r} and {eid!r}."
            )
        else:
            selection_by_key[key] = eid

    # Second pass: check evaluation rows
    for i, row in enumerate(rows):
        if row.get("event_type") != "evaluation":
            continue
        if row.get("policy") != "self_selection":
            continue

        sel_id = row.get("selection_id")
        if not isinstance(sel_id, str) or not sel_id:
            problems.append(f"Row {i}: self_selection evaluation missing/invalid selection_id.")
            continue

        if sel_id not in selection_by_event_id:
            problems.append(f"Row {i}: selection_id {sel_id!r} not found among selection event_ids.")
            continue

        pid = row.get("panelist_id")
        t = row.get("t")
        if not isinstance(pid, str) or not isinstance(t, int):
            problems.append(f"Row {i}: malformed evaluation row identifiers (panelist_id/t).")
            continue

        sel_pid, sel_t = selection_by_event_id[sel_id]
        if (pid, t) != (sel_pid, sel_t):
            problems.append(
                f"Row {i}: selection_id {sel_id!r} points to (panelist_id,t)=({sel_pid!r},{sel_t}) "
                f"but evaluation has ({pid!r},{t})."
            )

    return (len(problems) == 0), problems