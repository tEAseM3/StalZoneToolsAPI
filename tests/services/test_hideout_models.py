from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.hideout_perk import HideoutPerk
from app.models.hideout_recipe import HideoutRecipe
from app.models.hideout_recipe_item import HideoutRecipeItem


async def test_hideout_models_persist_recipe_and_components(db_session):
    perk = HideoutPerk(
        id="cooking",
        name="Cooking",
        description="Make food",
        raw={"id": "cooking"},
    )
    recipe = HideoutRecipe(
        source_index=0,
        bench="kitchen_table",
        category_key="hideout.categories.food",
        category_name="Food",
        subcategory_key=None,
        subcategory_name=None,
        energy=100,
        required_perks={"cooking": 1},
        required_features=["kitchen_table"],
        raw={"bench": "kitchen_table"},
        source_sha="abc123",
    )
    recipe.components = [
        HideoutRecipeItem(
            component_type="result",
            item_id="tea",
            amount=1,
            sort_order=0,
        ),
        HideoutRecipeItem(
            component_type="ingredient",
            item_id="water",
            amount=2,
            sort_order=0,
        ),
    ]
    db_session.add_all([perk, recipe])
    await db_session.commit()

    stored = await db_session.scalar(
        select(HideoutRecipe)
        .options(selectinload(HideoutRecipe.components))
        .where(HideoutRecipe.source_index == 0)
    )
    assert stored is not None
    assert stored.category_name == "Food"
    assert stored.required_perks == {"cooking": 1}
    assert len(stored.components) == 2
