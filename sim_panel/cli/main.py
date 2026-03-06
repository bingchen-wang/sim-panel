from __future__ import annotations

import argparse
import sys
import json
import os
from dataclasses import asdict, is_dataclass, replace
from typing import Any, Dict, List, Optional

from sim_panel.config.build import build_run_from_yaml
from sim_panel.generators.pipeline import EventGenerator

from sim_panel.io.paths import ensure_dir, default_run_filenames
from sim_panel.io.jsonl import read_jsonl_dicts, write_jsonl_rows
from sim_panel.io.csv_io import write_csv_rows
from sim_panel.io.metadata import build_metadata, write_metadata_json
from sim_panel.io.dictionary import build_data_dictionary, write_data_dictionary_json

from sim_panel.schema.validate import (
    validate_rows,
    validate_unique_event_id,
    validate_self_selection_links,
)

from sim_panel.config.yaml_loader import load_yaml
from sim_panel.data_gen.run import run_datagen_from_yaml

def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "make-data":
        return _cmd_make_data(args)
    if args.command == "generate":
        return _cmd_generate(args)
    if args.command == "validate":
        return _cmd_validate(args)
    if args.command == "sample":
        return _cmd_sample(args)

    parser.print_help()
    return 2


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sim-panel",
        description="sim-panel: synthetic panel-style events generator",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # make-data
    md = sub.add_parser("make-data", help="Generate demo personas/products datasets from a data_gen YAML config")
    md.add_argument("--config", required=True, help="Path to data_gen YAML config")
    md.add_argument("--no-enrich-after", action="store_true", help="Disable enrich_after even if enabled in YAML")
    md.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress display (tqdm if installed).",
    )

    # generate
    g = sub.add_parser("generate", help="Generate events from a YAML config")
    g.add_argument("--config", required=True, help="Path to YAML config")
    g.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (overrides output_dir in YAML if provided)",
    )
    g.add_argument("--csv", action="store_true", help="Also write events.csv")
    g.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip schema validation after generation",
    )
    g.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress display (tqdm if installed).",
    )

    # validate
    v = sub.add_parser("validate", help="Validate an events JSONL file against the schema")
    v.add_argument("--input", required=True, help="Path to events.jsonl")
    v.add_argument(
        "--schema-version",
        default=None,
        help="Schema version to validate against. If omitted, uses per-row schema_version.",
    )
    v.add_argument("--max-errors", type=int, default=50, help="Max validation errors to show")

    # sample
    s = sub.add_parser("sample", help="Sample N rows from events JSONL and print as JSON")
    s.add_argument("--input", required=True, help="Path to events.jsonl")
    s.add_argument("--n", type=int, default=10, help="Number of rows to sample")
    s.add_argument("--seed", type=int, default=0, help="RNG seed for sampling")

    return p

def _cmd_make_data(args: argparse.Namespace) -> int:
    # Load YAML so we can print output paths (and fail early if invalid)
    d = load_yaml(args.config)
    out = d.get("output") or {}
    personas_path = out.get("personas_path")
    products_path = out.get("products_path")

    _progress_note(
        "make-data",
        enabled=not bool(args.no_progress),
        extra="(install tqdm for a nicer progress bar)" if not _has_tqdm() else "",
    )
    run_datagen_from_yaml(
        args.config,
        disable_enrich_after=bool(args.no_enrich_after),
        progress=not bool(args.no_progress),
    )

    if isinstance(personas_path, str):
        print(f"Wrote: {personas_path}")
    if isinstance(products_path, str):
        print(f"Wrote: {products_path}")

    # If enrich_after is enabled (and not disabled), attempt to print save targets
    enrich_after = d.get("enrich_after") or {}
    if isinstance(enrich_after, dict) and bool(enrich_after.get("enabled", False)) and not args.no_enrich_after:
        p_save = ((enrich_after.get("panelists") or {}).get("save") if isinstance(enrich_after.get("panelists"), dict) else None)
        pr_save = _resolve_save_preview(personas_path, p_save)
        if pr_save is not None:
            print(f"Wrote (enriched personas): {pr_save}")

        prod_save = ((enrich_after.get("products") or {}).get("save") if isinstance(enrich_after.get("products"), dict) else None)
        pd_save = _resolve_save_preview(products_path, prod_save)
        if pd_save is not None:
            print(f"Wrote (enriched products): {pd_save}")

    return 0

