# Contributing

SIM-PANEL is currently maintained as an independent research-engineering project.

Contributions are welcome in the form of bug reports, documentation fixes, small
tests, and focused pull requests. For larger design changes, please open an issue
first to discuss scope and fit.

## Development setup

Install the package with development and documentation extras:

```bash
pip install -e ".[dev,docs]"
```

Run the test suite:

```bash
python -m pytest
```

Build the documentation:

```bash
sphinx-build -b html docs/source docs/build/html
```

Before submitting a pull request, preferably run:

```bash
python -m pytest
sphinx-build -b html docs/source docs/build/html -W
```

## Contribution guidelines

Please keep contributions small, focused, and consistent with the existing module
boundaries.

General guidelines:

- Keep source ingestion in `sources/`.
- Keep benchmark subset construction in `benchmarks/`.
- Keep synthetic generation orchestration in `generators/`.
- Keep exposure logic in `policies/`.
- Keep selection rendering, parsing, and execution rules in `decisions/`.
- Keep outcome-model interfaces in `outcomes/`.
- Keep event-schema logic in `schema/`.
- Keep single-run diagnostics in `analysis/`.
- Keep multi-condition comparison logic in `analysis/compare/`.
- Keep command-line entry points in `cli/`.

For behavioral changes, add or update tests where practical.

For documentation changes, describe implemented behavior rather than aspirational
features.

## Data and artifacts

Do not commit:

- raw external datasets;
- imported source artifacts;
- generated runs under `outputs/`;
- local benchmark subsets;
- built documentation artifacts;
- checkpoint files;
- large plots or report artifacts;
- private scratch scripts;
- machine-specific environment files.

Use these locations intentionally:

| Path | Purpose |
| --- | --- |
| `examples/` | Small user-facing configs and toy data. |
| `tests/fixtures/` | Minimal deterministic test fixtures. |
| `docs/source/` | Sphinx documentation source files. |
| `outputs/` | Local generated artifacts; should generally be ignored. |

## Reporting issues

For reproducible bugs, please include:

- the command or config used;
- expected behavior;
- observed behavior;
- relevant error messages;
- a minimal reproducible example when possible;
- whether the issue occurs with deterministic/non-LLM components or an optional
  LLM backend.

Please avoid attaching large raw datasets or generated output directories. Use
small synthetic examples whenever possible.

## Pull requests

A good pull request should:

- state the problem being solved;
- describe the implementation approach;
- mention any schema, config, CLI, or artifact-contract changes;
- include tests or explain why tests are not applicable;
- update documentation when user-facing behavior changes.

Before opening a pull request, check:

```bash
git status
git diff --stat
python -m pytest
sphinx-build -b html docs/source docs/build/html
```

## Conduct

Please keep discussion respectful, specific, and evidence-oriented.

This project is a research-engineering codebase. Critiques of design choices,
modeling assumptions, and implementation tradeoffs are welcome. Personal attacks,
harassment, or bad-faith behavior are not.