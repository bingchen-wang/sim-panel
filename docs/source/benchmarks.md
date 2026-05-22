# Benchmarks

In SIM-PANEL, the `benchmarks/` module freezes benchmark-ready real-data subsets.

It does **not** compute synthetic-vs-real comparison metrics. Actual comparison,
diagnostics, tables, and reports belong to `analysis/compare/`.

```text
sources/
  raw external data -> imported canonical artifacts

benchmarks/
  imported canonical artifacts -> frozen benchmark subset

analysis/compare/
  synthetic outputs + frozen reference subset -> metrics, tables, reports
```

## Purpose

A source import can be large, noisy, or inconvenient to compare against directly.
The benchmark subset builder creates a smaller, reproducible, product-level
reference subset.

Use benchmark subsets to:

- freeze a stable real-data reference;
- reduce imported datasets to manageable slices;
- ensure selected products have enough rating-bearing events;
- separate ingestion from downstream comparison.

The benchmark layer answers:

> Which imported real events and products should be kept as a frozen reference
> subset?

## Input and output

The input directory must contain:

```text
events.jsonl
```

It usually also contains:

```text
products.jsonl
metadata.json
data_dictionary.json
stats.json
personas.jsonl
```

If `require_product_record` is true, `products.jsonl` must exist.

The output directory contains:

```text
events.jsonl
products.jsonl
metadata.json
stats.json
```

Within a benchmark subset directory, `events.jsonl` refers to frozen reference
events selected from imported real-data artifacts. It should not be confused with
synthetic generation outputs in a separate run directory.

## Configuration

Benchmark subset configs can be written under `benchmark_subset`:

```yaml
benchmark_subset:
  import_dir: outputs/imports/all_beauty
  output_dir: outputs/benchmarks/all_beauty_subset
  seed: 42
  min_reviews_per_product: 25
  max_products: 100
  require_product_record: true
```

or directly at the top level:

```yaml
import_dir: outputs/imports/all_beauty
output_dir: outputs/benchmarks/all_beauty_subset
seed: 42
min_reviews_per_product: 25
max_products: 100
require_product_record: true
```

## Config fields

| Field | Default | Description |
| --- | --- | --- |
| `import_dir` | Required | Directory containing imported source artifacts. |
| `output_dir` | Required | Directory to write the frozen benchmark subset. |
| `seed` | `0` | Seed for reproducible product sampling. |
| `min_reviews_per_product` | `25` | Minimum number of rating-bearing events required for product eligibility. |
| `max_products` | `100` | Maximum number of eligible products to keep. Use `null` to keep all eligible products. |
| `require_product_record` | `true` | Require selected products to appear in `products.jsonl`. |

## Selection logic

The current builder selects products.

The selection basis is:

```text
rating_event_count
```

A rating-bearing event is an event row from which a numeric rating can be
extracted. The builder looks for rating in:

1. `outcomes.rating`
2. top-level `rating`

Product IDs are extracted from:

1. `product_id`
2. `parent_asin`

The fallback fields support simple or transitional artifacts, but canonical
SIM-PANEL artifacts should use `outcomes.rating` and `product_id`.

## Algorithm

The builder uses a streaming two-pass algorithm over `events.jsonl`.

First pass:

```text
count rating-bearing events per product
```

Product selection:

```text
eligible = products with count >= min_reviews_per_product
eligible.sort()
shuffle eligible with seed
selected = eligible[:max_products]
```

Second pass:

```text
write events for selected products
write matching products
write metadata.json and stats.json
```

This avoids loading the full event table into memory.

## Reproducibility

Benchmark subset construction is deterministic conditional on:

- imported `events.jsonl`;
- imported `products.jsonl`, when used;
- `seed`;
- `min_reviews_per_product`;
- `max_products`;
- `require_product_record`.

The config snapshot and config hash are stored in `metadata.json`.

## Output files

| File | Description |
| --- | --- |
| `events.jsonl` | Frozen reference event rows selected from imported source artifacts. |
| `products.jsonl` | Product records corresponding to selected products. |
| `metadata.json` | Benchmark contract version, builder version, source paths, config snapshot, config hash, and output file names. |
| `stats.json` | Selected product/event counts, unique panelist count, rating histogram, and selected product review counts. |

## Example workflow

Start with a source import:

```text
outputs/imports/all_beauty/
  events.jsonl
  products.jsonl
  personas.jsonl
  metadata.json
  data_dictionary.json
  stats.json
```

Build a frozen benchmark subset:

```yaml
benchmark_subset:
  import_dir: outputs/imports/all_beauty
  output_dir: outputs/benchmarks/all_beauty_100_products
  seed: 42
  min_reviews_per_product: 25
  max_products: 100
  require_product_record: true
```

The result is:

```text
outputs/benchmarks/all_beauty_100_products/
  events.jsonl
  products.jsonl
  metadata.json
  stats.json
```

This subset can then be used by `analysis/compare/` as a frozen reference.

## Choosing parameters

Use `min_reviews_per_product` to control support per product. Larger values
produce more stable per-product rating distributions but reduce coverage.

Use `max_products` to control benchmark size. Smaller values are useful for fast
development and report debugging.

Use `require_product_record: true` when downstream comparison needs product
metadata. Set it to false only when event-only reference subsets are acceptable.

## Failure modes

The builder fails if:

- `events.jsonl` is missing from `import_dir`;
- `require_product_record` is true and `products.jsonl` is missing;
- config fields have invalid types.

If few products satisfy `min_reviews_per_product`, the output may contain fewer
than `max_products` products. This is expected.

Rows without numeric ratings do not count toward eligibility and are not exported
into the subset.

## Design note

The benchmark subset builder is deliberately narrow. It does not perform
stratified sampling, semantic clustering, or comparison-metric computation.

The v0 contract is simple:

- select products by observed rating support;
- keep selected real events;
- keep matching product records;
- write metadata and stats;
- leave comparison to `analysis/compare/`.

## Related pages

- [Sources](sources.md) for importing real-data artifacts.
- [Comparison](comparison.md) for synthetic-vs-reference comparison.
- [Schema](schema.md) for event fields and validation rules.
- [CLI](cli.md) for the `benchmark-subset` command.