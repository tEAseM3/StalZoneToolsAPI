from datetime import UTC, datetime
from decimal import Decimal

from app.core.security import create_access_token
from app.models.auction_current_price import AuctionCurrentPrice
from app.models.craft_profit_snapshot import CraftProfitSnapshot
from app.models.hideout_recipe import HideoutRecipe
from app.models.hideout_recipe_item import HideoutRecipeItem
from app.models.item import Item
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole


async def _authorized_headers(db_session, permissions: list[str]) -> dict[str, str]:
    user = User(username="market-user", password_hash="hash")
    role = Role(name="market-reader")
    db_session.add_all([user, role])
    await db_session.flush()
    for name in permissions:
        permission = Permission(name=name)
        db_session.add(permission)
        await db_session.flush()
        db_session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.commit()
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


async def test_market_item_search_returns_price_with_item_name(client, db_session):
    db_session.add(
        Item(
            id="tea",
            source_path="global/items/tea.json",
            category="consumables",
            name="Tea",
            description=None,
            color=None,
            status_state=None,
            raw={},
            source_sha="source-sha",
        )
    )
    db_session.add(
        AuctionCurrentPrice(
            region="RU",
            item_id="tea",
            best_buyout_unit_price=Decimal("120"),
            best_bid_unit_price=Decimal("100"),
            lots_total=1,
            observed_at=datetime.now(UTC),
        )
    )
    await db_session.commit()
    headers = await _authorized_headers(db_session, ["items:read", "auction:read"])

    response = await client.get("/market/items?name=tea&region=RU", headers=headers)

    assert response.status_code == 200
    assert response.json()["items"][0]["name"] == "Tea"
    assert response.json()["items"][0]["current_buyout_unit_price"] == 120.0


async def test_market_item_search_requires_both_catalogue_and_auction_permissions(
    client, db_session
):
    headers = await _authorized_headers(db_session, ["items:read"])

    response = await client.get("/market/items?name=tea&region=RU", headers=headers)

    assert response.status_code == 403


async def test_craft_search_returns_ingredient_prices_and_profit(client, db_session):
    result = Item(
        id="tea",
        source_path="global/items/tea.json",
        category="consumables",
        name="Tea",
        description=None,
        color=None,
        status_state=None,
        raw={},
        source_sha="source-sha",
    )
    ingredient = Item(
        id="herbs",
        source_path="global/items/herbs.json",
        category="materials",
        name="Herbs",
        description=None,
        color=None,
        status_state=None,
        raw={},
        source_sha="source-sha",
    )
    recipe = HideoutRecipe(
        source_index=0,
        bench="kitchen_table",
        category_key="hideout.category.food",
        category_name="Food",
        subcategory_key=None,
        subcategory_name=None,
        energy=0,
        required_perks={},
        required_features=[],
        raw={},
        source_sha="source-sha",
    )
    recipe.components = [
        HideoutRecipeItem(component_type="result", item_id="tea", amount=1, sort_order=0),
        HideoutRecipeItem(component_type="ingredient", item_id="herbs", amount=2, sort_order=0),
    ]
    db_session.add_all([result, ingredient, recipe])
    await db_session.flush()
    db_session.add_all(
        [
            AuctionCurrentPrice(
                region="RU",
                item_id="tea",
                best_buyout_unit_price=Decimal("200"),
                best_bid_unit_price=None,
                lots_total=1,
                observed_at=datetime.now(UTC),
            ),
            AuctionCurrentPrice(
                region="RU",
                item_id="herbs",
                best_buyout_unit_price=Decimal("50"),
                best_bid_unit_price=None,
                lots_total=1,
                observed_at=datetime.now(UTC),
            ),
            CraftProfitSnapshot(
                recipe_id=recipe.id,
                region="RU",
                result_value=Decimal("200"),
                ingredients_cost=Decimal("100"),
                energy_required=0,
                energy_item_amount=0,
                energy_cost=Decimal("0"),
                total_cost=Decimal("100"),
                profit=Decimal("100"),
                margin_percent=Decimal("100"),
                has_complete_prices=True,
                calculated_at=datetime.now(UTC),
            ),
        ]
    )
    await db_session.commit()
    headers = await _authorized_headers(db_session, ["hideout:read", "auction:read"])

    response = await client.get("/hideout/crafts?name=tea&region=RU", headers=headers)

    assert response.status_code == 200
    craft = response.json()["crafts"][0]
    assert craft["results"][0]["name"] == "Tea"
    assert craft["ingredients"][0]["unit_price"] == 50.0
    assert craft["profit"]["profit"] == 100.0
