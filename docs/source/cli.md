# CLI

SIM-PANEL provides a command-line interface through the `sim-panel` command.

The CLI is designed around explicit YAML configs and reproducible file outputs.
Most commands follow the same pattern:

```bash
sim-panel <command> --config path/to/config.yaml
```

Use:

```bash
sim-panel --help
```

to list available commands.

## Commands

| Command | Purpose |
| --- | --- |
| `make-data` | Generate demo persona/product datasets from a data-generation config. |
| `generate` | Generate SIM-PANEL event rows from a run config. |
| `validate` | Validate an events JSONL file against the schema. |
| `sample` | Print a random sample of rows from an events JSONL file. |
| `import` | Import an external source dataset into SIM-PANEL artifacts. |
| `benchmark-subset` | Freeze a benchmark-ready real-data subset. |
| `analyze` | Run single-run analysis from an analysis config. |
| `compare` | Compare multiple conditions or synthetic outputs against a reference. |

## `make-data`

Generate demo persona and product records from a data-generation YAML config.

```bash
sim-panel make-data --config examples/configs/data_gen.yaml
```

Options:

| Option | Description |
| --- | --- |
| `--config` | Path to data-generation YAML config. Required. |
| `--no-enrich-after` | Disable `enrich_after` even if enabled in YAML. |
| `--no-progress` | Disable progress display. |

This command is useful for creating small local persona/product datasets before
running `generate`.

## `generate`

Generate event rows from a SIM-PANEL run config.

```bash
sim-panel generate --config examples/configs/minimal.yaml
```

Common usage:

```bash
sim-panel generate \
  --config examples/configs/minimal.yaml \
  --output-dir outputs/run_001 \
  --csv
```

Options:

| Option | Description |
| --- | --- |
| `--config` | Path to generation YAML config. Required. |
| `--output-dir` | Output directory. Overrides `output_dir` in YAML. |
| `--csv` | Also write `events.csv`. |
| `--no-validate` | Skip schema validation after generation. |
| `--no-progress` | Disable progress display. |
| `--resume` | Resume from checkpoint if a previous run was interrupted. |

The command writes:

```text
events.jsonl
metadata.json
data_dictionary.json
```

If `--csv` is provided, it also writes:

```text
events.csv
```

### Output directory precedence

The output directory is resolved in this order:

```text
--output-dir
  -> output_dir in YAML
  -> outputs/run
```

### Checkpointing and resume

When `--resume` is used, SIM-PANEL attempts to resume from checkpoint files in
the output directory.

The checkpoint is tied to a fingerprint of the config snapshot. If the config has
changed since the checkpoint was written, resume fails and the CLI asks you to
delete checkpoint files or use a different output directory.

After a successful final write, checkpoint files are cleared.

## `validate`

Validate an events JSONL file against the registered schema.

```bash
sim-panel validate --input outputs/run_001/events.jsonl
```

Options:

| Option | Description |
| --- | --- |
| `--input` | Path to `events.jsonl`. Required. |
| `--schema-version` | Optional schema version to validate against. If omitted, each row's `schema_version` is used. |
| `--max-errors` | Maximum number of validation errors to show. Default: `50`. |

Validation includes:

- row-level schema validation;
- event ID uniqueness;
- self-selection link checks.

A successful run prints:

```text
OK: validation passed.
```

A failed run prints row errors, warnings, event ID problems, or self-selection
linkage problems.

## `sample`

Print a random sample of rows from an events JSONL file.

```bash
sim-panel sample \
  --input outputs/run_001/events.jsonl \
  --n 5 \
  --seed 0
```

Options:

| Option | Description |
| --- | --- |
| `--input` | Path to `events.jsonl`. Required. |
| `--n` | Number of rows to sample. Default: `10`. |
| `--seed` | Sampling seed. Default: `0`. |

The sampled rows are printed as formatted JSON.

## `import`

Import an external source dataset from a source YAML config.

```bash
sim-panel import --config examples/configs/import_amazon.yaml
```

Example with output override:

