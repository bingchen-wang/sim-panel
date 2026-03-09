# SIM-PANEL — Synthetic Panelists for Product Reviews

<p align="center">
  <img src="assets/logo.svg" alt="sim-panel logo" width="500"/>
</p>

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

> Current version: IRP-v0 (Internal research prototype, 7 March, 2026)

**SIM-PANEL** generates **schema-validated** synthetic panelist–product interaction datasets for LLM agent-based simulation projects.


## Concepts
The simulation system is organized using the following concepts:
- **Panelist**: a simulated customer. At runtime, a panelist is driven by `persona_text` (system prompt) and can optionally carry structured `attributes` (emitted as `panelist_features` in events).
- **Product**: an item/intervention being evaluated. Products separate internal identifiers (`product_id`) from panelist-facing exposure (`display_name`, optional `display_text`) and structured `attributes` (emitted as `product_features`).
- **Event**: an interaction event, describing which panelist gets which product at what time and the outcome of the exposure. Under `self_selection` policy, it also includes an initial selection/offer stage.
- **Policy**: how exposures are generated.
  - `random`: assigns product(s) to each panelist-period (RCT-style supported; default `balanced_quota`).
  - `manual`: assigns based on a user-provided mapping loaded from file and injected as a function.
  - `self_selection`: shows a choice set and lets the panelist choose which items to evaluate; generator applies operational execution rules (e.g., caps).

---
## Outputs

A generation run writes an output directory containing:

- `events.jsonl` (default) and optionally `events.csv`
- `metadata.json` (schema version, seed, counts, config snapshot/hash, input paths/variants)
- `data_dictionary.json` (configs/spec snapshots, including questionnaire spec and execution rules)

### Structure of an `Event` (v0.1.0)

Typical columns include:

- `schema_version`
- `event_id`
- `event_type`: `selection` or `evaluation`
- `panelist_id`
- `t` (period index)
- `policy` (e.g., `random`, `manual`, `self_selection`)

Selection-only fields (`event_type == "selection"`):
- `choice_set`: list of product_ids shown
- `selected_product_ids`: list chosen/requested by the panelist (may be empty)

Evaluation-only fields (`event_type == "evaluation"`):
- `product_id`
- `product_display` (panelist-facing text rendered from product record)
- `panelist_features` (JSON; may be `{}`)
- `product_features` (JSON; may be `{}`)
- `outcomes` (JSON payload governed by YAML questionnaire; may be `null`)
- `traces` (optional JSON payload; may be `null`)
- `selection_id` (`null` unless `policy == "self_selection"`; links back to the corresponding selection event)

## Installation
From the repo root:

```bash
pip install -e .
```

A `sim-panel` console command is provided via `pyproject.toml` after installation. If you prefer, you can also invoke the CLI as

```bash
python -m sim_panel.cli.main <command> ...
```

## Quickstart

### 0) Repo layout

Keep generated datasets and outputs at the repo root:

```
sim-panel/
  sim_panel/
  data/
  outputs/
  README.md
  developer_manual.md
```

### 1) Create demo data (LLM spec generation)
Generate spec-only personas/products using a **data-gen YAML**:

```bash
sim-panel make-data --config sim_panel/data_gen/examples/beer_demo.yaml
```

This writes (as configured in the YAML):
- `data/personas_beer_demo.jsonl`
- `data/products_beer_demo.jsonl`

Notes:
- This generates **attributes/specs** (no persona/product text by default).
- Text can be generated later via persisted enrichment (`panelists.enrich` / `products.enrich`) in the run config, or via `enrich_after` in the data-gen YAML.

### 2) Generate a small dataset from an example run config

```bash
sim-panel generate --config sim_panel/config/examples/self_selection.yaml --output-dir outputs/run_001
```

Optional CSV:

```bash
sim-panel generate --config sim_panel/config/examples/manual.yaml --output-dir outputs/run_002 --csv
```

### 3) Validate output

```bash
sim-panel validate --input outputs/run_001/events.jsonl
```

Validation includes:
- per-row schema validation (Pydantic)
- global `event_id` uniqueness
- self-selection linkage checks (selection_id must reference a valid selection event at the same `(panelist_id, t)`)

### 4) Sample a few rows

```bash
sim-panel sample --input outputs/run_001/events.jsonl --n 5 --seed 0
```

---

## Configuration overview (high level)

There are two YAMLs you will commonly use:

1) **Data generation YAML** (for producing `data/*.jsonl` specs):
- `sim_panel/data_gen/examples/beer_demo.yaml`

2) **Run configuration YAML** (for producing `outputs/*/events.jsonl`):
- `sim_panel/config/examples/minimal.yaml`
- `sim_panel/config/examples/self_selection.yaml`
- `sim_panel/config/examples/manual.yaml`

