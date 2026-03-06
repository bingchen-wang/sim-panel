# Developer Manual

## Table of Contents
- [Backends overview](#backends-overview)
  - [Core contract](#core-contract)
  - [Messages](#messages)
  - [Backend API](#backend-api)
  - [Configuration](#configuration-yaml-governed-essentials)
  - [Registry pattern](#registry-pattern)
  - [Included Backends](#included-backends)
    - [ollama](#ollama)
    - [server](#server)
- [Panelists overview](#panelists-overview)
  - [What it is](#what-it-is)
  - [Key concepts](#key-concepts)
  - [Main files](#main-files)
  - [Typical usage](#typical-usage)
- [Products overview](#products-overview)
  - [What it is](#what-it-is-1)
  - [Key concepts](#key-concepts-1)
  - [Main files](#main-files-1)
  - [Typical usage](#typical-usage-1)
  - [Design invariants](#design-invariants)
- [Schema overview](#schema-overview)
  - [What the schema represents](#what-the-schema-represents)
  - [Key fields (v0.1.0)](#key-fields-v010)
  - [Versioning & registry](#versioning--registry)
  - [Validation utilities](#validation-utilities)


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