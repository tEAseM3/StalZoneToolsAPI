from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models.auction_current_price import AuctionCurrentPrice
from app.models.auction_price_candle import AuctionPriceCandle
from app.models.craft_profit_snapshot import CraftProfitSnapshot
from app.models.hideout_recipe import HideoutRecipe
from app.models.hideout_recipe_item import HideoutRecipeItem
from app.models.item import Item

PAGE_SIZE = 20
AUCTION_SELL_COMMISSION = Decimal("0.05")


async def search_items(db: AsyncSession, name: str, page: int) -> dict:
    items = (
        await db.scalars(
            select(Item)
            .where(Item.name.ilike(f"%{name}%"))
            .order_by(Item.name)
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )
    ).all()
    return {"page": page, "items": [await item_market(db, item) for item in items]}


async def top_buy_items(db: AsyncSession, sort: str, order: str, page: int) -> dict:
    latest_day_bucket = _latest_bucket_subquery("day")
    latest_week_bucket = _latest_bucket_subquery("week")
    daily = aliased(AuctionPriceCandle)
    weekly = aliased(AuctionPriceCandle)
    rows = (
        await db.execute(
            select(Item, AuctionCurrentPrice, daily, weekly)
            .join(
                AuctionCurrentPrice,
                (AuctionCurrentPrice.item_id == Item.id) & (AuctionCurrentPrice.region == "EU"),
            )
            .join(latest_day_bucket, latest_day_bucket.c.item_id == Item.id)
            .join(
                daily,
                (daily.item_id == Item.id)
                & (daily.region == "EU")
                & (daily.interval == "day")
                & (daily.bucket_start == latest_day_bucket.c.bucket_start),
            )
            .join(latest_week_bucket, latest_week_bucket.c.item_id == Item.id)
            .join(
                weekly,
                (weekly.item_id == Item.id)
                & (weekly.region == "EU")
                & (weekly.interval == "week")
                & (weekly.bucket_start == latest_week_bucket.c.bucket_start),
            )
            .where(
                AuctionCurrentPrice.best_buyout_unit_price.is_not(None),
                daily.volume >= 5,
                weekly.volume >= 20,
                weekly.median_unit_price > 0,
            )
        )
    ).all()
    candidates = []
    for item, current, latest_day, latest_week in rows:
        buyout_price = current.best_buyout_unit_price
        discount_percent = (
            (latest_week.median_unit_price - buyout_price) / latest_week.median_unit_price * 100
        )
        if discount_percent <= 0:
            continue
        liquidity_factor = min(Decimal(latest_day.volume) / Decimal(10), Decimal(10))
        candidates.append(
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "current_buyout_unit_price": buyout_price,
                "weekly_median_unit_price": latest_week.median_unit_price,
                "daily_median_unit_price": latest_day.median_unit_price,
                "daily_trade_volume": latest_day.volume,
                "weekly_trade_volume": latest_week.volume,
                "discount_percent": discount_percent,
                "buy_score": discount_percent * liquidity_factor,
                "observed_at": current.observed_at,
            }
        )
    sort_fields = {
        "score": "buy_score",
        "price": "current_buyout_unit_price",
        "discount": "discount_percent",
        "volume": "daily_trade_volume",
    }
    candidates.sort(key=lambda candidate: candidate[sort_fields[sort]], reverse=order == "desc")
    offset = (page - 1) * PAGE_SIZE
    return {
        "page": page,
        "criteria": {
            "region": "EU",
            "minimum_daily_trade_volume": 5,
            "minimum_weekly_trade_volume": 20,
            "strategy": "current buyout below the latest weekly median",
        },
        "sort": sort,
        "order": order,
        "items": candidates[offset : offset + PAGE_SIZE],
    }


