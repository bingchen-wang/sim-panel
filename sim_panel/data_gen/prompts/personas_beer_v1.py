from __future__ import annotations

from typing import Any, Dict


def render_personas_prompt(*, n: int, nonce: str | None = None) -> Dict[str, str]:
    """
    Generate persona attribute specs (NO persona_text).
    Output must be JSON only: {"personas": [ ... ]}.
    """
    system = (
        "You generate synthetic consumer persona attribute specs for simulation.\n"
        "Output MUST be valid JSON only. No prose.\n"
        "Do not include persona_text.\n"
        "Each persona must be internally consistent and realistic.\n"
    )
    if nonce:
        user = (
            f"Generate {n} distinct personas (batch token: {nonce}).\n\n"
            "Return JSON with this exact schema:\n"
            "{\n"
            '  "personas": [\n'
            "    {\n"
            '      "attributes": {\n'
            '        "age_group": "21-29|30-39|40-49|50-64|65+",\n'
            '        "gender": "female|male|nonbinary|prefer_not_say",\n'
            '        "region": "Northeast|Midwest|South|West",\n'
            '        "income_bracket": "<30k|30-60k|60-100k|100-150k|150k+",\n'
            '        "beer_style_affinity": {\n'
            '          "ipa": 0-1,\n'
            '          "stout": 0-1,\n'
            '          "lager": 0-1,\n'
            '          "sour": 0-1,\n'
            '          "wheat": 0-1\n'
            "        },\n"
            '        "bitterness_tolerance": 0-1,\n'
            '        "sweetness_preference": 0-1,\n'
            '        "abv_preference": 0-1,\n'
            '        "adventurousness": 0-1,\n'
            '        "price_sensitivity": 0-1\n'
            "      }\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- All numeric values must be floats in [0, 1].\n"
            "- Make personas diverse (age, region, preferences).\n"
            "- Avoid identical attribute vectors.\n"
        )
    else:
        user = (
            f"Generate {n} distinct personas.\n\n"
            "Return JSON with this exact schema:\n"
            "{\n"
            '  "personas": [\n'
            "    {\n"
            '      "attributes": {\n'
            '        "age_group": "21-29|30-39|40-49|50-64|65+",\n'
            '        "gender": "female|male|nonbinary|prefer_not_say",\n'
            '        "region": "Northeast|Midwest|South|West",\n'
            '        "income_bracket": "<30k|30-60k|60-100k|100-150k|150k+",\n'
            '        "beer_style_affinity": {\n'
            '          "ipa": 0-1,\n'
            '          "stout": 0-1,\n'
            '          "lager": 0-1,\n'
            '          "sour": 0-1,\n'
            '          "wheat": 0-1\n'
            "        },\n"
            '        "bitterness_tolerance": 0-1,\n'
            '        "sweetness_preference": 0-1,\n'
            '        "abv_preference": 0-1,\n'
            '        "adventurousness": 0-1,\n'
            '        "price_sensitivity": 0-1\n'
            "      }\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- All numeric values must be floats in [0, 1].\n"
            "- Make personas diverse (age, region, preferences).\n"
            "- Avoid identical attribute vectors.\n"
        )
    return {"system": system, "user": user}