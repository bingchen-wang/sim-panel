# API Reference

This section documents SIM-PANEL's Python modules.

The user guide explains workflows and concepts. The API reference is intended
for developers who need module, class, and function-level details.

## Module glossary

| Page | Module area | What it contains |
| --- | --- | --- |
| [Schema](api/schema) | `sim_panel.schema` | Versioned event schemas, schema registry, validation reports, and cross-row checks. |
| [Configuration](api/config) | `sim_panel.config` | YAML loading, run construction, and config-to-runtime wiring. |
| [Generators](api/generators) | `sim_panel.generators` | Event generation, deterministic RNG, event IDs, and generator config. |
| [Policies](api/policies) | `sim_panel.policies` | Random assignment, manual assignment, self-selection exposure logic, and policy registry. |
| [Decisions](api/decisions) | `sim_panel.decisions` | Selection contexts, selection parsing, and execution-rule application. |
| [Outcomes](api/outcomes) | `sim_panel.outcomes` | Outcome model interfaces, evaluation contexts, and outcome-model registry. |
| [Panelists](api/panelists) | `sim_panel.panelists` | Persona records, runtime panelists, and panelist-facing behavior. |
| [Products](api/products) | `sim_panel.products` | Product records, runtime products, display text, and product attributes. |
| [Sources](api/sources) | `sim_panel.sources` | External-data importers, source registry, Amazon Reviews'23 conversion, and streaming import. |
| [Benchmarks](api/benchmarks) | `sim_panel.benchmarks` | Benchmark subset configs and frozen reference subset construction. |
| [Analysis](api/analysis) | `sim_panel.analysis` | Single-run analysis config, summaries, metrics, plots, and regression integration. |
| [Comparison](api/comparison) | `sim_panel.analysis.compare` | Cross-condition and benchmark comparison APIs. |
| [CLI](api/cli) | `sim_panel.cli` | Command-line entry points and command handlers. |

## API pages

```{toctree}
:maxdepth: 2
:caption: API Reference

api/schema
api/config
api/generators
api/policies
api/decisions
api/outcomes
api/panelists
api/products
api/sources
api/benchmarks
api/analysis
api/comparison
api/cli
```