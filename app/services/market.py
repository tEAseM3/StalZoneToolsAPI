from datetime import UTC, datetime, timedelta
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
from app.services.auction_sync import ENERGY_ITEM_ID, ENERGY_PER_ITEM

PAGE_SIZE = 20


async def top_buy_items(db: AsyncSession, region: str, page: int) -> dict:
    latest_day_bucket = (
        select(
            AuctionPriceCandle.item_id,
            func.max(AuctionPriceCandle.bucket_start).label("bucket_start"),
        )
        .where(AuctionPriceCandle.region == region, AuctionPriceCandle.interval == "day")
        .group_by(AuctionPriceCandle.item_id)
        .subquery()
    )
    latest_week_bucket = (
        select(
            AuctionPriceCandle.item_id,
            func.max(AuctionPriceCandle.bucket_start).label("bucket_start"),
        )
        .where(AuctionPriceCandle.region == region, AuctionPriceCandle.interval == "week")
        .group_by(AuctionPriceCandle.item_id)
        .subquery()
    )
    daily = aliased(AuctionPriceCandle)
    weekly = aliased(AuctionPriceCandle)
    rows = (
        await db.execute(
            select(Item, AuctionCurrentPrice, daily, weekly)
            .join(
                AuctionCurrentPrice,
                (AuctionCurrentPrice.item_id == Item.id) & (AuctionCurrentPrice.region == region),
            )
            .join(
                latest_day_bucket,
                latest_day_bucket.c.item_id == Item.id,
            )
            .join(
                daily,
                (daily.item_id == Item.id)
                & (daily.region == region)
                & (daily.interval == "day")
                & (daily.bucket_start == latest_day_bucket.c.bucket_start),
            )
            .join(
                latest_week_bucket,
                latest_week_bucket.c.item_id == Item.id,
            )
            .join(
                weekly,
                (weekly.item_id == Item.id)
                & (weekly.region == region)
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
                "trend": "below_weekly_median",
                "observed_at": current.observed_at,
            }
        )
    candidates.sort(key=lambda candidate: candidate["buy_score"], reverse=True)
    offset = (page - 1) * PAGE_SIZE
    return {
        "page": page,
        "criteria": {
            "minimum_daily_trade_volume": 5,
            "minimum_weekly_trade_volume": 20,
            "strategy": "current buyout below the latest weekly median",
        },
        "items": candidates[offset : offset + PAGE_SIZE],
    }


async def search_items(db: AsyncSession, region: str, name: str, page: int) -> dict:
    statement = (
        select(Item)
        .where(Item.name.ilike(f"%{name}%"))
        .order_by(Item.name)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    )
    items = (await db.scalars(statement)).all()
    return {"page": page, "items": [await item_market(db, region, item) for item in items]}


async def item_market(db: AsyncSession, region: str, item: Item) -> dict:
    current = await db.get(AuctionCurrentPrice, {"region": region, "item_id": item.id})
    recent = await db.scalar(
        select(AuctionPriceCandle)
        .where(
            AuctionPriceCandle.region == region,
            AuctionPriceCandle.item_id == item.id,
            AuctionPriceCandle.interval == "day",
        )
        .order_by(AuctionPriceCandle.bucket_start.desc())
    )
    trend = await _price_trend(db, region, item.id, recent)
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
        "min_unit_price": recent.min_unit_price if recent else None,
        "max_unit_price": recent.max_unit_price if recent else None,
        "trade_volume": recent.volume if recent else None,
        "trend": trend,
    }


async def item_market_details(
    db: AsyncSession, region: str, item_id: str, interval: str
) -> dict | None:
    item = await db.get(Item, item_id)
    if item is None:
        return None
    result = await item_market(db, region, item)
    candles = (
        await db.scalars(
            select(AuctionPriceCandle)
            .where(
                AuctionPriceCandle.region == region,
                AuctionPriceCandle.item_id == item_id,
                AuctionPriceCandle.interval == interval,
            )
            .order_by(AuctionPriceCandle.bucket_start.desc())
            .limit(90)
        )
    ).all()
    result["interval"] = interval
    result["candles"] = [
        {
            "start": candle.bucket_start,
            "median": candle.median_unit_price,
            "vwap": candle.vwap_unit_price,
            "min": candle.min_unit_price,
            "max": candle.max_unit_price,
            "p10": candle.percentile_10_unit_price,
            "p90": candle.percentile_90_unit_price,
            "trades": candle.trade_count,
            "volume": candle.volume,
        }
        for candle in reversed(candles)
    ]
    return result