```bash
sim-panel import \
  --config examples/configs/import_amazon.yaml \
  --output-dir outputs/imports/all_beauty
```

Options:

| Option | Description |
| --- | --- |
| `--config` | Path to source import YAML config. Required. |
| `--output-dir` | Output directory. Overrides `source.output_dir` in YAML. |

The command builds the source from the YAML config and runs either the in-memory
or streaming import path, depending on the source config.

For the Amazon Reviews'23 source, typical outputs are:

```text
events.jsonl
products.jsonl
personas.jsonl
metadata.json
data_dictionary.json
stats.json
```

## `benchmark-subset`

Build a frozen benchmark-ready subset from imported real-data artifacts.

```bash
sim-panel benchmark-subset --config examples/configs/benchmark_subset.yaml
```

Options:

| Option | Description |
| --- | --- |
| `--config` | Path to benchmark subset YAML config. Required. |

Typical output:

```text
events.jsonl
products.jsonl
metadata.json
stats.json
```

The benchmark subset command belongs to the `benchmarks/` layer. It freezes a
reference subset; it does not compute synthetic-vs-reference comparison metrics.

## `analyze`

Run single-run analysis from an analysis YAML config.

```bash
sim-panel analyze --config examples/configs/analysis.yaml
```

Options:

| Option | Description |
| --- | --- |
| `--config` | Path to analysis YAML config. Required. |

The command prints the analysis output directory and a short run summary when
available.

Typical output directory structure:

```text
analysis/
  summary/
  metrics/
  plots/
  report/
  regression/
```

The `regression/` subdirectory is written only when regression is enabled in the
analysis config.

## `compare`

Compare multiple conditions from a comparison YAML config.

```bash
sim-panel compare --config examples/configs/compare.yaml
```

Options:

| Option | Description |
| --- | --- |
| `--config` | Path to comparison YAML config. Required. |

The command prints the number of compared conditions, the selected outcome field,
the output directory, and a compact per-condition rating summary when available.

Comparison has its own CLI flow and belongs to `analysis/compare/`.

Typical outputs may include:

```text
condition_metrics.json
condition_metrics.csv
pivot_tables.json
comparison_report.md
```

Benchmark-mode comparison may also write benchmark-specific summaries,
diagnostics, and figures.

## Typical workflows

### Synthetic generation workflow

```bash
sim-panel make-data --config examples/configs/data_gen.yaml

sim-panel generate \
  --config examples/configs/minimal.yaml \
  --output-dir outputs/run_001 \
  --csv

sim-panel validate --input outputs/run_001/events.jsonl

sim-panel analyze --config examples/configs/analyze_run_001.yaml
```

### Source-to-benchmark workflow

```bash
sim-panel import --config examples/configs/import_amazon.yaml

sim-panel benchmark-subset --config examples/configs/benchmark_subset.yaml
```

### Synthetic-vs-reference comparison workflow

```bash
sim-panel generate \
  --config examples/configs/synthetic_condition_a.yaml \
  --output-dir outputs/condition_a

sim-panel generate \
  --config examples/configs/synthetic_condition_b.yaml \
  --output-dir outputs/condition_b

sim-panel compare --config examples/configs/compare_against_reference.yaml
```

## Command boundaries

The CLI mirrors SIM-PANEL's module boundaries.

| Command | Module layer |
| --- | --- |
| `make-data` | Data-generation helpers. |
| `generate` | Generator pipeline. |
| `validate` | Schema validation. |
| `sample` | Lightweight IO inspection. |
| `import` | Sources. |
| `benchmark-subset` | Benchmarks. |
| `analyze` | Single-run analysis. |
| `compare` | Multi-run comparison. |

This separation is intentional:

```text
sources ingest
benchmarks freeze
analysis inspects
comparison evaluates
generation simulates
```

## Exit behavior

Most commands return `0` on success and non-zero on failure.

Validation returns:

| Result | Exit code |
| --- | --- |
| Validation passed | `0` |
| Validation failed | `1` |

If a command receives an invalid config or missing required file, it raises an
error with a message from the relevant loader, validator, or runner.