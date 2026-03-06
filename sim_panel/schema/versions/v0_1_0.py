from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator

from sim_panel.schema.types import JSONObject, PolicyName, ColumnSpec, EventType


SCHEMA_VERSION = "0.1.0"


class EventV0_1_0(BaseModel):
    """
    v0.1.0 supports two event types:

    1) selection (policy == "self_selection" only)
       - A choice set is presented at (panelist_id, t).
       - The panelist selects a subset (possibly empty).
       - This row records choice_set + selected_product_ids.

    2) evaluation (policy in {"random","manual","self_selection"})
       - A single (panelist_id, product_id, t) evaluation.
       - Records product_display plus flexible outcomes/traces.

    Note:
      - selection rows are only allowed when policy=="self_selection".
      - for self_selection evaluation rows, selection_id is required to link back.
    """

    model_config = ConfigDict(extra="forbid") #rejects unknown fields

    # version and identity
    schema_version: str = Field(default=SCHEMA_VERSION)
    event_id: str = Field(..., description="Deterministic unique id for the event row.")

    # event type and policy
    event_type: EventType = Field(..., description="Event type: selection|evaluation.")
    policy: PolicyName = Field(..., description="Policy: random|manual|self_selection.")

    # panel/time keys
    panelist_id: str
    product_id: str
    t: int = Field(..., ge=0, description="Period index (0-based).")


    # Linking: evaluation rows can reference the selection row at (panelist_id, t)
    selection_id: Optional[str] = Field(
        default=None,
        description="Deterministic id for the selection event (required for self_selection evaluation rows).",
    )

    # selection payload (selection rows only)
    choice_set: Optional[List[str]] = Field(
        default=None,
        description="Choice set (list of product_ids) presented to the panelist (selection rows).",
    )
    selected_product_ids: Optional[List[str]] = Field(
        default=None,
        description="Subset of choice_set selected by panelist (selection rows; may be empty).",
    )    

    # evaluation payload (evaluation rows only)
    product_id: Optional[str] = Field(
        default=None,
        description="Evaluated product_id (required for evaluation rows).",
    )
    product_display: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Panelist-facing display text (required for evaluation rows).",
    )

    # optional feature payloads (JSON; can be {})
    panelist_features: JSONObject = Field(default_factory=dict)
    product_features: JSONObject = Field(default_factory=dict)

    product_display: str = Field(
        ...,
        description="What the panelist sees. It may be enriched text (distinct from internal product_id).",
        min_length=1,
    )

    # flexible outcomes / traces (scalar or panel or nested)
    outcomes: Optional[JSONObject] = Field(
        default=None,
        description="Outcome(s) as JSON, e.g. {'rating': 4.2} or {'rating':4.2,'quality':3.8}.",
    )
    traces: Optional[JSONObject] = Field(
        default=None,
        description="Trace(s) as JSON, e.g. {'review_text':'...', 'rationale':'...'}",
    )

    @model_validator(mode="after")
    def _cross_field_rules(self) -> "EventV0_1_0":
        # selection stage only applies to self_selection policy
        if self.event_type == "selection" and self.policy != "self_selection":
            raise ValueError("event_type='selection' is only allowed when policy=='self_selection'.")

        if self.event_type == "selection":
            if self.choice_set is None:
                raise ValueError("selection event requires choice_set.")
            if self.selected_product_ids is None:
                raise ValueError("selection event requires selected_product_ids (can be empty list).")

            # selection rows must NOT include evaluation-only fields
            if any(
                x is not None
                for x in (self.product_id, self.product_display, self.outcomes, self.traces)
            ):
                raise ValueError("selection event must not include product_id/product_display/outcomes/traces.")

            # sanity: selected subset must be contained in choice_set
            choice = set(self.choice_set)
            for pid in self.selected_product_ids:
                if pid not in choice:
                    raise ValueError(f"selected_product_ids contains {pid!r} not in choice_set.")

            # selection_id is allowed but not required on selection rows
            return self

        # evaluation row
        if self.event_type == "evaluation":
            if self.product_id is None:
                raise ValueError("evaluation event requires product_id.")
            if self.product_display is None:
                raise ValueError("evaluation event requires product_display.")

            # evaluation rows must NOT include selection-only payloads
            if self.choice_set is not None or self.selected_product_ids is not None:
                raise ValueError("evaluation event must not include choice_set/selected_product_ids.")

            # Option A: self_selection evaluation rows must link back to selection
            if self.policy == "self_selection" and self.selection_id is None:
                raise ValueError("self_selection evaluation requires selection_id.")

            return self

        # unreachable (event_type is Literal)
        return self

COLUMNS: List[ColumnSpec] = [
    {"name": "schema_version", "dtype": "string", "required": True, "description": "Schema version."},
    {"name": "event_id", "dtype": "string", "required": True, "description": "Deterministic unique event id."},
    {"name": "event_type", "dtype": "string", "required": True, "description": "Event type: selection|evaluation."},
    {"name": "policy", "dtype": "string", "required": True, "description": "Policy: random|manual|self_selection."},
    {"name": "panelist_id", "dtype": "string", "required": True, "description": "Panelist identifier."},
    {"name": "t", "dtype": "int", "required": True, "description": "Period index (0-based)."},
    {"name": "selection_id", "dtype": "string", "required": False, "description": "Links evaluation rows to selection row."},
    {"name": "choice_set", "dtype": "json", "required": False, "description": "Presented choice set (selection rows only)."},
    {"name": "selected_product_ids", "dtype": "json", "required": False, "description": "Selected subset (selection rows only)."},
    {"name": "product_id", "dtype": "string", "required": False, "description": "Evaluated product id (evaluation rows only)."},
    {"name": "product_display", "dtype": "string", "required": False, "description": "Displayed product text (evaluation rows only)."},
    {"name": "panelist_features", "dtype": "json", "required": True, "description": "Panelist features JSON (may be {})."},
    {"name": "product_features", "dtype": "json", "required": True, "description": "Product features JSON (may be {})."},
    {"name": "outcomes", "dtype": "json", "required": False, "description": "Outcome(s) JSON (evaluation rows only)."},
    {"name": "traces", "dtype": "json", "required": False, "description": "Trace(s) JSON (evaluation rows only)."},
]