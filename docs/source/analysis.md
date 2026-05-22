# Analysis

The `analysis/` module provides single-run diagnostics for a generated or
imported SIM-PANEL run.

It reads one run directory, loads event rows and metadata, computes summaries and
metrics, optionally saves plots, and can run questionnaire-aware regression
models on the analyzed event data.

Analysis is for inspecting **one run**. Multi-run comparison and synthetic-vs-real
benchmarking live in [Comparison](comparison.md).

## Purpose

Use analysis when you want to answer questions such as:

- Did the run produce the expected number of events?
- Which outcome fields are present, and how much missingness do they have?
- How are ratings or other outcomes distributed?
- Do panelists or products differ in their observed outcome profiles?
- In self-selection runs, which products were requested or executed most often?
- Can simple regression models explain an outcome using available event features?

## Input directory

A typical analysis input is a SIM-PANEL run directory:

```text
outputs/run_001/
  events.jsonl
  metadata.json
  data_dictionary.json
```

The analysis loader primarily uses:

| File | Role |
| --- | --- |
| `events.jsonl` | Main event-level dataset. |
| `metadata.json` | Run provenance and configuration snapshot. |

Linked persona and product files are optional. Many summaries can be computed
directly from `events.jsonl` because event rows already contain
`panelist_features`, `product_features`, `outcomes`, and `traces`.

## Minimal config

A minimal analysis config contains a run directory and an output directory:

```yaml
run_dir: outputs/run_001
output_dir: outputs/run_001/analysis
```

Run analysis with the analysis CLI or runner used by the current project setup.

## Full config shape

The analysis YAML supports the following sections:

```yaml
run_dir: outputs/run_001
output_dir: outputs/run_001/analysis

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
  selection: false

plots:
  outcome_distributions:
    enabled: true
    normalize_to_share: false
    fields: null
    figsize: [7, 4.5]

  panelist_summary:
    enabled: false
    outcome_field: rating
    metrics: [mean, variance]
    max_items: 30
    sort_by: label_asc
    horizontal: false

  product_summary:
    enabled: false
    outcome_field: rating
    metrics: [mean, variance]
    max_items: 30
    sort_by: label_asc
    horizontal: false

  selection_concentration:
    enabled: false
    modes: [executed, requested]
    top_k: 15
    horizontal: true

export:
  csv: true
  json: true
  markdown: true
  overwrite: true
```

## Load options

The `load` section controls how much upstream source information analysis tries
to resolve.

| Field | Default | Description |
| --- | --- | --- |
| `resolve_sources` | `true` | Try to resolve linked persona/product source files from metadata. |
| `prefer_extra_paths` | `true` | Prefer explicit extra paths when multiple source paths are available. |
| `strict_source_resolution` | `false` | If true, fail when linked sources cannot be resolved. |

Source resolution is optional. Analysis should remain useful even when only
`events.jsonl` and `metadata.json` are available.

## Summaries

The `summaries` section controls human-readable structured summaries.

| Summary | Description |
| --- | --- |
| `run` | Row counts, event type counts, schema/policy/seed/backend metadata, observed panelist/product/period counts, and provenance paths. |
| `outcomes` | Per-outcome observed counts, missingness, and lightweight numeric or categorical summaries. |
| `traces` | Trace-field presence and text-oriented diagnostics. |
| `selections` | Selection-event summaries for self-selection runs. |

These summaries are intended for quick inspection and report generation.

## Metrics

The `metrics` section controls reusable analytic diagnostics.

| Metric group | Description |
| --- | --- |
| `quality` | Coverage, missingness, and basic linking checks. |
| `diversity` | Outcome diversity diagnostics. |
| `persona` | Panelist/product differentiation metrics. |
| `selection` | Selection concentration and entropy-style diagnostics. |

Summaries and metrics are separate by design: summaries are reader-facing tables,
while metrics are reusable machine-readable diagnostics.

## Plots

The `plots` section controls optional single-run diagnostic figures.

Current plot families include:

| Plot family | Description |
| --- | --- |
| `outcome_distributions` | Per-outcome distributions. |
| `panelist_summary` | Bar summaries over panelists for a chosen outcome. |
| `product_summary` | Bar summaries over products for a chosen outcome. |
| `selection_concentration` | Requested/executed product concentration in self-selection runs. |

