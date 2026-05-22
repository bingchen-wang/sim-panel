from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Protocol, Sequence


PolicyName = Literal["random", "manual", "self_selection"]
RandomMode = Literal["balanced_quota", "iid_probs"]


@dataclass(frozen=True)
class SelectionSpec:
    """
    Self-selection exposure spec.

    Policy controls what is SHOWN (choice_set).
    Panelist returns what they WANT (requested_product_ids) later.
    Generator may apply operational rules (budget caps, filtering) later.
    """
    choice_set: List[str]
    allow_empty: bool = True


@dataclass(frozen=True)
class ExposureDecision:
    """
    Policy decision for one ``(panelist_id, t)``.

    Exactly one of the following fields should be populated:

    - ``evaluate_product_ids`` for random/manual exposure.
    - ``selection`` for self-selection exposure.
    """
    panelist_id: str
    t: int
    policy: PolicyName

    evaluate_product_ids: Optional[List[str]] = None
    selection: Optional[SelectionSpec] = None

    meta: Optional[Dict[str, Any]] = None


class ManualAssignmentFn(Protocol):
    """
    Manual assignment hook. Expected to be deterministic conditional on inputs.

    Returns either a single product_id or a list of product_ids to evaluate.
    """
    def __call__(self, panelist_id: str, t: int, product_ids: Sequence[str]) -> str | List[str]:
        ...