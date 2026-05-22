# Comparison

The `analysis/compare/` module provides multi-condition comparison workflows for
SIM-PANEL.

It is separate from single-run [Analysis](analysis.md). Analysis inspects one
run; comparison evaluates relationships across runs or against a real reference.

## Purpose

Use comparison when you want to:

- compare prompting strategies;
- compare different models or policies;
- compare synthetic outputs against a frozen real-data reference;
- produce compact metrics, tables, diagnostics, and markdown reports.

The comparison layer currently supports two modes:

| Mode | Description |
| --- | --- |
| `cross` | Compare multiple synthetic conditions against one another. |
| `benchmark` | Compare synthetic conditions against exactly one real reference condition. |

Mode resolution is automatic from the condition list.

## CLI usage

The comparison pipeline has its own CLI command:

```bash
sim-panel compare --config path/to/compare.yaml
```

The CLI loads the compare config, runs the comparison pipeline, and writes
artifacts to the configured output directory.

## Config structure

A compare config requires:

- `output_dir`
- a non-empty `conditions` list

It also accepts:

- `outcome_field`
- `rating_scale`
- compare-mode-specific options supported by the current implementation

## Cross-condition config

Use cross mode when all conditions are synthetic runs.

```yaml
output_dir: outputs/compare_beer_strategies
outcome_field: rating

conditions:
  - label: beer_persona
    model: gemma3:12b
    strategy: persona
    run_dir: outputs/beer_persona
    condition_type: synthetic
    events_filename: events.jsonl

  - label: beer_persona_cot
    model: gemma3:12b
    strategy: persona_cot
    run_dir: outputs/beer_persona_cot
    condition_type: synthetic
    events_filename: events.jsonl
```

If `condition_type` is omitted, it defaults to `synthetic`.

If `events_filename` is omitted, it defaults to `events.jsonl`.

## Benchmark config

Use benchmark mode when the condition list contains exactly one real reference
condition.

```yaml
output_dir: outputs/compare_amazon_benchmark
outcome_field: rating
benchmark_top_k_products: 20

conditions:
  - label: amazon_real
    model: real
    strategy: reference
    run_dir: outputs/benchmarks/amazon_grocery_subset
    condition_type: real
    events_filename: events.jsonl

  - label: amazon_self_selection
    model: gemma3:12b
    strategy: persona
    run_dir: outputs/amazon_self_selection
    condition_type: synthetic
    events_filename: events.jsonl

  - label: amazon_self_selection_cot
    model: gemma3:12b
    strategy: persona_cot
    run_dir: outputs/amazon_self_selection_cot
    condition_type: synthetic
    events_filename: events.jsonl
```

Benchmark mode is intended for synthetic-vs-reference evaluation. The reference
condition is usually produced by the [Benchmarks](benchmarks.md) module from
imported real-data artifacts.

## Condition fields

Each condition defines one run or reference dataset.

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `label` | No | `cond_i` | Human-readable condition label. |
| `model` | No | `""` | Model identifier or descriptive label. |
| `strategy` | No | `""` | Prompting or generation strategy label. |
| `run_dir` | Yes | None | Directory containing event artifacts. |
| `condition_type` | No | `synthetic` | Either `synthetic` or `real`. |
| `events_filename` | No | `events.jsonl` | Event file name inside `run_dir`. |

The comparison loader reads event rows from each condition directory and filters
to evaluation events.

## Mode resolution

Comparison mode is resolved from the condition types.

| Condition mix | Mode |
| --- | --- |
| No real conditions | `cross` |
| Exactly one real condition | `benchmark` |
| More than one real condition | Invalid in the current implementation. |

This fail-fast behavior keeps the interpretation of benchmark results clear.

## Runtime flow

At a high level, the comparison runner:

1. resolves compare mode from the condition list;
2. loads event rows from each condition directory;
3. restricts rows to `event_type == "evaluation"`;
4. computes shared per-condition metrics;
5. dispatches to cross-mode or benchmark-mode artifact builders;
6. writes tables, JSON artifacts, plots where applicable, and a markdown report.

## Shared per-condition metrics

The comparison layer computes descriptive metrics for each condition once and
reuses them across reports and tables.

Typical metrics include:

- number of evaluation rows;
- number of panelists;
- number of products;
- observed outcome coverage;
- rating or outcome distribution summaries.

Exact metric fields may evolve as the comparison module develops.

## Cross mode

Cross mode compares synthetic conditions against one another.

Typical outputs include:

```text
condition_metrics.json
condition_metrics.csv
pivot_tables.json
js_divergence_matrix.json
pairwise_rmse_matrix.json
comparison_report.md
```

Cross mode is useful for comparing:

- prompting strategies;
- model choices;
- assignment policies;
- self-selection variants;
- ablation settings.

## Benchmark mode

Benchmark mode compares synthetic conditions against one real reference
condition.

Typical outputs include:

```text
condition_metrics.json
condition_metrics.csv
benchmark_summary.json
benchmark_summary.csv
benchmark_product_diagnostics_topk.json
benchmark_product_diagnostics_topk.csv
pivot_tables.json
benchmark_rating_bar_charts.png
comparison_report.md
```

Benchmark calculations are restricted to shared products where appropriate. This
keeps synthetic-vs-reference comparisons from being driven by products that exist
only in one side of the comparison.

## Benchmark diagnostics

Benchmark mode exports compact product-level diagnostics for the best and worst
matching products, controlled by:

```yaml
benchmark_top_k_products: 20
```

These diagnostics are intended for quick inspection, not as a complete error
analysis framework.

## Rating scale

If the outcome is a rating, you may provide a rating scale:

```yaml
rating_scale: [1, 2, 3, 4, 5]
```

The rating scale helps normalize rating-distribution comparisons and report
consistent tables.

## Output reports

Both comparison modes write:

```text
comparison_report.md
```

The report summarizes conditions, core metrics, and mode-specific diagnostics.
In benchmark mode, the markdown report may reference the saved rating bar-chart
figure through a relative image path.

## Relationship to sources and benchmarks

Comparison is downstream of source ingestion and benchmark subsetting.

Typical real-data workflow:

```text
sources/
  raw Amazon Reviews'23 files
  -> imported events/products/personas

benchmarks/
  imported events/products
  -> frozen reference subset

analysis/compare/
  frozen reference subset + synthetic runs
  -> comparison metrics and reports
```

Sources ingest. Benchmarks freeze. Comparison evaluates.

## Relationship to single-run analysis

Run single-run analysis before comparison when debugging output quality.

Analysis can reveal missing outcomes, malformed traces, sparse products, or
unexpected selection patterns before those issues propagate into multi-run
comparison.

Comparison assumes the input conditions are already valid enough to compare.

## Current limitations

The current comparison layer is intentionally compact.

Important limitations:

- benchmark mode supports exactly one real reference condition;
- benchmark comparison is product-overlap-aware but not a full causal evaluation;
- reports are lightweight markdown artifacts;
- richer multi-run visual diagnostics are still evolving.

The goal is to provide reproducible comparison scaffolding without hiding the
underlying event data or metric assumptions.

## Related pages

- [Analysis](analysis.md) for single-run summaries, metrics, plots, and regression.
- [Benchmarks](benchmarks.md) for freezing real-data reference subsets.
- [Sources](sources.md) for importing external datasets.
- [Schema](schema.md) for event fields and validation rules.