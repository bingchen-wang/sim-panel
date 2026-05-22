# Schema

SIM-PANEL writes event-level datasets. Each row in `events.jsonl` represents one
schema-validated event.

The current schema version is:

```text
0.1.0
```

Each row declares its own `schema_version`. The schema registry maps version
strings to Pydantic validation models.

Unknown top-level fields are rejected. This keeps the event envelope strict while
allowing flexible JSON payloads under `outcomes`, `traces`,
`panelist_features`, and `product_features`.

## Event types

Version `0.1.0` supports two event types:

| Event type | Description |
| --- | --- |
| `selection` | A panelist is shown a choice set and requests zero or more products. |
| `evaluation` | A panelist evaluates one product at one period. |

Selection events are only valid for `policy: self_selection`. Evaluation events
are valid for all supported policies.

## Policies

The schema recognizes three policy names:

| Policy | Meaning |
| --- | --- |
| `random` | Products are assigned exogenously. |
| `manual` | Product-panelist assignments are loaded from a schedule or mapping. |
| `self_selection` | Panelists choose products from a shown choice set. |

The policy field records exposure logic. It does not define the outcome model or
questionnaire.

## Core fields

Every row contains:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `schema_version` | string | Yes | Schema version. |
| `event_id` | string | Yes | Deterministic unique event ID. |
| `event_type` | string | Yes | `selection` or `evaluation`. |
| `policy` | string | Yes | `random`, `manual`, or `self_selection`. |
| `panelist_id` | string | Yes | Panelist identifier. |
| `t` | integer | Yes | Zero-based, non-negative period index. |

## Evaluation events

Evaluation rows describe one evaluated product.

Required evaluation fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `product_id` | string | Yes | Evaluated product identifier. |
| `product_display` | string | Yes | Panelist-facing product text. |

Additional evaluation fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `selection_id` | string or null | Required for self-selection evaluations | Linked selection event ID. |
| `panelist_features` | JSON object | Yes | Panelist feature payload; may be empty. |
| `product_features` | JSON object | Yes | Product feature payload; may be empty. |
| `outcomes` | JSON object or null | No | Structured outcome fields. |
| `traces` | JSON object or null | No | Optional text, rationale, errors, or debug information. |

Evaluation rows must not include selection-only fields such as `choice_set` or
`selected_product_ids`.

For `self_selection` evaluation rows, `selection_id` must reference a valid
selection event with the same `(panelist_id, t)`.

Example:

```json
{
  "schema_version": "0.1.0",
  "event_id": "5df59b89b0ab4b7eecb54723e2e708f5",
  "event_type": "evaluation",
  "policy": "random",
  "panelist_id": "panelist_001",
  "t": 0,
  "selection_id": null,
  "product_id": "product_001",
  "product_display": "A citrus-forward non-alcoholic pale ale.",
  "panelist_features": {},
  "product_features": {
    "category": "beer"
  },
  "outcomes": {
    "rating": 4,
    "purchase_intent": "maybe"
  },
  "traces": {
    "review_text": "Refreshing and easy to drink."
  }
}
```

## Selection events

Selection rows describe the choice set shown to a panelist and the product IDs
requested by the panelist.

Selection rows are only valid when:

```text
policy == "self_selection"
```

Required selection fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `choice_set` | JSON list | Yes | Product IDs shown to the panelist. |
| `selected_product_ids` | JSON list | Yes | Product IDs requested by the panelist; may be empty. |

Selection rows must not include evaluation-only fields:

- `product_id`
- `product_display`
- `outcomes`

Example:

```json
{
  "schema_version": "0.1.0",
  "event_id": "9a7d27614d09c68b0562b3a74ab9f0c2",
  "event_type": "selection",
  "policy": "self_selection",
  "panelist_id": "panelist_001",
  "t": 0,
  "selection_id": null,
  "choice_set": ["product_001", "product_002", "product_003"],
  "selected_product_ids": ["product_002", "product_003"],
  "panelist_features": {},
  "product_features": {},
  "outcomes": null,
  "traces": {
    "executed_product_ids": ["product_002"],
    "dropped_product_ids": ["product_003"]
  }
}
```

