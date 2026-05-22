# Changelog

All notable changes to SIM-PANEL will be documented in this file.

Version numbers may change as the public API, schemas, and documentation stabilize.

## v0.1.0 — Initial public release

Initial public release of SIM-PANEL as a reproducible research-engineering
toolkit for synthetic panel-style event generation, source ingestion, benchmark
subset construction, single-run analysis, and multi-condition comparison.

### Added

- Versioned event schema `0.1.0`.
- CLI commands for data generation, event generation, validation, sampling,
  source import, benchmark subset construction, analysis, and comparison.
- Random, manual, and self-selection exposure policies.
- JSONL-first event outputs with metadata and data dictionaries.
- Optional CSV export for generated events.
- Deterministic seeding for non-LLM components.
- Self-selection event linkage through `selection_id`.
- Generator-side execution rules for self-selection workflows.
- Amazon Reviews'23 source adapter with in-memory and streaming import paths.
- Benchmark subset builder for freezing product-level real-data references.
- Single-run analysis workflows for summaries, metrics, plots, and reports.
- Optional regression diagnostics under the analysis layer.
- Multi-condition comparison workflows under `analysis/compare/`.
- Sphinx documentation site with user-guide pages and API reference.
- Development documentation for local setup, tests, docs builds, and
  version-control hygiene.

### Notes

Synthetic data produced by SIM-PANEL is intended for schema debugging, pipeline
testing, ablation scaffolding, and simulation-design prototyping. It should not
be interpreted as a substitute for primary empirical validation.