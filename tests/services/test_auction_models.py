from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.models.auction_current_price import AuctionCurrentPrice
from app.models.auction_price_candle import AuctionPriceCandle
from app.models.auction_refresh_queue import AuctionRefreshQueue
from app.models.auction_trade import AuctionTrade
from app.models.craft_profit_snapshot import CraftProfitSnapshot
from app.models.hideout_recipe import HideoutRecipe

REGION = "EU"


async def test_auction_models_persist_current_price_history_and_craft_profit(db_session):
    now = datetime.now(UTC)
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
    db_session.add(recipe)
    await db_session.flush()
    db_session.add_all(
        [
            AuctionTrade(
                region=REGION,
                item_id="tea",
                amount=2,
                lot_price=200,
                unit_price=Decimal("100"),
                sold_at=now,
                source_fingerprint="a" * 64,
                created_at=now,
            ),
            AuctionCurrentPrice(
                region=REGION,
                item_id="tea",
                best_buyout_unit_price=Decimal("110"),
                best_bid_unit_price=Decimal("100"),
                lots_total=3,
                observed_at=now,
            ),
            AuctionPriceCandle(
                region=REGION,
                item_id="tea",
                interval="day",
                bucket_start=now,
                median_unit_price=Decimal("100"),
                vwap_unit_price=Decimal("100"),
                min_unit_price=Decimal("90"),
                max_unit_price=Decimal("120"),
                percentile_10_unit_price=Decimal("92"),
                percentile_90_unit_price=Decimal("118"),
                trade_count=2,
                volume=4,
                turnover=400,
            ),
            AuctionRefreshQueue(
                region=REGION,
                item_id="tea",
                priority=10,
                next_lots_refresh_at=now,
                next_history_refresh_at=now,
            ),
            CraftProfitSnapshot(
                recipe_id=recipe.id,
                region=REGION,
                result_value=Decimal("500"),
                ingredients_cost=Decimal("300"),
                energy_required=Decimal("1000"),
                energy_item_amount=Decimal("0.2"),
                energy_cost=Decimal("10"),
                total_cost=Decimal("310"),
                profit=Decimal("190"),
                margin_percent=Decimal("61.2903"),
                has_complete_prices=True,
                calculated_at=now,
            ),
        ]
    )
    await db_session.commit()

    price = await db_session.get(AuctionCurrentPrice, {"region": REGION, "item_id": "tea"})
    profit = await db_session.scalar(
        select(CraftProfitSnapshot).where(CraftProfitSnapshot.region == REGION)
    )

    assert price is not None
    assert price.best_buyout_unit_price == Decimal("110")
    assert profit is not None
    assert profit.profit == Decimal("190")