async def profitable_buy_items(db: AsyncSession, sort: str, order: str, page: int) -> dict:
    latest_day_bucket = _latest_bucket_subquery("day")
    daily = aliased(AuctionPriceCandle)
    rows = (
        await db.execute(
            select(Item, AuctionCurrentPrice, daily)
            .join(
                AuctionCurrentPrice,
                (AuctionCurrentPrice.item_id == Item.id) & (AuctionCurrentPrice.region == "EU"),
            )
            .join(latest_day_bucket, latest_day_bucket.c.item_id == Item.id)
            .join(
                daily,
                (daily.item_id == Item.id)
                & (daily.region == "EU")
                & (daily.interval == "day")
                & (daily.bucket_start == latest_day_bucket.c.bucket_start),
            )
            .where(
                AuctionCurrentPrice.best_buyout_unit_price.is_not(None),
                daily.median_unit_price > 0,
                daily.volume > 0,
            )
        )
    ).all()
    opportunities = []
    for item, current, daily_candle in rows:
        buy_price = current.best_buyout_unit_price
        expected_net_sale_price = daily_candle.median_unit_price * (
            Decimal(1) - AUCTION_SELL_COMMISSION
        )
        profit_per_unit = expected_net_sale_price - buy_price
        if profit_per_unit < 0:
            continue
        margin_percent = profit_per_unit / buy_price * 100 if buy_price else None
        opportunities.append(
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "buyout_unit_price": buy_price,
                "reference_sale_unit_price": daily_candle.median_unit_price,
                "expected_net_sale_unit_price": expected_net_sale_price,
                "auction_commission_percent": AUCTION_SELL_COMMISSION * 100,
                "profit_per_unit": profit_per_unit,
                "margin_percent": margin_percent,
                "trade_volume_24h": daily_candle.volume,
                "lots_observed_at": current.observed_at,
            }
        )
    sort_fields = {
        "profit": "profit_per_unit",
        "margin": "margin_percent",
        "price": "buyout_unit_price",
        "volume": "trade_volume_24h",
    }
    opportunities.sort(
        key=lambda opportunity: opportunity[sort_fields[sort]] or Decimal(0),
        reverse=order == "desc",
    )
    offset = (page - 1) * PAGE_SIZE
    return {
        "page": page,
        "sort": sort,
        "order": order,
        "method": "latest daily median of completed sales minus 5% auction commission",
        "lots_delay_notice": "Active lots can be delayed by approximately 10 minutes.",
        "opportunities": opportunities[offset : offset + PAGE_SIZE],
    }
async def search_crafts(db: AsyncSession, name: str, page: int) -> dict:
    recipes = (
        await db.scalars(
            select(HideoutRecipe)
            .join(HideoutRecipeItem)
            .join(Item, Item.id == HideoutRecipeItem.item_id)
            .where(HideoutRecipeItem.component_type == "result", Item.name.ilike(f"%{name}%"))
            .options(selectinload(HideoutRecipe.components))
            .distinct()
            .order_by(HideoutRecipe.id)
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )
    ).unique().all()
    return {"page": page, "crafts": [await craft_market(db, recipe) for recipe in recipes]}


async def top_crafts(db: AsyncSession, sort: str, order: str, page: int) -> dict:
    sort_fields = {
        "profit": CraftProfitSnapshot.profit,
        "margin": CraftProfitSnapshot.margin_percent,
        "cost": CraftProfitSnapshot.total_cost,
        "price": CraftProfitSnapshot.result_value,
    }
    sort_expression = sort_fields[sort]
    snapshots = (
        await db.scalars(
            select(CraftProfitSnapshot)
            .where(CraftProfitSnapshot.region == "EU", CraftProfitSnapshot.has_complete_prices)
            .order_by(sort_expression.asc() if order == "asc" else sort_expression.desc())
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )
    ).all()
    recipes = await _recipes_by_id(db, {snapshot.recipe_id for snapshot in snapshots})
    return {
        "page": page,
        "sort": sort,
        "order": order,
        "crafts": [await craft_market(db, recipes[snapshot.recipe_id]) for snapshot in snapshots],
    }


