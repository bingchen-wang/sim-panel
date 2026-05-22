# Configuration

SIM-PANEL runs are configured with YAML files. A generation config specifies
where panelist and product records come from, which exposure policy to use, how
many periods to generate, how outcomes should be produced, and where outputs
should be written.

The configuration layer is the bridge between static YAML and runtime objects:
it loads records, validates required sections, wires policies and outcome models,
and constructs the generator used by the CLI.

## Required structure

A generation config has three required top-level sections:

- `panelists`
- `products`
- `policy`

Optional top-level sections include:

- `generator`
- `selection`
- `execution`
- `outcomes_model`
- `questionnaire`
- `backend`
- `output_dir`

A small random-assignment config may look like this:

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
  event_namespace: minimal-random

outcomes_model:
  name: deterministic

questionnaire:
  outcomes:
    fields:
      rating:
        type: int
        choices: [1, 2, 3, 4, 5]
        question: "Overall, how much do you like this product?"
  traces:
    fields:
      review_text:
        type: text
        question: "Write a short review in 2–4 sentences."

output_dir: outputs/minimal_random
```

This configuration loads panelists and products from JSONL files, assigns
products randomly, generates three periods, fills a deterministic questionnaire,
and records the intended output directory as `outputs/minimal_random`.

## User-facing YAML and runtime config

The public YAML layout keeps major concerns as top-level sections. During loading,
SIM-PANEL normalizes these sections into runtime dataclasses.

Typical mapping:

| YAML section | Runtime role |
| --- | --- |
| `panelists` | Persona records, selected persona-text variant, optional enrichment and panelist settings. |
| `products` | Product records, selected display-text variant, optional enrichment. |
| `policy` | Exposure policy configuration. |
| `generator` | Run-level generation settings. |
| `selection` | Prompting and parsing behavior for self-selection. |
| `execution.rules` | Generator-side operational rules applied after selection. |
| `outcomes_model` | Outcome model selection. |
| `questionnaire` | Structured outcome and trace fields. |
| `backend` | Optional local or server-style chat backend. |
| `output_dir` | Intended output directory stored in the normalized run config. |

This separation matters: policies decide exposure, panelists may perform
selection or evaluation, outcomes parse and validate questionnaire responses,
and generators own event construction and validation.

## `panelists`

The `panelists` section identifies the persona records used in a run.

```yaml
panelists:
  source: examples/data/panelists.jsonl
  variant: default
```

Common fields:

| Field | Required | Description |
| --- | --- | --- |
| `source` | Yes | Path to a panelist/persona JSONL file. |
| `variant` | No | Persona-text variant to use. Defaults to `default`. |
| `enrich` | No | Optional persisted persona-text enrichment settings. |
| `eval_settings` | No | Optional settings passed to panelists during evaluation. |
| `select_settings` | No | Optional settings passed to panelists during self-selection. |

Panelist records may contain structured attributes, persona text, or both. The
selected `variant` determines which rendered persona representation is used at
runtime.

Runtime panelists are built from the loaded records. Their structured attributes
are attached as identity features and may be emitted as `panelist_features` in
evaluation events.

## `products`

The `products` section identifies the product or intervention records used in a
run.

```yaml
products:
  source: examples/data/products.jsonl
  variant: default
```

Common fields:

| Field | Required | Description |
| --- | --- | --- |
| `source` | Yes | Path to a product JSONL file. |
| `variant` | No | Product display-text variant to use. Defaults to `default`. |
| `enrich` | No | Optional persisted display-text enrichment settings. |

The selected product variant controls what the panelist sees during evaluation
or self-selection.

Runtime products are built from the loaded records. Product attributes may be
emitted as `product_features` in events.

## `policy`

The `policy` section controls exposure: how panelists and products are paired.

```yaml
policy:
  name: random
```

Supported policy names:

| Policy | Pairing mechanism |
| --- | --- |
| `random` | Products are assigned to panelists exogenously. |
| `manual` | Product-panelist assignments are loaded from a user-provided schedule. |
| `self_selection` | Panelists choose products from a candidate set. |

Policies control exposure. Outcome generation is handled separately by the
outcome model.

## Random assignment

Random assignment is the simplest policy:

```yaml
policy:
  name: random
