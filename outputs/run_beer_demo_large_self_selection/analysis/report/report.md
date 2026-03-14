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
- **outcomes_temperature**: `0.2000`
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
- **rows_with_any_outcome_rate**: `1.0000`
- **rows_with_any_trace_rate**: `1.0000`
- **panelist_feature_coverage_rate**: `1.0000`
- **product_feature_coverage_rate**: `1.0000`
- **selection_link_rate**: `1.0000`

## Panelist/product differentiation

- **outcome_field**: `rating`
- **supported**: `True`
- **n_observed**: `60`
- **overall_variance**: `0.8622`
- **n_panelists_observed**: `20`
- **n_products_observed**: `9`
- **panelist_mean_variance**: `0.3956`
- **product_mean_variance**: `0.2478`
- **mean_within_product_panelist_variance**: `0.6304`
- **mean_within_panelist_product_variance**: `0.4667`
- **mean_pairwise_panelist_distance**: `0.9730`
- **mean_pairwise_product_distance**: `0.8414`

## Selection behavior

- **n_selection_rows**: `20`
- **support_size_allowed**: `10`
- **avg_choice_set_size**: `10.0000`
- **avg_requested_size**: `4.2500`
- **avg_executed_size**: `3.0000`
- **avg_dropped_size**: `1.2500`
- **empty_request_rate**: `0.0000`
- **empty_execution_rate**: `0.0000`
- **request_to_execution_ratio**: `0.7059`
- **drop_rate_over_requested**: `0.2941`
- **requested_product_entropy**: `3.0457`
- **requested_product_normalized_entropy_full_support**: `0.9168`
- **requested_product_normalized_entropy_observed_support**: `0.9168`
- **executed_product_entropy**: `2.8305`
- **executed_product_normalized_entropy_full_support**: `0.8521`
- **executed_product_normalized_entropy_observed_support**: `0.8929`
- **n_unique_requested_products**: `10`
- **n_unique_executed_products**: `9`

## Regression analysis

- **n_models**: `2`

> Caution: coefficient estimates can still be useful diagnostically, but standard errors, p-values, and confidence intervals should be interpreted carefully. Observations are grouped by panelists and products, residual dependence may remain even with fixed effects, and finite-sample clustered inference can be unstable in small synthetic runs.

> Significance markers: `*` p < 0.10, `**` p < 0.05, `***` p < 0.01.

### ols / panelist_plus_product_features / rating

- **family**: `ols`
- **design**: `panelist_plus_product_features`
- **outcome_field**: `rating`
- **n_obs**: `60`
- **n_features**: `28`
- **covariance_type**: `cluster`
- **n_unique_panelist_clusters**: `20`
- **n_unique_product_clusters**: `9`
- **n_dropped_constant_columns**: `0`
- **n_dropped_duplicate_columns**: `1`
- **n_dropped_rank_deficient_columns**: `16`
- **r2**: `0.6538`
- **adj_r2**: `0.3616`
- **rmse**: `0.5464`
- **mae**: `0.4395`
- **aic**: `153.7392`
- **bic**: `212.3808`
- **log_likelihood**: `-48.8696`

Top attribute coefficients

| term | estimate | std_error | p_value | ci_low | ci_high |
| --- | --- | --- | --- | --- | --- |
| panelist.beer_style_affinity.lager | 16.6200*** | 0.8551 | 0.0000 | 14.8302 | 18.4099 |
| panelist.gender_male | 3.2496*** | 0.2714 | 0.0000 | 2.6816 | 3.8175 |
| panelist.beer_style_affinity.ipa | 18.7641*** | 1.9690 | 0.0000 | 14.6429 | 22.8853 |
| panelist.beer_style_affinity.wheat | 5.4601*** | 0.6074 | 0.0000 | 4.1888 | 6.7315 |
| panelist.age_group_40-49 | 7.7774*** | 0.9079 | 0.0000 | 5.8771 | 9.6777 |
| panelist.age_group_50-64 | 18.1850*** | 2.4985 | 0.0000 | 12.9555 | 23.4144 |
| panelist.beer_style_affinity.sour | -3.2396*** | 0.5937 | 0.0000 | -4.4822 | -1.9971 |
| panelist.sweetness_preference | 3.1629*** | 0.6333 | 0.0001 | 1.8374 | 4.4884 |
| panelist.age_group_65+ | 7.9960*** | 1.7732 | 0.0002 | 4.2845 | 11.7074 |
| panelist.region_Northeast | -2.3364*** | 0.5667 | 0.0006 | -3.5226 | -1.1502 |
| panelist.price_sensitivity | 5.0270*** | 1.2986 | 0.0010 | 2.3090 | 7.7451 |
| panelist.gender_nonbinary | 4.3521*** | 1.2377 | 0.0023 | 1.7616 | 6.9425 |

Dropped columns

