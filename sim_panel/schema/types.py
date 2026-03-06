from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

JSONScalar = Union[str, int, float, bool, None]
JSONValue = Union[JSONScalar, List["JSONValue"], Dict[str, "JSONValue"]]
JSONObject = Dict[str, JSONValue]

PolicyName = Literal["random", "manual", "self_selection"]
EventType = Literal["selection", "evaluation"]


class ColumnSpec(TypedDict):
    name: str
    dtype: str
    required: bool
    description: str
