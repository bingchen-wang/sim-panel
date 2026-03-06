from __future__ import annotations

from typing import List, Sequence

import numpy as np

from sim_panel.policies.base import Policy
from sim_panel.policies.types import ExposureDecision, SelectionSpec


def _sample_without_replacement(
    rng: np.random.Generator,
    items: Sequence[str],
    k: int,
) -> List[str]:
    if k <= 0:
        return []
    if k >= len(items):
        return list(items)
    idx = rng.choice(len(items), size=k, replace=False)
    return [items[i] for i in idx.tolist()]


class SelfSelectionPolicy(Policy):
    """
    Self-selection exposure.

    Default behavior (choice_set_size is None):
      - show ALL products

    If choice_set_size is provided:
      - show a shortlist sampled uniformly without replacement
    """

    def decide(
        self,
        *,
        rng: np.random.Generator,
        panelist_id: str,
        t: int,
        product_ids: Sequence[str],
    ) -> ExposureDecision:
        if self.cfg.choice_set_size is None:
            choice_set = list(product_ids)
            meta = {"choice_set": "all_products"}
        else:
            choice_set = _sample_without_replacement(rng, product_ids, self.cfg.choice_set_size)
            meta = {"choice_set": "shortlist", "choice_set_size": self.cfg.choice_set_size}

        sel = SelectionSpec(
            choice_set=choice_set,
            allow_empty=self.cfg.allow_empty_selection,
        )

        return ExposureDecision(
            panelist_id=panelist_id,
            t=t,
            policy=self.cfg.name,
            evaluate_product_ids=None,
            selection=sel,
            meta=meta,
        )