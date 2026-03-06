from __future__ import annotations

import os
import pytest

from sim_panel.backends.base import BackendConfig
from sim_panel.backends.ollama import OllamaBackend


@pytest.mark.integration
def test_ollama_backend_smoke():
    """
    Opt-in integration test.

    Run:
      SIM_PANEL_TEST_OLLAMA=1 pytest -m integration -q

    Optional env:
      SIM_PANEL_OLLAMA_MODEL=gemma3:12b
      SIM_PANEL_OLLAMA_BASE_URL=http://localhost:11434
      SIM_PANEL_OLLAMA_TIMEOUT_S=60
    """
    if os.environ.get("SIM_PANEL_TEST_OLLAMA") != "1":
        pytest.skip("Set SIM_PANEL_TEST_OLLAMA=1 to run Ollama integration test.")

    model = os.environ.get("SIM_PANEL_OLLAMA_MODEL", "gemma3:12b")
    base_url = os.environ.get("SIM_PANEL_OLLAMA_BASE_URL", "http://localhost:11434")
    timeout_s = float(os.environ.get("SIM_PANEL_OLLAMA_TIMEOUT_S", "60"))

    cfg = BackendConfig(
        name="ollama",
        model=model,
        seed=0,
        return_usage=False,
        params={"base_url": base_url, "timeout_s": timeout_s},
    )
    backend = OllamaBackend(cfg)

    prompts = [
        "Reply with exactly: OK",
        "Give me one sentence describing a rainy day in Singapore.",
        "Return a JSON object with keys a and b where a=1 and b='x'. Output JSON only.",
    ]

    for p in prompts:
        res = backend.chat(
            [{"role": "user", "content": p}],
            temperature=0.2,
            max_tokens=128,
        )
        assert isinstance(res.content, str)
        assert res.content.strip() != ""