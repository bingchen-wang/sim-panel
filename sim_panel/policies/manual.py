from __future__ import annotations

from typing import List, Sequence

import numpy as np

from sim_panel.policies.base import Policy
from sim_panel.policies.types import ExposureDecision


class ManualAssignmentPolicy(Policy):
    """
    Manual exposure from a user-provided mapping function.
    Loader/wiring from file happens elsewhere; policy stays pure.

    The function takes (panelist_id, t, product_ids) and returns:
      - product_id (str), or
      - list[str]
    """

    def decide(
        self,
        *,
        rng: np.random.Generator,  # unused; kept for API parity
        panelist_id: str,
        t: int,
        product_ids: Sequence[str],
    ) -> ExposureDecision:
        if self.cfg.manual_assignment_fn is None:
            raise ValueError("ManualAssignmentPolicy requires cfg.manual_assignment_fn")

        out = self.cfg.manual_assignment_fn(panelist_id, t, product_ids)
        chosen: List[str] = [out] if isinstance(out, str) else list(out)

        return ExposureDecision(
            panelist_id=panelist_id,
            t=t,
            policy=self.cfg.name,
            evaluate_product_ids=chosen,
            selection=None,
            meta={"method": "manual_fn"},
        )