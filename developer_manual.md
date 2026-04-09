# Developer Manual

<p align="center">
  <img src="assets/logo2.svg" alt="sim-panel logo" width="300"/>
</p>

This companion manual documents the architecture of `sim-panel` for developers. It explains the functions, interfaces, and design boundaries of each module, and shows how the main components fit together into the end-to-end generation pipeline.

## Table of Contents
## Table of Contents
- [Backends overview](#backends-overview)
  - [Core contract](#core-contract)
  - [Messages](#messages)
  - [Backend API](#backend-api)
  - [Configuration (YAML-governed essentials)](#configuration-yaml-governed-essentials)
  - [Registry pattern](#registry-pattern)
  - [Included Backends](#included-backends)
    - [ollama](#ollama)
    - [server](#server)

- [Panelists overview](#panelists-overview)
  - [What it is](#what-it-is)
  - [Key concepts](#key-concepts)
  - [Main files](#main-files)
  - [Typical usage](#typical-usage)
    - [Load panelists](#load-panelists)
    - [Enrich `persona_text` from `attributes` (one-time)](#enrich-persona_text-from-attributes-one-time)

- [Products overview](#products-overview)
  - [What it is](#what-it-is-1)
  - [Key concepts](#key-concepts-1)
  - [Main files](#main-files-1)
  - [Typical usage](#typical-usage-1)
    - [Load products](#load-products)
    - [Get what the panelist should see](#get-what-the-panelist-should-see)
    - [Enrich `display_text` for a campaign (one-time)](#enrich-display_text-for-a-campaign-one-time)
  - [Design invariants](#design-invariants)

- [Schema overview](#schema-overview)
  - [What the schema represents](#what-the-schema-represents)
  - [Key fields (v0.1.0)](#key-fields-v010)
  - [Versioning & registry](#versioning--registry)
  - [Validation utilities](#validation-utilities)

- [Policies overview](#policies-overview)
  - [Core contract](#core-contract-1)
  - [Policy behaviors](#policy-behaviors)
    - [Random (`policies/random.py`)](#random-policiesrandompy)
    - [Manual (`policies/manual.py`)](#manual-policiesmanualpy)
    - [Self-selection (`policies/self_selection.py`)](#self-selection-policiesself_selectionpy)
  - [Generator–Policy boundary (important)](#generatorpolicy-boundary-important)

- [Outcomes overview](#outcomes-overview)
  - [Core concepts](#core-concepts)
    - [QuestionnaireSpec (YAML-defined)](#questionnairespec-yaml-defined)
    - [Prompt rendering](#prompt-rendering)
    - [Strict output format](#strict-output-format)
    - [Parsing and validation](#parsing-and-validation)
  - [Models](#models)
    - [DeterministicOutcomeModel](#deterministicoutcomemodel)
    - [LLMOutcomeModel](#llmoutcomemodel)
  - [Registry](#registry)

- [Decisions overview](#decisions-overview)
  - [Selection prompt and parsing](#selection-prompt-and-parsing)
    - [SelectionContext](#selectioncontext)
    - [SelectionConfig](#selectionconfig)
    - [Prompt rendering](#prompt-rendering-1)
    - [Strict output format](#strict-output-format-1)
    - [Parsing](#parsing)
  - [Generator-side operational rules (execution budget)](#generator-side-operational-rules-execution-budget)
  - [Event semantics](#event-semantics)

- [Generators overview](#generators-overview)
  - [Core entrypoint](#core-entrypoint)
  - [High-level flow (per run)](#high-level-flow-per-run)
  - [Determinism](#determinism)
  - [GeneratorConfig highlights](#generatorconfig-highlights)
  - [Boundary rules (important)](#boundary-rules-important)

- [IO overview](#io-overview)
  - [Atomic writes](#atomic-writes)
  - [JSONL utilities](#jsonl-utilities)
  - [Record IO](#record-io)
  - [Metadata artifact (`metadata.json`)](#metadata-artifact-metadatajson)
  - [Data dictionary artifact (`data_dictionary.json`)](#data-dictionary-artifact-data_dictionaryjson)
  - [CSV output (optional)](#csv-output-optional)
  - [Paths helpers](#paths-helpers)

- [Config overview](#config-overview)
  - [Entry points](#entry-points)
  - [Required YAML structure](#required-yaml-structure)
  - [Persisted enrichment (panelists/products)](#persisted-enrichment-panelistsproducts)
  - [Manual policy loader wiring](#manual-policy-loader-wiring)
  - [Runtime object construction](#runtime-object-construction)
  - [Output_dir](#output_dir)
  - [Fail-fast philosophy](#fail-fast-philosophy)

- [Analysis overview](#analysis-overview)
  - [Design principles](#design-principles)
  - [Current module structure](#current-module-structure)
  - [Main files](#main-files-2)
    - [`types.py`](#typespy)
    - [`config.py`](#configpy)
    - [`metadata.py`](#metadatapy)
    - [`resolve.py`](#resolvepy)
    - [`run.py`](#runpy)
    - [`runner.py`](#runnerpy)
    - [`tables.py`](#tablespy)
  - [Metrics overview](#metrics-overview)
    - [`metrics/utils.py`](#metricsutilspy)
    - [`metrics/quality.py`](#metricsqualitypy)
    - [`metrics/diversity.py`](#metricsdiversitypy)
    - [`metrics/persona.py`](#metricspersonapy)
    - [`metrics/selection.py`](#metricsselectionpy)
  - [Typical analysis flow](#typical-analysis-flow)
  - [Example YAML shape](#example-yaml-shape)
  - [Plot generation](#plot-generation)
  - [Design principles](#design-principles-1)
  - [Current plot families](#current-plot-families)
    - [Outcome distributions](#outcome-distributions)
    - [Panelist summary plots](#panelist-summary-plots)
    - [Product summary plots](#product-summary-plots)
    - [Selection concentration plots](#selection-concentration-plots)
  - [Current module structure](#current-module-structure-1)
  - [Plot YAML configuration](#plot-yaml-configuration)
  - [Meaning of the current options](#meaning-of-the-current-options)
    - [`outcome_distributions`](#outcome_distributions)
    - [`panelist_summary`](#panelist_summary)
    - [`product_summary`](#product_summary)
    - [`selection_concentration`](#selection_concentration)
  - [Current artifact behavior](#current-artifact-behavior)
  - [Current limitations](#current-limitations)
  - [Artifact writing and report generation](#artifact-writing-and-report-generation)
    - [`summary/`](#summary)
    - [`metrics/`](#metrics)
    - [`plots/`](#plots)
    - [`report/`](#report)
  - [Export controls](#export-controls)
  - [Current scope of markdown reporting](#current-scope-of-markdown-reporting)
  - [Regression analysis module](#regression-analysis-module)
    - [What it does](#what-it-does)
    - [Design philosophy](#design-philosophy)
    - [Main components](#main-components)
    - [Supported regression designs](#supported-regression-designs)
    - [Collinearity handling](#collinearity-handling)
    - [Covariance / inference options](#covariance--inference-options)
    - [Output artifacts](#output-artifacts)
    - [Interpretation caution](#interpretation-caution)
  - [Analysis YAML: regression-enabled example](#analysis-yaml-regression-enabled-example)
  - [Available options by section](#available-options-by-section)
    - [`load`](#load)
    - [`summaries`](#summaries)
    - [`metrics`](#metrics-1)
    - [`plots.outcome_distributions`](#plotsoutcome_distributions)
    - [`plots.panelist_summary` and `plots.product_summary`](#plotspanelist_summary-and-plotsproduct_summary)
    - [`plots.selection_concentration`](#plotsselection_concentration)
    - [`regression.options`](#regressionoptions)
    - [`regression.specs[*].family`](#regressionspecsfamily)
    - [`regression.specs[*].design`](#regressionspecsdesign)
    - [`regression.specs[*].outcome_field`](#regressionspecsoutcome_field)
    - [`export`](#export)
  - [Current scope and limitations](#current-scope-and-limitations)

- [Sources overview](#sources-overview)
  - [Design goals](#design-goals)
  - [Current structure](#current-structure)
  - [Core abstractions](#core-abstractions)
    - [`SourceConfig`](#sourceconfig)
    - [`SourceRawBundle`](#sourcerawbundle)
    - [`SourceExportBundle`](#sourceexportbundle)
    - [`SourceStats`](#sourcestats)
  - [Base interface and registry](#base-interface-and-registry)
    - [`BaseSource`](#basesource)
    - [Source registry](#source-registry)
  - [Amazon Reviews’23 source](#amazon-reviews23-source)
    - [Import model](#import-model)
    - [Product identity](#product-identity)
    - [Product mapping](#product-mapping)
    - [Persona mapping](#persona-mapping)
    - [Event mapping](#event-mapping)
    - [Outcomes](#outcomes-1)
    - [Traces](#traces)
    - [Time index `t`](#time-index-t)
  - [Import modes](#import-modes)
    - [`in_memory`](#in_memory)
    - [`streaming`](#streaming)
    - [Streaming support by time index mode](#streaming-support-by-time-index-mode)
  - [Loader / transform / export / streaming separation](#loader--transform--export--streaming-separation)
    - [`loader.py`](#loaderpy)
    - [`transform.py`](#transformpy)
    - [`export.py`](#exportpy)
    - [`streaming.py`](#streamingpy)
  - [CLI integration](#cli-integration)
  - [Example configuration](#example-configuration)
  - [Progress reporting and large-file imports](#progress-reporting-and-large-file-imports)
  - [Current limitations](#current-limitations-1)
    - [In-memory path does not scale to very large categories](#in-memory-path-does-not-scale-to-very-large-categories)
    - [Streaming path does not yet support `global_sequence`](#streaming-path-does-not-yet-support-global_sequence)
    - [Independent caps can reduce metadata overlap](#independent-caps-can-reduce-metadata-overlap)
    - [Event provenance remains schema-constrained](#event-provenance-remains-schema-constrained)

- [Benchmarks overview](#benchmarks-overview)
  - [What it is](#what-it-is-2)
  - [Current benchmark subset scope](#current-benchmark-subset-scope)
  - [Current benchmark outputs](#current-benchmark-outputs)
  - [Design notes and planned extensions](#design-notes-and-planned-extensions)

## Backends overview
`sim_panel/backends/` provides a single, provider-agnostic interface for anything that looks like “send messages → get text back”. Everything else in the repo (`panelists/products/generators`) should depend on this interface, not on vendor-specific SDKs.

### Core contract
- Input: a list of chat messages
- Output: a ChatResult (text + optional usage + raw response)
```python
from sim_panel.backends.base import Backend, BackendConfig
from sim_panel.backends.types import Message, ChatResult
```
### Messages
```python
{"role": "system"|"user"|"assistant"|"tool", "content": "..."}
```
### Backend API
```python
res = backend.chat(
    messages,
    temperature=0.2,
    max_tokens=256,
    metadata={"module": "panelists.enrich"},
)
text = res.content
```
### Configuration (YAML-governed essentials)
Backends are configured via `BackendConfig`, which is typically constructed from YAML.
Recommended YAML shape:
```yaml
backend:
  name: ollama          # mock | ollama | server | (future: gemini, etc.)
  model: gemma3:12b
  seed: 0
  return_usage: false
  params:
    base_url: http://localhost:11434
    timeout_s: 60
```
- `name`: which backend implementation to use
- `model`: model identifier used by that backend
- `seed`: best-effort deterministic seed (supported by some backends; ignored by others)
- `return_usage`: if true, backend tries to populate token usage fields
- `params`: backend-specific settings (e.g., `base_url`, `headers`, auth env-var names)

### Registry pattern
Backends are created by name via a registry:
```python
from sim_panel.backends import get_registry
from sim_panel.backends.base import BackendConfig

cfg = BackendConfig(
    name="ollama",
    model="gemma3:12b",
    seed=0,
    return_usage=False,
    params={"base_url": "http://localhost:11434", "timeout_s": 60},
)

backend = get_registry().create(cfg)
```

### Included Backends
#### ollama
Use case: local dev with Ollama (`/api/chat`), no API keys.
- Default `base_url`: `http://localhost:11434`
- Endpoint: `/api/chat`
- Model chosen by `backend.model` (e.g., `gemma3:12b`)
YAML:
```yaml
backend:
  name: ollama
  model: gemma3:12b
  params:
    base_url: http://localhost:11434
    timeout_s: 60
```

#### server
Use case: remote/self-hosted inference on GPU/cluster (e.g., vLLM/TGI/SGLang gateways).
- Generic HTTP backend speaking a chat-completions-style schema
- Intended target: servers exposing something like `POST {base_url}/chat/completions` (often under `/v1/...`)
YAML:
```yaml
backend:
  name: server
  model: Qwen/Qwen2.5-7B-Instruct
  params:
    base_url: http://<host>:8000/v1
    endpoint: chat/completions   # optional; default shown
    timeout_s: 120
```

## Panelists overview

### What it is

`panelists/` manages synthetic panelist personas in two layers:
-	`PersonaRecord` (canonical, persisted): what you store/load from `personas.jsonl` (or CSV).
-	`Panelist` (runtime agent): wraps a `persona_text` (system prompt) + an optional LLM `Backend` and exposes `.evaluate()`.

### Key concepts
- `persona_id`: internal stable identifier (not shown to the panelist).
- `persona_text`: the system prompt used to drive an LLM panelist. This is the “end all” for inference-time evaluation.
-attributes: optional structured persona fields used for feature extraction/policies/outcomes; not required for evaluation if persona_text exists.
-`variants`: `persona_text_variant` lets you store multiple persona_text realizations (e.g., `default` vs `strict`) per persona.

### Main files
- `records.py`: `PersonaRecord` (fields: `persona_id`, `persona_text`, `attributes`, `persona_text_variant`, hashes, `provenance`)
- `io.py`: `JSONL` read/write + atomic save + merge helpers
- `render.py`: prompt renderer used to generate `persona_text` from `attributes`
- `enrich.py`: `ensure_persona_text(records, backend, settings, overwrite=False)` generates missing `persona_text` once and logs provenance (model/usage)
- `panelist.py`: runtime `Panelist` + `PanelistState` + `EvalSettings` (defaults governed by `YAML`)
- `factory.py`: `build_panelists(records, backend, variant, eval_settings)` → list of runtime panelists

### Typical usage

#### Load panelists

```python
from sim_panel.panelists import load_persona_records, build_panelists, EvalSettings
from sim_panel.backends import build_backend  # your factory
# backend = build_backend(cfg.backend)

records = load_persona_records("data/personas/personas.jsonl")
panelists = build_panelists(
    records,
    backend=backend,
    variant="default",
    eval_settings=EvalSettings(temperature=0.2, max_tokens=512, metadata={"module": "eval"}),
)
```

#### Enrich `persona_text` from `attributes` (one-time)

```python
from sim_panel.panelists import ensure_persona_text, PersonaTextGenSettings, save_persona_records

records = ensure_persona_text(
    records,
    backend=backend,
    settings=PersonaTextGenSettings(prompt_version="v1", temperature=0.2, max_tokens=300),
    variant="default",
    overwrite=False,
)
save_persona_records("data/personas/personas.jsonl", records)
```

---

## Products overview

### What it is

`products/` manages items or interventions that panelists evaluate. It separates:
- Internal ID (`product_id`) — stable, not shown to panelists
- Human-facing exposure (`display_name`, `display_text`) — what panelists “see”
- Structured features (`attributes`) — for policies/outcomes and deterministic rendering

### Key concepts
- `display_name`: short label shown to panelists (e.g., “Anchor IPA”, “Trial Arm B: 10% discount”).
- `display_text`: longer stimulus text; optional; can be LLM-enriched to fit a campaign/experiment.
- `attributes`: required structured product/intervention fields (ABV, price; or trial parameters).
- `variants`: `display_variant` lets you store multiple `display_text` realizations per product (e.g., different campaigns).

### Main files
- `records.py`: `ProductRecord` (fields: `product_id`, `attributes`, `display_name`, `display_text`, `display_variant`, hashes, `meta`, `provenance`)
- `io.py`: `JSONL` read/write + atomic save + merge helpers
- `render.py`: `render_product_display(product_record)` returns the stimulus to embed in prompts (prefers `display_text`, otherwise uses `display_name` + `attributes`)
- `enrich.py`: `ensure_display_text(records, backend, settings, overwrite=False)` generates missing `display_text` once and logs `provenance` (model/usage)
- `product.py`: runtime `Product` wrapper with `.display()` convenience
- `factory.py`: `build_products(records, variant)` → list of `Product`

### Typical usage

#### Load products

```python
from sim_panel.products import load_product_records, build_products

records = load_product_records("data/products/products.jsonl")
products = build_products(records, variant="default")
```

#### Get what the panelist should see

```python
from sim_panel.products import render_product_display

stimulus = render_product_display(products[0].record)
```

#### Enrich display_text for a campaign (one-time)

```python
from sim_panel.products import ensure_display_text, ProductDisplayTextGenSettings, save_product_records

records = ensure_display_text(
    records,
    backend=backend,
    settings=ProductDisplayTextGenSettings(
        prompt_version="v1",
        temperature=0.3,
        max_tokens=200,
        campaign="Spring promo A/B",
        tone="enthusiastic",
        length="short",
        metadata={"module": "product_display_text"},
    ),
    variant="default",
    overwrite=False,
)
save_product_records("data/products/products.jsonl", records)
```

---

### Design invariants
- Never show `persona_id` / `product_id` to the panelist by default.
- Panelist evaluation is driven by `persona_text` (system prompt).
- Product exposure is driven by `display_name`/`display_text` (stimulus).
- `attributes` are structured and stable; text fields are optional, enrichable, and provenance-tracked.
- Enrichment functions are idempotent under `overwrite=False` (generate once, reuse forever).

## Schema overview

`sim_panel/schema/` defines the versioned contract for all generated datasets and provides validation utilities. Everything that emits or consumes data (policies, outcomes, IO, CLI) should treat the schema as the source of truth.

### What the schema represents

The core artifact is an events table (JSONL by default). Each row is an event. In v0.1.0, the schema supports two event types:

#### `selection` events (self-selection only)

A choice set is presented to a panelist at time `t`, and the panelist selects a subset (possibly empty).
- Allowed only when `policy == "self_selection"`.
- Records:
    - `choice_set`: list of candidate `product_ids` shown
	- `selected_product_ids`: subset chosen (may be `[]`)
	- Must not include evaluation-only fields (`product_display`, `outcomes`, `traces`, etc.)

#### `evaluation` events (all policies)

A single panelist–product evaluation at time `t`.
- Allowed when `policy` in `{"random", "manual", "self_selection"}`.
- Records:
    - `product_id`: evaluated product
    - `product_display`: panelist-facing text (distinct from internal `product_id`)
    - `outcomes:` flexible JSON payload (e.g., rating, purchase_intent, etc.)
    - `traces`: optional JSON payload (e.g., review_text, rationale, logits)
- If `policy == "self_selection"`, `selection_id` is required to link back to the corresponding `selection` event.

### Key fields (v0.1.0)

All events share:
- `schema_version` (e.g., `"0.1.0"`)
- `event_id` (deterministic unique id)
- `event_type`: `"selection"` or `"evaluation"`
- `policy`: `"random"` | `"manual"` | `"self_selection"`
- `panelist_id`
- `t` (0-based period index)

Selection-only payload:
- `choice_set`: `List[str]`
- `selected_product_ids`: `List[str]`

Evaluation-only payload:
- `product_id`: `str`
- `product_display`: `str`
- `panelist_features`: `JSON` (may be `{}`)
- `product_features`: `JSON` (may be `{}`)
- `outcomes`: `JSON` | `null`
- `traces`: `JSON` | `null`

Linking:
- `selection_id`: `str` | `null`
    - optional on `selection` rows
    - required on `self_selection` `evaluation` rows
    - should reference the `event_id` of the corresponding selection row at the same `(panelist_id, t)`

### Versioning & registry

Schemas are stored under `sim_panel/schema/versions/` and registered in `sim_panel/schema/registry.py`.
- `get_schema(version)` returns a `SchemaSpec(version, model)` where `model` is a Pydantic model (e.g., `EventV0_1_0`).
- The registry is the single place to add future versions (`v0_2_0`, etc.).


### Validation utilities

`sim_panel/schema/validate.py` provides:
- `validate_rows(rows, schema_version=None, max_errors=50)` -> `ValidationReport`
Validates row structure/types against the schema.
If `schema_version=None`, validates using each row’s own `schema_version` field.
- `validate_unique_event_id(rows)` -> `(ok, message)`
Checks global uniqueness of `event_id`.
- `validate_self_selection_links(rows)` -> `(ok, problems)`
Cross-row checks for `v0.1.0`:
- self-selection evaluation rows must reference an existing `selection_id`
- referenced selection must match the same `(panelist_id, t)`


## Policies overview

`policies/` defines **pure exposure logic**: who sees what, when.

Policies return **exposure decisions** that `generators/` executes and converts into **schema-compliant events**.

### Core contract

Each policy implements:

- `Policy.decide(rng, panelist_id, t, product_ids) -> ExposureDecision`

Where `ExposureDecision` is one of:
- **evaluation assignment** (random/manual): `evaluate_product_ids: list[str]`
- **self-selection exposure**: `selection: SelectionSpec` with a `choice_set: list[str]`

Addtionally, `RandomAssignmentPolicy` allows batch decisions:
- `RandomAssignmentPolicy.decide_batch(rng, panelist_ids, t, product_ids) -> List[ExposureDecision]`

Policies are intentionally schema-agnostic; they return **domain decisions**, not event rows.

---

## Policy behaviors

### Random (`policies/random.py`)
Default intent: emulate an RCT-style assignment.

Supported modes (YAML via `PolicyConfig.random_mode`):
- `balanced_quota` (default): near-equal panelist counts per product **within each period `t`**.
  - Best for comparisons across products; reduces variance and accidental imbalance.
  - Implemented via a per-period pool of product IDs repeated to match `n_panelists * evals_per_period`, shuffled with the run RNG.
  - **Recommended integration:** generator calls a batch helper (e.g., `decide_batch(...)`) for each `t` to guarantee balance.
- `iid_probs`: per-panelist draws from a product probability distribution.
  - Use when modeling targeting / non-uniform exposure.
  - If `product_probs` not provided, defaults to uniform.

Notes:
- `evals_per_period` controls how many products each panelist evaluates per period.

### Manual (`policies/manual.py`)
Manual exposure uses a **pre-loaded mapping** (schedule) injected at build time.

- Policy consumes `manual_assignment_fn(panelist_id, t, product_ids) -> str | list[str]`.
- Policies stay pure: **no file parsing or IO here**.

**Where mapping is processed:**
- Mapping files (CSV/JSON/YAML) are loaded and validated in `io/`.
- `generators/` (or config loader) wires the resulting in-memory schedule into `PolicyConfig.manual_assignment_fn`.

Recommended mapping format (v0):
- Long format table: `(panelist_id, t, product_id)` with `t` optional (default 0).

### Self-selection (`policies/self_selection.py`)
Self-selection is a two-stage exposure pattern.

- Policy controls only the **choice set** shown to the panelist.
- **Default:** show **all products** (choice_set = full catalog).
- Optional: set `choice_set_size` to sample a shortlist uniformly without replacement (for large catalogs).

Panelist free will:
- The panelist (LLM) decides *what* and *how many* items they want to evaluate.
- Any operational caps (budget/limits) are applied **in `generators/`**, not as a policy constraint.

---

## Generator–Policy boundary (important)

- `policies/` decides **exposure** (choice sets / forced assignments).
- `panelists/` performs **actions** using the persona-endowed LLM:
  - `Panelist.select(...)` for self-selection (separate LLM call)
  - `Panelist.evaluate(...)` for evaluation (separate LLM call)
- `generators/` orchestrates:
  - looping over `t`, calling policies
  - emitting `selection` + `evaluation` events per schema
  - calling panelists for selection/evaluation
  - applying execution budgets / parsing/cleaning selection output
  - schema validation and IO streaming

Design principle:
- **Policies remain deterministic and testable** (no LLM, no IO).
- **Generators own orchestration and event emission**.

## Outcomes overview

`outcomes/` implements **evaluation as a YAML-governed questionnaire**. After a panelist evaluates a product, the system asks them to fill in a structured form and returns:

- `event["outcomes"]`: structured, verifiable reward fields (e.g., rating, purchase_intent)
- `event["traces"]`: optional auxiliary fields (e.g., review_text, rationale, debug info)

`outcomes/` is designed for **LLM-based evaluation** but also provides **deterministic stubs** for CI and pipeline debugging.

### Core concepts

#### QuestionnaireSpec (YAML-defined)
Outcomes and traces are specified by the user via YAML. Each field is defined by a spec:

- **name**: the JSON key (must match exactly)
- **type**: one of `int | float | categorical | bool | text | json`
- **question**: the user-facing prompt (“How much do you like it?”)
- **instruction** (optional): formatting guidance (“Pick one integer.”)
- **choices** (optional, recommended for categorical / discrete int): allowed values

Example shape:
```yaml
questionnaire:
  outcomes:
    fields:
      rating:
        type: int
        choices: [1,2,3,4,5]
        question: "Overall, how much do you like this product?"
      purchase_intent:
        type: categorical
        choices: ["no","maybe","yes"]
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
#### Prompt rendering
`outcomes.render.render_evaluation_prompt(...)` converts the questionnaire spec into an evaluation prompt that includes:
- product stimulus (`product_display` is primary)
- optional `product_features` (JSON)
- a field-by-field form with choices/rules
- strict output instructions

**Important:** Panelist attributes are assumed to be encoded in `persona_text` and are not required in the prompt.

#### Strict output format
LLM evaluation must return **JSON only**:
```json
{"outcomes": {...}, "traces": {...}}
```
Field names must match YAML keys exactly.

#### Parsing and validation
`outcomes.parsing.extract_json_object(...)` extracts a JSON object defensively.  
`QuestionnaireSpec.validate_payload(...)` validates:
- required keys present
- types match
- choices respected
- min/max constraints satisfied

Extra keys are allowed but surfaced as warnings (`[warn] ...`).

On hard failure, `OutcomeResult.outcomes` is `None` and `traces` carries debug info:
- `parse_error` or `validation_errors`
- `raw_excerpt` (truncated)

### Models

#### DeterministicOutcomeModel
`outcomes.deterministic.DeterministicOutcomeModel` fills the questionnaire deterministically using hashes of `(panelist_id, product_id, t)`. Used for:
- determinism tests
- schema/pipeline scaffolding
- CPU-only runs

#### LLMOutcomeModel
`outcomes.llm.LLMOutcomeModel`:
1) renders the prompt from the questionnaire spec  
2) calls `panelist.evaluate(task_prompt=...)`  
3) parses JSON and validates against the spec  +
4) returns `OutcomeResult(outcomes, traces, errors, raw_text?)`

### Registry
`outcomes.registry.build_outcome_model(...)` instantiates `deterministic` or `llm`.  
`outcomes.registry.outcome_config_from_yaml_dict(...)` is a convenience helper to build `OutcomeConfig` + `QuestionnaireSpec` from a YAML-parsed dict.

---

## Decisions overview

`decisions/` defines **selection as a structured decision task** (distinct from evaluation outcomes). It supports self-selection policies where the panelist chooses which products to evaluate.

Design principles:
- **Policies** control exposure (what is shown / choice set).
- **Panelist** makes the selection via LLM (`Panelist.select(...)`).
- **Generator** applies operational rules (budgets/caps) after parsing selection.
- **Selection is separate from evaluation** (separate LLM calls).

### Selection prompt and parsing

#### SelectionContext
`SelectionContext` contains:
- `panelist_id`, `t`
- `products_shown`: list of items, each with:
  - `product_id` (stable identifier, used for output)
  - `product_display` (human-facing stimulus)
  - optional `product_features` (only if enabled)

Panelist features are not rendered (persona already encoded in `persona_text`).

#### SelectionConfig
Controls selection prompt/rendering and parsing behavior:
- `allow_empty` (default true): whether empty selection is permissible
- `include_product_features` (default true): include `product_features` in the prompt
- `require_json_only` (default true): instruct strict JSON output
- `max_selected_soft` (optional): *soft hint* only (not a panelist constraint)
- `include_raw_text` (debugging)

#### Prompt rendering
`decisions.selection.render_selection_prompt(...)` renders:
- a list of shown products (id + display + optional features)
- instructions emphasizing free choice
- strict JSON-only output instructions

#### Strict output format
Selection expects **JSON only**:
```json
{"selected_product_ids": ["p1","p2"], "traces": {"notes": "..."}}
```

#### Parsing
`decisions.selection.parse_selection_response(...)`:
- extracts JSON  
- validates `selected_product_ids` is a list of strings  
- dedupes while preserving order  
- returns `SelectionResult(requested_product_ids, traces, errors, raw_text?)`

### Generator-side operational rules (execution budget)

Selection is **what the panelist requests**. Execution is **what the system actually evaluates**.

`ExecutionRules` (applied by generator, not shown to panelist) includes:
- `enforce_subset_of_choice_set`: drop IDs not in the shown set
- `max_evals_per_panelist_per_t`: optional cap (None = unlimited)
- `allow_empty`: if false and empty, generator decides fallback (e.g., re-prompt)
- `keep_strategy`: v0 supports `keep_first` (preserve panelist order)

`decisions.selection.apply_execution_rules(...)` returns:
- `(executed_product_ids, dropped_product_ids)`

### Event semantics
For `policy == self_selection`:
- generator emits a `selection` event with:
  - `choice_set` (what was shown)
  - `selected_product_ids` (panelist requested ids, after parsing; optional filtering can be logged)
- generator emits `evaluation` events for the executed subset (post budget rules), each linked via `selection_id`.

## Generators overview

`generators/` is the **orchestration layer** that turns the repo’s building blocks into a schema-compliant events table (JSONL rows). It owns:

- simulation clock (`t`)
- RNG / determinism for exposure decisions and event ids
- calling policies for exposure
- calling panelists for selection + evaluation (LLM)
- calling outcomes for questionnaire parsing/validation
- converting everything into **schema rows** and validating them

`generators/` must not contain policy logic or questionnaire definitions; it wires together:
- `policies/` (exposure)
- `decisions/` (selection prompt + parsing + execution rules)
- `outcomes/` (evaluation questionnaire prompt + parsing/validation)
- `schema/` (row validation)

### Core entrypoint

`EventGenerator(cfg).generate(panelists=..., products=...) -> list[dict]`

Inputs:
- `panelists`: runtime `Panelist` objects (LLM-capable), including `panelist_id`, `persona_text`, `attributes`, `state`.
- `products`: runtime `Product` wrappers, including `product_id`, `record`, and `display()`.

Output:
- a list of event dicts suitable for JSONL emission (streaming IO can be layered later).

### High-level flow (per run)

For each period `t = 0..n_periods-1`:

1. **Advance time**
   - generator sets `panelist.state.t = t` (generator owns the clock)

2. **Exposure decisions (policy)**
   - generator calls `policy.decide(...)` per panelist
   - for `random` with `balanced_quota`, generator uses the policy’s batch decision helper (e.g., `decide_batch(...)`) to guarantee RCT-style balance

3. **Execution**
   - **random/manual**: generator emits evaluation events for `evaluate_product_ids`
   - **self_selection**:
     - generator constructs a selection prompt via `decisions.render_selection_prompt(...)`
       - shows product list using `Product.display()`
       - includes product features only if configured
     - generator calls `Panelist.select(...)` (separate LLM call)
     - parses the result via `decisions.parse_selection_response(...)`
     - emits a `selection` event recording:
       - `choice_set` (what was shown)
       - `selected_product_ids` (what the panelist requested; free will)
     - applies generator-side operational rules via `decisions.apply_execution_rules(...)` to obtain the executed subset
     - emits linked `evaluation` events for executed items with `selection_id` pointing to the selection event

4. **Evaluation outcomes**
   - generator constructs `EvaluationContext` and calls `outcome_model.evaluate(...)`
   - writes `event["outcomes"]` and `event["traces"]` from the returned `OutcomeResult`
   - `panelist_features` in events come from `Panelist.attributes` (identity features)
   - product features in events come from `Product.attributes`

5. **Schema validation**
   - optional end-of-run validation:
     - schema row validation
     - unique `event_id` check
     - self-selection link integrity check (`selection_id` references)

### Determinism

Generators ensure deterministic behavior (conditional on deterministic backends):
- RNG seeded by `cfg.seed` controls exposure sampling and balanced assignment shuffles
- `event_id` uses a deterministic hash of stable payload fields (`stable_event_id(namespace, payload)`)

Note: LLM calls are not inherently deterministic. For reproducibility, prefer:
- temperature=0
- fixed prompts and model versions
- caching (future)

### GeneratorConfig highlights

- `schema_version`, `seed`, `n_periods`
- `policy: PolicyConfig` (random/manual/self_selection)
- `selection: SelectionConfig` (selection prompt behavior; product_features only)
- `execution: ExecutionConfig` (`ExecutionRules` such as caps, subset enforcement)
- `outcome: OutcomeConfig | None` (LLM or deterministic questionnaire evaluation)
- `validate_on_finish`, `max_errors`
- `event_namespace` (for stable id hashing)
- `row_meta` (small metadata merged into each row)

### Boundary rules (important)

- **Policies are pure** (no backend calls, no IO, no schema rows).
- **Panelists perform LLM actions** (`select`, `evaluate`).
- **Decisions parse/guard selection** and apply execution rules (budgeting on our side).
- **Outcomes parse/validate questionnaire** and return structured `outcomes`/`traces`.
- **Generators own orchestration + event emission + validation**.

## IO overview
`io/` provides the repo’s **canonical read/write layer**. It is intentionally generic and reusable across modules, and supports:

- primary dataset output: **JSONL**
- secondary output: **CSV** (optional; nested fields JSON-serialized)
- run artifacts: **metadata.json** + **data_dictionary.json**
- record IO: read/write `PersonaRecord` and `ProductRecord` JSONL

Design goals:
- deterministic outputs (stable key ordering)
- crash-safe writes (atomic replace)
- minimal assumptions about higher-level modules

### Atomic writes

`io.atomic.atomic_write_bytes(path, data)` and `atomic_write_text(...)`:
- write to a temp file in the **same directory**
- `fsync` the temp file
- atomically swap into place using `os.replace`
- best-effort cleanup of temp files on failure

This prevents partially-written outputs if generation is interrupted.

### JSONL utilities

`io.jsonl`:
- `read_jsonl_dicts(path) -> list[dict]`
- `write_jsonl_dicts(path, rows)` / `write_jsonl_rows(...)`

Writes are JSONL with:
- one JSON object per line
- `ensure_ascii=False`
- `sort_keys=True` for stable diffs
- atomic write

### Record IO

`io.records`:
- `read_persona_records_jsonl(path) -> list[PersonaRecord]`
- `write_persona_records_jsonl(path, records)`
- `read_product_records_jsonl(path) -> list[ProductRecord]`
- `write_product_records_jsonl(path, records)`

Domain modules may keep their own convenience wrappers (e.g., stable sorting, merge helpers) but should delegate JSONL writing/reading to `io/`.

### Metadata artifact (`metadata.json`)

`io.metadata`:
- `build_metadata(...) -> dict`
- `write_metadata_json(path, metadata)`

Metadata includes:
- `generated_at_utc`
- `schema_version`, `seed`
- counts: rows/panelists/products/periods
- policy name
- optional `config_snapshot` (typically YAML parsed dict or subset)
- `config_hash_sha256` (via `utils.hashing.sha256_json`) for quick equivalence checks

Purpose:
- reproducibility and run bookkeeping
- lightweight summary without opening the dataset

### Data dictionary artifact (`data_dictionary.json`)

`io.dictionary`:
- `build_data_dictionary(...) -> dict`
- `write_data_dictionary_json(path, data_dictionary)`

Data dictionary records:
- schema version
- JSONable snapshots of key configs/specs:
  - generator config
  - policy config
  - selection config
  - execution rules
  - outcome config (including questionnaire spec)
- optional human notes

Purpose:
- “legend/contract” for downstream users: explains what `outcomes` and `traces` mean
- preserves semantics alongside the dataset output

`_to_jsonable(...)` converts dataclasses and nested structures into JSON-serializable payloads for this artifact.

### CSV output (optional)

`io.csv_io.write_csv_rows(path, rows, fieldnames=None)`:
- writes a CSV header + rows
- nested structures (dict/list) are JSON-serialized into string cells
- intended for convenience only (JSONL is primary)

### Paths helpers

`io.paths`:
- `ensure_dir(path)` creates output directories
- `RunFilenames` / `default_run_filenames()` provide conventional run filenames:
  - `events.jsonl`, `events.csv`, `metadata.json`, `data_dictionary.json`


## Config overview

`config/` is the **YAML-to-runtime wiring layer**. It translates a YAML run specification into a fully-built, ready-to-run bundle:

- `EventGenerator` (wired with policy/selection/execution/outcomes configs)
- runtime `Panelist` objects (LLM-capable, persona-endowed)
- runtime `Product` objects (with display rendering)
- config snapshots for reproducibility

`config/` is responsible for:
- parsing YAML and enforcing required sections
- loading persona/product records from disk
- **persisted enrichment orchestration** (optional, YAML-governed)
- wiring manual policy schedules (YAML-governed, file-backed)
- constructing dataclass configs (`PolicyConfig`, `SelectionConfig`, `ExecutionRules`, `OutcomeConfig`, `GeneratorConfig`)
- building runtime objects using domain factories

It must not:
- generate events (that’s `generators/`)
- write run outputs (that’s `io/` + CLI)

### Entry points

- `build_run_from_yaml(path) -> RunBundle`
- `build_run_from_dict(d) -> RunBundle`

`RunBundle` contains:
- `generator: EventGenerator`
- `panelists: list[Panelist]`
- `products: list[Product]`
- `config_snapshot: dict` (raw YAML dict for metadata)
- `run_config: RunConfig` (normalized paths/variants/output_dir)

### Required YAML structure

Required top-level sections:
- `panelists`:
  - `source`: personas JSONL path
  - `variant`: persona_text_variant (default: "default")
  - optional: `enrich`, `eval_settings`, `select_settings`
- `products`:
  - `source`: products JSONL path
  - `variant`: display_variant (default: "default")
  - optional: `enrich`
- `policy`:
  - `name`: `random | manual | self_selection`

Optional top-level sections:
- `generator`, `selection`, `execution`
- `outcomes_model`, `questionnaire`
- `backend`
- `output_dir`

### Persisted enrichment (panelists/products)

If `panelists.enrich.enabled: true`:
- `config/` calls `panelists.enrich.ensure_persona_text(...)` to generate missing `persona_text` for the chosen variant.
- Enrichment writes provenance into each `PersonaRecord.provenance["persona_text"]` (generated_at, prompt_version, backend model, usage).
- Results are **persisted** via `panelists.io.save_persona_records(...)`:
  - `save: in_place` (default) overwrites the source file
  - `save: {path: "..."}` writes to a separate file
- `RunConfig.personas_path` is updated to the saved path (important for later reuse).

If `products.enrich.enabled: true`:
- `config/` calls `products.enrich.ensure_display_text(...)` to generate missing `display_text`.
- Persists via `products.io.save_product_records(...)` with the same `save` semantics.
- Updates `RunConfig.products_path` accordingly.

Backend requirement:
- enrichment requires `backend` because it calls `backend.chat(...)`.
- if outcomes are LLM-based (`outcomes_model.name: llm`), backend is also required.

### Manual policy loader wiring

If `policy.name: manual`, YAML must include:
- `policy.manual.format`: `csv_long` or `json`
- `policy.manual.path`: mapping file path

`config/` loads and validates the schedule using `io.manual_schedule.load_manual_schedule(...)`, then injects:
- `PolicyConfig.manual_assignment_fn = schedule.to_fn(...)`

Validation is performed at config-load time against available IDs for the selected variants:
- allowed `panelist_id`s come from persona records of the chosen variant
- allowed `product_id`s come from product records of the chosen variant

### Runtime object construction

- Panelists: built via `panelists.factory.build_panelists(...)`
  - requires `persona_text` to be present for selected variant
  - attaches `attributes` to runtime `Panelist` (identity features)
  - passes `backend`, `eval_settings`, `select_settings` defaults

- Products: built via `products.factory.build_products(...)`
  - filters by `display_variant`
  - wraps each `ProductRecord` as runtime `Product(record=...)`

### Output_dir

`output_dir` is stored in `RunConfig` but not used directly by `config/`.
CLI will typically override or construct run directories and pass them to `io/` writers.

### Fail-fast philosophy

`config/` enforces missing/invalid YAML structure early:
- required sections/keys must exist and be well-typed
- manual policy requires `policy.manual`
- enrichment requires backend
- llm outcomes require backend

This avoids deferred runtime failures during generation.

## Analysis overview

`sim_panel/analysis/` provides a config-driven post-processing layer for generated runs. Its job is to load one run from `outputs/`, interpret it through the run metadata, compute selected summaries and metrics, and write a reproducible analysis bundle to disk.

The analysis layer is designed around a **single-run-first** philosophy. The native unit of analysis is one run directory, typically containing `events.jsonl`, `metadata.json`, and companion output files. Multi-run comparison is treated as a later layer built on top of standardized single-run summaries, rather than as the core abstraction from the outset.

### Design principles

- **One run is the native analysis unit.**  
  A run is the combination of generated event outputs under `outputs/<run_name>/` plus metadata-traced provenance to the original persona/product source files.

- **Analysis is YAML-governed.**  
  Like generation, analysis is controlled through a YAML file. The YAML specifies which run to analyze, where to write the analysis artifacts, whether to resolve linked source files, and which summaries/metrics to compute.

- **Metadata is the source of provenance.**  
  The analysis layer relies primarily on `metadata.json` rather than file naming conventions. In particular, `metadata.json` stores the run configuration snapshot and the paths needed to trace back to persona and product source files.

- **Linked source files are optional enrichments.**  
  Many summaries and metrics can be computed directly from `events.jsonl`, since evaluation rows already carry panelist features and product features. Source resolution is still supported so that later analyses can use richer upstream information when needed.

- **Summaries and metrics are separate responsibilities.**  
  `tables.py` produces human-readable structured summaries; `metrics/` computes reusable analytic diagnostics. This separation keeps the analysis layer modular and easier to extend.

### Current module structure

```text
sim_panel/
  analysis/
    __init__.py
    types.py
    config.py
    metadata.py
    resolve.py
    run.py
    runner.py
    tables.py
    metrics/
      __init__.py
      utils.py
      quality.py
      diversity.py
      persona.py
      selection.py
```

### Main files

#### `types.py`
Defines the core analysis dataclasses:

- `AnalysisConfig`: normalized analysis configuration extracted from YAML
- `RunAnalysis`: in-memory representation of one analyzed run, including:
  - all event rows
  - selection rows
  - evaluation rows
  - raw metadata
  - flattened metadata summary
  - optional linked persona/product source records
  - computed analysis artifacts

#### `config.py`
Parses a YAML config into an `AnalysisConfig`, following the same style as the generation/config layer. The YAML currently supports:

- `run_dir`
- `output_dir`
- `load`
- `summaries`
- `metrics`
- `plots`
- `export`

This module is responsible only for validation and normalization of analysis config, not for executing the analysis.

#### `metadata.py`
Flattens nested `metadata.json` into a compact analysis-facing record. This makes later comparison and reporting easier by exposing stable top-level keys such as:

- run name
- schema version
- policy
- seed
- backend name/model
- outcome model temperature
- counts
- config path
- personas/products source paths

It also exposes questionnaire field declarations for outcomes and traces.

#### `resolve.py`
Resolves linked source files from metadata. In particular, it traces persona and product sources from:

- `extra.personas_path` / `extra.products_path`
- or fallback paths inside `config_snapshot.panelists.source` / `config_snapshot.products.source`

This module makes source loading optional and robust to missing files.

#### `run.py`
Implements the single-run loading and orchestration logic. It:

1. loads `events.jsonl`
2. loads `metadata.json`
3. flattens metadata
4. splits events into `selection` and `evaluation` rows
5. optionally resolves linked persona/product source files
6. computes the requested summaries and metrics

This is the main internal entry point for single-run analysis.

#### `runner.py`
Provides the top-level `run_analysis(...)` entry point. At present, it delegates to the single-run analysis pipeline. Over time, this file can grow to coordinate exports, plots, and richer analysis workflows.

#### `tables.py`
Builds summary records for one run. Current summaries include:

- **run summary**
  - row counts
  - event type counts
  - policy/schema/seed/backend info
  - observed panelist/product/period counts
  - provenance paths

- **outcome summary**
  - declared questionnaire outcome fields
  - observed counts
  - missingness by field
  - lightweight numeric/categorical summaries

- **trace summary**
  - declared questionnaire trace fields
  - observed counts
  - missingness by field
  - text-length summaries where applicable

- **selection summary**
  - average choice-set size
  - average requested/executed/dropped sizes
  - empty-selection rates
  - top requested and executed products

### Metrics overview

The `metrics/` submodule contains reusable analytic diagnostics, separate from descriptive summary tables.

#### `metrics/utils.py`
Shared helpers for metric computation, including:

- safe means/variances
- entropy computation
- observed-support and full-support normalized entropy
- support size
- value counts
- grouped extraction of numeric outcomes

For entropy-based metrics, the design distinguishes between:

- **full-support normalized entropy**: normalized by the full allowed support of the questionnaire or product universe
- **observed-support normalized entropy**: normalized by the categories actually observed in the run

Both are retained because they answer different questions.

#### `metrics/quality.py`
Operational and completeness diagnostics for one run. Current responsibilities include:

- event / selection / evaluation row counts
- rate of non-empty outcomes
- rate of non-empty traces
- panelist-feature and product-feature coverage
- selection linkage rate
- missingness rates by declared outcome field
- missingness rates by declared trace field

This file answers the question: **did the run execute cleanly enough to trust downstream analysis?**

#### `metrics/diversity.py`
Field-level diversity diagnostics for declared outcome fields. Current metrics include:

- raw entropy
- full-support normalized entropy
- observed-support normalized entropy
- observed support size
- allowed support size
- numeric mean/variance where applicable
- value counts

This file answers the question: **how much variation is present in the realized outputs?**

#### `metrics/persona.py`
Panelist/product differentiation diagnostics for numeric outcome fields (currently designed around fields such as `rating`). Current metrics include:

- `panelist_mean_variance`
- `product_mean_variance`
- `mean_within_product_panelist_variance`
- `mean_within_panelist_product_variance`
- `mean_pairwise_panelist_distance`
- `mean_pairwise_product_distance`

These metrics provide a symmetric view of behavioral differentiation along both axes of the evaluation matrix:

- do panelists disagree on the same product?
- does a given panelist distinguish among products?
- are panelist preference profiles distinct?
- are product response profiles distinct across panelists?

#### `metrics/selection.py`
Selection-behavior diagnostics for `selection` rows, especially under `self_selection`. Current metrics include:

- average choice-set size
- average requested/executed/dropped sizes
- empty request/execution rates
- request-to-execution ratio
- drop rate over requested selections
- requested-product entropy
- executed-product entropy
- both full-support and observed-support normalized entropy
- number of unique requested and executed products

This file treats self-selection as a first-class behavioral object, rather than a side effect of evaluation.

### Typical analysis flow

At a high level, the intended workflow is:

1. load analysis YAML
2. load one run from `outputs/<run_name>/`
3. flatten and inspect metadata
4. optionally resolve linked source files
5. split events into selection/evaluation rows
6. compute requested summaries
7. compute requested metrics
8. save artifacts to the requested analysis output directory

### Example YAML shape

```yaml
run_dir: outputs/run_beer_demo_large_self_selection
output_dir: outputs/run_beer_demo_large_self_selection/analysis

load:
  resolve_sources: true
  prefer_extra_paths: true
  strict_source_resolution: false

summaries:
  run: true
  outcomes: true
  traces: true
  selections: true

metrics:
  quality: true
  diversity: true
  persona: true
  selection: true

plots:
  outcome_distributions: true
  persona_diagnostics: false

export:
  csv: true
  json: true
  markdown: true
  overwrite: true
```

### Plot generation

`sim_panel/analysis/plots.py` provides the plotting layer for single-run analysis. It is responsible for turning computed event outcomes and selection behavior into saved visual artifacts under the analysis output directory.

The plotting layer is intentionally kept separate from summaries and metrics:

- `tables.py` builds structured descriptive summaries
- `metrics/` computes reusable analytic diagnostics
- `plots.py` renders selected visual views of those results

This separation makes it easier to iterate on visual outputs without entangling plotting logic with metric computation.

### Design principles

- **Plots are generated from one run at a time.**  
  As with the rest of the analysis layer, plotting is currently single-run-first.

- **Plot families are YAML-configurable.**  
  The analysis YAML specifies which plot families to enable and provides a small set of stable display options.

- **Saved image files are the primary artifact.**  
  Plot functions save `.png` files directly under `analysis/plots/`. The runner also writes a `plot_index.json` file when JSON export is enabled.

- **The plot API is split into a stable entry point plus lower-level functions.**  
  `generate_plots(...)` is the production entry point used by `run.py`, while the individual `plot_*` functions can be imported directly for experimentation or future notebook-style workflows.

### Current plot families

The current implementation supports four plot families.

#### Outcome distributions
These plots visualize the empirical distribution of declared outcome fields from evaluation rows.

Supported outcome types:
- numeric / ordinal (`int`, `float`)
- categorical

Current options include:
- plotting counts or shares
- restricting plots to a subset of declared outcome fields
- controlling figure size

Typical output files include:

- `outcome_distribution_rating_count.png`
- `outcome_distribution_purchase_intent_count.png`

#### Panelist summary plots
These plots summarize one numeric outcome field by `panelist_id`.

Current supported summary metrics:
- `mean`
- `variance`

They are useful for checking whether panelists differ in their overall level or dispersion of responses.

Typical output files include:

- `panelist_mean_rating.png`
- `panelist_variance_rating.png`

#### Product summary plots
These plots summarize one numeric outcome field by `product_id`.

Current supported summary metrics:
- `mean`
- `variance`

They are useful for checking whether products differ in their average appeal or in the spread of responses they elicit.

Typical output files include:

- `product_mean_rating.png`
- `product_variance_rating.png`

#### Selection concentration plots
These plots visualize how selection mass is distributed across products in `selection` rows.

Current supported modes:
- `executed`
- `requested`

They are especially relevant for `self_selection` runs, where one wants to inspect whether choices are concentrated on a narrow subset of products or spread more broadly.

Typical output files include:

- `selection_concentration_executed.png`
- `selection_concentration_requested.png`

### Current module structure

The plotting layer is currently centered on:

- `generate_plots(...)`
- `plot_outcome_distributions(...)`
- `plot_panelist_summary(...)`
- `plot_product_summary(...)`
- `plot_selection_concentration(...)`

Helper functions inside `plots.py` handle:
- value-count bar charts
- labeled summary bar charts
- grouping evaluation outcomes by panelist or product
- counting requested/executed product selections

### Plot YAML configuration

Plot generation is controlled through a nested `plots:` section in the analysis YAML. The current supported shape is:

```yaml
plots:
  outcome_distributions:
    enabled: true
    normalize_to_share: false
    fields: null
    figsize: [7, 4.5]

  panelist_summary:
    enabled: true
    outcome_field: rating
    metrics: [mean, variance]
    max_items: 30
    sort_by: label_asc
    horizontal: false

  product_summary:
    enabled: true
    outcome_field: rating
    metrics: [mean, variance]
    max_items: 30
    sort_by: label_asc
    horizontal: false

  selection_concentration:
    enabled: true
    modes: [executed, requested]
    top_k: 15
    horizontal: true
```

### Meaning of the current options

#### `outcome_distributions`
- `enabled`: whether to generate distribution plots
- `normalize_to_share`: if `true`, plot shares instead of counts
- `fields`: optional subset of declared outcome fields; `null` means plot all declared fields
- `figsize`: size of each plot in inches

#### `panelist_summary`
- `enabled`: whether to generate panelist summary plots
- `outcome_field`: numeric outcome field to summarize, typically `rating`
- `metrics`: one or more of `mean`, `variance`
- `max_items`: truncate to the first `max_items` after sorting
- `sort_by`: one of
  - `label_asc`
  - `label_desc`
  - `value_asc`
  - `value_desc`
- `horizontal`: whether to use a horizontal bar chart

#### `product_summary`
Same options as `panelist_summary`, but grouped by `product_id`.

#### `selection_concentration`
- `enabled`: whether to generate selection concentration plots
- `modes`: one or both of `executed`, `requested`
- `top_k`: show only the top `k` products by count
- `horizontal`: whether to use a horizontal bar chart

### Current artifact behavior

Plot images are always written under:

```text
<analysis_output_dir>/plots/
```

When JSON export is enabled, the analysis runner also writes:

```text
plots/plot_index.json
```

This file maps plot artifact names to the saved image paths, making it easier for downstream tooling or reports to reference generated images.

### Current limitations

The current plotting layer is intentionally modest. It focuses on stable, inspectable single-run diagnostics rather than polished presentation graphics.

Not yet implemented:

- multi-run comparison plots
- embedded plots in markdown or HTML reports
- richer diagnostic figures such as heatmaps or scatter comparisons
- regression-diagnostic plots for attribute usefulness / consistency
- custom styling beyond the current small set of display options

The intended development path is to keep the current plot families stable first, then add richer visual diagnostics only after the summary and metric contracts have settled.

### Artifact writing and report generation

The analysis runner now writes artifacts to a structured output directory under the configured `output_dir`. The current layout is:

```text
<analysis_output_dir>/
  summary/
  metrics/
  plots/
  report/
```

#### `summary/`
Holds structured single-run summaries such as:

- `run_summary`
- `outcome_summary`
- `trace_summary`
- `selection_summary`

Depending on export settings, these are written as JSON and/or CSV.

#### `metrics/`
Holds machine-readable metric artifacts such as:

- `quality_metrics`
- `diversity_metrics`
- `persona_metrics`
- `selection_metrics`

Depending on export settings, these are written as JSON and/or CSV.

#### `plots/`
Holds saved plot images generated by `plots.py`. When JSON export is enabled, the runner also writes a `plot_index.json` file mapping plot artifact names to saved paths.

#### `report/`
Holds lightweight human-readable report artifacts. The current implementation writes:

- `report.md`

This markdown report is intentionally minimal. Its purpose is to give a concise overview of the run, surface the main summary and metric values, and point the reader to the saved JSON/CSV/plot artifacts. It is not intended to replace the machine-readable outputs.

### Export controls

Artifact writing is governed by `export:` in the analysis YAML:

```yaml
export:
  csv: true
  json: true
  markdown: true
  overwrite: true
```

Current behavior:

- `json: true` enables JSON output for summaries, metrics, and `plots/plot_index.json`
- `csv: true` enables CSV output for summaries and selected metrics that can be flattened into row-oriented tables
- `markdown: true` enables `report/report.md`
- `overwrite: true` allows existing artifact files to be replaced

### Current scope of markdown reporting

The current markdown report includes:

- run overview
- selected quality metrics
- selected panelist/product differentiation metrics
- selected selection metrics
- a list of generated plot artifacts

This report is intentionally lightweight. Richer report generation (e.g. more detailed narrative sections, embedded tables, or HTML output) is deferred until the summary/metric contracts stabilize further.

### Regression analysis module

`sim_panel/analysis/regression/` adds a regression layer on top of `RunAnalysis`, so model fitting can be run directly from analyzed event data without introducing a separate preprocessing pipeline.

#### What it does

The regression module currently supports:

- continuous outcomes via `ols`
- binary outcomes via `logit` and `probit`
- nominal categorical outcomes via `multinomial_logit`
- ordinal categorical outcomes via `ordered_logit` and `ordered_probit`

The module is questionnaire-aware. It uses `FieldSpec.analysis_type` and related metadata from `QuestionnaireSpec` to validate whether a requested regression family is compatible with the selected outcome field.

#### Design philosophy

The regression layer is intended primarily for:

- descriptive diagnostics
- fit comparison across specifications
- coefficient pattern inspection
- evaluating whether observed attributes or fixed effects explain synthetic outcomes

It is **not** positioned as a full econometrics package for strong inferential claims. In particular, standard errors and p-values should be interpreted cautiously when:

- observations are repeated within panelists and/or products
- clustering is limited
- the design is highly saturated
- synthetic runs are small

#### Main components

- `registry.py`
  Resolves outcome fields into regression-facing `OutcomeSpec` objects and checks family compatibility.

- `design.py`
  Builds design matrices from `RunAnalysis.evaluation_rows` using the shared flattened evaluation dataframe from `analysis.tables`.

- `preprocess.py`
  Applies target coercion, dummy encoding, optional standardization, intercept handling, and collinearity safeguards.

- `families/`
  Implements family-specific fitting logic:
  - `ols.py`
  - `discrete.py`

- `fit.py`
  End-to-end dispatcher:
  - validates the regression request
  - builds and preprocesses the design matrix
  - resolves covariance settings
  - dispatches to the requested family

- `summarize.py`
  Converts regression results into compact summary rows and filtered coefficient tables.

- `io.py`
  Saves per-model regression outputs to disk.

#### Supported regression designs

The current design names are:

- `panelist_features`
- `product_features`
- `panelist_plus_product_features`
- `panelist_id_fe`
- `product_id_fe`
- `two_way_fe`
- `features_plus_two_way_fe`

These are built from the flattened evaluation dataframe:

- `panelist.*` columns come from `panelist_features`
- `product.*` columns come from `product_features`
- `panelist_id` and `product_id` can be used as fixed-effect identifiers

#### Collinearity handling

The preprocessing layer includes explicit guards against exact collinearity:

- categorical regressors are dummy-encoded with reference-category coding
- constant columns are dropped
- duplicate columns are dropped
- rank-deficient columns are dropped via incremental rank checking

This is especially important for fixed-effect-heavy specifications such as `two_way_fe` and `features_plus_two_way_fe`.

Note that in FE-heavy designs, some static attributes may be absorbed or nearly absorbed by the fixed effects. The preprocessing step records dropped columns so this behavior is auditable.

#### Covariance / inference options

The regression options support several covariance choices:

- `nonrobust`
- `HC1`
- `cluster_panelist`
- `cluster_product`
- `cluster_two_way`

Current support:

- `cluster_two_way` is enabled for `ols`
- nonlinear families currently support the one-way and robust options exposed by the underlying `statsmodels` fit path, but not two-way clustered covariance

#### Output artifacts

When regression is enabled in analysis config, the analysis run stores a `regression` artifact under `run.artifacts["regression"]`.

Each requested spec can produce:

- a compact summary row
- a full coefficient table
- an attribute-only coefficient table
- a top-attribute coefficient table
- a dropped-columns table
- metadata describing covariance type and preprocessing behavior

If saving is enabled, these are written under:

- `analysis/regression/`

Typical files include:

- `*_summary.json`
- `*_metadata.json`
- `*_coefficients_full.csv`
- `*_coefficients_attributes.csv`
- `*_coefficients_top_attributes.csv`
- `*_dropped_columns.csv`

The markdown report also includes:

- a regression section
- compact coefficient tables
- dropped-column tables
- an inference caution note

#### Interpretation caution

Regression outputs are useful for diagnosis and comparison, but should be read carefully.

In particular:

- fixed effects do not by themselves make errors iid
- repeated evaluation rows induce grouped dependence
- clustered inference can be unstable in small runs
- FE-heavy specifications may absorb static panelist/product features
- missing standard errors or confidence intervals usually indicate inference instability, not necessarily missing coefficient estimates

---

### Analysis YAML: regression-enabled example

Below is a documented example analysis config showing all currently supported analysis sections, including regression.

```yaml
run_dir: outputs/run_beer_demo_large_self_selection
output_dir: outputs/run_beer_demo_large_self_selection/analysis

load:
  # Resolve linked persona/product source files if metadata points to them.
  resolve_sources: true

  # Prefer extra metadata paths when multiple possible source paths exist.
  prefer_extra_paths: true

  # If true, fail hard when linked sources cannot be resolved.
  strict_source_resolution: false

summaries:
  # High-level run diagnostics.
  run: true

  # Per-outcome summary tables.
  outcomes: true

  # Per-trace summary tables.
  traces: true

  # Selection summary for runs with selection events.
  selections: true

metrics:
  # Coverage / missingness / linking checks.
  quality: true

  # Outcome diversity metrics.
  diversity: true

  # Panelist/product differentiation metrics.
  persona: true

  # Selection concentration / entropy metrics.
  selection: true

plots:
  outcome_distributions:
    # Plot per-outcome distributions.
    enabled: true

    # If true, show normalized shares rather than raw counts.
    normalize_to_share: false

    # Optional subset of outcome fields. Null means all eligible fields.
    fields: null

    # Figure size as [width, height].
    figsize: [7, 4.5]

  panelist_summary:
    # Summary bars over panelists for a chosen outcome.
    enabled: true

    # Outcome field used for aggregation.
    outcome_field: rating

    # Supported summary metrics currently include "mean" and "variance".
    metrics: [mean, variance]

    # Maximum number of items displayed.
    max_items: 30

    # Current sort options depend on plotting implementation; common values include:
    # - label_asc
    # - mean_desc
    # - variance_desc
    sort_by: label_asc

    # Horizontal or vertical bar layout.
    horizontal: false

  product_summary:
    enabled: true
    outcome_field: rating
    metrics: [mean, variance]
    max_items: 30
    sort_by: label_asc
    horizontal: false

  selection_concentration:
    # Plot concentration of requested/executed products.
    enabled: true

    # Supported modes:
    # - requested
    # - executed
    modes: [executed, requested]

    # Number of products to display.
    top_k: 15

    horizontal: true

regression:
  # Master toggle for regression analysis.
  enabled: true

  # Whether per-model regression outputs should be written to disk.
  save_results: true

  # Subdirectory under analysis output for regression files.
  output_subdir: regression

  options:
    # Drop rows with missing regressors or target before fitting.
    drop_missing: true

    # Standardize numeric regressors before fitting.
    standardize_numeric: false

    # Add intercept where relevant.
    add_intercept: true

    # Maximum optimizer iterations for nonlinear models.
    max_iter: 200

    # Whether to request coefficient-level inference outputs.
    include_inference: true

    # Confidence level used for confidence intervals.
    confidence_level: 0.95

    # Supported covariance types:
    # - nonrobust
    # - HC1
    # - cluster_panelist
    # - cluster_product
    # - cluster_two_way   # currently OLS only
    covariance_type: cluster_panelist

  specs:
    # Each entry defines one requested regression.
    # family must be compatible with the questionnaire outcome field.

    - family: ols
      design: panelist_plus_product_features
      outcome_field: rating

    - family: ols
      design: two_way_fe
      outcome_field: rating

    - family: ols
      design: features_plus_two_way_fe
      outcome_field: rating

export:
  # Export CSV artifacts where supported.
  csv: true

  # Export JSON artifacts.
  json: true

  # Export markdown report.
  markdown: true

  # If false, existing files are preserved.
  overwrite: true
```

---

### Available options by section

#### `load`
- `resolve_sources`: `true | false`
- `prefer_extra_paths`: `true | false`
- `strict_source_resolution`: `true | false`

#### `summaries`
- `run`: `true | false`
- `outcomes`: `true | false`
- `traces`: `true | false`
- `selections`: `true | false`

#### `metrics`
- `quality`: `true | false`
- `diversity`: `true | false`
- `persona`: `true | false`
- `selection`: `true | false`

#### `plots.outcome_distributions`
- `enabled`: `true | false`
- `normalize_to_share`: `true | false`
- `fields`: `null | [field_name, ...]`
- `figsize`: `[width, height]`

#### `plots.panelist_summary` and `plots.product_summary`
- `enabled`: `true | false`
- `outcome_field`: string
- `metrics`: list of metric names, currently typically:
  - `mean`
  - `variance`
- `max_items`: integer
- `sort_by`: string
- `horizontal`: `true | false`

#### `plots.selection_concentration`
- `enabled`: `true | false`
- `modes`: subset of:
  - `requested`
  - `executed`
- `top_k`: integer
- `horizontal`: `true | false`

#### `regression.options`
- `drop_missing`: `true | false`
- `standardize_numeric`: `true | false`
- `add_intercept`: `true | false`
- `max_iter`: integer
- `include_inference`: `true | false`
- `confidence_level`: float, usually `0.95`
- `covariance_type`:
  - `nonrobust`
  - `HC1`
  - `cluster_panelist`
  - `cluster_product`
  - `cluster_two_way`

#### `regression.specs[*].family`
- `ols`
- `logit`
- `probit`
- `multinomial_logit`
- `ordered_logit`
- `ordered_probit`

#### `regression.specs[*].design`
- `panelist_features`
- `product_features`
- `panelist_plus_product_features`
- `panelist_id_fe`
- `product_id_fe`
- `two_way_fe`
- `features_plus_two_way_fe`

#### `regression.specs[*].outcome_field`
Any questionnaire outcome field name that is present in the run metadata and compatible with the requested family.

#### `export`
- `csv`: `true | false`
- `json`: `true | false`
- `markdown`: `true | false`
- `overwrite`: `true | false`

---


### Current scope and limitations

At present, the analysis layer supports:

- single-run loading
- metadata-driven provenance resolution
- structured summary generation
- core metrics for quality, diversity, panelist/product differentiation, and selection behavior
- `plots.py` for visual outputs
- markdown report generation
- multi-run comparison layer
- regression-based attribute diagnostics for consistency and feature usefulness

The following component(s) are planned but not yet implemented:

- benchmark-style comparison against real observed data

These later component(s) should build on the current single-run summary/metric contracts rather than bypassing them.

## Sources overview

The `sources/` module provides a structured import layer for bringing **external observational datasets** into the internal `sim-panel` artifact format. Its role is not to generate synthetic events directly, but to convert raw third-party data into canonical `products.jsonl`, `personas.jsonl`, and `events.jsonl` artifacts that can later be inspected, validated, sampled, analyzed, or used as substrates for downstream simulation.

This module is intended for cases where the project needs to ingest real-world data, preserve useful provenance, and project it into the same internal contracts used elsewhere in the repository.

### Design goals

The `sources/` layer is built around the following principles:

- **Separation of concerns**: raw ingestion, canonical transformation, and export are handled in distinct stages.
- **Canonical internal artifacts**: imported data should end up in the same durable on-disk formats used by the rest of the repo.
- **Schema alignment**: imported event rows must conform to the shared `sim-panel` event schema rather than carry arbitrary source-specific top-level fields.
- **Typed records where appropriate**: imported products and personas are represented using `ProductRecord` and `PersonaRecord`, not ad hoc dictionaries.
- **Source-specific flexibility with shared infrastructure**: each source can define its own config and transformation logic while conforming to a common interface.
- **Reproducible import runs**: imports emit metadata, statistics, and a data dictionary alongside the main JSONL artifacts.
- **Execution-strategy flexibility**: the same source adaptor may support both an in-memory path and a streaming / low-memory path, controlled by configuration rather than by changing the source semantics.

### Current structure

The module currently follows this structure:

```text
sim_panel/
  sources/
    __init__.py
    base.py
    build.py
    registry.py
    types.py

    amazon_reviews_2023/
      __init__.py
      config.py
      loader.py
      transform.py
      export.py
      streaming.py
      source.py
```

### Core abstractions

#### `SourceConfig`
A generic base configuration object for source importers. Source-specific config classes inherit from this and add source-local fields.

Typical responsibilities:
- source name
- output directory
- seed or source-specific parameters
- source-specific import options
- execution strategy options such as import mode

#### `SourceRawBundle`
A lightweight container holding raw source artifacts before transformation.

For the current design, it contains:
- `reviews`: raw review-side rows
- `products`: raw product-side rows
- `aux`: additional import context

This bundle is intentionally generic because raw source structures differ across datasets.

`SourceRawBundle` is primarily used by **in-memory** import paths. Streaming paths may bypass it entirely.

#### `SourceExportBundle`
A canonical container produced by an in-memory source transform.

Current fields:
- `events: List[dict]`
- `products: List[ProductRecord]`
- `personas: List[PersonaRecord]`
- `metadata: dict`
- `data_dictionary: dict`
- `stats: SourceStats`

This design reflects a deliberate long-run choice:
- events remain schema-valid row dictionaries
- products and personas travel as typed record objects end-to-end

For streaming import paths, large artifacts are written directly to disk rather than fully materialized in memory. In that case, a source may return a **lightweight** `SourceExportBundle` carrying only metadata, dictionary, and stats, with `events`, `products`, and `personas` left empty.

#### `SourceStats`
A small structured summary of the import process, used to write `stats.json`.

Current statistics include:
- number of raw reviews loaded or streamed
- number of raw metadata rows loaded or streamed
- number of exported events
- number of exported products
- number of exported personas
- number of review rows missing matched product metadata
- source-specific extras

### Base interface and registry

#### `BaseSource`
All sources inherit from `BaseSource`, which defines the shared interface.

Core methods:
- `validate_config()`
- `load_raw()`
- `transform(raw)`
- `run()`
- `export(bundle, output_dir=None)`
- `export_streaming(output_dir=None)`

The intended execution patterns are:

**In-memory path**
1. validate config
2. load raw source artifacts
3. transform into canonical internal artifacts
4. export to disk

**Streaming path**
1. validate config
2. stream and process source artifacts incrementally
3. write canonical artifacts directly to disk
4. return lightweight metadata / stats

This split is deliberate: `import_mode` should change the **execution strategy**, not the semantic meaning of the imported artifacts.

#### Source registry
The registry provides name-to-source resolution so CLI and higher-level orchestration code do not need to hard-code source classes directly.

This allows a YAML config to declare a source like:

```yaml
source:
  name: amazon_reviews_2023
  ...
```

and then use a builder to instantiate the correct source object.

### Amazon Reviews’23 source

The first implemented source is `amazon_reviews_2023`, which imports Amazon Reviews’23 category files into sim-panel artifacts.

#### Import model

The importer is intentionally asymmetric:

- `products.jsonl` is built from the **item metadata** file
- `personas.jsonl` is derived from **user review histories**
- `events.jsonl` is built from **review rows**

This reflects the structure of the underlying dataset:
- review rows carry `user_id`, `asin`, `parent_asin`, timestamps, ratings, review title/text, purchase flags, and related review-level information
- metadata rows carry product title, description, features, category, store, price, ratings, details, and related product-level information

#### Product identity
For this source, canonical `product_id` is the metadata-side `parent_asin`.

This is a deliberate modeling choice:
- imported products are metadata-backed product-family entities
- review-side child `asin` is preserved in event traces rather than promoted to canonical product identity
- this avoids collisions in `products.jsonl` while still retaining child-level provenance in imported events

#### Product mapping
Imported products are emitted as `ProductRecord` objects.

Current mapping:
- `product_id` <- `parent_asin`
- `display_name` <- metadata `title`
- `display_text` <- metadata `description`
- fallback: `features` if `description` is missing and fallback is enabled
- `attributes` <- compact structured metadata such as category, store, price, ratings, categories, and details
- `meta` <- optional raw source-side product payload
- `provenance` <- source lineage and import timestamp

#### Persona mapping
Imported personas are emitted as `PersonaRecord` objects.

Current mapping:
- `persona_id` <- `user_id`
- `persona_text` <- `None` for source-derived personas
- `attributes` <- summary statistics derived from review history

Current persona summaries include:
- number of reviews
- number of unique products reviewed
- number of verified-purchase reviews
- mean rating when available

These personas are deliberately **spec-like** rather than prompt-like. They are canonical source-derived entities, not ready-made runtime prompts.

#### Event mapping
Imported events are emitted as schema-valid evaluation rows compatible with `EventV0_1_0`.

Current event design:
- `event_type = "evaluation"`
- `policy = "manual"`
- `panelist_id` <- `user_id`
- `product_id` <- `parent_asin`
- `product_display` <- imported product `display_text` or `display_name`
- `panelist_features` <- `PersonaRecord.attributes` when a persona is emitted
- `product_features` <- `ProductRecord.attributes`
- `outcomes` <- observed review-side outcomes
- `traces` <- mapped review text fields plus source-side child provenance
- `selection_id = None`

The event schema forbids unknown top-level fields, so source-specific provenance is not stored in a top-level `meta` field. Instead, the importer keeps events schema-pure and places structured child-level provenance under `traces["source"]` when needed.

#### Outcomes
For Amazon review imports, the current importer keeps the following review-side quantities in `outcomes`:
- `rating`
- `verified_purchase`
- `helpful_vote`

This is a deliberate design choice: although not all of these are preference measures in the narrowest sense, they are event-level observed outcomes attached to the review and may be useful downstream.

#### Traces
The event `traces` field is a single JSON dictionary, aligned with the main event schema and questionnaire design elsewhere in the repository.

Review text fields are mapped into `traces` via `trace_field_map`, for example:

```yaml
trace_field_map:
  title: review_title
  text: review_text
```

This produces traces like:

```json
{
  "review_title": "Loved it",
  "review_text": "Tasty and fresh.",
  "source": {
    "child_asin": "B00EXAMPLE",
    "timestamp": 1680300000000
  }
}
```

This preserves the distinction between:
- textual traces for human interpretation
- structured source provenance

#### Time index `t`
Imported event rows must satisfy the main event schema, where `t` is an integer period index.

For Amazon imports, `t` is derived from source timestamps according to `time_index_mode`.

Currently supported modes:
- `panelist_sequence`: assign `t = 0, 1, 2, ...` within each user after chronological sorting of that user’s reviews
- `global_sequence`: assign a single global event order
- `raw_timestamp`: use raw integer timestamp directly

The recommended default is `panelist_sequence`, since it aligns best with the panel-style schema and preserves within-user temporal ordering without collapsing `t` into wall-clock time.

### Import modes

The Amazon source supports an execution-strategy switch:

```python
import_mode: Literal["in_memory", "streaming"] = "in_memory"
```

This field controls **how** the importer runs, not **what** it means.

#### `in_memory`
The in-memory path:
- loads review rows and metadata rows into a `SourceRawBundle`
- builds products, personas, and events in memory
- assembles a full `SourceExportBundle`
- writes artifacts to disk via `export.py`

This path is straightforward and remains the reference implementation for transformation semantics.

#### `streaming`
The streaming path is designed for large categories where fully materializing all reviews, personas, and events in memory is not practical.

Current streaming design:
- stream metadata rows and write `products.jsonl` incrementally
- retain a product lookup in memory
- stream review rows once and shard them to temporary files by `user_id`
- process each shard independently
- derive personas shard-by-shard and write `personas.jsonl` incrementally
- emit `events.jsonl` incrementally without building a giant in-memory event list

This keeps memory bounded while preserving the same canonical on-disk output contracts.

#### Streaming support by time index mode
Streaming mode currently supports:
- `panelist_sequence`
- `raw_timestamp`

Streaming mode does **not yet** support:
- `global_sequence`

This is deliberate. Exact `global_sequence` semantics require a corpus-wide sort, which is better treated as a separate external-sort problem rather than hidden behind a nominally low-memory path.

### Loader / transform / export / streaming separation

#### `loader.py`
Responsible for raw ingestion helpers:
- open raw review and metadata files
- read JSONL / JSONL.GZ
- provide either eager loading or row iterators

For in-memory mode, it returns a `SourceRawBundle`.

For streaming mode, it exposes iterators such as:
- review-row iterators
- metadata-row iterators

It performs no canonical mapping.

#### `transform.py`
Responsible for the main source-specific projection logic used by the in-memory path:
- build `ProductRecord` objects
- build `PersonaRecord` objects
- build schema-valid event rows
- derive time indices
- map traces
- compute import statistics
- assemble `SourceExportBundle`

This remains the semantic core of the source.

The file also contains reusable row-level helpers that are shared by both in-memory and streaming execution paths.

#### `export.py`
Responsible only for writing transformed artifacts to disk using the shared `io/` layer.

Current outputs:
- `events.jsonl`
- `products.jsonl`
- `personas.jsonl`
- `metadata.json`
- `data_dictionary.json`
- `stats.json`

Because the source bundle stores typed product/persona records, export uses the record-aware IO helpers:
- `write_product_records_jsonl(...)`
- `write_persona_records_jsonl(...)`

while events remain row dictionaries written via:
- `write_jsonl_rows(...)`

#### `streaming.py`
Responsible for the low-memory execution path.

Typical responsibilities:
- stream metadata and build product lookup
- write product records incrementally
- shard review rows by `user_id`
- process shards independently
- derive personas and events without full-corpus materialization
- write final metadata, data dictionary, and stats

This module should be viewed as an **execution orchestration layer**. It reuses the same row-level semantic mapping logic as `transform.py`, but changes the memory strategy.

### CLI integration

The source layer is integrated into the top-level CLI via the `import` command.

Typical usage:

```bash
sim-panel import --config sim_panel/config/examples/import_amazon_reviews_2023.yaml
```

The command performs:
1. YAML loading
2. source construction from config
3. dispatch by `import_mode`
4. either in-memory import or streaming import
5. export / finalize on-disk artifacts

This keeps source import aligned with the style of the existing CLI commands such as `generate`, `validate`, and `sample`, while allowing large-source imports to bypass the in-memory bundle path.

### Example configuration

A typical source-import YAML looks like:

```yaml
source:
  name: amazon_reviews_2023
  output_dir: outputs/import_amazon_grocery_full

  reviews_path: data/raw/amazon/Grocery_and_Gourmet_Food.jsonl
  metadata_path: data/raw/amazon/meta_Grocery_and_Gourmet_Food.jsonl
  category: Grocery_and_Gourmet_Food

  import_mode: streaming

  require_metadata_match_for_events: false

  trace_field_map:
    title: review_title
    text: review_text

  time_index_mode: panelist_sequence

  product_description_fallback_to_features: true
  include_raw_product_meta: true
  include_raw_review_meta: false

  min_reviews_per_persona: 1
  max_reviews: null
  max_metadata_rows: null
```

### Progress reporting and large-file imports

The importer supports progress reporting via `tqdm_wrap(...)`.

In-memory mode may report progress during:
- review loading
- metadata loading
- product construction
- persona grouping / building
- event construction

Streaming mode may report progress during:
- metadata streaming
- review sharding
- shard processing

This is especially important because source files can be large. For smoke tests, capped runs can be used via:
- `max_reviews`
- `max_metadata_rows`

For full imports, progress feedback is important both for user experience and for diagnosing slow stages.

### Current limitations

The current implementation is already functional and supports both reference-scale and larger-scale imports, but several limitations remain.

#### In-memory path does not scale to very large categories
The in-memory path materializes raw reviews and metadata before transformation, and also constructs large persona and event collections in memory. This is fine for smaller runs and as a semantic reference path, but can fail on large categories.

#### Streaming path does not yet support `global_sequence`
Exact global ordering requires a corpus-wide sort. This is intentionally out of scope for the initial streaming path.

#### Independent caps can reduce metadata overlap
If reviews and metadata are independently capped using `max_reviews` and `max_metadata_rows`, the loaded slices may not overlap well on `parent_asin`. This can produce many review rows that do not match loaded metadata rows, even when the full dataset contains the relevant metadata.

This is expected under capped independent prefixes and does not indicate a bug in the importer.

#### Event provenance remains schema-constrained
Because event rows must validate against the shared event schema, they cannot carry arbitrary top-level source metadata fields. The source importer therefore keeps event rows schema-pure and places only selected child-level provenance under `traces["source"]`.

## Benchmarks overview

### What it is

`sim_panel/benchmarks/` provides lightweight utilities for freezing benchmark-ready subsets from already imported real-data artifacts.

In the current Phase 2 path, the benchmark module is intentionally narrow:
- it reads an imported source directory, typically one produced by `sim-panel import`
- it selects a reproducible subset of real events at the product level
- it writes a frozen benchmark directory for downstream comparison

This keeps the original full import untouched. The intended workflow is:

```text
import real data -> freeze benchmark subset -> compare synthetic runs against that reference
```

The current subset builder is streaming-first and uses a two-pass scan over `events.jsonl`:
1. count rating-bearing events per product
2. select eligible products reproducibly with a seed
3. rescan and write only the selected events/products into the benchmark directory

This avoids loading the full imported `events.jsonl` into memory.

### Current benchmark subset scope

The current subset builder is dataset-pertinent: it is designed around the imported Amazon Reviews path and assumes a default imported Amazon Reviews category as its source benchmark pool.

Concretely, the current selection logic is intentionally narrow:
- rating-focused
- product-level eligibility based on review volume
- reproducible seeded selection
- no elaborate stratification in v0

At present, benchmark subsetting operates over the imported dataset as a whole, for example a default imported Amazon Reviews category directory.

A planned extension is to support additional filtering using product-level metadata already present in `products.jsonl`, especially:
- subsetting by `main_category`
- where `main_category` is stored inside product `attributes`

That extension would allow finer benchmark carving within a previously imported source directory without changing the benchmark directory contract.

### Current benchmark outputs

The benchmark subset directory contract is currently:

- `events_real.jsonl`
- `products.jsonl`
- `metadata.json`
- `stats.json`

The current `stats.json` is intentionally high-level. It records summary information about the subsetting event, such as:
- number of selected products
- number of selected events
- number of unique panelists
- aggregate rating histogram
- selected-product review counts

The current rating histogram is aggregate only. It should be interpreted as a quick sanity-check summary of the exported benchmark subset, not as a full per-product diagnostic report.

### Design notes and planned extensions

The current benchmark stats are minimal by design. They are meant to answer:
- what subset was frozen
- how large it is
- whether the exported benchmark looks broadly sensible

They are not yet intended to provide rich benchmark diagnostics.

A planned extension is to add more granular product-level benchmark summaries, for example:
- per-product rating histograms
- per-product mean ratings
- per-product event counts in a richer diagnostic format

Those product-level summaries are deferred until they are directly needed by downstream comparison or reporting. For now, benchmark diagnostics remain deliberately lightweight so that the subset builder stays simple, reproducible, and fast on large imported artifacts.

Implementation note:
- `sim_panel/analysis/compare.py` remains the canonical comparison layer
- benchmark subsets created under `sim_panel/benchmarks/` are frozen reference inputs to that layer, not a separate analysis framework