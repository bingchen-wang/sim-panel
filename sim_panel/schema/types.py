from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union, TypedDict

from pydantic import RootModel

JSONScalar = Union[str, int, float, bool, None]

class JSONValue(RootModel[Union[JSONScalar, List["JSONValue"], Dict[str, "JSONValue"]]]):
    pass

JSONValue.model_rebuild()

JSONObject = Dict[str, JSONValue]

PolicyName = Literal["random", "manual", "self_selection"]
EventType = Literal["selection", "evaluation"]


class ColumnSpec(TypedDict):
    name: str
    dtype: str
    required: bool
    description: str
