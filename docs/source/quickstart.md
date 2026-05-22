# Quickstart

This page walks through a minimal SIM-PANEL run: install the package, generate a
small synthetic panel dataset, validate the output, and inspect a few rows.

SIM-PANEL is designed to be configuration-driven. A typical run starts from a
YAML file and writes JSONL artifacts plus metadata into an output directory.

## Installation

From the repository root, install the package in editable mode:

```bash
pip install -e .
```

For development, install optional development dependencies if they are defined
in the project configuration:

```bash
pip install -e ".[dev]"
```

Check that the command-line interface is available:

```bash
sim-panel --help
```

## Generate a small dataset

Run the generator with an example configuration:

```bash
sim-panel generate \
  --config examples/configs/minimal.yaml \
  --out outputs/run_001
```

This command reads the YAML configuration, loads panelists and products, applies
the configured assignment or selection policy, generates event-level outcomes,
and writes artifacts to `outputs/run_001`.

A typical run directory contains:

```text
outputs/run_001/
  events.jsonl
  metadata.json
  data_dictionary.json
```

If CSV export is enabled by the command or writer settings, the run directory may
also include:

```text
events.csv
```

`events.jsonl` is the primary dataset output. `events.csv` is a convenience
export; nested structures are JSON-serialized into string cells.

## Validate the output

Validate the generated event file against the SIM-PANEL schema:

```bash
sim-panel validate \
  --data outputs/run_001/events.jsonl \
  --meta outputs/run_001/metadata.json
```

Validation checks that generated rows follow the expected event schema. For
self-selection runs, validation may also check that evaluation events are linked
correctly to their corresponding selection events.

## Inspect sample rows

Print a few generated events:

```bash
sim-panel sample \
  --data outputs/run_001/events.jsonl \
  --n 5
```

Each row represents an event-level observation. A typical evaluation event
contains fields such as:

```text
event_id
schema_version
event_type
panelist_id
product_id
t
policy
outcomes
traces
panelist_features
product_features
```

For random and manual assignment runs, most rows are evaluation events. For
self-selection runs, the output may contain both `selection` events and linked
`evaluation` events.

## Minimal configuration

A minimal generation config has three required top-level sections:

- `panelists`
- `products`
- `policy`

Most useful runs also define `generator`, `outcomes_model`, `questionnaire`, and
`output_dir`.

A small deterministic random-assignment config looks like this:

```yaml
panelists:
  source: examples/data/panelists.jsonl
  variant: default

products:
  source: examples/data/products.jsonl
  variant: default

policy:
  name: random

generator:
  schema_version: "0.1.0"
  seed: 42
  n_periods: 3
  validate_on_finish: true
  max_errors: 50
  event_namespace: quickstart
  max_workers: 1
  prompting_strategy: persona

outcomes_model:
  name: deterministic

questionnaire:
  outcomes:
    fields:
      rating:
        type: int
        choices: [1, 2, 3, 4, 5]
        question: "Overall, how much do you like this product?"
      purchase_intent:
        type: categorical
        choices: ["no", "maybe", "yes"]
        question: "How likely are you to purchase in 30 days?"
  traces:
    fields:
      review_text:
        type: text
        question: "Write a short review in 2–4 sentences."

output_dir: outputs/quickstart
```

The deterministic outcome model fills the questionnaire using stable hashes of
`panelist_id`, `product_id`, and `t`. This makes it useful for local tests,
schema checks, CI, and CPU-only pipeline debugging.

## What to inspect first

After your first run, check the following files:

| File | Purpose |
| --- | --- |
| `events.jsonl` | Primary event-level dataset. |
| `metadata.json` | Lightweight run bookkeeping: generation time, schema version, seed, row counts, panelist/product/period counts, policy name, optional config snapshot, and config hash. |
| `data_dictionary.json` | Dataset legend/contract: schema version plus JSONable snapshots of key configs and specs, including generator config, policy config, selection config, execution rules, and outcome config. |
| `events.csv` | Optional convenience export. Nested structures are JSON-serialized into string cells. |

The most important file is `events.jsonl`. It is the canonical output format for
validation, downstream analysis, and benchmarking.

## Reproducibility

SIM-PANEL uses deterministic seeding for non-LLM components such as exposure
sampling, assignment shuffles, and stable event-id generation. Re-running the
same configuration with the same seed should produce the same non-LLM outputs.

LLM-backed enrichment, selection, or outcome generation may not be perfectly
deterministic unless the backend, model version, prompts, decoding parameters,
and runtime behavior are also controlled. For reproducible local tests, prefer
deterministic or mock components.

## Next steps

After completing the quickstart, the most useful pages are:

- [Configuration](configs.md) for YAML-driven experiment setup.
- [Schema](schema.md) for event-level fields, artifacts, and validation rules.
- [Generation](generation.md) for the synthetic panel generation pipeline.
- [Sources](sources.md) for real-data adapters such as Amazon Reviews'23.
- [Benchmarks](benchmarks.md) for freezing benchmark-ready real-data subsets.