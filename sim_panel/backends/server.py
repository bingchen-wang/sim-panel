from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Mapping, Optional, Sequence

from .base import Backend, BackendConfig
from .errors import BackendConfigError, BackendRequestError
from .types import ChatResult, Message, Usage


class ServerBackend(Backend):
    """
    Generic server HTTP backend using the Chat Completions schema.

    Intended for self-hosted inference servers (e.g., vLLM/TGI/SGLang gateways)
    that expose an endpoint compatible with:
      POST {base_url}/chat/completions

    BackendConfig.params (YAML-governed):
      - base_url: str (e.g., "http://host:8000/v1")
      - timeout_s: float (default 120)
      - api_key_env: str (optional env var name holding a bearer token)
      - api_key: str (optional; discouraged vs api_key_env)
      - headers: dict[str, str] (optional extra headers)
      - endpoint: str (optional; default "chat/completions")
    """

    def __init__(self, config: BackendConfig):
        super().__init__(config)

        params = self.config.params

        base_url = str(params.get("base_url", "")).strip()
        if not base_url:
            raise BackendConfigError("ServerBackend requires params.base_url (e.g., http://host:8000/v1).")

        self.timeout_s = float(params.get("timeout_s", 120.0))
        if self.timeout_s <= 0:
            raise BackendConfigError("ServerBackend timeout_s must be > 0.")

        endpoint = str(params.get("endpoint", "chat/completions")).strip().lstrip("/")
        self.url = base_url.rstrip("/") + "/" + endpoint

        api_key = None
        api_key_env = params.get("api_key_env")
        if api_key_env:
            api_key = os.environ.get(str(api_key_env))
            if not api_key:
                raise BackendConfigError(f"Environment variable '{api_key_env}' is not set.")
        else:
            # Allow literal api_key in YAML, but discourage it (secrets in files).
            if "api_key" in params and params["api_key"]:
                api_key = str(params["api_key"])

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        extra_headers = params.get("headers")
        if extra_headers:
            if not isinstance(extra_headers, dict):
                raise BackendConfigError("params.headers must be a dict[str, str].")
            for k, v in extra_headers.items():
                headers[str(k)] = str(v)

        self.headers = headers

    def chat(
        self,
        messages: Sequence[Message],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> ChatResult:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [dict(m) for m in messages],
        }
        if temperature is not None:
            payload["temperature"] = float(temperature)
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        if self.config.seed is not None:
            # Some servers support seed; others ignore.
            payload["seed"] = int(self.config.seed)
        if metadata:
            # Some gateways accept metadata; harmless if ignored.
            payload["metadata"] = dict(metadata)

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self.url, data=data, headers=self.headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw_bytes = resp.read()
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            raise BackendRequestError(
                f"ServerBackend HTTPError {e.code} calling {self.url}: {body[:800]}"
            ) from e
        except Exception as e:
            raise BackendRequestError(f"ServerBackend request failed calling {self.url}: {e}") from e

        try:
            obj = json.loads(raw_bytes.decode("utf-8"))
        except Exception as e:
            snippet = raw_bytes[:200].decode("utf-8", errors="replace")
            raise BackendRequestError(
                f"ServerBackend returned non-JSON response (first 200 chars): {snippet}"
            ) from e

        # Parse Chat Completions-like response:
        # {
        #   "choices": [{"message": {"role":"assistant","content":"..."}, "finish_reason":"stop"}],
        #   "usage": {"prompt_tokens":..., "completion_tokens":..., "total_tokens":...}
        # }
        try:
            choice0 = obj["choices"][0]
        except Exception as e:
            raise BackendRequestError(f"Unexpected response format (missing choices): {obj}") from e

        finish_reason = choice0.get("finish_reason")

        content: Optional[str] = None
        msg = choice0.get("message")
        if isinstance(msg, dict) and "content" in msg:
            content = msg.get("content")
        # Some servers may return "text" instead of message.content for completions-y variants.
        if content is None and "text" in choice0:
            content = choice0.get("text")

        if content is None:
            raise BackendRequestError(f"Unexpected response format (missing content): {obj}")

        usage = Usage()
        if self.config.return_usage:
            u = obj.get("usage") or {}
            usage = Usage(
                prompt_tokens=int(u.get("prompt_tokens", 0) or 0),
                completion_tokens=int(u.get("completion_tokens", 0) or 0),
                total_tokens=int(u.get("total_tokens", 0) or 0),
            )

        return ChatResult(
            content=str(content),
            model=str(obj.get("model") or self.config.model),
            usage=usage,
            raw=obj,
            finish_reason=str(finish_reason) if finish_reason is not None else None,
        )


def factory(config: BackendConfig) -> ServerBackend:
    return ServerBackend(config)