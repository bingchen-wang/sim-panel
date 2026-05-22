# Sources

SIM-PANEL sources convert external datasets into canonical internal artifacts:
event rows, product records, persona records, metadata, data dictionaries, and
import statistics.

The source layer is for **data ingestion and conversion**. It is separate from
synthetic generation, benchmark subset construction, and comparison.

```text
sources/
  raw external data -> canonical imported artifacts

benchmarks/
  imported artifacts -> frozen real-data subset

analysis/compare/
  synthetic outputs + reference subset -> comparison metrics and reports
```

## Source-layer contract

All source importers inherit from `BaseSource`.

A source is responsible for:

- validating its configuration;
- loading raw source artifacts;
- transforming raw rows into SIM-PANEL records;
- exporting materialized bundles;
- optionally supporting a streaming import/export path.

The default in-memory flow is:

```text
validate config
  -> load raw artifacts
  -> transform into canonical records
  -> return SourceExportBundle
  -> export artifacts
```

Streaming sources may bypass raw-bundle materialization and write artifacts
incrementally to disk.

## Source registry

SIM-PANEL uses a source registry so orchestration code does not need to hard-code
source classes.

A source config declares the source name:

```yaml
source:
  name: amazon_reviews_2023
  reviews_path: data/raw/All_Beauty.jsonl.gz
  metadata_path: data/raw/meta_All_Beauty.jsonl.gz
  output_dir: outputs/imports/all_beauty
```

The currently implemented source is:

| Source name | Description |
| --- | --- |
| `amazon_reviews_2023` | Imports Amazon Reviews'23 review and metadata files into SIM-PANEL artifacts. |

## Export bundle

A source import produces a `SourceExportBundle` containing:

| Artifact | Description |
| --- | --- |
| `events` | Schema-valid event rows. |
| `products` | Product records. |
| `personas` | Persona records. |
| `metadata` | Source-level import metadata. |
| `data_dictionary` | Field-level source/export dictionary. |
| `stats` | Lightweight import statistics. |

For streaming imports, large artifacts are written directly to disk. The returned
bundle may contain empty row lists while still carrying metadata and stats.

## Amazon Reviews'23 background

