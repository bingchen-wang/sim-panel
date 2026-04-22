from __future__ import annotations

from typing import List, Optional, Tuple

from sim_panel.analysis.compare.types import CompareMode, ConditionSpec


def resolve_compare_mode(conditions: list[ConditionSpec]) -> CompareMode:
    """
    Detect whether compare is running with a real reference condition.

    Returns:
        (benchmark_mode, reference_condition)

    Rules:
    - 0 real conditions: benchmark mode off
    - 1 real condition: benchmark mode on
    - >1 real conditions: fail fast
    """
    real_conditions = [cond for cond in conditions if cond.is_real]

    if not real_conditions:
        return CompareMode(kind="cross")

    if len(real_conditions) == 1:
        return CompareMode(
            kind="benchmark",
            reference_label=real_conditions[0].label,
        )

    labels = ", ".join(cond.label for cond in real_conditions)
    raise ValueError(
        "compare currently supports at most one real reference condition; "
        f"found {len(real_conditions)} real conditions: {labels}"
    )