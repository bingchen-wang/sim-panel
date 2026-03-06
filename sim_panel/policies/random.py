from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from sim_panel.policies.base import Policy
from sim_panel.policies.types import ExposureDecision


def _normalize_probs(p: Dict[str, float]) -> Dict[str, float]:
    s = 0.0
    out: Dict[str, float] = {}
    for k, v in p.items():
        if v < 0:
            raise ValueError(f"Negative probability for product_id={k}: {v}")
        if v == 0:
            continue
        out[k] = float(v)
        s += float(v)
    if s <= 0:
        raise ValueError("All probabilities are zero (or empty).")
    for k in list(out.keys()):
        out[k] = out[k] / s
    return out


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


@dataclass
class _BalancedScheduler:
    """
    Internal helper to assign products to panelists in a balanced-quota way per period t.

    For each t, build a product pool with near-equal counts across products, shuffle it,
    then pop assignments for each panelist.
    """
    rng: np.random.Generator
    product_ids: List[str]
    evals_per_period: int

    # keyed by t: list of remaining product assignments (acting as a stack)
    pools: Dict[int, List[str]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.pools = {}

    def assignments_for(self, *, t: int, n_panelists: int) -> List[List[str]]:
        # Each panelist needs evals_per_period products, so total draws:
        total = n_panelists * self.evals_per_period
        pool = self._make_pool(total=total)
        self.rng.shuffle(pool)
        # Partition sequentially into per-panelist allocations
        out: List[List[str]] = []
        i = 0
        for _ in range(n_panelists):
            out.append(pool[i : i + self.evals_per_period])
            i += self.evals_per_period
        return out

    def _make_pool(self, *, total: int) -> List[str]:
        m = len(self.product_ids)
        if m == 0:
            return []
        # Repeat full cycles + remainder to hit 'total'
        q, r = divmod(total, m)
        pool: List[str] = []
        if q > 0:
            pool.extend(self.product_ids * q)
        if r > 0:
            # sample r distinct products for the remainder to keep balance tight
            pool.extend(_sample_without_replacement(self.rng, self.product_ids, r))
        return pool


class RandomAssignmentPolicy(Policy):
    """
    Randomized exposure, with RCT-like balanced allocation by default.

    Modes:
      - balanced_quota: equal/near-equal panelist counts per product (per period)
      - iid_probs: per-panelist independent draws using a product probability distribution
    """

    def __init__(self, cfg) -> None:
        super().__init__(cfg)
        self._balanced_scheduler: Optional[_BalancedScheduler] = None
        self._balanced_cache_key: Optional[Tuple[int, int, int]] = None  # (seed_marker, n_products, evals_per_period)

    def prepare_for_period(
        self,
        *,
        rng: np.random.Generator,
        product_ids: Sequence[str],
    ) -> None:
        """
        Optional hook: generator may call this once per run (or per period) to prime schedulers.
        (Kept optional so Policy API stays minimal.)
        """
        if self.cfg.random_mode != "balanced_quota":
            return
        # Cache scheduler keyed by product set size + evals_per_period.
        # rng identity is external; scheduler uses rng passed at construction time.
        key = (id(rng), len(product_ids), self.cfg.evals_per_period)
        if self._balanced_scheduler is None or self._balanced_cache_key != key:
            self._balanced_scheduler = _BalancedScheduler(
                rng=rng,
                product_ids=list(product_ids),
                evals_per_period=self.cfg.evals_per_period,
            )
            self._balanced_cache_key = key

    def decide_batch(
        self,
        *,
        rng: np.random.Generator,
        panelist_ids: Sequence[str],
        t: int,
        product_ids: Sequence[str],
    ) -> List[ExposureDecision]:
        """
        Batch decision method for balanced_quota (preferred) to guarantee balance.

        Generator can call this for each t to get all decisions in one shot.
        """
        if self.cfg.random_mode != "balanced_quota":
            # Fallback to per-panelist decide
            return [
                self.decide(rng=rng, panelist_id=pid, t=t, product_ids=product_ids)
                for pid in panelist_ids
            ]

        if self._balanced_scheduler is None:
            self.prepare_for_period(rng=rng, product_ids=product_ids)

        assert self._balanced_scheduler is not None
        allocs = self._balanced_scheduler.assignments_for(t=t, n_panelists=len(panelist_ids))

        out: List[ExposureDecision] = []
        for pid, chosen in zip(panelist_ids, allocs):
            out.append(
                ExposureDecision(
                    panelist_id=pid,
                    t=t,
                    policy=self.cfg.name,
                    evaluate_product_ids=list(chosen),
                    selection=None,
                    meta={"random_mode": "balanced_quota"},
                )
            )
        return out

    def decide(
        self,
        *,
        rng: np.random.Generator,
        panelist_id: str,
        t: int,
        product_ids: Sequence[str],
    ) -> ExposureDecision:
        if self.cfg.random_mode == "balanced_quota":
            # Note: balanced_quota is best used via decide_batch; this is a reasonable fallback.
            chosen = _sample_without_replacement(rng, product_ids, self.cfg.evals_per_period)
            return ExposureDecision(
                panelist_id=panelist_id,
                t=t,
                policy=self.cfg.name,
                evaluate_product_ids=chosen,
                selection=None,
                meta={"random_mode": "balanced_quota", "note": "fallback_single_decide"},
            )

        if self.cfg.random_mode == "iid_probs":
            probs = self.cfg.product_probs
            if probs is None:
                # Default to uniform iid
                chosen = list(rng.choice(list(product_ids), size=self.cfg.evals_per_period, replace=False))
                return ExposureDecision(
                    panelist_id=panelist_id,
                    t=t,
                    policy=self.cfg.name,
                    evaluate_product_ids=chosen,
                    selection=None,
                    meta={"random_mode": "iid_probs", "probs": "uniform"},
                )

            pnorm = _normalize_probs(probs)
            # Align probabilities to product_ids; missing products get prob 0.
            ids = list(product_ids)
            pvec = np.array([pnorm.get(pid, 0.0) for pid in ids], dtype=float)
            if pvec.sum() <= 0:
                raise ValueError("product_probs assigns zero probability mass to all available products.")
            pvec = pvec / pvec.sum()
            chosen_idx = rng.choice(len(ids), size=min(self.cfg.evals_per_period, len(ids)), replace=False, p=pvec)
            chosen = [ids[i] for i in chosen_idx.tolist()]
            return ExposureDecision(
                panelist_id=panelist_id,
                t=t,
                policy=self.cfg.name,
                evaluate_product_ids=chosen,
                selection=None,
                meta={"random_mode": "iid_probs", "probs": "custom"},
            )

        raise ValueError(f"Unknown random_mode: {self.cfg.random_mode}")