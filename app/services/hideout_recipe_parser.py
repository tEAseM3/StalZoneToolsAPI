from dataclasses import dataclass
from decimal import Decimal
from typing import Any


class HideoutRecipeParseError(ValueError):
    """Raised when the hideout recipe source cannot be stored in the local schema."""


@dataclass(frozen=True)
class ParsedHideoutPerk:
    id: str
    name: str
    description: str | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class ParsedHideoutRecipeItem:
    component_type: str
    item_id: str
    amount: Decimal
    sort_order: int


@dataclass(frozen=True)
class ParsedHideoutRecipe:
    source_index: int
    bench: str
    category_key: str
    category_name: str
    subcategory_key: str | None
    subcategory_name: str | None
    energy: Decimal
    required_perks: dict[str, int]
    required_features: list[str]
    raw: dict[str, Any]
    components: list[ParsedHideoutRecipeItem]


@dataclass(frozen=True)
class ParsedHideoutRecipes:
    perks: list[ParsedHideoutPerk]
    recipes: list[ParsedHideoutRecipe]


def parse_hideout_recipes(raw_json: dict[str, Any]) -> ParsedHideoutRecipes:
    perks = raw_json.get("perks")
    recipes = raw_json.get("recipes")
    if not isinstance(perks, list) or not isinstance(recipes, list):
        raise HideoutRecipeParseError("Hideout source must contain 'perks' and 'recipes' lists")

    parsed_perks = [_parse_perk(perk) for perk in perks]
    perk_ids = [perk.id for perk in parsed_perks]
    if len(perk_ids) != len(set(perk_ids)):
        raise HideoutRecipeParseError("Hideout source contains duplicate perk ids")

    return ParsedHideoutRecipes(
        perks=parsed_perks,
        recipes=[_parse_recipe(recipe, index) for index, recipe in enumerate(recipes)],
    )


def _parse_perk(raw_perk: object) -> ParsedHideoutPerk:
    if not isinstance(raw_perk, dict):
        raise HideoutRecipeParseError("Hideout perk must be an object")

    perk_id = _require_string(raw_perk, "id", "Hideout perk")
    name = _require_english_text(raw_perk.get("name"), f"Hideout perk '{perk_id}' name")
    return ParsedHideoutPerk(
        id=perk_id,
        name=name,
        description=_get_english_text(raw_perk.get("desc")),
        raw=raw_perk,
    )


def _parse_recipe(raw_recipe: object, source_index: int) -> ParsedHideoutRecipe:
    if not isinstance(raw_recipe, dict):
        raise HideoutRecipeParseError(f"Recipe at index {source_index} must be an object")

    category_key, category_name = _parse_translation(
        raw_recipe.get("category"), "category", source_index
    )
    subcategory = raw_recipe.get("subcategory")
    subcategory_key, subcategory_name = (
        _parse_translation(subcategory, "subcategory", source_index)
        if subcategory is not None
        else (None, None)
    )
    energy = _require_positive_or_zero_number(raw_recipe, "energy", source_index)
    requirements = raw_recipe.get("requirements", {})
    if not isinstance(requirements, dict):
        raise HideoutRecipeParseError(f"Recipe at index {source_index} has invalid requirements")

    components = _parse_components(raw_recipe, "result", "result", source_index)
    if not components:
        raise HideoutRecipeParseError(f"Recipe at index {source_index} has no results")
    components.extend(_parse_components(raw_recipe, "ingredients", "ingredient", source_index))

    return ParsedHideoutRecipe(
        source_index=source_index,
        bench=_require_string(raw_recipe, "bench", f"Recipe at index {source_index}"),
        category_key=category_key,
        category_name=category_name,
        subcategory_key=subcategory_key,
        subcategory_name=subcategory_name,
        energy=energy,
        required_perks=_parse_required_perks(requirements.get("perks"), source_index),
        required_features=_parse_required_features(requirements.get("features"), source_index),
        raw=raw_recipe,
        components=components,
    )


def _parse_translation(value: object, field: str, source_index: int) -> tuple[str, str]:
    if not isinstance(value, dict):
        raise HideoutRecipeParseError(f"Recipe at index {source_index} has invalid {field}")
    key = value.get("key")
    if not isinstance(key, str) or not key.strip():
        raise HideoutRecipeParseError(f"Recipe at index {source_index} has invalid {field} key")
    return key, _require_english_text(value, f"Recipe at index {source_index} {field}")


def _parse_components(
    raw_recipe: dict[str, Any], field: str, component_type: str, source_index: int
) -> list[ParsedHideoutRecipeItem]:
    raw_components = raw_recipe.get(field, [])
    if not isinstance(raw_components, list):
        raise HideoutRecipeParseError(f"Recipe at index {source_index} has invalid {field}")

    result: list[ParsedHideoutRecipeItem] = []
    for sort_order, component in enumerate(raw_components):
        if not isinstance(component, dict):
            raise HideoutRecipeParseError(
                f"Recipe at index {source_index} has invalid {field} entry"
            )
        item_id = _require_string(component, "item", f"Recipe at index {source_index} {field}")
        amount = _require_positive_number(component, "amount", source_index, field)
        result.append(
            ParsedHideoutRecipeItem(
                component_type=component_type,
                item_id=item_id,
                amount=amount,
                sort_order=sort_order,
            )
        )
    return result


def _parse_required_perks(value: object, source_index: int) -> dict[str, int]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise HideoutRecipeParseError(
            f"Recipe at index {source_index} has invalid perk requirements"
        )

    parsed: dict[str, int] = {}
    for perk_id, level in value.items():
        if (
            not isinstance(perk_id, str)
            or not perk_id.strip()
            or not isinstance(level, int)
            or level < 0
        ):
            raise HideoutRecipeParseError(
                f"Recipe at index {source_index} has invalid perk requirements"
            )
        parsed[perk_id] = level
    return parsed


def _parse_required_features(value: object, source_index: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(
        not isinstance(feature, str) or not feature.strip() for feature in value
    ):
        raise HideoutRecipeParseError(
            f"Recipe at index {source_index} has invalid feature requirements"
        )
    return value


def _get_english_text(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    lines = value.get("lines")
    if not isinstance(lines, dict):
        return None
    english = lines.get("en")
    return english if isinstance(english, str) else None


def _require_english_text(value: object, field: str) -> str:
    english = _get_english_text(value)
    if english is None or not english.strip():
        raise HideoutRecipeParseError(f"{field} does not have an English translation")
    return english


def _require_string(raw_json: dict[str, Any], field: str, context: str) -> str:
    value = raw_json.get(field)
    if not isinstance(value, str) or not value.strip():
        raise HideoutRecipeParseError(f"{context} has an invalid '{field}'")
    return value


def _require_positive_or_zero_number(
    raw_json: dict[str, Any], field: str, source_index: int
) -> Decimal:
    value = raw_json.get(field)
    if not _is_number(value) or value < 0:
        raise HideoutRecipeParseError(f"Recipe at index {source_index} has invalid {field}")
    return Decimal(str(value))


def _require_positive_number(
    raw_json: dict[str, Any], field: str, source_index: int, context: str
) -> Decimal:
    value = raw_json.get(field)
    if not _is_number(value) or value <= 0:
        raise HideoutRecipeParseError(
            f"Recipe at index {source_index} has invalid {context} {field}"
        )
    return Decimal(str(value))


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
