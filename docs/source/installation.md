# Installation

This page describes how to install SIM-PANEL for local use, development, and
documentation builds.

## Clone the repository

```bash
git clone https://github.com/bingchen-wang/sim-panel.git
cd sim-panel
```

## Create a virtual environment

Using Python's built-in `venv`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

## Install SIM-PANEL

For ordinary local use, install the package in editable mode:

```bash
pip install -e .
```

Editable mode is convenient during development because changes to the source tree
are reflected without reinstalling the package.

Verify that the CLI is available:

```bash
sim-panel --help
```

## Development install

For tests and development tooling, install the development extras:

```bash
pip install -e ".[dev]"
```

Run the test suite:

```bash
python -m pytest
```

## Documentation install

For documentation work, install the documentation extras:

```bash
pip install -e ".[docs]"
```

Build the documentation from the repository root:

```bash
sphinx-build -b html docs/source docs/build/html
```

Or from the `docs/` directory:

```bash
cd docs
make html
```

## Full development and docs install

For contributors working on both code and documentation, install both extras:

```bash
pip install -e ".[dev,docs]"
```

Then verify the main checks:

```bash
sim-panel --help
python -m pytest
sphinx-build -b html docs/source docs/build/html
```

## Optional local model backends

Core SIM-PANEL workflows do not require proprietary APIs. Deterministic generation
and schema validation run locally.

LLM-backed selection, enrichment, or outcome generation require a configured
backend, such as a local Ollama endpoint or another compatible local/server-style
backend supported by the current codebase. These backends are optional and should
be configured explicitly in YAML.

## Troubleshooting

### `sim-panel` command not found

Make sure the environment is activated and the package is installed:

```bash
source .venv/bin/activate
pip install -e .
```

Then retry:

```bash
sim-panel --help
```

### Sphinx cannot import `sim_panel`

Install the package in editable mode:

```bash
pip install -e ".[docs]"
```

The documentation config also adds the repository root to Python's import path,
but an editable install is still the cleanest local setup.

### Documentation build has stale pages

Clean the build directory and rebuild:

```bash
rm -rf docs/build/html
sphinx-build -b html docs/source docs/build/html
```

## Next steps

After installation, continue with:

- [Quickstart](quickstart.md) for a minimal end-to-end run.
- [Concepts](concepts.md) for the main SIM-PANEL vocabulary.
- [CLI](cli.md) for command-line workflows.