Key run-config capabilities:
- **Persisted enrichment** (generate `persona_text` / `display_text` once and save in place or to a new file).
- **Manual schedule loader** (load CSV/JSON mapping and inject `manual_assignment_fn` into `PolicyConfig`).
- **Outcomes questionnaire** governed by YAML (fields + choices + instructions), emitted as `outcomes` and optional `traces`.

### Example of a run config (LLM run with Ollama)

```yaml
# Minimal run config (LLM-based evaluation; Ollama backend required)
output_dir: outputs/run_llm_minimal

backend:
  name: ollama
  model: gemma3:12b
  return_usage: true
  params:
    base_url: "http://localhost:11434"
    timeout_s: 60

generator:
  schema_version: "0.1.0"
  seed: 0
  n_periods: 1
  validate_on_finish: true
  max_errors: 50
  event_namespace: "sim_panel.v0"

panelists:
  source: data/personas_beer_demo.jsonl
  variant: default
  # Assumes persona_text already exists. If not, enable persisted enrichment:
  # enrich:
  #   enabled: true
  #   overwrite: false
  #   save: in_place
  #   settings:
  #     prompt_version: v1
  #     temperature: 0.2
  #     max_tokens: 600
  #     metadata: {module: panelists.enrich}

  eval_settings:
    temperature: 0.2
    max_tokens: 900
    metadata: {module: panelists.evaluate}

products:
  source: data/products_beer_demo.jsonl
  variant: default
  # Assumes display_text exists (optional). If missing, enable persisted enrichment:
  # enrich:
  #   enabled: true
  #   overwrite: false
  #   save: in_place
  #   settings:
  #     prompt_version: v1
  #     campaign: "beer-demo"
  #     tone: neutral
  #     length: short
  #     temperature: 0.2
  #     max_tokens: 320
  #     metadata: {module: products.enrich}

policy:
  name: random
  evals_per_period: 1
  random_mode: balanced_quota

selection:
  allow_empty: true
  include_product_features: true
  require_json_only: true
  max_selected_soft: null
  include_raw_text: true

execution:
  enforce_subset_of_choice_set: true
  max_evals_per_panelist_per_t: null
  allow_empty: true
  keep_strategy: keep_first

outcomes_model:
  name: llm
  temperature: 0.2
  max_tokens: 900
  include_raw_text: true

questionnaire:
  outcomes:
    fields:
      rating:
        type: int
        choices: [1, 2, 3, 4, 5]
        question: "Overall, how much do you like this beer?"
        instruction: "Pick one integer."
        required: true

      purchase_intent:
        type: categorical
        choices: ["no", "maybe", "yes"]
        question: "How likely are you to purchase this beer in the next 30 days?"
        instruction: "Choose one option."
        required: true

  traces:
    fields:
      rationale:
        type: text
        question: "Briefly explain your ratings."
        required: false
```

Suggested command:

```bash
sim-panel generate --config sim_panel/config/examples/llm_minimal.yaml --output-dir outputs/run_llm_minimal
```
### Example of a data-gen config (LLM spec generation with Ollama)

```yaml
# Minimal data-gen config (LLM-based spec generation; Ollama backend required)
backend:
  name: ollama
  model: gemma3:12b
  return_usage: true
  params:
    base_url: "http://localhost:11434"
    timeout_s: 60

output:
  personas_path: data/personas_beer_demo.jsonl
  products_path: data/products_beer_demo.jsonl

personas:
  n: 20
  seed: 101
  persona_text_variant: default
  persona_id_prefix: p
  llm:
    prompt_version: v1
    temperature: 0.2
    max_tokens: 1600
    batch_size: 10
    max_retries: 2
    require_json_only: true

products:
  kind: beer
  n: 5
  seed: 101
  display_variant: default
  product_id_prefix: prod
  llm:
    prompt_version: v1
    temperature: 0.2
    max_tokens: 1800
    batch_size: 10
    max_retries: 2
    require_json_only: true

# Optional: run text enrichment immediately after spec generation (persisted).
enrich_after:
  enabled: false
  panelists:
    overwrite: false
    save: in_place
    settings:
      prompt_version: v1
      temperature: 0.2
      max_tokens: 600
      metadata: {module: panelists.enrich}
  products:
    overwrite: false
    save: in_place
    settings:
      prompt_version: v1
      campaign: "beer-demo"
      tone: neutral
      length: short
      temperature: 0.2
      max_tokens: 320
      metadata: {module: products.enrich}
```

Suggested command:

```bash
sim-panel make-data --config sim_panel/data_gen/examples/beer_demo.yaml
```

For module-level details and invariants, see the [Developer Manual](developer_manual.md).

## License
Apache-2.0. See `LICENSE` (and `NOTICE`).