from __future__ import annotations

import concurrent.futures
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence

from sim_panel.utils.progress import tqdm_wrap
from sim_panel.decisions.selection import (
    render_selection_prompt,
    parse_selection_response,
    apply_execution_rules,
)
from sim_panel.decisions.types import SelectionContext

from sim_panel.generators.rng import make_rng, stable_event_id
from sim_panel.generators.types import GeneratorConfig

from sim_panel.outcomes.base import EvaluationContext
from sim_panel.outcomes.registry import build_outcome_model

from sim_panel.policies.registry import build_policy
from sim_panel.policies.types import ExposureDecision
from sim_panel.policies.random import RandomAssignmentPolicy  # renamed file

from sim_panel.schema.validate import (
    validate_rows,
    validate_unique_event_id,
    validate_self_selection_links,
)

from sim_panel.panelists.panelist import Panelist
from sim_panel.products.product import Product


# Type for checkpoint callback: called with (period, rows_for_period)
OnPeriodComplete = Callable[[int, List[Dict[str, Any]]], None]


@dataclass
class EventGenerator:
    """
    Orchestrates policy exposure + panelist selection/evaluation + outcomes into schema rows.

    Expectations:
      - panelists: Sequence[Panelist] runtime agents (LLM-capable)
      - products:  Sequence[Product] runtime wrappers (record + display())
    """

    cfg: GeneratorConfig

    def generate(
        self,
        *,
        panelists: Sequence[Panelist],
        products: Sequence[Product],
        progress: bool = True,
        resume_from_period: int = 0,
        prior_rows: Optional[List[Dict[str, Any]]] = None,
        on_period_complete: Optional[OnPeriodComplete] = None,
    ) -> List[Dict[str, Any]]:
        rng = make_rng(self.cfg.seed)

        policy = build_policy(self.cfg.policy)
        outcome_model = build_outcome_model(self.cfg.outcome) if self.cfg.outcome is not None else None

        panelist_ids = [p.panelist_id for p in panelists]
        product_ids = [p.product_id for p in products]

        product_by_id = {p.product_id: p for p in products}
        panelist_by_id = {p.panelist_id: p for p in panelists}

        # Start with prior rows from checkpoint (if resuming)
        rows: List[Dict[str, Any]] = list(prior_rows) if prior_rows else []

        # Advance RNG past completed periods so seeds match a fresh run
        for t in range(resume_from_period):
            self._decide_for_period(
                rng=rng, policy=policy, panelist_ids=panelist_ids,
                t=t, product_ids=product_ids,
            )

        if resume_from_period > 0:
            print(
                f"[checkpoint] Resuming from period {resume_from_period}/{self.cfg.n_periods} "
                f"({len(rows)} prior rows loaded)",
                file=sys.stderr, flush=True,
            )

        remaining = range(resume_from_period, self.cfg.n_periods)

        for t in tqdm_wrap(remaining, total=len(remaining), desc="Periods", enabled=progress):
            # generator owns time; update runtime agents
            for p in tqdm_wrap(panelists, total=len(panelists), desc=f"Set t={t}", enabled=progress and len(panelists) > 1000):
                p.state.t = t

            # Decide exposures for this period
            decisions = self._decide_for_period(
                rng=rng,
                policy=policy,
                panelist_ids=panelist_ids,
                t=t,
                product_ids=product_ids,
            )

            period_rows: List[Dict[str, Any]] = []

            # Execute decisions into events
            use_parallel = self.cfg.max_workers > 1 and len(decisions) > 1

            if use_parallel:
                ordered_batches: List[Optional[List[Dict[str, Any]]]] = [None] * len(decisions)

                with concurrent.futures.ThreadPoolExecutor(max_workers=self.cfg.max_workers) as pool:
                    future_to_meta = {
                        pool.submit(
                            self._execute_decision,
                            dec=dec,
                            panelist=panelist_by_id[dec.panelist_id],
                            product_by_id=product_by_id,
                            t=t,
                            outcome_model=outcome_model,
                        ): (idx, dec)
                        for idx, dec in enumerate(decisions)
                    }

                    for future in tqdm_wrap(
                        concurrent.futures.as_completed(future_to_meta),
                        total=len(future_to_meta),
                        desc=f"Execute t={t}",
                        enabled=progress,
                    ):
                        idx, dec = future_to_meta[future]
                        try:
                            ordered_batches[idx] = future.result()
                        except Exception as exc:
                            raise RuntimeError(
                                f"Decision execution failed at t={t}, idx={idx}, panelist_id={dec.panelist_id}"
                            ) from exc

                for batch in ordered_batches:
                    if batch is None:
                        raise RuntimeError("Parallel execution finished with a missing result batch.")
                    period_rows.extend(batch)
            else:
                for dec in tqdm_wrap(decisions, total=len(decisions), desc=f"Execute t={t}", enabled=progress):
                    period_rows.extend(
                        self._execute_decision(
                            dec=dec,
                            panelist=panelist_by_id[dec.panelist_id],
                            product_by_id=product_by_id,
                            t=t,
                            outcome_model=outcome_model,
                        )
                    )

            rows.extend(period_rows)

            if on_period_complete is not None:
                on_period_complete(t, period_rows)

        if self.cfg.validate_on_finish:
            self._validate(rows)

        return rows

    def _execute_decision(
        self,
        *,
        dec: ExposureDecision,
        panelist: Panelist,
        product_by_id: Dict[str, Product],
        t: int,
        outcome_model: Optional[Any],
    ) -> List[Dict[str, Any]]:
        """Process a single ExposureDecision and return the resulting event rows."""
        result_rows: List[Dict[str, Any]] = []

        if dec.evaluate_product_ids is not None:
            # random/manual: directly evaluate assigned products
            for prod_id in dec.evaluate_product_ids:
                prod = product_by_id.get(prod_id)
                if prod is None:
                    raise ValueError(f"Policy assigned unknown product_id={prod_id!r}")
                result_rows.append(
                    self._emit_evaluation_event(
                        panelist=panelist,
                        product=prod,
                        t=t,
                        selection_id=None,
                        outcome_model=outcome_model,
                    )
                )
            return result_rows

        if dec.selection is not None:
            # self_selection: show choice_set, let panelist request any number, then apply execution rules
            choice_set = list(dec.selection.choice_set)

            products_shown: List[Dict[str, Any]] = []
            for pid in choice_set:
                prod = product_by_id.get(pid)
                if prod is None:
                    continue
                item: Dict[str, Any] = {
                    "product_id": pid,
                    "product_display": prod.display(),
                }
                if self.cfg.selection.include_features:
                    item["product_features"] = dict(prod.attributes)
                products_shown.append(item)

            sel_ctx = SelectionContext(
                panelist_id=panelist.panelist_id,
                t=t,
                products_shown=products_shown,
            )
            strategy = self.cfg.prompting_strategy
            sel_prompt = render_selection_prompt(ctx=sel_ctx, cfg=self.cfg.selection, prompting_strategy=strategy)

            # For zero_shot / few_shot, override system prompt to remove persona
            sel_system_prompt = None
            if strategy in ("zero_shot", "few_shot"):
                sel_system_prompt = "You are evaluating consumer products. Provide honest, thoughtful responses."

            raw_sel = panelist.select(
                task_prompt=sel_prompt,
                choice_set=choice_set,
                metadata={"module": "generators.selection", "policy": self.cfg.policy.name, "t": t},
                system_prompt=sel_system_prompt,
            )

            parsed_sel = parse_selection_response(
                raw_text=raw_sel,
                choice_set_ids=choice_set,
                cfg=self.cfg.selection,
            )

            # Emit selection event (records free-will request)
            sel_row = self._emit_selection_event(
                panelist_id=panelist.panelist_id,
                t=t,
                choice_set=choice_set,
                selected_product_ids=parsed_sel.requested_product_ids,
                selection_traces=parsed_sel.traces,
                selection_errors=parsed_sel.errors,
            )
            result_rows.append(sel_row)
            selection_id = sel_row["event_id"]

            executed, dropped = apply_execution_rules(
                requested_product_ids=parsed_sel.requested_product_ids,
                choice_set_ids=choice_set,
                rules=self.cfg.execution.rules,
            )

            if not self.cfg.execution.rules.allow_empty and len(executed) == 0 and len(choice_set) > 0:
                # v0 fallback: evaluate the first shown item deterministically
                executed = [choice_set[0]]

            # Evaluate executed subset
            for prod_id in executed:
                prod = product_by_id.get(prod_id)
                if prod is None:
                    continue
                result_rows.append(
                    self._emit_evaluation_event(
                        panelist=panelist,
                        product=prod,
                        t=t,
                        selection_id=selection_id,
                        outcome_model=outcome_model,
                    )
                )

            # Store operational details as traces on the selection row
            if dropped or executed:
                sel_row.setdefault("traces", {})
                if isinstance(sel_row["traces"], dict):
                    if dropped:
                        sel_row["traces"]["dropped_product_ids"] = dropped
                    sel_row["traces"]["executed_product_ids"] = executed

            return result_rows

        raise ValueError("ExposureDecision must have either evaluate_product_ids or selection.")

    def _decide_for_period(
        self,
        *,
        rng,
        policy,
        panelist_ids: Sequence[str],
        t: int,
        product_ids: Sequence[str],
    ) -> List[ExposureDecision]:
        # Balanced RCT-like assignment is inherently global; use batch API when available.
        if isinstance(policy, RandomAssignmentPolicy) and getattr(policy.cfg, "random_mode", None) == "balanced_quota":
            return policy.decide_batch(rng=rng, panelist_ids=panelist_ids, t=t, product_ids=product_ids)  # type: ignore[attr-defined]
        return [
            policy.decide(rng=rng, panelist_id=pid, t=t, product_ids=product_ids)
            for pid in panelist_ids
        ]

    def _emit_selection_event(
        self,
        *,
        panelist_id: str,
        t: int,
        choice_set: List[str],
        selected_product_ids: List[str],
        selection_traces: Optional[Dict[str, Any]],
        selection_errors: Optional[List[str]],
    ) -> Dict[str, Any]:
        base: Dict[str, Any] = {
            "schema_version": self.cfg.schema_version,
            "event_type": "selection",
            "policy": self.cfg.policy.name,
            "panelist_id": panelist_id,
            "t": t,
            "choice_set": list(choice_set),
            "selected_product_ids": list(selected_product_ids),
            "selection_id": None,
            "outcomes": None,
            "traces": selection_traces if selection_traces is not None else None,
        }
        if selection_errors:
            base.setdefault("traces", {})
            if isinstance(base["traces"], dict):
                base["traces"]["selection_errors"] = selection_errors

        event_id = stable_event_id(
            self.cfg.event_namespace,
            {
                "schema_version": self.cfg.schema_version,
                "event_type": "selection",
                "policy": self.cfg.policy.name,
                "panelist_id": panelist_id,
                "t": t,
                "choice_set": list(choice_set),
                "selected_product_ids": list(selected_product_ids),
            },
        )
        return {"event_id": event_id, **base, **(self.cfg.row_meta or {})}

    def _emit_evaluation_event(
        self,
        *,
        panelist: Panelist,
        product: Product,
        t: int,
        selection_id: Optional[str],
        outcome_model: Optional[Any],
    ) -> Dict[str, Any]:
        panelist_id = panelist.panelist_id
        product_id = product.product_id

        product_display = product.display()

        panelist_features: Dict[str, Any] = {}
        if self.cfg.include_panelist_features_in_events:
            panelist_features = dict(getattr(panelist, "attributes", {}) or {})

        product_features: Dict[str, Any] = {}
        if self.cfg.include_product_features_in_events:
            product_features = dict(product.attributes)

        outcomes = None
        traces = None
        if outcome_model is not None:
            ctx = EvaluationContext(
                panelist_id=panelist_id,
                product_id=product_id,
                t=t,
                product_display=product_display,
                panelist_features=panelist_features,
                product_features=product_features,
            )
            res = outcome_model.evaluate(panelist=panelist, ctx=ctx, prompting_strategy=self.cfg.prompting_strategy)
            outcomes = res.outcomes
            traces = res.traces
            if res.errors:
                traces = dict(traces or {})
                traces["outcome_errors"] = res.errors

        base = {
            "schema_version": self.cfg.schema_version,
            "event_type": "evaluation",
            "policy": self.cfg.policy.name,
            "panelist_id": panelist_id,
            "t": t,
            "product_id": product_id,
            "product_display": product_display,
            "panelist_features": panelist_features,
            "product_features": product_features,
            "outcomes": outcomes,
            "traces": traces,
            "selection_id": selection_id,
        }

        event_id = stable_event_id(
            self.cfg.event_namespace,
            {
                "schema_version": self.cfg.schema_version,
                "event_type": "evaluation",
                "policy": self.cfg.policy.name,
                "panelist_id": panelist_id,
                "t": t,
                "product_id": product_id,
                "selection_id": selection_id,
            },
        )
        return {"event_id": event_id, **base, **(self.cfg.row_meta or {})}

    def _validate(self, rows: Sequence[Dict[str, Any]]) -> None:
        report = validate_rows(rows, schema_version=None, max_errors=self.cfg.max_errors)
        if not report.ok:
            raise ValueError(f"Schema validation failed: {report.summary()}")

        ok, msg = validate_unique_event_id(rows)
        if not ok:
            raise ValueError(f"event_id uniqueness check failed: {msg}")

        if self.cfg.policy.name == "self_selection":
            ok2, problems = validate_self_selection_links(rows)
            if not ok2:
                raise ValueError(f"self_selection link check failed: {problems}")