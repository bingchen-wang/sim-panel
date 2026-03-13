from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from sim_panel.outcomes.base import EvaluationContext, OutcomeConfig, OutcomeResult
from sim_panel.outcomes.specs import QuestionnaireSpec, FieldSpec


class DeterministicOutcomeModel:
    """
    Deterministic questionnaire filler for CI/tests.

    Strategy:
      - For categorical / choices fields: pick the first choice deterministically (or hash-index if desired).
      - For int/float: hash into range if provided, else 0/0.0.
      - For bool: hash parity.
      - For text: short templated stub.
    """

    def __init__(self, cfg: OutcomeConfig) -> None:
        self.cfg = cfg

    def evaluate(self, *, panelist, ctx: EvaluationContext, prompting_strategy: str = "persona") -> OutcomeResult:
        q = self.cfg.questionnaire
        seed = f"{ctx.panelist_id}|{ctx.product_id}|{ctx.t}".encode("utf-8")
        h = hashlib.blake2b(seed, digest_size=8).hexdigest()
        u = int(h, 16)

        outcomes: Dict[str, Any] = {}
        for fs in q.outcome_fields:
            outcomes[fs.name] = _fill_field(fs, u)

        traces: Dict[str, Any] = {}
        for fs in q.trace_fields:
            traces[fs.name] = _fill_trace_field(fs, u, ctx)

        return OutcomeResult(
            outcomes=outcomes,
            traces=traces if q.trace_fields else {},
            raw_text=None,
            errors=[],
        )


def _fill_field(fs: FieldSpec, u: int) -> Any:
    if fs.choices:
        # Stable but not always first: index by hash
        idx = u % len(fs.choices)
        return fs.choices[idx]

    if fs.type == "int":
        lo = int(fs.min_value) if fs.min_value is not None else 0
        hi = int(fs.max_value) if fs.max_value is not None else lo + 10
        if hi < lo:
            hi = lo
        span = max(1, hi - lo + 1)
        return lo + (u % span)

    if fs.type == "float":
        lo = float(fs.min_value) if fs.min_value is not None else 0.0
        hi = float(fs.max_value) if fs.max_value is not None else lo + 1.0
        if hi < lo:
            hi = lo
        # map u to [0,1)
        frac = (u % 10_000) / 10_000.0
        return lo + (hi - lo) * frac

    if fs.type == "bool":
        return bool(u % 2)

    if fs.type == "categorical":
        # categorical without choices is ill-formed; return a placeholder
        return "option"

    if fs.type == "text":
        return "..."

    if fs.type == "json":
        return {}

    return None


def _fill_trace_field(fs: FieldSpec, u: int, ctx: EvaluationContext) -> Any:
    if fs.type == "text":
        # Short stable stub
        return f"[deterministic trace] panelist={ctx.panelist_id} product={ctx.product_id} t={ctx.t}"
    if fs.type == "json":
        return {"panelist_id": ctx.panelist_id, "product_id": ctx.product_id, "t": ctx.t, "seed": int(u % 1_000_000)}
    # For other types, reuse general filler
    return _fill_field(fs, u)