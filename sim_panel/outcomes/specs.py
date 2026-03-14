from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Mapping, Optional, Tuple


FieldType = Literal["int", "float", "categorical", "bool", "text", "json"]
AnalysisType = Literal["continuous", "binary", "nominal", "ordinal"]

@dataclass(frozen=True)
class FieldSpec:
    """
    A single questionnaire field. Used for both outcomes and traces.

    name:
      The JSON key that must appear in the model output under outcomes/traces.

    type:
      Controls prompt rendering and validation.

    question:
      The user-facing question / instruction to the panelist.

    instruction:
      Optional additional formatting guidance.

    choices:
      Optional list of allowed values (strongly recommended for categorical / int with discrete choices).

    required:
      If False, missing key is allowed. If True, missing is a validation error.

    analysis_type:
      Optional analysis-facing semantic type. This does not affect prompt rendering
      or payload validation used by existing outcome modules. It is intended for
      downstream analysis modules such as regression.

      Allowed values:
      - "continuous"
      - "binary"
      - "nominal"
      - "ordinal"

    choice_order:
      Optional explicit ordering for ordinal outcomes. If omitted, downstream
      analysis may fall back to `choices` if appropriate.      

    min_value/max_value:
      Optional numeric constraints for int/float.
    """
    name: str
    type: FieldType
    question: str
    instruction: Optional[str] = None
    choices: Optional[List[Any]] = None
    required: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    analysis_type: Optional[AnalysisType] = None
    choice_order: Optional[Tuple[Any]] = None

    def validate_value(self, v: Any) -> Optional[str]:
        if v is None:
            return None if not self.required else f"Field '{self.name}' is required but null."
        t = self.type

        if t == "int":
            if not isinstance(v, int):
                return f"Field '{self.name}' expects int, got {type(v).__name__}."
            if self.min_value is not None and v < int(self.min_value):
                return f"Field '{self.name}' must be >= {int(self.min_value)}, got {v}."
            if self.max_value is not None and v > int(self.max_value):
                return f"Field '{self.name}' must be <= {int(self.max_value)}, got {v}."
        elif t == "float":
            if not isinstance(v, (int, float)):
                return f"Field '{self.name}' expects float, got {type(v).__name__}."
            fv = float(v)
            if self.min_value is not None and fv < float(self.min_value):
                return f"Field '{self.name}' must be >= {float(self.min_value)}, got {fv}."
            if self.max_value is not None and fv > float(self.max_value):
                return f"Field '{self.name}' must be <= {float(self.max_value)}, got {fv}."
        elif t == "bool":
            if not isinstance(v, bool):
                return f"Field '{self.name}' expects bool, got {type(v).__name__}."
        elif t == "categorical":
            if self.choices is None or len(self.choices) == 0:
                return f"Field '{self.name}' is categorical but has no choices."
        elif t == "text":
            if not isinstance(v, str):
                return f"Field '{self.name}' expects text (string), got {type(v).__name__}."
        elif t == "json":
            # Any JSON-serializable object is acceptable; we don't deeply validate here.
            if isinstance(v, (str, int, float, bool)) or v is None:
                # still valid JSON, but likely not intended; allow it.
                return None
            if not isinstance(v, (dict, list)):
                return f"Field '{self.name}' expects json (dict/list), got {type(v).__name__}."
        else:
            return f"Unknown field type '{t}' for field '{self.name}'."

        if self.choices is not None:
            if v not in self.choices:
                return f"Field '{self.name}' must be one of {self.choices}, got {v!r}."
        return None


