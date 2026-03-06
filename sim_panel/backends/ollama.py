from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Mapping, Optional, Sequence

from .base import Backend, BackendConfig
from .errors import BackendConfigError, BackendRequestError
from .types import ChatResult, Message, Usage

class OllamaBackend(Backend):
    """
    Backend that calls Ollama's native REST API: POST /api/chat.

    Docs:
      - Default base URL: http://localhost:11434
      - Endpoint: /api/chat
    """
    def __init__(self, config: BackendConfig):
        super().__init__(config)

        self.base_url = str(self.config.params.get("base_url", "http://localhost:11434"))
        self.timeout_s = float(self.config.params.get("timeout_s", 60.0))

        base = self.base_url.strip()
        if not base:
            raise BackendConfigError("Ollama base_url is empty.")
        if self.timeout_s <= 0:
            raise BackendConfigError("Ollama timeout_s must be > 0.")

        self._chat_url = base.rstrip("/") + "/api/chat"

    def chat(
        self,
        messages: Sequence[Message],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> ChatResult:
        # Ollama native API supports model + messages. "stream": false for a single JSON response.
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [dict(m) for m in messages],  # ensure plain dicts
            "stream": False,
        }

        # Ollama supports various "options" knobs; we pass a minimal subset.
        # If None, omit to avoid sending junk.
        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = float(temperature)
        if max_tokens is not None:
            # Ollama uses "num_predict" for max generated tokens.
            options["num_predict"] = int(max_tokens)
        if self.config.seed is not None:
            options["seed"] = int(self.config.seed)

        if options:
            payload["options"] = options

        # _ = metadata

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self._chat_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw_bytes = resp.read()
        except urllib.error.HTTPError as e:
            # Include response body snippet if available for debugging.
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            raise BackendRequestError(
                f"Ollama HTTPError {e.code} calling {self._chat_url}: {body[:500]}"
            ) from e
        except Exception as e:
            raise BackendRequestError(f"Ollama request failed calling {self._chat_url}: {e}") from e

        try:
            obj = json.loads(raw_bytes.decode("utf-8"))
        except Exception as e:
            snippet = raw_bytes[:200].decode("utf-8", errors="replace")
            raise BackendRequestError(f"Ollama returned non-JSON response (first 200 chars): {snippet}") from e

        # Typical response includes:
        # {
        #   "model": "...",
        #   "message": {"role":"assistant","content":"..."},
        #   "done": true,
        #   ...
        # }
        try:
            content = obj["message"]["content"]
        except Exception as e:
            raise BackendRequestError(f"Unexpected Ollama response format: {obj}") from e

        usage = Usage()
        if self.config.return_usage:
            # Native Ollama API does not guarantee token usage.
            # Some builds/providers may include eval_count/prompt_eval_count; map if present.
            prompt_eval = obj.get("prompt_eval_count")
            eval_count = obj.get("eval_count")
            if isinstance(prompt_eval, int) or isinstance(eval_count, int):
                pt = int(prompt_eval or 0)
                ct = int(eval_count or 0)
                usage = Usage(prompt_tokens=pt, completion_tokens=ct, total_tokens=pt + ct)

        return ChatResult(
            content=str(content),
            model=str(obj.get("model") or self.config.model),
            usage=usage,
            raw=obj,
            finish_reason="stop" if obj.get("done") is True else None,
        )


def factory(config: BackendConfig) -> OllamaBackend:
    return OllamaBackend(config)