async def item_market(db: AsyncSession, item: Item) -> dict:
    current = await db.get(AuctionCurrentPrice, {"region": "EU", "item_id": item.id})
    recent = await db.scalar(
        select(AuctionPriceCandle)
        .where(
            AuctionPriceCandle.region == "EU",
            AuctionPriceCandle.item_id == item.id,
            AuctionPriceCandle.interval == "day",
        )
        .order_by(AuctionPriceCandle.bucket_start.desc())
    )
    return {
        "id": item.id,
        "name": item.name,
        "category": item.category,
        "current_buyout_unit_price": current.best_buyout_unit_price if current else None,
        "current_bid_unit_price": current.best_bid_unit_price if current else None,
        "lots_total": current.lots_total if current else None,
        "observed_at": current.observed_at if current else None,
        "median_unit_price": recent.median_unit_price if recent else None,
        "vwap_unit_price": recent.vwap_unit_price if recent else None,
        "trade_volume": recent.volume if recent else None,
    }


async def craft_market(db: AsyncSession, recipe: HideoutRecipe) -> dict:
    component_ids = {component.item_id for component in recipe.components}
    items = await _items_by_id(db, component_ids)
    prices = await _prices_by_item_id(db, component_ids)
    snapshot = await db.get(CraftProfitSnapshot, {"recipe_id": recipe.id, "region": "EU"})
    return {
        "recipe_id": recipe.id,
        "bench": recipe.bench,
        "category": recipe.category_name,
        "energy": recipe.energy,
        "results": _components(recipe.components, "result", items, prices),
        "ingredients": _components(recipe.components, "ingredient", items, prices),
        "profit": _snapshot(snapshot),
    }


def _latest_bucket_subquery(interval: str):
    return (
        select(
            AuctionPriceCandle.item_id,
            func.max(AuctionPriceCandle.bucket_start).label("bucket_start"),
        )
        .where(AuctionPriceCandle.region == "EU", AuctionPriceCandle.interval == interval)
        .group_by(AuctionPriceCandle.item_id)
        .subquery()
    )


async def _items_by_id(db: AsyncSession, item_ids: set[str]) -> dict[str, Item]:
    if not item_ids:
        return {}
    items = (await db.scalars(select(Item).where(Item.id.in_(item_ids)))).all()
    return {item.id: item for item in items}


async def _prices_by_item_id(db: AsyncSession, item_ids: set[str]) -> dict[str, Decimal | None]:
    if not item_ids:
        return {}
    prices = (
        await db.scalars(
            select(AuctionCurrentPrice).where(
                AuctionCurrentPrice.region == "EU", AuctionCurrentPrice.item_id.in_(item_ids)
            )
        )
    ).all()
    return {price.item_id: price.best_buyout_unit_price for price in prices}


async def _recipes_by_id(db: AsyncSession, recipe_ids: set[int]) -> dict[int, HideoutRecipe]:
    if not recipe_ids:
        return {}
    recipes = (
        await db.scalars(
            select(HideoutRecipe)
            .where(HideoutRecipe.id.in_(recipe_ids))
            .options(selectinload(HideoutRecipe.components))
        )
    ).all()
    return {recipe.id: recipe for recipe in recipes}


def _components(
    components,
    component_type: str,
    items: dict[str, Item],
    prices: dict[str, Decimal | None],
):
    return [
        {
            "item_id": component.item_id,
            "name": items.get(component.item_id).name if component.item_id in items else None,
            "amount": component.amount,
            "unit_price": prices.get(component.item_id),
        }
        for component in components
        if component.component_type == component_type
    ]


def _snapshot(snapshot: CraftProfitSnapshot | None) -> dict | None:
    if snapshot is None:
        return None
    return {
        "result_value": snapshot.result_value,
        "net_result_value": (
            snapshot.result_value * (Decimal(1) - AUCTION_SELL_COMMISSION)
            if snapshot.result_value is not None
            else None
        ),
        "auction_commission_percent": AUCTION_SELL_COMMISSION * 100,
        "ingredients_cost": snapshot.ingredients_cost,
        "energy_cost": snapshot.energy_cost,
        "total_cost": snapshot.total_cost,
        "profit": snapshot.profit,
        "margin_percent": snapshot.margin_percent,
        "has_complete_prices": snapshot.has_complete_prices,
        "calculated_at": snapshot.calculated_at,
    }