[Amazon Reviews'23](https://amazon-reviews-2023.github.io/) is a large-scale
review dataset released by McAuley Lab. It contains user reviews, item metadata,
and user-item interaction structure across multiple product categories.

SIM-PANEL does not redistribute the raw dataset. The `amazon_reviews_2023`
adapter assumes users have downloaded review and metadata files locally, then
converts those local files into SIM-PANEL-compatible artifacts.

Users should consult the original dataset page for download links, citation
information, licensing terms, and data-use conditions.

## Amazon Reviews'23 source

The Amazon importer expects two local files:

- a review JSONL or JSONL.GZ file;
- a metadata JSONL or JSONL.GZ file.

Example config:

```yaml
source:
  name: amazon_reviews_2023
  reviews_path: data/raw/All_Beauty.jsonl.gz
  metadata_path: data/raw/meta_All_Beauty.jsonl.gz
  category: All_Beauty
  output_dir: outputs/imports/all_beauty
  import_mode: in_memory
```

## Amazon config fields

| Field | Default | Description |
| --- | --- | --- |
| `reviews_path` | Required | Path to raw review JSONL or JSONL.GZ file. |
| `metadata_path` | Required | Path to raw metadata JSONL or JSONL.GZ file. |
| `category` | `null` | Optional category/domain label. |
| `output_dir` | `null` | Output directory. |
| `import_mode` | `in_memory` | Either `in_memory` or `streaming`. |
| `require_metadata_match_for_events` | `false` | Drop review events without matching product metadata if true. |
| `trace_field_map` | title/text mapping | Maps review fields into event traces. |
| `time_index_mode` | `panelist_sequence` | How event period index `t` is derived. |
| `min_reviews_per_persona` | `1` | Minimum review count required to emit a persona record. |
| `max_reviews` | `null` | Optional cap on raw review rows. |
| `max_metadata_rows` | `null` | Optional cap on raw metadata rows. |

Default trace mapping:

```yaml
trace_field_map:
  title: review_title
  text: review_text
```

## Import mapping

The Amazon importer converts source files as follows:

| SIM-PANEL artifact | Built from |
| --- | --- |
| `products.jsonl` | Item metadata rows. |
| `personas.jsonl` | User review histories. |
| `events.jsonl` | Review rows. |

SIM-PANEL uses `parent_asin` as the canonical `product_id`. Child `asin` values
are retained as source provenance under event traces.

Imported review rows become schema-valid `evaluation` events with:

| Event field | Source |
| --- | --- |
| `policy` | `"manual"` |
| `panelist_id` | Amazon `user_id` |
| `product_id` | Amazon `parent_asin` |
| `product_display` | Product display text or display name. |
| `outcomes.rating` | Review `rating`. |
| `outcomes.verified_purchase` | Review `verified_purchase`. |
| `outcomes.helpful_vote` | Review `helpful_vote` or `helpful_votes`. |
| `traces.review_title` | Review `title`, by default. |
| `traces.review_text` | Review `text`, by default. |

Imported real events use `policy: manual` because they are observational records,
not randomized synthetic assignments.

## Time index `t`

The Amazon importer supports three time-index modes:

| Mode | Description | Streaming support |
| --- | --- | --- |
| `panelist_sequence` | Sort each user's reviews chronologically and assign `t = 0, 1, ...` within user. | Yes |
| `raw_timestamp` | Use the source timestamp directly. | Yes |
| `global_sequence` | Sort the full corpus chronologically and assign a corpus-wide index. | In-memory only |

Default:

```yaml
time_index_mode: panelist_sequence
```

`panelist_sequence` is recommended for panel-style simulation because it gives
each panelist an individual exposure history.

## Import modes

### In-memory

The in-memory path materializes raw review and metadata rows before transforming
them.

Use it for:

- small categories;
- capped development runs;
- transformation debugging;
- semantic tests.

Example:

```yaml
source:
  name: amazon_reviews_2023
  reviews_path: data/raw/All_Beauty.jsonl.gz
  metadata_path: data/raw/meta_All_Beauty.jsonl.gz
  output_dir: outputs/imports/all_beauty_small
  import_mode: in_memory
  max_reviews: 10000
  max_metadata_rows: 5000
```

### Streaming

The streaming path writes large artifacts incrementally and avoids constructing
the full event table in memory.

Use it for larger imports.

Example:

```yaml
source:
  name: amazon_reviews_2023
  reviews_path: data/raw/All_Beauty.jsonl.gz
  metadata_path: data/raw/meta_All_Beauty.jsonl.gz
  output_dir: outputs/imports/all_beauty_streaming
  import_mode: streaming
  time_index_mode: panelist_sequence
```

Streaming supports `panelist_sequence` and `raw_timestamp`. It does not support
`global_sequence`.

## Exported files

The Amazon source export writes:

```text
events.jsonl
products.jsonl
personas.jsonl
metadata.json
data_dictionary.json
stats.json
```

| File | Description |
| --- | --- |
| `events.jsonl` | Schema-valid evaluation rows derived from reviews. |
| `products.jsonl` | Product records derived from metadata. |
| `personas.jsonl` | Persona records derived from user review histories. |
| `metadata.json` | Source-level import metadata. |
| `data_dictionary.json` | Source export dictionary. |
| `stats.json` | Import counts and source-specific statistics. |

## Missing product metadata

Amazon review rows may reference products whose metadata is absent from the
loaded metadata file.

By default:

```yaml
require_metadata_match_for_events: false
```

With this setting, review events may still be emitted even when product metadata
is missing. Missing metadata counts are recorded in `stats.json`.

To keep only metadata-backed events:

```yaml
require_metadata_match_for_events: true
```

## Capped development imports

For development, use caps:

```yaml
source:
  name: amazon_reviews_2023
  reviews_path: data/raw/All_Beauty.jsonl.gz
  metadata_path: data/raw/meta_All_Beauty.jsonl.gz
  output_dir: outputs/imports/all_beauty_dev
  import_mode: in_memory
  max_reviews: 1000
  max_metadata_rows: 1000
```

Independent caps can reduce review/metadata overlap because the first `N` review
rows and first `M` metadata rows may not refer to the same products.

## Downstream use

After source import, the `benchmarks/` module can freeze a smaller
benchmark-ready subset. The comparison layer can then compare synthetic outputs
against that frozen reference.

Sources ingest. Benchmarks freeze. Comparison evaluates.

## Related pages

- [Benchmarks](benchmarks.md) for freezing benchmark-ready real-data subsets.
- [Comparison](comparison.md) for synthetic-vs-reference comparison.
- [Schema](schema.md) for event fields and validation rules.
- [CLI](cli.md) for source import commands.