from __future__ import annotations

from typing import Any, Mapping, Optional

from sim_panel.outcomes.base import OutcomeConfig, OutcomeModel
from sim_panel.outcomes.deterministic import DeterministicOutcomeModel
from sim_panel.outcomes.llm import LLMOutcomeModel
from sim_panel.outcomes.specs import QuestionnaireSpec


def build_outcome_model(cfg: OutcomeConfig) -> OutcomeModel:
    if cfg.name == "deterministic":
        return DeterministicOutcomeModel(cfg)
    if cfg.name == "llm":
        return LLMOutcomeModel(cfg)
    raise ValueError(f"Unknown outcome model name: {cfg.name}")


def outcome_config_from_yaml_dict(d: Mapping[str, Any]) -> OutcomeConfig:
    """
    Convenience helper: build OutcomeConfig from a YAML-parsed dict.

    Expected shape (suggested):
      outcomes_model:
        name: llm | deterministic
        temperature: 0.2
        max_tokens: 512
        include_raw_text: true
      questionnaire:
        outcomes:
          fields: ...
        traces:
          fields: ...
    """
    model_cfg = d.get("outcomes_model", {})
    if not isinstance(model_cfg, Mapping):
        raise ValueError("outcomes_model must be a mapping.")

    name = model_cfg.get("name", "llm")
    if not isinstance(name, str):
        raise ValueError("outcomes_model.name must be a string.")

    temperature = model_cfg.get("temperature", 0.2)
    if not isinstance(temperature, (int, float)):
        raise ValueError("outcomes_model.temperature must be numeric.")

    max_tokens = model_cfg.get("max_tokens", None)
    if max_tokens is not None and not isinstance(max_tokens, int):
        raise ValueError("outcomes_model.max_tokens must be int or null.")

    include_raw_text = model_cfg.get("include_raw_text", True)
    if not isinstance(include_raw_text, bool):
        raise ValueError("outcomes_model.include_raw_text must be bool.")

    custom_few_shot_example = model_cfg.get("custom_few_shot_example", None)
    if custom_few_shot_example is not None and not isinstance(custom_few_shot_example, Mapping):
        raise ValueError("outcomes_model.custom_few_shot_example must be a mapping if provided.")

    questionnaire_cfg = d.get("questionnaire", d)  # allow top-level questionnaire dict directly
    if not isinstance(questionnaire_cfg, Mapping):
        raise ValueError("questionnaire must be a mapping.")
    q = QuestionnaireSpec.from_config_dict(questionnaire_cfg)

    return OutcomeConfig(
        name=name,
        questionnaire=q,
        temperature=float(temperature),
        max_tokens=max_tokens,
        include_raw_text=include_raw_text,
        custom_few_shot_example=custom_few_shot_example,
    )