```

The generator uses the configured random seed to control exposure sampling and
assignment shuffles. This mode is useful for controlled experiments,
RCT-style baselines, and deterministic sanity checks.

## Manual assignment

Manual assignment uses a file-backed schedule. This is useful for scripted
experiments, designed interventions, or ablations.

```yaml
policy:
  name: manual
  manual:
    format: csv_long
    path: examples/policies/manual_schedule.csv
```

For manual policy runs, `policy.manual.format` and `policy.manual.path` are
required.

Supported schedule formats are:

| Format | Description |
| --- | --- |
| `csv_long` | Long CSV schedule. |
| `json` | JSON schedule. |

A long CSV schedule typically identifies the period, panelist, and product to
expose:

```text
t,panelist_id,product_id
0,panelist_001,product_001
0,panelist_002,product_003
1,panelist_001,product_002
```

The configuration loader validates the schedule against available panelist and
product IDs. Invalid IDs should fail at configuration-load time rather than
during generation.

## Self-selection

Self-selection allows panelists to choose which products to interact with. This
mode introduces endogenous exposure and may emit both `selection` and
`evaluation` events.

A minimal self-selection policy uses `policy.name: self_selection`:

```yaml
policy:
  name: self_selection
```

Selection prompting and parsing behavior is configured separately under
`selection`, while generator-side execution rules are configured under
`execution.rules`.

## `selection`

The optional `selection` section controls selection prompt rendering and response
parsing. It governs what the panelist is asked to return, not what the generator
ultimately executes.

```yaml
selection:
  allow_empty: true
  include_features: true
  require_json_only: true
  max_selected_soft: null
  include_raw_text: true
```

Fields:

| Field | Default | Description |
| --- | --- | --- |
| `allow_empty` | `true` | Whether an empty selection is permissible after parsing. |
| `include_features` | `true` | Whether product features are included in the selection prompt. |
| `require_json_only` | `true` | Whether the prompt requires strict JSON-only output. |
| `max_selected_soft` | `null` | Optional soft hint in the prompt; not a hard execution constraint. |
| `include_raw_text` | `true` | Whether to keep raw model text in the parsed selection result for debugging. |
| `custom_few_shot_example` | `null` | Optional few-shot example used when `generator.prompting_strategy` is `few_shot`. |

Selection expects JSON only:

```json
{"selected_product_ids": ["product_001", "product_003"], "traces": {"notes": "..."}}
```

The parsed result records the product IDs requested by the panelist. The
generator may later apply execution rules to filter invalid IDs, enforce caps, or
handle empty selections.

## `execution`

The optional `execution` section controls generator-side operational rules for
self-selection runs. These are not panelist-facing constraints; they are applied
after selection parsing.

Execution rules are nested under `execution.rules`:

```yaml
execution:
  rules:
    enforce_subset_of_choice_set: true
    max_evals_per_panelist_per_t: null
    allow_empty: true
    keep_strategy: keep_first
```

Fields:

| Field | Default | Description |
| --- | --- | --- |
| `enforce_subset_of_choice_set` | `true` | Drop selected product IDs that were not in the shown choice set. |
| `max_evals_per_panelist_per_t` | `null` | Optional cap on executed evaluations per panelist per period. `null` means unlimited. |
| `allow_empty` | `true` | Whether the generator may execute no evaluations after filtering. |
| `keep_strategy` | `keep_first` | Strategy used when applying a cap. In v0, `keep_first` preserves panelist order. |

Selection is what the panelist requests. Execution is what the system actually
evaluates.

## `generator`

The optional `generator` section controls run-level generation behavior.

```yaml
generator:
  schema_version: "0.1.0"
  seed: 42
  n_periods: 5
  validate_on_finish: true
  max_errors: 50
  include_panelist_features_in_events: true
  include_product_features_in_events: true
  include_product_features_in_selection_prompt: true
  event_namespace: sim_panel.v0
  max_workers: 1
  prompting_strategy: persona
  row_meta:
    experiment: beer-demo
