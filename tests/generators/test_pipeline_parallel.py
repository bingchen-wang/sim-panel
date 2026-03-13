from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from sim_panel.generators.pipeline import EventGenerator


class DummyState:
    def __init__(self) -> None:
        self.t = -1


class DummyPanelist:
    def __init__(self, panelist_id: str) -> None:
        self.panelist_id = panelist_id
        self.state = DummyState()
        self.attributes = {}


class DummyProduct:
    def __init__(self, product_id: str) -> None:
        self.product_id = product_id
        self.attributes = {}

    def display(self) -> str:
        return f"display:{self.product_id}"


def _make_cfg(max_workers: int) -> SimpleNamespace:
    return SimpleNamespace(
        seed=123,
        n_periods=1,
        max_workers=max_workers,
        outcome=None,
        policy=SimpleNamespace(name="random"),
        validate_on_finish=False,
    )


def test_parallel_generation_preserves_decision_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sim_panel.generators.pipeline.build_policy",
        lambda _cfg: object(),
    )

    panelists = [DummyPanelist(f"u{i}") for i in range(5)]
    products = [DummyProduct("p0")]

    decisions = [
        SimpleNamespace(panelist_id=f"u{i}", order=i)
        for i in range(5)
    ]

    def fake_decide_for_period(self, *, rng, policy, panelist_ids, t, product_ids):
        return decisions

    def fake_execute_decision(self, *, dec, panelist, product_by_id, t, outcome_model):
        # Later decisions finish earlier to force out-of-order completion.
        time.sleep(0.05 * (len(decisions) - 1 - dec.order))
        return [
            {
                "event_id": f"e-{dec.order}",
                "panelist_id": dec.panelist_id,
                "t": t,
                "event_type": "evaluation",
            }
        ]

    monkeypatch.setattr(EventGenerator, "_decide_for_period", fake_decide_for_period)
    monkeypatch.setattr(EventGenerator, "_execute_decision", fake_execute_decision)

    rows_seq = EventGenerator(cfg=_make_cfg(max_workers=1)).generate(
        panelists=panelists,
        products=products,
        progress=False,
    )
    rows_par = EventGenerator(cfg=_make_cfg(max_workers=4)).generate(
        panelists=panelists,
        products=products,
        progress=False,
    )

    assert rows_par == rows_seq
    assert [row["panelist_id"] for row in rows_par] == [f"u{i}" for i in range(5)]
    assert all(p.state.t == 0 for p in panelists)


def test_parallel_generation_wraps_worker_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sim_panel.generators.pipeline.build_policy",
        lambda _cfg: object(),
    )

    panelists = [DummyPanelist(f"u{i}") for i in range(3)]
    products = [DummyProduct("p0")]

    decisions = [
        SimpleNamespace(panelist_id="u0", order=0),
        SimpleNamespace(panelist_id="u1", order=1),
        SimpleNamespace(panelist_id="u2", order=2),
    ]

    def fake_decide_for_period(self, *, rng, policy, panelist_ids, t, product_ids):
        return decisions

    def fake_execute_decision(self, *, dec, panelist, product_by_id, t, outcome_model):
        if dec.panelist_id == "u1":
            raise ValueError("boom")
        return [
            {
                "event_id": f"e-{dec.order}",
                "panelist_id": dec.panelist_id,
                "t": t,
                "event_type": "evaluation",
            }
        ]

    monkeypatch.setattr(EventGenerator, "_decide_for_period", fake_decide_for_period)
    monkeypatch.setattr(EventGenerator, "_execute_decision", fake_execute_decision)

    with pytest.raises(RuntimeError) as exc_info:
        EventGenerator(cfg=_make_cfg(max_workers=4)).generate(
            panelists=panelists,
            products=products,
            progress=False,
        )

    message = str(exc_info.value)
    assert "Decision execution failed" in message
    assert "t=0" in message
    assert "panelist_id=u1" in message