from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Sequence, TypedDict

Role = Literal["system", "user", "assistant", "tool"]

class Message(TypedDict, total = False):
    """
    Minimal chat message format.
    We keep it permissive so backends can pass through provider-specific keys if needed.
    """
    role: Role
    content: str

    # Optional fields for more structured chats/tools (future-proofing)
    name: str
    tool_call_id: str


@dataclass(frozen=True)
class Usage:
    """
    Token usage accounting.
    """
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

@dataclass(frozen=True)
class ChatResult:
    """
    Standard return value from Backend.chat().
    - content: assistant text output
    - model: provider model identifier used for this call
    - usage: token usage (optional)
    - raw: raw provider response for debugging (optional)
    - finish_reason: provider finish reason if available (optional)
    """
    content: str
    model: str
    usage: Usage = Usage()
    raw: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None

def ensure_messages(messages: Sequence[Message]) -> list[dict[str, Any]]:
    """
    Optional function to convert messages to plain dicts.
    """
    return [dict(m) for m in messages]