```

Fields:

| Field | Default | Description |
| --- | --- | --- |
| `schema_version` | `"0.1.0"` | Event schema version to emit. |
| `seed` | `0` | Random seed for deterministic non-LLM generation. |
| `n_periods` | `1` | Number of time periods to generate. |
| `validate_on_finish` | `true` | Whether to validate rows after generation. |
| `max_errors` | `50` | Maximum validation errors to report before stopping. |
| `include_panelist_features_in_events` | `true` | Whether evaluation events include panelist features. |
| `include_product_features_in_events` | `true` | Whether events include product features. |
| `include_product_features_in_selection_prompt` | `true` | Whether product features may be forwarded into selection prompts. |
| `event_namespace` | `"sim_panel.v0"` | Namespace used for stable event-id generation. |
| `max_workers` | `1` | Number of concurrent decision workers. `1` means sequential. |
| `prompting_strategy` | `"persona"` | Prompting strategy. Supported values include `zero_shot`, `few_shot`, `persona`, and `persona_cot`. |
| `row_meta` | `{}` | Small metadata dictionary merged into each emitted row. |

For reproducibility, keep `seed`, `schema_version`, input files, policy settings,
questionnaire settings, and backend settings fixed across runs.

## `outcomes_model`

The optional `outcomes_model` section controls how product evaluations are
converted into structured outcomes and traces.

SIM-PANEL supports deterministic and LLM-backed outcome models.

A deterministic model is suitable for tests, CI, and CPU-only pipeline debugging:

```yaml
outcomes_model:
  name: deterministic
```

The deterministic outcome model fills the questionnaire using stable hashes of
`panelist_id`, `product_id`, and `t`.

LLM-backed evaluation uses the configured panelist backend:

```yaml
outcomes_model:
  name: llm

backend:
  name: ollama
  model: qwen2.5:7b
```

If `outcomes_model.name` is `llm`, a top-level `backend` section is required.

LLM-backed outcomes may not be exactly reproducible unless the backend, model
version, prompts, decoding parameters, and runtime behavior are controlled.

## `questionnaire`

The `questionnaire` section defines the structured fields collected during
evaluation.

Outcome fields are stored under `event["outcomes"]`. Trace fields are stored
under `event["traces"]`.

Each field is defined by a name, type, question, and optional validation rules.

```yaml
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
      rationale:
        type: text
        question: "Explain the main reasons for your responses."
```

Supported field types:

| Type | Meaning |
| --- | --- |
| `int` | Integer-valued response. |
| `float` | Floating-point response. |
| `categorical` | Response from a fixed set of choices. |
| `bool` | Boolean response. |
| `text` | Free-text response. |
| `json` | JSON-valued response. |

Each field may include:

| Field | Description |
| --- | --- |
| `type` | Field type. Required. |
| `question` | User-facing prompt. Required. |
| `instruction` | Optional formatting guidance. |
| `choices` | Optional allowed values. Recommended for categorical and discrete integer fields. |

For categorical or discrete integer fields, `choices` is recommended because it
allows validation to catch malformed model outputs.

LLM evaluation must return JSON only, with the expected shape:

```json
{
  "outcomes": {
    "rating": 5,
    "purchase_intent": "yes"
  },
  "traces": {
    "review_text": "Short review text.",
    "rationale": "Brief rationale."
  }
}
```

Field names must match the YAML keys exactly.

## `backend`

The optional `backend` section configures a local or server-style chat backend.
It is required when a run uses LLM-backed enrichment or LLM-backed outcomes.

Example local backend:

```yaml
backend:
  name: ollama
  model: qwen2.5:7b
```

Example server-style backend:

```yaml
backend:
  name: server
  model: local-model-name
  base_url: http://localhost:8000/v1
```

The backend interface is provider-agnostic: other modules depend on the SIM-PANEL
backend contract rather than vendor-specific SDKs.

## Persisted enrichment

SIM-PANEL can persistently enrich panelist or product records before generation.
This is useful when structured records need rendered text variants for prompts.

Panelist enrichment:

```yaml
panelists:
  source: examples/data/panelists.jsonl
  variant: default
  enrich:
    enabled: true
    save: in_place
```

Product enrichment:

```yaml
products:
  source: examples/data/products.jsonl
  variant: default
  enrich:
    enabled: true
    save:
      path: outputs/enriched_products.jsonl
