# Generation

SIM-PANEL generation turns configured panelists, products, policies, decisions,
and outcome models into schema-compliant event rows.

The event generator owns orchestration: it advances time, calls exposure
policies, invokes panelist selection or evaluation, constructs event rows, and
runs validation.

## High-level flow

A generation run follows this structure:

```text
YAML config
  -> runtime panelists and products
  -> EventGenerator
  -> exposure decisions
  -> selection or evaluation
  -> outcome model
  -> schema rows
  -> validation
  -> output artifacts
```

At runtime, the generator receives:

- `Panelist` objects;
- `Product` objects;
- a `GeneratorConfig`.

It returns event dictionaries suitable for JSONL output. Output writing is
handled by the CLI and IO layer.

## Component boundaries

| Component | Responsibility |
| --- | --- |
| Policy | Decide exposure: which products are assigned or shown. |
| Panelist | Perform selection and evaluation actions. |
| Decisions | Render selection prompts, parse selection output, and apply execution rules. |
| Outcome model | Produce structured outcomes and traces. |
| Schema | Validate rows and self-selection links. |
| Generator | Orchestrate components and emit event rows. |

Policies are pure exposure logic. They do not call LLMs, perform IO, define
questionnaires, or create schema rows.

## Period loop

For each period `t`, the generator:

1. sets each panelist's runtime period;
2. calls the configured policy;
3. executes each exposure decision;
4. emits selection and/or evaluation events;
5. optionally calls an outcome model;
6. appends period rows to the run output.

## Exposure decisions

Policies return `ExposureDecision` objects. Each decision is associated with one
panelist and one period.

There are two decision shapes:

| Decision shape | Used by | Meaning |
| --- | --- | --- |
| `evaluate_product_ids` | `random`, `manual` | Directly evaluate these products. |
| `selection` | `self_selection` | Show a choice set and ask the panelist to select products. |

## Random assignment

Random assignment directly assigns products to panelists.

```yaml
policy:
  name: random
  evals_per_period: 1
  random_mode: balanced_quota
```

Supported random modes:

| Mode | Description |
| --- | --- |
| `balanced_quota` | Near-balanced product allocation within each period. |
| `iid_probs` | Independent per-panelist draws from product probabilities. |

For non-uniform exposure:

```yaml
policy:
  name: random
  evals_per_period: 1
  random_mode: iid_probs
  product_probs:
    product_001: 0.5
    product_002: 0.3
    product_003: 0.2
```

If `product_probs` is omitted under `iid_probs`, the policy uses uniform
sampling.

## Manual assignment

Manual assignment directly assigns products using a pre-loaded schedule or
mapping function.

```yaml
policy:
  name: manual
  manual:
    format: csv_long
    path: examples/policies/manual_schedule.csv
```

The manual policy consumes an in-memory assignment function. File parsing,
validation, and wiring happen in the configuration/IO layer.

Manual assignment emits evaluation events directly.

## Self-selection

Self-selection is a two-stage exposure pattern.

First, the policy determines what the panelist sees. Then the panelist chooses
which products to request for evaluation.

```yaml
policy:
  name: self_selection
  choice_set_size: null
  allow_empty_selection: true
```

If `choice_set_size` is `null`, the full product catalog is shown. If it is set,
the policy samples a shortlist without replacement.

The policy controls only the shown choice set. Execution rules decide which
requested products are actually evaluated.

## Selection and execution

Selection prompting is controlled by `selection`:

```yaml
selection:
  allow_empty: true
  include_features: true
  require_json_only: true
  max_selected_soft: null
  include_raw_text: true
```

`max_selected_soft` is a prompt-level hint, not a hard cap.

Execution rules are generator-side operational rules:

```yaml
execution:
  rules:
    enforce_subset_of_choice_set: true
    max_evals_per_panelist_per_t: null
    allow_empty: true
    keep_strategy: keep_first
```

Selection records what the panelist requested. Execution records what the system
actually evaluated.

For self-selection, the sequence is:

1. policy constructs a choice set;
2. generator renders a selection prompt;
3. panelist returns a selection response;
4. parser extracts requested product IDs;
5. generator emits a `selection` event;
6. execution rules determine executed products;
7. generator emits linked `evaluation` events.

## Outcome generation

Evaluation events may include structured outcomes and traces.

If no outcome model is configured, evaluation rows have `outcomes` and `traces`
set to `null`.

If an outcome model is configured, the generator constructs an evaluation context
containing panelist ID, product ID, period, product display text, and optional
panelist/product features.

The outcome model returns:

| Returned field | Stored in event |
| --- | --- |
| `outcomes` | `event["outcomes"]` |
| `traces` | `event["traces"]` |
| `errors` | `event["traces"]["outcome_errors"]` |

Deterministic outcome models are useful for tests, CI, and schema debugging.
LLM-backed outcome models are optional and require a backend.

## Event rows

The generator emits two event types:

| Event type | Emitted when |
| --- | --- |
| `selection` | A self-selection choice set is shown and parsed. |
| `evaluation` | A product is evaluated. |

For self-selection evaluations, `selection_id` links the evaluation event back to
the corresponding selection event.

## Determinism

SIM-PANEL generation is deterministic for non-LLM components when inputs and
seeds are fixed.

The configured seed controls:

- exposure sampling;
- balanced random assignment shuffles;
- self-selection shortlist sampling;
- deterministic event-ID inputs.

LLM calls are not inherently deterministic. For reproducible LLM-backed runs,
keep backend settings, model versions, prompts, and decoding parameters fixed.
For CI and schema tests, prefer deterministic or mock components.

## Parallel execution

The generator supports concurrent decision execution:

```yaml
generator:
  max_workers: 1
```

`max_workers: 1` runs sequentially. Larger values use a thread pool and reassemble
results in decision order before appending rows.

Parallelism can speed up LLM-backed runs, but reproducibility still depends on
backend behavior.

## Prompting strategy

The generator passes a prompting strategy into selection and outcome calls.

```yaml
generator:
  prompting_strategy: persona
```

Supported values include:

| Strategy | Description |
| --- | --- |
| `zero_shot` | Generic task prompt without persona conditioning. |
| `few_shot` | Includes few-shot examples where configured. |
| `persona` | Uses the panelist persona. |
| `persona_cot` | Persona-conditioned prompting with additional reasoning-style instruction. |

## Validation

If validation is enabled, the generator validates rows after generation:

```yaml
generator:
  validate_on_finish: true
  max_errors: 50
```

Validation includes:

- row-level schema validation;
- event-ID uniqueness;
- self-selection linkage checks.

Validation failure raises an error before the run is treated as successful.

## Checkpointing

The CLI supports checkpoint/resume behavior for interrupted generation runs.

When resuming, SIM-PANEL checks that the config fingerprint matches the saved
checkpoint. If the config changed, resume fails and the user should use a new
output directory or clear the checkpoint.

## Boundary rules

The generator should stay orchestration-focused. It should not parse YAML,
perform source import, define policy logic, implement backend clients, or compute
comparison metrics.

Those responsibilities belong to configuration, sources, policies, backends,
analysis, and comparison modules.

## Related pages

- [Configuration](configs.md) for YAML-driven run setup.
- [Schema](schema.md) for event fields and validation rules.
- [Sources](sources.md) for real-data adapters.
- [CLI](cli.md) for the `generate` command.