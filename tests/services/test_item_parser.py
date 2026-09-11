from decimal import Decimal

import pytest

from app.services.item_parser import ItemParseError, parse_item


def _translation(key: str, english: str) -> dict:
    return {"key": key, "lines": {"en": english, "ru": "Русский"}}


def test_parse_item_extracts_numeric_attribute_and_direct_english_unit():
    parsed = parse_item(
        {
            "id": "tea",
            "category": "consumables",
            "name": _translation("items.tea.name", "Tea"),
            "infoBlocks": [
                {
                    "type": "list",
                    "elements": [
                        {
                            "type": "numeric",
                            "name": _translation("items.tea.weight", "Weight"),
                            "value": 1.5,
                            "formatted": {"value": {"en": "kg", "ru": "кг"}},
                        }
                    ],
                }
            ],
        }
    )

    assert parsed.name == "Tea"
    assert parsed.attributes[0].key == "items.tea.weight"
    assert parsed.attributes[0].value_numeric == Decimal("1.5")
    assert parsed.attributes[0].unit_label == "kg"


def test_parse_item_rejects_missing_english_name():
    with pytest.raises(ItemParseError, match="does not have an English name"):
        parse_item({"id": "tea", "category": "consumables", "name": {"lines": {"ru": "Чай"}}})
