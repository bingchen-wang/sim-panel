import json
import urllib.request

import pytest

from sim_panel.backends import BackendConfig
from sim_panel.backends.ollama import OllamaBackend


class _FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._data = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_ollama_backend_parses_response(monkeypatch):
    # Arrange
    cfg = BackendConfig(
        name="ollama",
        model="llama3.1:8b-instruct",
        seed=7,
        return_usage=True,
        params={"base_url": "http://localhost:11434", "timeout_s": 1},
    )
    backend = OllamaBackend(cfg)

    fake_obj = {
        "model": "llama3.1:8b-instruct",
        "message": {"role": "assistant", "content": "hello from ollama"},
        "done": True,
        "prompt_eval_count": 10,
        "eval_count": 5,
    }

    def fake_urlopen(req: urllib.request.Request, timeout: float):
        # Basic sanity checks about the outgoing request
        assert req.full_url.endswith("/api/chat")
        assert req.get_method() == "POST"
        body = json.loads(req.data.decode("utf-8"))
        assert body["model"] == "llama3.1:8b-instruct"
        assert body["stream"] is False
        # We expect seed passed via options (if set) and num_predict mapping for max_tokens
        assert body["options"]["seed"] == 7
        return _FakeHTTPResponse(fake_obj)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    # Act
    res = backend.chat(
        [{"role": "user", "content": "say hi"}],
        temperature=0.2,
        max_tokens=12,
    )

    # Assert
    assert res.content == "hello from ollama"
    assert res.model == "llama3.1:8b-instruct"
    assert res.finish_reason == "stop"
    assert res.usage.prompt_tokens == 10
    assert res.usage.completion_tokens == 5
    assert res.usage.total_tokens == 15
    assert res.raw is not None