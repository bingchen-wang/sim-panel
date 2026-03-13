from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from sim_panel.data_gen.personas import generate_persona_records_llm
from sim_panel.data_gen.products import generate_beer_product_records_llm


class DummyBackend:
    pass


def _persona_settings(max_workers: int) -> SimpleNamespace:
    return SimpleNamespace(
        batch_size=2,
        max_retries=0,
        max_workers=max_workers,
        temperature=0.2,
        max_tokens=256,
        metadata=None,
        use_nonce=False,
    )


def _product_settings(max_workers: int) -> SimpleNamespace:
    return SimpleNamespace(
        batch_size=2,
        max_retries=0,
        max_workers=max_workers,
        temperature=0.2,
        max_tokens=256,
        metadata=None,
        use_nonce=False,
    )


def test_parallel_persona_generation_preserves_order(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_call_personas_batch(*, backend, n, seed, base_seed, batch_idx, settings):
        time.sleep(0.05 * (2 - batch_idx))
        return f"persona-batch-{batch_idx}"

    def fake_parse_personas_payload(raw: str, *, k_expected: int):
        batch_idx = int(raw.rsplit("-", 1)[1])
        return [{"attributes": {"batch_idx": batch_idx, "item_idx": j}} for j in range(k_expected)]

    monkeypatch.setattr("sim_panel.data_gen.personas._call_personas_batch", fake_call_personas_batch)
    monkeypatch.setattr("sim_panel.data_gen.personas._parse_personas_payload", fake_parse_personas_payload)

    rows_seq = generate_persona_records_llm(
        backend=DummyBackend(),
        n_personas=6,
        seed=123,
        settings=_persona_settings(max_workers=1),
        progress=False,
    )
    rows_par = generate_persona_records_llm(
        backend=DummyBackend(),
        n_personas=6,
        seed=123,
        settings=_persona_settings(max_workers=4),
        progress=False,
    )

    assert [r.persona_id for r in rows_par] == [r.persona_id for r in rows_seq]
    assert [r.attributes for r in rows_par] == [r.attributes for r in rows_seq]


def test_parallel_persona_generation_wraps_worker_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_call_personas_batch(*, backend, n, seed, base_seed, batch_idx, settings):
        if batch_idx == 1:
            raise ValueError("boom")
        return f"persona-batch-{batch_idx}"

    monkeypatch.setattr("sim_panel.data_gen.personas._call_personas_batch", fake_call_personas_batch)

    with pytest.raises(RuntimeError) as exc_info:
        generate_persona_records_llm(
            backend=DummyBackend(),
            n_personas=6,
            seed=123,
            settings=_persona_settings(max_workers=4),
            progress=False,
        )

    assert "Persona batch generation failed at batch_idx=1" in str(exc_info.value)


def test_parallel_product_generation_preserves_order(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_call_products_batch(*, backend, n, seed, base_seed, batch_idx, settings):
        time.sleep(0.05 * (2 - batch_idx))
        return f"product-batch-{batch_idx}"

    def fake_parse_products_payload(raw: str, *, k_expected: int):
        batch_idx = int(raw.rsplit("-", 1)[1])
        return [
            {
                "display_name": f"beer-{batch_idx}-{j}",
                "attributes": {"batch_idx": batch_idx, "item_idx": j},
            }
            for j in range(k_expected)
        ]

    monkeypatch.setattr("sim_panel.data_gen.products._call_products_batch", fake_call_products_batch)
    monkeypatch.setattr("sim_panel.data_gen.products._parse_products_payload", fake_parse_products_payload)

    rows_seq = generate_beer_product_records_llm(
        backend=DummyBackend(),
        n_products=6,
        seed=123,
        settings=_product_settings(max_workers=1),
        progress=False,
    )
    rows_par = generate_beer_product_records_llm(
        backend=DummyBackend(),
        n_products=6,
        seed=123,
        settings=_product_settings(max_workers=4),
        progress=False,
    )

    assert [r.product_id for r in rows_par] == [r.product_id for r in rows_seq]
    assert [r.attributes for r in rows_par] == [r.attributes for r in rows_seq]
    assert [r.display_name for r in rows_par] == [r.display_name for r in rows_seq]


def test_parallel_product_generation_wraps_worker_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_call_products_batch(*, backend, n, seed, base_seed, batch_idx, settings):
        if batch_idx == 1:
            raise ValueError("boom")
        return f"product-batch-{batch_idx}"

    monkeypatch.setattr("sim_panel.data_gen.products._call_products_batch", fake_call_products_batch)

    with pytest.raises(RuntimeError) as exc_info:
        generate_beer_product_records_llm(
            backend=DummyBackend(),
            n_products=6,
            seed=123,
            settings=_product_settings(max_workers=4),
            progress=False,
        )

    assert "Product batch generation failed at batch_idx=1" in str(exc_info.value)