If JSON export is enabled, analysis also writes a plot index mapping plot names
to saved image paths.

## Exported artifacts

The analysis runner writes structured artifacts under the configured
`output_dir`.

Typical layout:

```text
analysis/
  summary/
  metrics/
  plots/
  report/
```

### `summary/`

Contains structured single-run summaries such as:

```text
run_summary
outcome_summary
trace_summary
selection_summary
```

Depending on export settings, summaries may be written as JSON and/or CSV.

### `metrics/`

Contains machine-readable metric artifacts such as:

```text
quality_metrics
diversity_metrics
persona_metrics
selection_metrics
```

Depending on export settings, metrics may be written as JSON and/or CSV.

### `plots/`

Contains saved diagnostic figures. When JSON export is enabled, this directory
also includes:

```text
plot_index.json
```

### `report/`

Contains a lightweight markdown report:

```text
report.md
```

The report is intentionally concise. It gives a run overview, surfaces selected
summary and metric values, and points to saved artifacts.

## Export controls

Export behavior is controlled by the `export` section:

```yaml
export:
  csv: true
  json: true
  markdown: true
  overwrite: true
```

| Field | Description |
| --- | --- |
| `csv` | Write row-oriented CSV summaries and selected metric tables. |
| `json` | Write machine-readable JSON outputs and plot index. |
| `markdown` | Write `report/report.md`. |
| `overwrite` | Allow existing artifact files to be replaced. |

## Regression analysis

Regression is an optional submodule of single-run analysis.

It is integrated into the analysis workflow rather than exposed as a separate
top-level CLI command. When enabled, regression models are fit from the analyzed
event data and written under a regression subdirectory.

Enable regression with:

```yaml
regression:
  enabled: true
  save_results: true
  output_subdir: regression

  options:
    drop_missing: true
    standardize_numeric: false
    add_intercept: true
    max_iter: 200
    include_inference: true
    confidence_level: 0.95
    covariance_type: nonrobust

  specs:
    - family: ols
      design: product_features + panelist_features
      outcome_field: rating
```

Supported model families include:

| Family | Outcome type |
| --- | --- |
| `ols` | Continuous outcomes. |
| `logit` | Binary outcomes. |
| `probit` | Binary outcomes. |
| `multinomial_logit` | Nominal categorical outcomes. |
| `ordered_logit` | Ordinal categorical outcomes. |
| `ordered_probit` | Ordinal categorical outcomes. |

Regression is questionnaire-aware. The selected model family should be compatible
with the declared analysis type of the requested outcome field.

## Regression options

| Field | Default | Description |
| --- | --- | --- |
| `drop_missing` | `true` | Drop rows with missing target or regressors before fitting. |
| `standardize_numeric` | `false` | Standardize numeric regressors before fitting. |
| `add_intercept` | `true` | Add an intercept where appropriate. |
| `max_iter` | `200` | Maximum optimizer iterations for nonlinear models. |
| `include_inference` | `true` | Request coefficient-level inference outputs. |
| `confidence_level` | `0.95` | Confidence level for intervals. |
| `covariance_type` | `nonrobust` | Covariance estimator. Supported values include `nonrobust`, `HC1`, `cluster_panelist`, `cluster_product`, and `cluster_two_way` where implemented. |

## Analysis versus comparison

Analysis and comparison serve different roles.

| Layer | Scope | Typical input | Typical output |
| --- | --- | --- | --- |
| `analysis/` | One run | One run directory | Summaries, metrics, plots, report, optional regression. |
| `analysis/compare/` | Multiple conditions or synthetic-vs-reference | Multiple run/reference directories | Comparison metrics, tables, diagnostics, report. |

Use analysis first to inspect whether individual runs are healthy. Use comparison
afterwards to evaluate differences across conditions or against a frozen
benchmark reference.

## Related pages

- [Generation](generation.md) for how event rows are produced.
- [Schema](schema.md) for event fields and validation rules.
- [Benchmarks](benchmarks.md) for freezing real-data reference subsets.
- [Comparison](comparison.md) for multi-run and benchmark comparison workflows.