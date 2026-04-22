# Cross-condition comparison report

Mode: `cross`

Outcome field: `rating`

## Per-condition metrics

| label | model | strategy | n_evaluations | n_with_outcome | rating_mean | rating_std | rating_median | rating_entropy | rating_normalized_entropy | panelist_mean_variance | mean_pairwise_panelist_distance | product_mean_variance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amazon_self_selection | gemma3:12b | persona | 58 | 58 | 2.5345 | 1.0207 | 3.0000 | 1.9025 | 0.9513 | 0.2586 | 1.2355 | 0.3642 |
| amazon_self_selection_cot | gemma3:12b | persona_cot | 29 | 29 | 2.5862 | 1.0345 | 3.0000 | 1.7780 | 0.8890 | 0.3287 | 1.0061 | 0.5648 |

## rating_mean (model x strategy)

| model | persona | persona_cot |
| --- | --- | --- |
| gemma3:12b | 2.5345 | 2.5862 |

## rating_std (model x strategy)

| model | persona | persona_cot |
| --- | --- | --- |
| gemma3:12b | 1.0207 | 1.0345 |

## panelist_mean_variance (model x strategy)

| model | persona | persona_cot |
| --- | --- | --- |
| gemma3:12b | 0.2586 | 0.3287 |

## mean_pairwise_panelist_distance (model x strategy)

| model | persona | persona_cot |
| --- | --- | --- |
| gemma3:12b | 1.2355 | 1.0061 |

## product_mean_variance (model x strategy)

| model | persona | persona_cot |
| --- | --- | --- |
| gemma3:12b | 0.3642 | 0.5648 |

## rating_normalized_entropy (model x strategy)

| model | persona | persona_cot |
| --- | --- | --- |
| gemma3:12b | 0.9513 | 0.8890 |

## Jensen-Shannon divergence (distribution overlap)

| | amazon_self_selection | amazon_self_selection_cot |
| --- | --- | --- |
| amazon_self_selection | 0.0000 | 0.0114 |
| amazon_self_selection_cot | 0.0114 | 0.0000 |

## Pairwise RMSE (over shared panelist-product pairs)

| | amazon_self_selection | amazon_self_selection_cot |
| --- | --- | --- |
| amazon_self_selection | 0.0000 | 0.4330 |
| amazon_self_selection_cot | 0.4330 | 0.0000 |
