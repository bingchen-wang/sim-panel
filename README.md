# SIM-PANEL — Synthetic Panel Datasets for Agent Evaluation

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.svg">
    <img src="assets/logo-light.svg" alt="SIM-PANEL logo" width="500">
  </picture>
</p>

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/bingchen-wang/sim-panel?label=release)](https://github.com/bingchen-wang/sim-panel/releases)
[![Docs](https://img.shields.io/github/actions/workflow/status/bingchen-wang/sim-panel/docs.yml?branch=main&label=docs)](https://github.com/bingchen-wang/sim-panel/actions/workflows/docs.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

> Current version: v0.1.0-public — research prototype release, May 2026

**Documentation / project site:** https://bingchen-wang.github.io/sim-panel/

**SIM-PANEL** is a reproducible research-engineering toolkit for generating,
validating, analyzing, and comparing panel-style event datasets.

It is designed as an engineering scaffold for LLM-based agent simulation,
preference reconstruction, and verifiable behavioral evaluation. The package
focuses on transparent data generation, schema validation, YAML-configured
experiments, and distributional diagnostics rather than large-scale black-box
simulation.

## What SIM-PANEL does

SIM-PANEL supports workflows where simulated panelists evaluate products,
interventions, or other candidate items over time.

Core capabilities include:

- versioned event-level schemas;
- YAML-configured generation runs;
- randomized, manual, and self-selection exposure policies;
- deterministic seeding for non-LLM components;
- JSONL-first outputs with metadata and data dictionaries;
- optional CSV export;
- source adapters for importing real review-style data;
- benchmark subset construction from imported real data;
- single-run analysis, optional regression diagnostics, and multi-condition comparison;
- optional LLM-backed enrichment, selection, and outcome generation.

Synthetic data in SIM-PANEL is intended for **schema debugging, pipeline testing,
ablation scaffolding, and simulation-design prototyping**. It should not be
interpreted as a substitute for primary empirical validation.

## Core concepts

| Concept | Meaning |
| --- | --- |
| Panelist | A simulated respondent, user, customer, or agent. |
| Product | An item, intervention, treatment, or candidate object being evaluated. |
| Event | One schema-valid row in `events.jsonl`. |
| Policy | Exposure logic determining how panelists encounter products. |
| Outcome | Structured evaluation result, such as rating or purchase intent. |
| Trace | Optional auxiliary text, rationale, source provenance, or debug payload. |

SIM-PANEL currently supports three exposure policies:

| Policy | Description |
| --- | --- |
| `random` | Products are assigned to panelists exogenously. |
| `manual` | Product-panelist assignments are loaded from a schedule or mapping. |
| `self_selection` | Panelists choose products from a shown choice set. |

## Module structure

SIM-PANEL keeps ingestion, generation, analysis, and comparison separate:

```text
sources/
  raw external data -> imported canonical artifacts

benchmarks/
  imported artifacts -> frozen real-data subsets

generators/
  panelists + products + policies + outcomes -> synthetic events

analysis/
  one run -> summaries, metrics, plots, reports, optional regression

analysis/compare/
  multiple conditions or reference subsets -> comparison metrics and reports
```

The shorthand is:

> Sources ingest. Benchmarks freeze. Generation simulates. Analysis inspects.
> Comparison evaluates.

## Outputs

A standard generation run writes:

```text
outputs/run_001/
  events.jsonl
  metadata.json
  data_dictionary.json
```

Optional CSV export writes:

```text
outputs/run_001/
  events.csv
```

`events.jsonl` is the canonical dataset artifact. Each row is a schema-valid
event with fields such as:

- `schema_version`
- `event_id`
- `event_type`
- `policy`
- `panelist_id`
- `product_id`
- `t`
- `outcomes`
- `traces`
- `panelist_features`
- `product_features`

Self-selection runs may also include `selection` events and linked `evaluation`
events via `selection_id`.

## Installation

Clone the repository:

```bash
git clone https://github.com/bingchen-wang/sim-panel.git
cd sim-panel
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install SIM-PANEL:

```bash
pip install -e .
```

For development and documentation work:

```bash
pip install -e ".[dev,docs]"
```

Verify the CLI:

```bash
sim-panel --help
```

## Quickstart

Generate a small dataset from a YAML config:

```bash
sim-panel generate \
  --config examples/configs/minimal.yaml \
  --output-dir outputs/run_001
```

Validate the generated events:

```bash
sim-panel validate --input outputs/run_001/events.jsonl
```

Sample a few rows:

```bash
sim-panel sample \
  --input outputs/run_001/events.jsonl \
  --n 5 \
  --seed 0
```

Run single-run analysis:

```bash
sim-panel analyze --config examples/configs/analysis.yaml
```

Compare multiple conditions or compare synthetic outputs against a reference:

```bash
sim-panel compare --config examples/configs/compare.yaml
```

## Source import and benchmark subsets

SIM-PANEL can import external review-style datasets into canonical artifacts.
The current source layer includes an Amazon Reviews'23 adapter.

A typical real-data workflow is:

```bash
sim-panel import --config examples/configs/import_amazon.yaml

sim-panel benchmark-subset --config examples/configs/benchmark_subset.yaml
```

This produces a frozen real-data subset that can be used by the comparison layer.

## CLI commands

| Command | Purpose |
| --- | --- |
| `make-data` | Generate demo persona/product datasets. |
| `generate` | Generate synthetic event rows from a run config. |
| `validate` | Validate an events JSONL file. |
| `sample` | Print sampled rows from an events JSONL file. |
| `import` | Import an external source dataset. |
| `benchmark-subset` | Freeze a benchmark-ready real-data subset. |
| `analyze` | Run single-run analysis. |
| `compare` | Compare multiple conditions or synthetic outputs against a reference. |

## Documentation

The Sphinx documentation lives under:

```text
docs/source/
```

Build locally with:

```bash
sphinx-build -b html docs/source docs/build/html
```

After the repository is public and GitHub Pages is enabled, the documentation
site will be available at:

```text
https://bingchen-wang.github.io/sim-panel/
```

## Development

Run tests:

```bash
python -m pytest
```

Build docs with warnings treated as errors:

```bash
sphinx-build -b html docs/source docs/build/html -W
```

Check the CLI:

```bash
sim-panel --help
sim-panel generate --help
sim-panel validate --help
sim-panel analyze --help
sim-panel compare --help
```

Do not commit raw external data, generated outputs, local benchmark runs, or built
documentation artifacts.

## Project status and scope

SIM-PANEL is an ongoing research-engineering project. The public API and schema
may evolve.

The current emphasis is on:

- clean event schemas;
- deterministic local generation;
- modular policies and outcome models;
- real-data ingestion scaffolds;
- frozen reference subsets;
- transparent diagnostics and comparison reports.

SIM-PANEL is not intended to claim that synthetic panelists are substitutes for
human subjects or primary empirical validation.


## Contact

For reproducible bugs, feature requests, or documentation issues, please use the
[GitHub issue tracker](https://github.com/bingchen-wang/sim-panel/issues).

For research-related inquiries, contact **Bingchen Wang** at
`bw2506 [at] columbia [dot] edu`.


## Acknowledgements

SIM-PANEL is developed and maintained by **Bingchen Wang** as an independent
research-engineering project.

The project benefited from early discussions with **Bruno Abrahao** and
**Teutly Correia** on agent-based product evaluation workflows. These discussions
helped motivate the beer-demo example and informed the Amazon Reviews'23
ingestion and benchmarking direction. Bruno Abrahao also contributed initial
commits to an early prototype.

Any errors, design choices, or limitations remain the responsibility of the
maintainer.


## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).