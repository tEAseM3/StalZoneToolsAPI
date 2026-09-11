from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.models.auction_current_price import AuctionCurrentPrice
from app.models.auction_refresh_queue import AuctionRefreshQueue
from app.models.craft_profit_snapshot import CraftProfitSnapshot
from app.models.hideout_recipe import HideoutRecipe
from app.models.hideout_recipe_item import HideoutRecipeItem
from app.services.auction_client import AuctionLot, AuctionTradeRecord
from app.services.auction_sync import ENERGY_ITEM_ID, AuctionSyncService


class FakeAuctionClient:
    def __init__(self):
        self.lots = {
            "result": [AuctionLot(amount=1, current_price=150, buyout_price=200)],
            "ingredient": [AuctionLot(amount=2, current_price=40, buyout_price=100)],
            ENERGY_ITEM_ID: [AuctionLot(amount=1, current_price=50, buyout_price=50)],
        }

    async def get_lots(self, region: str, item_id: str):
        return len(self.lots[item_id]), self.lots[item_id]

    async def get_history(self, region: str, item_id: str):
        return 1, [
            AuctionTradeRecord(
                amount=2,
                lot_price=100,
                sold_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        ]


async def test_auction_sync_updates_recipe_candidates_prices_and_profit(db_session):
    recipe = HideoutRecipe(
        source_index=0,
        bench="workbench",
        category_key="hideout.category",
        category_name="Category",
        subcategory_key=None,
        subcategory_name=None,
        energy=1000,
        required_perks={},
        required_features=[],
        raw={},
        source_sha="source-sha",
    )
    recipe.components = [
        HideoutRecipeItem(component_type="result", item_id="result", amount=1, sort_order=0),
        HideoutRecipeItem(
            component_type="ingredient", item_id="ingredient", amount=2, sort_order=0
        ),
    ]
    db_session.add(recipe)
    await db_session.commit()

    service = AuctionSyncService(
        db_session, FakeAuctionClient(), lots_refresh_minutes=10, history_refresh_hours=6
    )
    assert await service.ensure_recipe_candidates(["RU"]) == 3

    requests_used = await service.sync_due("RU", max_requests=6)

    assert requests_used == 6
    current_price = await db_session.get(
        AuctionCurrentPrice, {"region": "RU", "item_id": "ingredient"}
    )
    profit = await db_session.get(CraftProfitSnapshot, {"recipe_id": recipe.id, "region": "RU"})
    queue = await db_session.scalar(
        select(AuctionRefreshQueue).where(AuctionRefreshQueue.region == "RU")
    )
    assert current_price is not None
    assert current_price.best_buyout_unit_price == Decimal("50")
    assert profit is not None
    assert profit.ingredients_cost == Decimal("100")
    assert profit.energy_cost == Decimal("10")
    assert profit.profit == Decimal("90")
    assert queue is not None