@dataclass(frozen=True)
class QuestionnaireSpec:
    """
    A questionnaire defines what the panelist must fill out after evaluation.

    - outcome_fields define the `event["outcomes"]` object.
    - trace_fields define the `event["traces"]` object (optional / free-form-ish).

    The model output is expected to be JSON:
      {"outcomes": {...}, "traces": {...}}
    """
    outcome_fields: Tuple[FieldSpec, ...]
    trace_fields: Tuple[FieldSpec, ...] = ()

    def outcome_names(self) -> List[str]:
        return [f.name for f in self.outcome_fields]

    def trace_names(self) -> List[str]:
        return [f.name for f in self.trace_fields]

    def validate_payload(self, payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], List[str]]:
        """
        Validate a parsed JSON payload against the questionnaire spec.
        Returns (outcomes, traces, errors).
        """
        errors: List[str] = []
        outcomes_obj = payload.get("outcomes")
        traces_obj = payload.get("traces")

        if outcomes_obj is None:
            errors.append("Missing top-level key 'outcomes'.")
            outcomes_obj = {}
        if not isinstance(outcomes_obj, dict):
            errors.append(f"Top-level 'outcomes' must be an object/dict, got {type(outcomes_obj).__name__}.")
            outcomes_obj = {}

        if traces_obj is None:
            traces_obj = {}
        if not isinstance(traces_obj, dict):
            errors.append(f"Top-level 'traces' must be an object/dict, got {type(traces_obj).__name__}.")
            traces_obj = {}

        outcomes: Dict[str, Any] = {}
        traces: Dict[str, Any] = {}

        # Validate outcomes
        for fs in self.outcome_fields:
            if fs.name not in outcomes_obj:
                if fs.required:
                    errors.append(f"Missing required outcome field '{fs.name}'.")
                continue
            v = outcomes_obj.get(fs.name)
            msg = fs.validate_value(v)
            if msg:
                errors.append(msg)
            else:
                outcomes[fs.name] = v

        # Validate traces
        for fs in self.trace_fields:
            if fs.name not in traces_obj:
                if fs.required:
                    errors.append(f"Missing required trace field '{fs.name}'.")
                continue
            v = traces_obj.get(fs.name)
            msg = fs.validate_value(v)
            if msg:
                errors.append(msg)
            else:
                traces[fs.name] = v

        # Extra keys are allowed, but we surface them as warnings inside errors (prefixed).
        extra_outcomes = set(outcomes_obj.keys()) - set(self.outcome_names())
        extra_traces = set(traces_obj.keys()) - set(self.trace_names())
        if extra_outcomes:
            errors.append(f"[warn] Extra outcome keys not in spec: {sorted(extra_outcomes)}")
        if extra_traces:
            errors.append(f"[warn] Extra trace keys not in spec: {sorted(extra_traces)}")

        # If there are hard errors (non-warn), treat as invalid
        hard_errors = [e for e in errors if not e.startswith("[warn]")]
        if hard_errors:
            return None, None, errors

        # If no trace fields specified, traces can be None downstream if desired.
        return outcomes, (traces if self.trace_fields else {}), errors

    @staticmethod
    def from_config_dict(cfg: Mapping[str, Any]) -> "QuestionnaireSpec":
        """
        Build QuestionnaireSpec from a YAML-parsed dict.

        Expected shape:
          outcomes:
            fields:
              <name>:
                type: ...
                question: ...
                instruction: ...
                choices: [...]
                required: true/false
                min: ...
                max: ...
          traces:
            fields:
              <name>: ...
        """
        outcomes_cfg = cfg.get("outcomes", {}) if isinstance(cfg, Mapping) else {}
        traces_cfg = cfg.get("traces", {}) if isinstance(cfg, Mapping) else {}

        out_fields = _parse_fields(outcomes_cfg.get("fields", {}), section="outcomes")
        tr_fields = _parse_fields(traces_cfg.get("fields", {}), section="traces")

        if len(out_fields) == 0:
            raise ValueError("QuestionnaireSpec requires at least one outcomes.fields entry.")
        return QuestionnaireSpec(outcome_fields=tuple(out_fields), trace_fields=tuple(tr_fields))


