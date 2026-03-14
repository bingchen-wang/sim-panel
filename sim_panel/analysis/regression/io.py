from __future__ import annotations

import json
import os
from typing import Dict

from sim_panel.analysis.regression.summarize import (
    coefficient_table_to_dataframe,
    dropped_columns_to_dataframe,
    filter_coefficient_table,
    regression_metadata_to_row,
    regression_result_to_summary_row,
    top_attribute_coefficients,
)
from sim_panel.analysis.regression.types import RegressionResult


def save_regression_result(
    *,
    result: RegressionResult,
    output_dir: str,
    prefix: str,
) -> Dict[str, str]:
    """
    Save a regression result and companion tables.

    Outputs:
    - summary json
    - metadata json
    - full coefficient table csv
    - attribute-only coefficient table csv
    - top-attribute coefficient table csv
    - dropped-columns csv
    """
    os.makedirs(output_dir, exist_ok=True)

    paths: Dict[str, str] = {}

    summary_path = os.path.join(output_dir, f"{prefix}_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(regression_result_to_summary_row(result), f, indent=2, ensure_ascii=False)
    paths["summary_json"] = summary_path

    metadata_path = os.path.join(output_dir, f"{prefix}_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(regression_metadata_to_row(result), f, indent=2, ensure_ascii=False)
    paths["metadata_json"] = metadata_path

    coef_df = coefficient_table_to_dataframe(result)
    coef_path = os.path.join(output_dir, f"{prefix}_coefficients_full.csv")
    coef_df.to_csv(coef_path, index=False)
    paths["coefficients_full_csv"] = coef_path

    attr_df = filter_coefficient_table(
        result,
        include_fixed_effects=False,
        include_intercept=False,
        include_thresholds=False,
        attribute_only=True,
    )
    attr_path = os.path.join(output_dir, f"{prefix}_coefficients_attributes.csv")
    attr_df.to_csv(attr_path, index=False)
    paths["coefficients_attributes_csv"] = attr_path

    top_df = top_attribute_coefficients(result, n=20, by="abs_estimate")
    top_path = os.path.join(output_dir, f"{prefix}_coefficients_top_attributes.csv")
    top_df.to_csv(top_path, index=False)
    paths["coefficients_top_attributes_csv"] = top_path

    dropped_df = dropped_columns_to_dataframe(result)
    dropped_path = os.path.join(output_dir, f"{prefix}_dropped_columns.csv")
    dropped_df.to_csv(dropped_path, index=False)
    paths["dropped_columns_csv"] = dropped_path

    return paths