async def search_crafts(db: AsyncSession, region: str, name: str, page: int) -> dict:
    statement = (
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
    recipes = (await db.scalars(statement)).unique().all()
    return {"page": page, "crafts": [await craft_market(db, region, recipe) for recipe in recipes]}


async def top_crafts(db: AsyncSession, region: str, page: int) -> dict:
    snapshots = (
        await db.scalars(
            select(CraftProfitSnapshot)
            .where(CraftProfitSnapshot.region == region, CraftProfitSnapshot.has_complete_prices)
            .order_by(CraftProfitSnapshot.profit.desc())
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )
    ).all()
    recipes = await _recipes_by_id(db, {snapshot.recipe_id for snapshot in snapshots})
    crafts = [await craft_market(db, region, recipes[snapshot.recipe_id]) for snapshot in snapshots]
    return {"page": page, "crafts": crafts}


async def craft_market(db: AsyncSession, region: str, recipe: HideoutRecipe) -> dict:
    component_ids = {component.item_id for component in recipe.components}
    items = await _items_by_id(db, component_ids)
    prices = await _prices_by_item_id(db, region, component_ids)
    snapshot = await db.get(CraftProfitSnapshot, {"recipe_id": recipe.id, "region": region})
    return {
        "recipe_id": recipe.id,
        "bench": recipe.bench,
        "category": recipe.category_name,
        "energy": recipe.energy,
        "results": _components(recipe.components, "result", items, prices),
        "ingredients": _components(recipe.components, "ingredient", items, prices),
        "profit": _snapshot(snapshot),
    }


async def craft_chain(db: AsyncSession, region: str, recipe_id: int) -> dict | None:
    recipe = await db.scalar(
        select(HideoutRecipe)
        .options(selectinload(HideoutRecipe.components))
        .where(HideoutRecipe.id == recipe_id)
    )
    if recipe is None:
        return None
    recipes = (
        await db.scalars(select(HideoutRecipe).options(selectinload(HideoutRecipe.components)))
    ).all()
    component_ids = {
        component.item_id for candidate in recipes for component in candidate.components
    }
    prices = await _prices_by_item_id(db, region, component_ids)
    producers: dict[str, list[HideoutRecipe]] = {}
    for candidate in recipes:
        for component in candidate.components:
            if component.component_type == "result":
                producers.setdefault(component.item_id, []).append(candidate)
    energy_unit_price = prices.get(ENERGY_ITEM_ID)
    ingredients = [item for item in recipe.components if item.component_type == "ingredient"]
    return {
        "recipe_id": recipe.id,
        "ingredients": [
            _chain_node(item, prices, producers, energy_unit_price, set()) for item in ingredients
        ],
    }


async def reprocess_options(db: AsyncSession, region: str, item_id: str) -> list[dict]:
    recipes = (
        (
            await db.scalars(
                select(HideoutRecipe)
                .join(HideoutRecipeItem)
                .where(
                    HideoutRecipeItem.component_type == "ingredient",
                    HideoutRecipeItem.item_id == item_id,
                )
                .options(selectinload(HideoutRecipe.components))
                .distinct()
            )
        )
        .unique()
        .all()
    )
    price = (await _prices_by_item_id(db, region, {item_id})).get(item_id)
    options = []
    for recipe in recipes:
        craft = await craft_market(db, region, recipe)
        input_amount = sum(
            Decimal(component.amount)
            for component in recipe.components
            if component.component_type == "ingredient" and component.item_id == item_id
        )
        raw_value = input_amount * price if price is not None else None
        profit = craft["profit"]
        options.append(
            {
                **craft,
                "selected_ingredient": {
                    "item_id": item_id,
                    "amount": input_amount,
                    "sell_as_is_value": raw_value,
                },
                "recommendation": _reprocess_recommendation(profit),
            }
        )
    return options


async def _price_trend(
    db: AsyncSession,
    region: str,
    item_id: str,
    recent: AuctionPriceCandle | None,
) -> dict | None:
    if recent is None:
        return None
    since = datetime.now(UTC) - timedelta(days=30)
    candles = (
        await db.scalars(
            select(AuctionPriceCandle)
            .where(
                AuctionPriceCandle.region == region,
                AuctionPriceCandle.item_id == item_id,
                AuctionPriceCandle.interval == "day",
                AuctionPriceCandle.bucket_start >= since,
            )
            .order_by(AuctionPriceCandle.bucket_start.desc())
        )
    ).all()
    if len(candles) < 2:
        return {
            "status": "insufficient_data",
            "median_24h": recent.median_unit_price,
            "median_30d": None,
            "change_percent": None,
        }
    historical = sum((candle.median_unit_price for candle in candles), Decimal(0)) / len(candles)
    change_percent = (
        (recent.median_unit_price - historical) / historical * 100 if historical else None
    )
    if change_percent is None:
        status = "insufficient_data"
    elif change_percent > 5:
        status = "above_usual"
    elif change_percent < -5:
        status = "below_usual"
    else:
        status = "normal"
    return {
        "status": status,
        "median_24h": recent.median_unit_price,
        "median_30d": historical,
        "change_percent": change_percent,
    }


async def _items_by_id(db: AsyncSession, item_ids: set[str]) -> dict[str, Item]:
    if not item_ids:
        return {}
    items = (await db.scalars(select(Item).where(Item.id.in_(item_ids)))).all()
    return {item.id: item for item in items}


async def _prices_by_item_id(
    db: AsyncSession, region: str, item_ids: set[str]
) -> dict[str, Decimal | None]:
    if not item_ids:
        return {}
    prices = (
        await db.scalars(
            select(AuctionCurrentPrice).where(
                AuctionCurrentPrice.region == region, AuctionCurrentPrice.item_id.in_(item_ids)
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
        "ingredients_cost": snapshot.ingredients_cost,
        "energy_cost": snapshot.energy_cost,
        "total_cost": snapshot.total_cost,
        "profit": snapshot.profit,
        "margin_percent": snapshot.margin_percent,
        "has_complete_prices": snapshot.has_complete_prices,
        "calculated_at": snapshot.calculated_at,
    }


def _reprocess_recommendation(profit: dict | None) -> str:
    if profit is None or not profit["has_complete_prices"]:
        return "insufficient_price_data"
    return "reprocess" if profit["profit"] > 0 else "sell_as_is"


def _chain_node(component, prices, producers, energy_unit_price, visited: set[str]) -> dict:
    direct_price = prices.get(component.item_id)
    if component.item_id in visited:
        return {"item_id": component.item_id, "amount": component.amount, "cycle": True}
    next_visited = visited | {component.item_id}
    variants = []
    for recipe in producers.get(component.item_id, []):
        result_amount = sum(
            Decimal(result.amount)
            for result in recipe.components
            if result.component_type == "result" and result.item_id == component.item_id
        )
        ingredient_nodes = [
            _chain_node(ingredient, prices, producers, energy_unit_price, next_visited)
            for ingredient in recipe.components
            if ingredient.component_type == "ingredient"
        ]
        ingredient_cost = _sum_best_cost(ingredient_nodes)
        energy_cost = (
            Decimal(0)
            if recipe.energy == 0
            else (
                Decimal(recipe.energy) / ENERGY_PER_ITEM * energy_unit_price
                if energy_unit_price is not None
                else None
            )
        )
        base_cost = (
            ingredient_cost + energy_cost
            if ingredient_cost is not None and energy_cost is not None
            else None
        )
        craft_cost = (
            base_cost / result_amount * Decimal(component.amount)
            if base_cost is not None and result_amount > 0
            else None
        )
        variants.append(
            {
                "recipe_id": recipe.id,
                "craft_cost": craft_cost,
                "ingredients": ingredient_nodes,
            }
        )
    buy_cost = direct_price * Decimal(component.amount) if direct_price is not None else None
    craft_costs = [
        variant["craft_cost"] for variant in variants if variant["craft_cost"] is not None
    ]
    best_craft_cost = min(craft_costs, default=None)
    available_costs = [cost for cost in (buy_cost, best_craft_cost) if cost is not None]
    best_cost = min(available_costs) if available_costs else None
    return {
        "item_id": component.item_id,
        "amount": component.amount,
        "buy_unit_price": direct_price,
        "buy_cost": buy_cost,
        "best_craft_cost": best_craft_cost,
        "best_cost": best_cost,
        "recommended_strategy": (
            "buy" if buy_cost == best_cost else "craft" if best_cost is not None else None
        ),
        "craft_variants": variants,
    }


def _sum_best_cost(nodes: list[dict]) -> Decimal | None:
    costs = [node.get("best_cost") for node in nodes]
    if any(cost is None for cost in costs):
        return None
    return sum(costs, Decimal(0))
