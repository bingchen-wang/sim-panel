from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from sim_panel.decisions.types import SelectionConfig, ExecutionRules
from sim_panel.outcomes.base import OutcomeConfig
from sim_panel.policies.base import PolicyConfig


@dataclass(frozen=True)
class ExecutionConfig:
    """
    Generator-side operational rules (NOT panelist constraints).
    This controls how many evaluations we actually execute after parsing selection.
    """
    rules: ExecutionRules = ExecutionRules()


@dataclass(frozen=True)
class GeneratorConfig:
    """
    Top-level generation config (YAML-governed in the CLI).

    Generators orchestrate:
      - policy exposure decisions
      - panelist selection/evaluation calls
      - outcome parsing/validation
      - schema event construction
      - optional schema validation

    Notes:
      - schema_version is stored per row and validated against schema registry.
      - seed governs RNG for exposure decisions and deterministic event ids.
    """
    schema_version: str = "0.1.0"
    seed: int = 0
    n_periods: int = 1

    policy: PolicyConfig = field(default_factory=lambda: PolicyConfig(name="random"))
    selection: SelectionConfig = field(default_factory=SelectionConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)

    outcome: Optional[OutcomeConfig] = None  # if None, outcomes/traces will be null

    # validation / debugging
    validate_on_finish: bool = True
    max_errors: int = 50
    include_panelist_features_in_events: bool = True  # stored in evaluation events (even if not rendered)
    include_product_features_in_events: bool = True
    include_product_features_in_selection_prompt: bool = True  # forwarded into decisions.SelectionConfig if desired

    # deterministic id namespace
    event_namespace: str = "sim_panel.v0"

    # parallelism: number of concurrent decision workers (1 = sequential)
    max_workers: int = 1

    # small metadata merged into each row
    row_meta: Dict[str, Any] = field(default_factory=dict)