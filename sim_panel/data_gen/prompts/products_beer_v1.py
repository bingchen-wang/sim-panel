from __future__ import annotations

from typing import Dict


def render_beer_products_prompt(*, n: int, nonce: str | None = None) -> Dict[str, str]:
    """
    Generate beer product specs (attributes + display_name).
    Output must be JSON only: {"products": [ ... ]}.
    """
    system = (
        "You generate synthetic beer product specs for simulation.\n"
        "Output MUST be valid JSON only. No prose.\n"
        "Do not mention internal IDs.\n"
        "Each product must be plausible and internally consistent.\n"
    )
    if nonce:
                user = (
            f"Generate {n} distinct beer products (batch token: {nonce}).\n\n"
            "Return JSON with this exact schema:\n"
            "{\n"
            '  "products": [\n'
            "    {\n"
            '      "display_name": "short human-facing name",\n'
            '      "attributes": {\n'
            '        "style": "IPA|Stout|Pilsner|Lager|Sour|Wheat|Porter|Saison",\n'
            '        "abv": 2.5-14.0,\n'
            '        "ibu": 0-120,\n'
            '        "color_srm": 1-40,\n'
            '        "price_usd_6pack": 6-24,\n'
            '        "ingredients": {\n'
            '          "citrus_hops": true/false,\n'
            '          "roasted_malt": true/false,\n'
            '          "lactose": true/false,\n'
            '          "fruit_added": true/false,\n'
            '          "barrel_aged": true/false\n'
            "        },\n"
            '        "flavor_profile": {\n'
            '          "bitterness": 0-1,\n'
            '          "sweetness": 0-1,\n'
            '          "body": 0-1,\n'
            '          "acidity": 0-1,\n'
            '          "aroma_intensity": 0-1\n'
            "        }\n"
            "      }\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Numeric ranges must be respected.\n"
            "- flavor_profile values must be floats in [0, 1].\n"
            "- Make products diverse by style and profile.\n"
            "- display_name should not include ABV/IBU numbers explicitly.\n"
        )
    else:
        user = (
            f"Generate {n} distinct beer products.\n\n"
            "Return JSON with this exact schema:\n"
            "{\n"
            '  "products": [\n'
            "    {\n"
            '      "display_name": "short human-facing name",\n'
            '      "attributes": {\n'
            '        "style": "IPA|Stout|Pilsner|Lager|Sour|Wheat|Porter|Saison",\n'
            '        "abv": 2.5-14.0,\n'
            '        "ibu": 0-120,\n'
            '        "color_srm": 1-40,\n'
            '        "price_usd_6pack": 6-24,\n'
            '        "ingredients": {\n'
            '          "citrus_hops": true/false,\n'
            '          "roasted_malt": true/false,\n'
            '          "lactose": true/false,\n'
            '          "fruit_added": true/false,\n'
            '          "barrel_aged": true/false\n'
            "        },\n"
            '        "flavor_profile": {\n'
            '          "bitterness": 0-1,\n'
            '          "sweetness": 0-1,\n'
            '          "body": 0-1,\n'
            '          "acidity": 0-1,\n'
            '          "aroma_intensity": 0-1\n'
            "        }\n"
            "      }\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Numeric ranges must be respected.\n"
            "- flavor_profile values must be floats in [0, 1].\n"
            "- Make products diverse by style and profile.\n"
            "- display_name should not include ABV/IBU numbers explicitly.\n"
        )
    return {"system": system, "user": user}