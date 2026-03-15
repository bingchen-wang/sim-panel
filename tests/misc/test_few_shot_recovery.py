from sim_panel.decisions.selection import render_selection_prompt
from sim_panel.decisions.types import SelectionConfig, SelectionContext


def test_render_selection_prompt_uses_custom_few_shot_example_and_resolves_placeholders() -> None:
    ctx = SelectionContext(
        panelist_id="p1",
        t=0,
        products_shown=[
            {"product_id": "prodA", "product_display": "Beer A"},
            {"product_id": "prodB", "product_display": "Beer B"},
            {"product_id": "prodC", "product_display": "Beer C"},
        ],
    )
    cfg = SelectionConfig(
        custom_few_shot_example={
            "intro": "Given products about craft beverages, a respondent might select:",
            "response": {
                "selected_product_ids": [
                    "__FIRST_SHOWN__",
                    "__SECOND_SHOWN_IF_AVAILABLE__",
                    "__THIRD_SHOWN_IF_AVAILABLE__",
                ],
                "traces": {"reasoning": "Selected based on personal taste preferences."},
            },
        }
    )

    prompt = render_selection_prompt(ctx=ctx, cfg=cfg, prompting_strategy="few_shot")

    assert "## Example Selection" in prompt
    assert "Given products about craft beverages, a respondent might select:" in prompt
    assert '"selected_product_ids": [' in prompt
    assert '"prodA"' in prompt
    assert '"prodB"' in prompt
    assert '"prodC"' in prompt
    assert "__FIRST_SHOWN__" not in prompt
    assert "__SECOND_SHOWN_IF_AVAILABLE__" not in prompt
    assert "__THIRD_SHOWN_IF_AVAILABLE__" not in prompt


def test_render_selection_prompt_drops_unavailable_optional_placeholders() -> None:
    ctx = SelectionContext(
        panelist_id="p1",
        t=0,
        products_shown=[
            {"product_id": "prodA", "product_display": "Beer A"},
        ],
    )
    cfg = SelectionConfig(
        custom_few_shot_example={
            "intro": "Example selection:",
            "response": {
                "selected_product_ids": [
                    "__FIRST_SHOWN__",
                    "__SECOND_SHOWN_IF_AVAILABLE__",
                    "__THIRD_SHOWN_IF_AVAILABLE__",
                ],
                "traces": {"reasoning": "Example reasoning."},
            },
        }
    )

    prompt = render_selection_prompt(ctx=ctx, cfg=cfg, prompting_strategy="few_shot")

    assert '"prodA"' in prompt
    assert "__SECOND_SHOWN_IF_AVAILABLE__" not in prompt
    assert "__THIRD_SHOWN_IF_AVAILABLE__" not in prompt


def test_render_selection_prompt_filters_literal_ids_not_in_choice_set() -> None:
    ctx = SelectionContext(
        panelist_id="p1",
        t=0,
        products_shown=[
            {"product_id": "prodA", "product_display": "Beer A"},
            {"product_id": "prodB", "product_display": "Beer B"},
        ],
    )
    cfg = SelectionConfig(
        custom_few_shot_example={
            "intro": "Example selection:",
            "response": {
                "selected_product_ids": ["prodA", "prodX"],
                "traces": {"reasoning": "Example reasoning."},
            },
        }
    )

    prompt = render_selection_prompt(ctx=ctx, cfg=cfg, prompting_strategy="few_shot")

    assert '"prodA"' in prompt
    assert '"prodX"' not in prompt

from sim_panel.outcomes.registry import outcome_config_from_yaml_dict


def test_outcome_config_from_yaml_parses_custom_few_shot_example() -> None:
    d = {
        "outcomes_model": {
            "name": "llm",
            "temperature": 0.2,
            "max_tokens": 900,
            "include_raw_text": True,
            "custom_few_shot_example": {
                "intro": "For a product like 'Classic Lager - A traditional pale lager with crisp finish', a respondent might answer:",
                "response": {
                    "outcomes": {
                        "rating": 7,
                        "purchase_intent": "maybe",
                    },
                    "traces": {
                        "rationale": "Solid traditional beer, nothing exceptional but reliable."
                    },
                },
            },
        },
        "questionnaire": {
            "outcomes": {
                "fields": {
                    "rating": {
                        "type": "int",
                        "choices": [1, 2, 3, 4, 5],
                        "question": "Overall, how much do you like this beer?",
                        "instruction": "Pick one integer.",
                        "required": True,
                    },
                    "purchase_intent": {
                        "type": "categorical",
                        "choices": ["no", "maybe", "yes"],
                        "question": "How likely are you to purchase this beer in the next 30 days?",
                        "instruction": "Choose one option.",
                        "required": True,
                    },
                }
            },
            "traces": {
                "fields": {
                    "rationale": {
                        "type": "text",
                        "question": "Briefly explain your answers.",
                        "required": False,
                    }
                }
            },
        },
    }

    cfg = outcome_config_from_yaml_dict(d)

    assert cfg.name == "llm"
    assert cfg.custom_few_shot_example is not None
    assert cfg.custom_few_shot_example["intro"].startswith("For a product like")
    assert cfg.custom_few_shot_example["response"]["outcomes"]["rating"] == 7
    assert cfg.custom_few_shot_example["response"]["outcomes"]["purchase_intent"] == "maybe"

from sim_panel.outcomes.base import EvaluationContext, OutcomeConfig
from sim_panel.outcomes.render import render_evaluation_prompt
from sim_panel.outcomes.specs import QuestionnaireSpec


def test_render_evaluation_prompt_uses_custom_few_shot_example() -> None:
    questionnaire = QuestionnaireSpec.from_config_dict(
        {
            "outcomes": {
                "fields": {
                    "rating": {
                        "type": "int",
                        "choices": [1, 2, 3, 4, 5],
                        "question": "Overall, how much do you like this beer?",
                        "required": True,
                    }
                }
            },
            "traces": {
                "fields": {
                    "rationale": {
                        "type": "text",
                        "question": "Briefly explain your answers.",
                        "required": False,
                    }
                }
            },
        }
    )
    outcome_cfg = OutcomeConfig(
        name="llm",
        questionnaire=questionnaire,
        custom_few_shot_example={
            "intro": "For a product like 'Classic Lager - A traditional pale lager with crisp finish', a respondent might answer:",
            "response": {
                "outcomes": {"rating": 7},
                "traces": {"rationale": "Solid traditional beer, nothing exceptional but reliable."},
            },
        },
    )
    ctx = EvaluationContext(
        panelist_id="p1",
        product_id="prodA",
        t=0,
        product_display="Beer A",
    )

    prompt = render_evaluation_prompt(
        ctx=ctx,
        questionnaire=questionnaire,
        outcome_cfg=outcome_cfg,
        include_features=True,
        prompting_strategy="few_shot",
    )

    assert "## Example Evaluation" in prompt
    assert "Classic Lager" in prompt
    assert '"rating": 7' in prompt
    assert "Solid traditional beer" in prompt