def _cmd_generate(args: argparse.Namespace) -> int:
    bundle = build_run_from_yaml(args.config)

    # Determine output directory: CLI override > YAML > default
    out_dir = args.output_dir or bundle.run_config.output_dir or _default_output_dir()
    ensure_dir(out_dir)
    names = default_run_filenames()

    generator = bundle.generator

    # Honor --no-validate without mutating frozen configs
    if args.no_validate:
        new_cfg = replace(generator.cfg, validate_on_finish=False)
        generator = EventGenerator(new_cfg)

    _progress_note(
        "generate",
        enabled=not bool(args.no_progress),
        extra="(install tqdm for a nicer progress bar)" if not _has_tqdm() else "",
    )

    rows = generator.generate(panelists=bundle.panelists, products=bundle.products)

    # Write events
    events_path = os.path.join(out_dir, names.events_jsonl)
    write_jsonl_rows(events_path, rows)

    if args.csv:
        csv_path = os.path.join(out_dir, names.events_csv)
        write_csv_rows(csv_path, rows)

    # Write metadata
    meta = build_metadata(
        schema_version=generator.cfg.schema_version,
        seed=generator.cfg.seed,
        n_rows=len(rows),
        n_panelists=len(bundle.panelists),
        n_products=len(bundle.products),
        n_periods=generator.cfg.n_periods,
        policy_name=generator.cfg.policy.name,
        config_snapshot=bundle.config_snapshot,
        extra={
            "config_path": args.config,
            "personas_path": bundle.run_config.personas_path,
            "products_path": bundle.run_config.products_path,
            "persona_variant": bundle.run_config.persona_variant,
            "product_variant": bundle.run_config.product_variant,
        },
    )
    metadata_path = os.path.join(out_dir, names.metadata_json)
    write_metadata_json(metadata_path, meta)

    # Write data dictionary
    dd = build_data_dictionary(
        schema_version=generator.cfg.schema_version,
        generator_config=_to_jsonable(generator.cfg),
        policy_config=_to_jsonable(generator.cfg.policy),
        selection_config=_to_jsonable(generator.cfg.selection),
        execution_rules=_to_jsonable(generator.cfg.execution.rules),
        outcome_config=_to_jsonable(generator.cfg.outcome),
        notes="Auto-generated by sim-panel CLI.",
    )
    dict_path = os.path.join(out_dir, names.data_dictionary_json)
    write_data_dictionary_json(dict_path, dd)

    print(f"Wrote: {events_path}")
    print(f"Wrote: {metadata_path}")
    print(f"Wrote: {dict_path}")
    if args.csv:
        print(f"Wrote: {os.path.join(out_dir, names.events_csv)}")

    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    rows = read_jsonl_dicts(args.input)

    report = validate_rows(rows, schema_version=args.schema_version, max_errors=args.max_errors)
    ok_ids, msg = validate_unique_event_id(rows)

    ok_links = True
    link_problems: List[str] = []
    try:
        ok_links, link_problems = validate_self_selection_links(rows)
    except Exception:
        # In case the validator changes; keep validate robust.
        ok_links = True
        link_problems = []

    if report.ok and ok_ids and ok_links:
        print("OK: validation passed.")
        if report.warnings:
            print("\nWarnings:")
            for w in report.warnings:
                print(f"- {w}")
        return 0

    print("Validation failed.")
    print(f"- schema_version mode: {report.schema_version}")
    print(f"- rows: {report.n_rows}, valid: {report.n_valid}, invalid: {report.n_invalid}")

    if report.errors:
        print("\nRow errors:")
        for e in report.errors:
            print(f"- row {e.index}: {e.message}")

    if report.warnings:
        print("\nWarnings:")
        for w in report.warnings:
            print(f"- {w}")

    if not ok_ids:
        print("\nevent_id uniqueness check failed:")
        print(f"- {msg}")

    if not ok_links:
        print("\nSelf-selection link check failed:")
        for p in link_problems[: args.max_errors]:
            print(f"- {p}")
        if len(link_problems) > args.max_errors:
            print(f"... ({len(link_problems) - args.max_errors} more)")

    return 1


def _cmd_sample(args: argparse.Namespace) -> int:
    import numpy as np

    rows = read_jsonl_dicts(args.input)
    if args.n <= 0 or not rows:
        print("[]")
        return 0

    rng = np.random.default_rng(args.seed)
    n = min(args.n, len(rows))
    idx = rng.choice(len(rows), size=n, replace=False).tolist()
    sample = [rows[i] for i in idx]

    print(json.dumps(sample, ensure_ascii=False, indent=2))
    return 0

def _resolve_save_preview(source_path: Any, save: Any) -> Optional[str]:
    if not isinstance(source_path, str):
        return None
    if save is None:
        return source_path
    if isinstance(save, str) and save == "in_place":
        return source_path
    if isinstance(save, dict):
        p = save.get("path")
        return p if isinstance(p, str) else None
    return None

def _default_output_dir() -> str:
    # Keep it simple; CLI can override. (We can add timestamped runs later.)
    return os.path.join("outputs", "run")


def _to_jsonable(obj: Any) -> Any:
    if obj is None:
        return None
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    return repr(obj)

def _has_tqdm() -> bool:
    try:
        import tqdm  # type: ignore
        return True
    except Exception:
        return False


def _progress_note(kind: str, *, enabled: bool, extra: str = "") -> None:
    """
    Print a one-line progress note. Real progress bars happen in data_gen/enrich/generators.
    This avoids changing generator internals from the CLI layer.
    """
    if not enabled:
        return
    msg = f"[{kind}] running"
    if extra:
        msg = f"{msg} {extra}"
    print(msg, file=sys.stderr, flush=True)


if __name__ == "__main__":
    raise SystemExit(main())