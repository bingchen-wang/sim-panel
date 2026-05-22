# Development

SIM-PANEL is designed as a modular research software package. The development
workflow should keep the repository reproducible, inspectable, and lightweight.

The core rule is simple: source code, small examples, tests, and documentation
belong in the repo; raw external data and generated experiment outputs do not.

## Local setup

From the repository root, install SIM-PANEL in editable mode:

```bash
pip install -e .
```

For development and documentation work, install optional extras:

```bash
pip install -e ".[dev,docs]"
```

Check that the CLI is available:

```bash
sim-panel --help
```

## Run tests

Run the full test suite with:

```bash
python -m pytest
```

For faster iteration, run a specific test file:

```bash
python -m pytest tests/test_schema.py
```

Tests should cover at least:

- schema validation;
- deterministic generation with fixed seeds;
- policy behavior;
- source conversion on small fixtures;
- benchmark subset construction;
- CLI smoke tests where practical.

## Build documentation

Build the Sphinx documentation from the repository root:

```bash
sphinx-build -b html docs/source docs/build/html
```

Or from the `docs/` directory:

```bash
cd docs
make html
```

Before release, prefer a warning-strict build:

```bash
sphinx-build -b html docs/source docs/build/html -W
```

A clean documentation build should have no missing toctree targets, unresolved
cross-references, malformed directives, or syntax-highlight warnings.

## CLI smoke checks

After meaningful changes, run a small end-to-end workflow:

```bash
sim-panel make-data --config examples/configs/data_gen.yaml

sim-panel generate \
  --config examples/configs/minimal.yaml \
  --output-dir outputs/dev_run

sim-panel validate --input outputs/dev_run/events.jsonl

sim-panel sample --input outputs/dev_run/events.jsonl --n 3
```

For source and benchmark work, also test the relevant commands on small fixtures
or capped imports:

```bash
sim-panel import --config examples/configs/import_amazon_dev.yaml

sim-panel benchmark-subset --config examples/configs/benchmark_subset_dev.yaml
```

## Version-control hygiene

Do not commit:

- raw external datasets;
- imported source artifacts;
- generated runs under `outputs/`;
- local benchmark subsets;
- large plots or report artifacts;
- checkpoint files;
- private scratch scripts;
- machine-specific environment files.

Use these locations intentionally:

| Path | Purpose |
| --- | --- |
| `examples/` | Small user-facing configs and toy data. |
| `tests/fixtures/` | Minimal deterministic test fixtures. |
| `docs/source/` | Sphinx documentation source files. |
| `outputs/` | Local generated artifacts; should generally be ignored. |

## Data and artifact policy

SIM-PANEL should not redistribute large external datasets. Source adapters should
assume users have downloaded raw data locally and point configs to local paths.

Generated artifacts should be reproducible from committed configs and small
fixtures where possible. For large or external-data-dependent runs, commit the
configuration and documentation, not the generated output.

## Modular boundaries

Keep module responsibilities separate:

| Module | Responsibility |
| --- | --- |
| `sources/` | Ingest and convert external datasets. |
| `benchmarks/` | Freeze benchmark-ready real-data subsets. |
| `generators/` | Orchestrate policies, decisions, outcomes, and schema-row emission. |
| `policies/` | Define pure exposure logic. |
| `decisions/` | Render and parse self-selection decisions. |
| `outcomes/` | Produce structured outcomes and traces. |
| `schema/` | Define and validate event schemas. |
| `analysis/` | Analyze one run. |
| `analysis/compare/` | Compare conditions or synthetic outputs against references. |
| `cli/` | Expose stable command-line workflows. |

When adding a feature, place it according to the boundary above rather than
folding unrelated logic into the nearest existing file.

## Documentation conventions

Documentation should describe implemented behavior, not aspirational behavior.
When documenting configs, use the actual dataclass and YAML vocabulary used by
the current code.

Keep user-guide pages concise. Move long field inventories, implementation
details, and edge cases into API or reference pages when needed.

## Before opening a pull request

Run:

```bash
python -m pytest
sphinx-build -b html docs/source docs/build/html -W
```

Then check:

- generated files are not staged accidentally;
- examples still run;
- docs match current CLI flags and config fields;
- new modules have tests or fixtures;
- public-facing wording does not overclaim what synthetic data validates.