def _parse_fields(fields_cfg: Any, section: str) -> List[FieldSpec]:
    if fields_cfg is None:
        return []
    if not isinstance(fields_cfg, Mapping):
        raise ValueError(f"{section}.fields must be a mapping, got {type(fields_cfg).__name__}.")

    out: List[FieldSpec] = []
    for name, raw in fields_cfg.items():
        if not isinstance(name, str) or not name:
            raise ValueError(f"{section}.fields has invalid field name: {name!r}")

        if not isinstance(raw, Mapping):
            raise ValueError(f"{section}.fields['{name}'] must be a mapping, got {type(raw).__name__}.")

        ftype = raw.get("type")
        question = raw.get("question")
        if not isinstance(ftype, str) or not ftype:
            raise ValueError(f"{section}.fields['{name}'] missing/invalid 'type'.")
        if not isinstance(question, str) or not question:
            raise ValueError(f"{section}.fields['{name}'] missing/invalid 'question'.")

        instruction = raw.get("instruction")
        if instruction is not None and not isinstance(instruction, str):
            raise ValueError(f"{section}.fields['{name}'].instruction must be string if provided.")

        choices = raw.get("choices")
        if choices is not None and not isinstance(choices, list):
            raise ValueError(f"{section}.fields['{name}'].choices must be a list if provided.")

        required = raw.get("required", True)
        if not isinstance(required, bool):
            raise ValueError(f"{section}.fields['{name}'].required must be bool if provided.")

        minv = raw.get("min")
        maxv = raw.get("max")
        if minv is not None and not isinstance(minv, (int, float)):
            raise ValueError(f"{section}.fields['{name}'].min must be numeric if provided.")
        if maxv is not None and not isinstance(maxv, (int, float)):
            raise ValueError(f"{section}.fields['{name}'].max must be numeric if provided.")

        analysis_type = raw.get("analysis_type")
        if analysis_type is not None:
            if analysis_type not in {"continuous", "binary", "nominal", "ordinal"}:
                raise ValueError(
                    f"{section}.fields['{name}'].analysis_type must be one of "
                    "['continuous', 'binary', 'nominal', 'ordinal'] if provided."
                )

        choice_order = raw.get("choice_order")
        if choice_order is not None and not isinstance(choice_order, list):
            raise ValueError(
                f"{section}.fields['{name}'].choice_order must be a list if provided."
            )

        choice_order_tuple = tuple(choice_order) if choice_order is not None else None


        fs = FieldSpec(
            name=name,
            type=ftype,  # type: ignore[assignment]
            question=question,
            instruction=instruction,
            choices=choices,
            required=required,
            min_value=float(minv) if minv is not None else None,
            max_value=float(maxv) if maxv is not None else None,
            analysis_type=analysis_type,
            choice_order=choice_order_tuple,
        )

        # A few sanity checks
        if fs.type == "categorical" and (fs.choices is None or len(fs.choices) == 0):
            raise ValueError(f"{section}.fields['{name}'] categorical requires non-empty choices.")

        if fs.analysis_type == "binary" and fs.choices is not None and len(fs.choices) != 2:
            raise ValueError(
                f"{section}.fields['{name}'] analysis_type='binary' requires exactly 2 choices "
                f"when choices are provided, got {len(fs.choices)}."
            )

        if fs.choice_order is not None and fs.analysis_type != "ordinal":
            raise ValueError(
                f"{section}.fields['{name}'].choice_order is only valid when "
                "analysis_type='ordinal'."
            )

        if fs.analysis_type == "ordinal":
            if fs.choice_order is None and fs.choices is None:
                raise ValueError(
                    f"{section}.fields['{name}'] analysis_type='ordinal' requires "
                    "either choice_order or choices."
                )
            if fs.choice_order is not None and fs.choices is not None:
                if set(fs.choice_order) != set(fs.choices):
                    raise ValueError(
                        f"{section}.fields['{name}'].choice_order must contain the same "
                        "elements as choices."
                    )


        out.append(fs)

    return out