`selected_product_ids` records what the panelist requested.
`traces.executed_product_ids` records what the generator actually evaluated
after execution rules were applied.

## Outcomes and traces

`outcomes` and `traces` are flexible JSON objects shaped by the questionnaire and
outcome model.

Typical `outcomes`:

```json
{
  "rating": 5,
  "purchase_intent": "yes"
}
```

Typical `traces`:

```json
{
  "review_text": "A crisp and refreshing option.",
  "rationale": "The panelist likes citrus notes."
}
```

If an outcome model reports errors, the generator may store them under
`traces.outcome_errors`.

If selection parsing reports errors, the generator may store them under
`traces.selection_errors`.

## Selection traces

Selection traces may include operational details:

| Trace field | Description |
| --- | --- |
| `executed_product_ids` | Product IDs actually evaluated after execution rules. |
| `dropped_product_ids` | Requested product IDs that were dropped. |
| `selection_errors` | Parsing or selection errors. |

When present, executed and dropped product lists must not contain duplicates or
overlap. Executed product IDs must belong to the original `choice_set`.

## Feature payloads

The schema includes two required JSON feature fields:

| Field | Description |
| --- | --- |
| `panelist_features` | Structured panelist attributes included in events. May be `{}`. |
| `product_features` | Structured product attributes included in events. May be `{}`. |

The generator controls whether these features are populated in emitted events:

```yaml
generator:
  include_panelist_features_in_events: true
  include_product_features_in_events: true
```

## Event IDs

Event IDs are deterministic. The generator constructs them from an event
namespace and a canonicalized payload.

Default namespace:

```yaml
generator:
  event_namespace: sim_panel.v0
```

Changing the namespace is useful when separate experiments might otherwise
produce similar visible payloads.

## Validation

SIM-PANEL validates rows in three layers.

| Layer | Description |
| --- | --- |
| Row-level schema validation | Each row is validated against the registered schema version. |
| Event-ID uniqueness | No two rows may share the same `event_id`. |
| Self-selection linkage | Self-selection evaluations must reference valid selection rows with matching `(panelist_id, t)`. |

The generator runs validation automatically when:

```yaml
generator:
  validate_on_finish: true
  max_errors: 50
```

The CLI also exposes explicit validation:

```bash
sim-panel validate --input outputs/run_001/events.jsonl
```

## Column dictionary

The current schema declares these top-level columns:

| Column | Type | Required | Description |
| --- | --- | --- | --- |
| `schema_version` | string | Yes | Schema version. |
| `event_id` | string | Yes | Deterministic unique event ID. |
| `event_type` | string | Yes | `selection` or `evaluation`. |
| `policy` | string | Yes | `random`, `manual`, or `self_selection`. |
| `panelist_id` | string | Yes | Panelist identifier. |
| `t` | int | Yes | Zero-based period index. |
| `selection_id` | string | No | Links evaluation rows to selection rows. |
| `choice_set` | JSON | No | Presented choice set; selection rows only. |
| `selected_product_ids` | JSON | No | Requested product IDs; selection rows only. |
| `product_id` | string | No | Evaluated product ID; evaluation rows only. |
| `product_display` | string | No | Displayed product text; evaluation rows only. |
| `panelist_features` | JSON | Yes | Panelist feature payload; may be `{}`. |
| `product_features` | JSON | Yes | Product feature payload; may be `{}`. |
| `outcomes` | JSON | No | Outcome payload. |
| `traces` | JSON | No | Trace payload. |

## Design notes

The v0.1.0 schema keeps top-level event structure strict and versioned, while
leaving experimental content flexible inside JSON payloads.

This lets different questionnaires, product domains, and simulation designs
share the same event envelope without changing the schema whenever a new outcome
or trace field is added.

## Related pages

- [Configuration](configs.md) for YAML-driven run setup.
- [Generation](generation.md) for the generator pipeline.
- [Sources](sources.md) for real-data adapters.
- [CLI](cli.md) for validation commands.