| column | reason |
| --- | --- |
| panelist.income_bracket_30-60k | duplicate |
| product.ingredients.barrel_aged | rank_deficient |
| product.ingredients.citrus_hops | rank_deficient |
| product.ingredients.fruit_added | rank_deficient |
| product.ingredients.lactose | rank_deficient |
| product.ingredients.roasted_malt | rank_deficient |
| product.price_usd_6pack | rank_deficient |
| panelist.income_bracket_60-100k | rank_deficient |
| panelist.income_bracket_<30k | rank_deficient |
| panelist.region_South | rank_deficient |
| panelist.region_West | rank_deficient |
| product.style_Pilsner | rank_deficient |

Artifacts:
- `coefficients_attributes_csv`: `regression/00_ols_panelist_plus_product_features_rating_coefficients_attributes.csv`
- `coefficients_full_csv`: `regression/00_ols_panelist_plus_product_features_rating_coefficients_full.csv`
- `coefficients_top_attributes_csv`: `regression/00_ols_panelist_plus_product_features_rating_coefficients_top_attributes.csv`
- `dropped_columns_csv`: `regression/00_ols_panelist_plus_product_features_rating_dropped_columns.csv`
- `metadata_json`: `regression/00_ols_panelist_plus_product_features_rating_metadata.json`
- `summary_json`: `regression/00_ols_panelist_plus_product_features_rating_summary.json`

### ols / panelist_plus_product_features / bitterness

- **family**: `ols`
- **design**: `panelist_plus_product_features`
- **outcome_field**: `bitterness`
- **n_obs**: `60`
- **n_features**: `28`
- **covariance_type**: `cluster`
- **n_unique_panelist_clusters**: `20`
- **n_unique_product_clusters**: `9`
- **n_dropped_constant_columns**: `0`
- **n_dropped_duplicate_columns**: `1`
- **n_dropped_rank_deficient_columns**: `16`
- **r2**: `0.7575`
- **adj_r2**: `0.5530`
- **rmse**: `0.3399`
- **mae**: `0.2673`
- **aic**: `96.7667`
- **bic**: `155.4083`
- **log_likelihood**: `-20.3834`

Top attribute coefficients

| term | estimate | std_error | p_value | ci_low | ci_high |
| --- | --- | --- | --- | --- | --- |
| panelist.beer_style_affinity.wheat | -5.1397*** | 0.3236 | 0.0000 | -5.8170 | -4.4623 |
| panelist.beer_style_affinity.lager | -7.4732*** | 0.5555 | 0.0000 | -8.6360 | -6.3105 |
| panelist.price_sensitivity | -7.1186*** | 0.6116 | 0.0000 | -8.3986 | -5.8385 |
| panelist.gender_male | -1.8492*** | 0.1721 | 0.0000 | -2.2095 | -1.4889 |
| panelist.beer_style_affinity.sour | 5.3615*** | 0.5766 | 0.0000 | 4.1546 | 6.5684 |
| panelist.beer_style_affinity.ipa | -9.7548*** | 1.2654 | 0.0000 | -12.4034 | -7.1062 |
| panelist.gender_nonbinary | -5.9320*** | 0.8846 | 0.0000 | -7.7835 | -4.0806 |
| panelist.income_bracket_150k+ | -3.7347*** | 0.7273 | 0.0001 | -5.2569 | -2.2124 |
| panelist.abv_preference | 3.3277*** | 1.1573 | 0.0097 | 0.9054 | 5.7499 |
| product.flavor_profile.bitterness | 16.9154** | 6.1794 | 0.0131 | 3.9818 | 29.8490 |
| panelist.age_group_40-49 | -2.1895** | 0.8016 | 0.0133 | -3.8673 | -0.5118 |
| panelist.adventurousness | 3.2883** | 1.2434 | 0.0160 | 0.6859 | 5.8907 |

Dropped columns

| column | reason |
| --- | --- |
| panelist.income_bracket_30-60k | duplicate |
| product.ingredients.barrel_aged | rank_deficient |
| product.ingredients.citrus_hops | rank_deficient |
| product.ingredients.fruit_added | rank_deficient |
| product.ingredients.lactose | rank_deficient |
| product.ingredients.roasted_malt | rank_deficient |
| product.price_usd_6pack | rank_deficient |
| panelist.income_bracket_60-100k | rank_deficient |
| panelist.income_bracket_<30k | rank_deficient |
| panelist.region_South | rank_deficient |
| panelist.region_West | rank_deficient |
| product.style_Pilsner | rank_deficient |

Artifacts:
- `coefficients_attributes_csv`: `regression/01_ols_panelist_plus_product_features_bitterness_coefficients_attributes.csv`
- `coefficients_full_csv`: `regression/01_ols_panelist_plus_product_features_bitterness_coefficients_full.csv`
- `coefficients_top_attributes_csv`: `regression/01_ols_panelist_plus_product_features_bitterness_coefficients_top_attributes.csv`
- `dropped_columns_csv`: `regression/01_ols_panelist_plus_product_features_bitterness_dropped_columns.csv`
- `metadata_json`: `regression/01_ols_panelist_plus_product_features_bitterness_metadata.json`
- `summary_json`: `regression/01_ols_panelist_plus_product_features_bitterness_summary.json`

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

- Detailed machine-readable artifacts are saved under `summary/`, `metrics/`, `plots/`, and `regression/`.
- This report is intentionally lightweight and is meant to complement, not replace, the JSON/CSV outputs.
