from dataclasses import dataclass
from decimal import Decimal
from typing import Any


class ItemParseError(ValueError):
    """Raised when a source item cannot be stored in the local schema."""


@dataclass(frozen=True)
class ParsedItemAttribute:
    key: str
    label: str | None
    value_text: str | None
    value_numeric: Decimal | None
    unit_label: str | None
    sort_order: int


@dataclass(frozen=True)
class ParsedItem:
    id: str
    category: str
    name: str
    description: str | None
    color: str | None
    status_state: str | None
    raw: dict[str, Any]
    attributes: list[ParsedItemAttribute]


def parse_item(raw_json: dict[str, Any]) -> ParsedItem:
    item_id = _require_nonempty_string(raw_json, "id")
    category = _require_nonempty_string(raw_json, "category")
    name = _get_english_text(raw_json.get("name"))
    if name is None or not name.strip():
        raise ItemParseError(f"Item '{item_id}' does not have an English name")

    description: str | None = None
    attributes: list[ParsedItemAttribute] = []

    for block in raw_json.get("infoBlocks", []):
        if not isinstance(block, dict):
            continue

        if block.get("type") == "list":
            for element in block.get("elements", []):
                attribute = _parse_list_element(element, len(attributes))
                if attribute is not None:
                    attributes.append(attribute)
        elif block.get("type") == "text":
            text_key = _get_translation_key(block.get("text"))
            if _is_description_block(block, text_key):
                description = _get_english_text(block.get("text"))
                continue

            attribute = _parse_text_block(block, text_key, len(attributes))
            if attribute is not None:
                attributes.append(attribute)

    status = raw_json.get("status")
    return ParsedItem(
        id=item_id,
        category=category,
        name=name,
        description=description,
        color=_get_optional_string(raw_json.get("color")),
        status_state=_get_optional_string(status.get("state"))
        if isinstance(status, dict)
        else None,
        raw=raw_json,
        attributes=attributes,
    )


def _parse_list_element(element: object, sort_order: int) -> ParsedItemAttribute | None:
    if not isinstance(element, dict):
        return None

    if element.get("type") == "key-value":
        key = _get_translation_key(element.get("key"))
        value_text = _get_english_text(element.get("value"))
        if key is None or value_text is None:
            return None

        return ParsedItemAttribute(
            key=key,
            label=_get_english_text(element.get("key")),
            value_text=value_text,
            value_numeric=None,
            unit_label=None,
            sort_order=sort_order,
        )

    if element.get("type") == "numeric":
        key = _get_translation_key(element.get("name"))
        value = element.get("value")
        if key is None or not _is_number(value):
            return None

        formatted = element.get("formatted")
        formatted_value = formatted.get("value") if isinstance(formatted, dict) else None
        return ParsedItemAttribute(
            key=key,
            label=_get_english_text(element.get("name")),
            value_text=None,
            value_numeric=Decimal(str(value)),
            unit_label=_get_english_line(formatted_value),
            sort_order=sort_order,
        )

    return None


def _parse_text_block(
    block: dict[str, Any], text_key: str | None, sort_order: int
) -> ParsedItemAttribute | None:
    value_text = _get_english_text(block.get("text"))
    if text_key is None or value_text is None:
        return None

    return ParsedItemAttribute(
        key=text_key,
        label=_get_english_text(block.get("title")),
        value_text=value_text,
        value_numeric=None,
        unit_label=None,
        sort_order=sort_order,
    )


def _is_description_block(block: dict[str, Any], text_key: str | None) -> bool:
    title = block.get("title")
    return (
        isinstance(title, dict)
        and title.get("text") == ""
        and text_key is not None
        and text_key.endswith(".description")
    )


def _get_english_text(value: object) -> str | None:
    if not isinstance(value, dict):
        return None

    lines = value.get("lines")
    if not isinstance(lines, dict):
        return None

    english_text = lines.get("en")
    return english_text if isinstance(english_text, str) else None


def _get_english_line(value: object) -> str | None:
    if not isinstance(value, dict):
        return None

    english_text = value.get("en")
    return english_text if isinstance(english_text, str) else None


def _get_translation_key(value: object) -> str | None:
    if not isinstance(value, dict):
        return None

    key = value.get("key")
    return key if isinstance(key, str) and key.strip() else None


def _get_optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _require_nonempty_string(raw_json: dict[str, Any], field_name: str) -> str:
    value = raw_json.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ItemParseError(f"Item has an invalid '{field_name}'")
    return value
