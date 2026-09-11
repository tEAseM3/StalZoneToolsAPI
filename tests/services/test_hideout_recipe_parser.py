from decimal import Decimal

import pytest

from app.services.hideout_recipe_parser import HideoutRecipeParseError, parse_hideout_recipes


def _translation(key: str, english: str) -> dict:
    return {"key": key, "lines": {"en": english, "ru": "Русский"}}


def _source() -> dict:
    return {
        "perks": [
            {
                "id": "cooking",
                "name": _translation("hideout.perks.cooking.name", "Cooking"),
                "desc": _translation("hideout.perks.cooking.desc", "Make food"),
            }
        ],
        "recipes": [
            {
                "bench": "kitchen_table",
                "category": _translation("hideout.category.food", "Food"),
                "subcategory": _translation("hideout.category.food.drinks", "Drinks"),
                "result": [{"item": "tea", "amount": 2}],
                "ingredients": [{"item": "water", "amount": 1}],
                "energy": 25.5,
                "requirements": {"perks": {"cooking": 2}, "features": ["kitchen_table"]},
            }
        ],
    }


def test_parse_hideout_recipes_returns_normalized_models():
    parsed = parse_hideout_recipes(_source())

    assert parsed.perks[0].name == "Cooking"
    recipe = parsed.recipes[0]
    assert recipe.source_index == 0
    assert recipe.category_name == "Food"
    assert recipe.required_perks == {"cooking": 2}
    assert recipe.required_features == ["kitchen_table"]
    assert recipe.energy == Decimal("25.5")
    components = [
        (component.component_type, component.item_id, component.amount)
        for component in recipe.components
    ]
    assert components == [
        ("result", "tea", Decimal("2")),
        ("ingredient", "water", Decimal("1")),
    ]


def test_parse_hideout_recipes_rejects_recipe_without_result():
    source = _source()
    source["recipes"][0]["result"] = []

    with pytest.raises(HideoutRecipeParseError, match="no results"):
        parse_hideout_recipes(source)


def test_parse_hideout_recipes_rejects_missing_english_category_name():
    source = _source()
    source["recipes"][0]["category"] = {"key": "hideout.category.food", "lines": {"ru": "Еда"}}

    with pytest.raises(HideoutRecipeParseError, match="English translation"):
        parse_hideout_recipes(source)
