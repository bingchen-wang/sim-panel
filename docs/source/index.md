# SIM-PANEL

<img src="_static/main-logo-light.svg" alt="SIM-PANEL logo" class="main-logo main-logo-light" />
<img src="_static/main-logo-dark.svg" alt="SIM-PANEL logo" class="main-logo main-logo-dark" />

<div class="repo-link-card">
  <a href="https://github.com/bingchen-wang/sim-panel" target="_blank" rel="noopener">
    <strong>GitHub repository</strong>
  </a>
</div>

**SIM-PANEL** is a reproducible simulation and benchmarking toolkit for generating
synthetic panel-style datasets in which agents evaluate products, interventions,
or other candidate items under controlled experimental designs.

It is designed as an engineering scaffold for research on LLM-based agent
simulation, preference reconstruction, and verifiable behavioral evaluation.
The package focuses on transparent data generation, schema validation,
YAML-configured experiments, and distributional diagnostics rather than
large-scale black-box simulation.

```{admonition} Project status
:class: note

SIM-PANEL is an ongoing project. The API and schemas may evolve, but the core
design principle is stable: reproducible, inspectable, CPU-friendly workflows for
agent-based panel experiments.
```

## Overview

### Why SIM-PANEL?

LLM-agent simulation workflows often fail for mundane reasons before they fail
for deep scientific ones: unclear schemas, brittle prompts, hidden assignment
rules, inconsistent outputs, and non-reproducible experiment configuration.

SIM-PANEL addresses this engineering layer. It provides a modular pipeline for:

- defining versioned event-level schemas;
- generating panelists, products, assignments, outcomes, and optional traces;
- running randomized, manual, or self-selection exposure policies;
- validating JSONL and optional CSV artifacts;
- importing external review-style data into canonical SIM-PANEL artifacts;
- freezing benchmark-ready real-data subsets;
- analyzing individual runs and comparing synthetic outputs against references;
- producing metadata, data dictionaries, diagnostics, and reports.

Synthetic data in SIM-PANEL is intended for **schema debugging, pipeline testing,
ablation scaffolding, and simulation-design prototyping**. It is not a substitute
for primary empirical validation.

### Core workflow

```text
YAML config
  -> Panelists and products
  -> Assignment or selection policy
  -> Outcome model
  -> events.jsonl
  -> Validation
  -> Analysis and comparison
```

A typical SIM-PANEL run starts from a YAML configuration file, constructs
panelists and products, applies an assignment or selection policy, generates
outcomes, and writes validated event-level artifacts.

### Simulation modes

SIM-PANEL currently supports three primary exposure designs:

```{list-table}
:header-rows: 1
:widths: 25 35 40

* - Mode
  - Pairing mechanism
  - Use case
* - Random assignment
  - Products are assigned to agents exogenously.
  - Controlled experiments, RCT-style baselines, sanity checks.
* - Manual assignment
  - Products are assigned according to a user-specified rule or schedule.
  - Designed interventions, targeted exposure, scripted ablations.
* - Self-selection
  - Agents choose which products or interventions to interact with.
  - Endogenous selection, recommender-like settings, behavioral diagnostics.
```

### Outputs

A standard generation run writes event-level JSONL plus run metadata:

```text
outputs/run_001/
  events.jsonl
  metadata.json
  data_dictionary.json
```

CSV export is optional:

```text
outputs/run_001/
  events.csv
```

Every generated dataset should be accompanied by metadata and a data dictionary
so that simulation assumptions remain explicit.

### Real-data workflows

SIM-PANEL also supports real-data ingestion and reference construction.

The modular workflow is:

```text
sources/
  raw external data -> imported canonical artifacts

benchmarks/
  imported artifacts -> frozen real-data subsets

analysis/compare/
  synthetic outputs + reference subsets -> comparison metrics and reports
```

The current source layer includes support for Amazon Reviews'23-style
product-review data, enabling workflows that convert review histories, product
metadata, and observed ratings into panel-style reference artifacts.

### Design principles

SIM-PANEL follows deliberately conservative engineering principles:

- **Configuration over hidden state**: experiments should be reproducible from YAML.
- **Schema first**: generated artifacts should validate against explicit versions.
- **CPU first**: v0 workflows should run locally at small-to-medium scale.
- **Modular components**: schemas, policies, outcome models, source adapters, and
  analysis modules should be swappable.
- **No required proprietary APIs**: LLM-based traces or outcomes should be optional
  plugins, not core dependencies.
- **Synthetic data is scaffolding**: generated data helps debug and benchmark
  pipelines; it should not be over-claimed as empirical evidence.

## Contact

For reproducible bugs, feature requests, or documentation issues, please use the
[GitHub issue tracker](https://github.com/bingchen-wang/sim-panel/issues).

For research-related inquiries, contact **Bingchen Wang** at
`bw2506 [at] columbia [dot] edu`.

## Acknowledgements

SIM-PANEL is developed and maintained by **Bingchen Wang** as an independent
research-engineering project.

The project benefited from early discussions with **Bruno Abrahao** and
**Teutly Correia** on agent-based product evaluation workflows. Those discussions
helped motivate the beer-demo example, while discussions with Bruno Abrahao also
informed the Amazon Reviews'23 ingestion and benchmarking direction. Bruno
Abrahao contributed initial commits to an early prototype.

The real-data reference workflow builds on public review-style datasets,
including Amazon Reviews'23 from McAuley Lab. SIM-PANEL uses such sources for
schema conversion, reference construction, and diagnostic evaluation. Synthetic
panel outputs should not be interpreted as substitutes for primary empirical
validation.

Any errors, design choices, or limitations remain the responsibility of the
maintainer.

## Where to start

```{toctree}
:maxdepth: 2
:caption: User Guide

installation
quickstart
concepts
cli
configs
schema
generation
sources
benchmarks
analysis
comparison
development
api
```