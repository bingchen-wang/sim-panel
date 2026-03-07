from __future__ import annotations

from sim_panel.utils.hashing import sha256_json


def make_nonce(*, kind: str, seed: int, batch_idx: int) -> str:
    """
    Deterministic, content-neutral perturbation token to vary LLM outputs across batches.
    """
    return sha256_json({"kind": kind, "seed": seed, "batch_idx": batch_idx})[:12]