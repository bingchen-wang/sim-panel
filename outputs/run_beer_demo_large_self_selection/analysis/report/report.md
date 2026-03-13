# Analysis report: run_beer_demo_large_self_selection

## Run overview

- **run_name**: `run_beer_demo_large_self_selection`
- **run_dir**: `outputs/run_beer_demo_large_self_selection`
- **policy**: `self_selection`
- **schema_version**: `0.1.0`
- **seed**: `101`
- **generated_at_utc**: `2026-03-07T08:44:01+00:00`
- **backend_name**: `ollama`
- **backend_model**: `gemma3:12b`
- **outcomes_model_name**: `llm`
- **outcomes_temperature**: `0.2`
- **n_events**: `80`
- **n_selection_rows**: `20`
- **n_evaluation_rows**: `60`
- **n_unique_panelists_observed**: `20`
- **n_unique_products_evaluated**: `9`
- **n_unique_periods_observed**: `1`
- **personas_path**: `data/personas_beer_demo_large.jsonl`
- **products_path**: `data/products_beer_demo_large.jsonl`
- **config_path**: `sim_panel/config/examples/beer_demo_large_self_selection.yaml`

## Quality metrics

- **n_events**: `80`
- **n_selection_rows**: `20`
- **n_evaluation_rows**: `60`
- **rows_with_any_outcome_rate**: `1.0`
- **rows_with_any_trace_rate**: `1.0`
- **panelist_feature_coverage_rate**: `1.0`
- **product_feature_coverage_rate**: `1.0`
- **selection_link_rate**: `1.0`

## Panelist/product differentiation

- **outcome_field**: `rating`
- **supported**: `True`
- **n_observed**: `60`
- **overall_variance**: `0.8622222222222222`
- **n_panelists_observed**: `20`
- **n_products_observed**: `9`
- **panelist_mean_variance**: `0.39555555555555555`
- **product_mean_variance**: `0.24776515612697947`
- **mean_within_product_panelist_variance**: `0.6303967666948437`
- **mean_within_panelist_product_variance**: `0.4666666666666666`
- **mean_pairwise_panelist_distance**: `0.972972972972973`
- **mean_pairwise_product_distance**: `0.841388888888889`

## Selection behavior

- **n_selection_rows**: `20`
- **support_size_allowed**: `10`
- **avg_choice_set_size**: `10.0`
- **avg_requested_size**: `4.25`
- **avg_executed_size**: `3.0`
- **avg_dropped_size**: `1.25`
- **empty_request_rate**: `0.0`
- **empty_execution_rate**: `0.0`
- **request_to_execution_ratio**: `0.7058823529411765`
- **drop_rate_over_requested**: `0.29411764705882354`
- **requested_product_entropy**: `3.0456973128101152`
- **requested_product_normalized_entropy_full_support**: `0.9168462488690281`
- **requested_product_normalized_entropy_observed_support**: `0.9168462488690281`
- **executed_product_entropy**: `2.830500958093699`
- **executed_product_normalized_entropy_full_support**: `0.8520656911418407`
- **executed_product_normalized_entropy_observed_support**: `0.8929236359869157`
- **n_unique_requested_products**: `10`
- **n_unique_executed_products**: `9`

## Plot artifacts

- `outcome_distribution_bitterness_count`: `plots/outcome_distribution_bitterness_count.png`
- `outcome_distribution_purchase_intent_count`: `plots/outcome_distribution_purchase_intent_count.png`
- `outcome_distribution_rating_count`: `plots/outcome_distribution_rating_count.png`
- `panelist_mean_rating`: `plots/panelist_mean_rating.png`
- `panelist_variance_rating`: `plots/panelist_variance_rating.png`
- `product_mean_rating`: `plots/product_mean_rating.png`
- `product_variance_rating`: `plots/product_variance_rating.png`
- `selection_concentration_executed`: `plots/selection_concentration_executed.png`
- `selection_concentration_requested`: `plots/selection_concentration_requested.png`

## Notes

- Detailed machine-readable artifacts are saved under `summary/`, `metrics/`, and `plots/`.
- This report is intentionally lightweight and is meant to complement, not replace, the JSON/CSV outputs.
