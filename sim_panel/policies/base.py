from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence

import numpy as np

from sim_panel.policies.types import ExposureDecision, ManualAssignmentFn, PolicyName, RandomMode


@dataclass(frozen=True)
class PolicyConfig:
    """
    YAML-governed policy config.

    Note:
      - policies are PURE exposure logic (no LLM calls, no IO, no schema row creation)
      - generator owns orchestration, validation, and execution budgets
    """
    name: PolicyName

    # random/manual: how many evaluations per (panelist, t)
    evals_per_period: int = 1

    # random specifics
    random_mode: RandomMode = "balanced_quota"
    # Used only when random_mode == "iid_probs"
    product_probs: Optional[Dict[str, float]] = None  # product_id -> prob (need not sum to 1)

    # self_selection exposure
    # Default is "show all"; if want shortlist later, set choice_set_size.
    choice_set_size: Optional[int] = None  # None => show all
    allow_empty_selection: bool = True

    # manual policy hook (loader/wiring happens elsewhere)
    manual_assignment_fn: Optional[ManualAssignmentFn] = None


class Policy:
    """
    Pure exposure logic: decides what the panelist is exposed to.

    - random/manual -> list of product_ids to evaluate
    - self_selection -> choice_set of product_ids shown
    """

    def __init__(self, cfg: PolicyConfig) -> None:
        self.cfg = cfg

    @property
    def name(self) -> PolicyName:
        return self.cfg.name

    def decide(
        self,
        *,
        rng: np.random.Generator,
        panelist_id: str,
        t: int,
        product_ids: Sequence[str],
    ) -> ExposureDecision:
        raise NotImplementedError