```

Enrichment requires a configured `backend` because it calls the backend chat
interface.

If `save: in_place`, the source file is overwritten with enriched records. If
`save: {path: ...}` is used, enriched records are written to the specified path
and the normalized run config is updated to use that path.

## `output_dir`

The optional `output_dir` field records the intended output directory:

```yaml
output_dir: outputs/run_001
```

The configuration loader stores this value in the normalized run config. The CLI
may still override or construct run directories and pass them to the IO writers,
for example via `--out`.

A typical generation run writes:

```text
events.jsonl
metadata.json
data_dictionary.json
```

Optional outputs may include:

```text
events.csv
```

`events.jsonl` is the primary dataset output. `events.csv` is optional and
intended for convenience; nested structures are JSON-serialized into string
cells.

`metadata.json` records run bookkeeping such as generation time, schema version,
seed, row counts, panelist/product/period counts, policy name, optional config
snapshot, and config hash.

`data_dictionary.json` records schema version and JSONable snapshots of key
configs/specs, including generator config, policy config, selection config,
execution rules, and outcome config.

## Complete deterministic example

The following example combines random assignment, deterministic outcomes, schema
validation, and an explicit output directory.

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

Run it with:

```bash
sim-panel generate --config examples/configs/minimal.yaml
```

or override the output directory from the command line:

```bash
sim-panel generate \
  --config examples/configs/minimal.yaml \
  --out outputs/quickstart_override
```

## Complete self-selection example

The following example enables self-selection and applies explicit execution
rules after panelist choice.

```yaml
panelists:
  source: examples/data/panelists.jsonl
  variant: default
  select_settings:
    temperature: 0
  eval_settings:
    temperature: 0

products:
  source: examples/data/products.jsonl
  variant: default

policy:
  name: self_selection

selection:
  allow_empty: true
  include_features: true
  require_json_only: true
  max_selected_soft: 2
  include_raw_text: true

execution:
  rules:
    enforce_subset_of_choice_set: true
    max_evals_per_panelist_per_t: 2
    allow_empty: true
    keep_strategy: keep_first

generator:
  schema_version: "0.1.0"
  seed: 42
  n_periods: 2
  validate_on_finish: true
  event_namespace: self-selection-example
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
  traces:
    fields:
      rationale:
        type: text
        question: "Explain the main reason for your rating."

output_dir: outputs/self_selection_example
```

In this example, `selection.max_selected_soft` is only a prompt-level hint.
The hard cap is `execution.rules.max_evals_per_panelist_per_t`.

## Complete LLM-backed example

The following example uses an LLM backend for questionnaire evaluation.

```yaml
panelists:
  source: examples/data/panelists.jsonl
  variant: default
  eval_settings:
    temperature: 0

products:
  source: examples/data/products.jsonl
  variant: default

policy:
  name: random

generator:
  schema_version: "0.1.0"
  seed: 42
  n_periods: 2
  validate_on_finish: true
  event_namespace: llm-example
  prompting_strategy: persona

outcomes_model:
  name: llm

questionnaire:
  outcomes:
    fields:
      rating:
        type: int
        choices: [1, 2, 3, 4, 5]
        question: "Overall, how much do you like this product?"
  traces:
    fields:
      rationale:
        type: text
        question: "Explain the main reason for your rating."

backend:
  name: ollama
  model: qwen2.5:7b

output_dir: outputs/llm_example
```

This configuration requires a working backend. LLM results may vary if backend
settings, model versions, prompts, or runtime behavior change.

## Fail-fast behavior

Configuration loading should fail early when required sections are missing,
required keys are absent, manual schedules reference unavailable IDs, enrichment
is requested without a backend, or LLM outcomes are requested without a backend.

This is intentional. SIM-PANEL treats YAML files as executable research
specifications, so invalid assumptions should be caught before generation begins.

## Related pages

- [Quickstart](quickstart.md) for a minimal end-to-end run.
- [Schema](schema.md) for event-level fields and validation rules.
- [Generation](generation.md) for the generator pipeline.
- [Sources](sources.md) for real-data adapters.
- [Benchmarks](benchmarks.md) for freezing benchmark-ready real-data subsets.