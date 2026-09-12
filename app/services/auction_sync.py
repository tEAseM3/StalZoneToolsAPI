import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auction_current_price import AuctionCurrentPrice
from app.models.auction_price_candle import AuctionPriceCandle
from app.models.auction_refresh_queue import AuctionRefreshQueue
from app.models.auction_trade import AuctionTrade
from app.models.craft_profit_snapshot import CraftProfitSnapshot
from app.models.hideout_recipe import HideoutRecipe
from app.models.hideout_recipe_item import HideoutRecipeItem
from app.services.auction_client import (
    AuctionClient,
    AuctionLot,
    AuctionTradeRecord,
    per_unit_price,
)

ENERGY_ITEM_ID = "401j"
ENERGY_PER_ITEM = Decimal("5000")


class AuctionSyncService:
    def __init__(
        self,
        db: AsyncSession,
        client: AuctionClient,
        lots_refresh_minutes: int,
        history_refresh_hours: int,
    ):
        self.db = db
        self.client = client
        self.lots_refresh = timedelta(minutes=lots_refresh_minutes)
        self.history_refresh = timedelta(hours=history_refresh_hours)

    async def ensure_recipe_candidates(self, regions: list[str]) -> int:
        rows = (
            await self.db.execute(
                select(HideoutRecipeItem.item_id, HideoutRecipeItem.component_type)
            )
        ).all()
        priorities: dict[str, int] = {ENERGY_ITEM_ID: 200}
        for item_id, component_type in rows:
            priority = 100 if component_type == "result" else 50
            priorities[item_id] = max(priorities.get(item_id, 0), priority)

        now = _now()
        created = 0
        for region in regions:
            for item_id, priority in priorities.items():
                queue_item = await self.db.get(
                    AuctionRefreshQueue, {"region": region, "item_id": item_id}
                )
                if queue_item is None:
                    self.db.add(
                        AuctionRefreshQueue(
                            region=region,
                            item_id=item_id,
                            priority=priority,
                            next_lots_refresh_at=now,
                            next_history_refresh_at=now,
                        )
                    )
                    created += 1
                else:
                    queue_item.priority = max(queue_item.priority, priority)
        await self.db.commit()
        return created

    async def sync_due(self, region: str, max_requests: int) -> int:
        now = _now()
        queue_items = (
            await self.db.scalars(
                select(AuctionRefreshQueue)
                .where(AuctionRefreshQueue.region == region)
                .where(
                    (AuctionRefreshQueue.next_lots_refresh_at <= now)
                    | (AuctionRefreshQueue.next_history_refresh_at <= now)
                )
                .order_by(AuctionRefreshQueue.priority.desc())
            )
        ).all()
        requests_used = 0
        changed_prices = False
        for queue_item in queue_items:
            if requests_used >= max_requests:
                break
            if queue_item.next_lots_refresh_at <= now:
                _, lots = await self.client.get_lots(region, queue_item.item_id)
                await self._store_lots(region, queue_item.item_id, lots, now)
                queue_item.last_lots_refresh_at = now
                queue_item.next_lots_refresh_at = now + self.lots_refresh
                requests_used += 1
                changed_prices = True
            if requests_used >= max_requests:
                continue
            if queue_item.next_history_refresh_at <= now:
                _, trades = await self.client.get_history(region, queue_item.item_id)
                await self._store_trades(region, queue_item.item_id, trades, now)
                await self._rebuild_candles(region, queue_item.item_id)
                queue_item.last_history_refresh_at = now
                queue_item.next_history_refresh_at = now + self.history_refresh
                requests_used += 1

        if changed_prices:
            await self.recalculate_craft_profit(region, now)
        await self.db.commit()
        return requests_used

    async def recalculate_craft_profit(
        self, region: str, calculated_at: datetime | None = None
    ) -> None:
        recipes = (
            await self.db.scalars(
                select(HideoutRecipe).options(selectinload(HideoutRecipe.components))
            )
        ).all()
        prices = {
            current.item_id: current.best_buyout_unit_price
            for current in (
                await self.db.scalars(
                    select(AuctionCurrentPrice).where(AuctionCurrentPrice.region == region)
                )
            ).all()
        }
        energy_price = prices.get(ENERGY_ITEM_ID)
        for recipe in recipes:
            ingredients = [
                item for item in recipe.components if item.component_type == "ingredient"
            ]
            results = [item for item in recipe.components if item.component_type == "result"]
            energy_item_amount = Decimal(recipe.energy) / ENERGY_PER_ITEM
            ingredient_cost = _component_cost(ingredients, prices)
            result_value = _component_cost(results, prices)
            energy_cost = energy_item_amount * energy_price if energy_price is not None else None
            complete = (
                ingredient_cost is not None
                and result_value is not None
                and (recipe.energy == 0 or energy_cost is not None)
            )
            total_cost = ingredient_cost + energy_cost if complete else None
            profit = result_value - total_cost if complete and result_value is not None else None
            margin = (profit / total_cost * 100) if profit is not None and total_cost else None
            snapshot = CraftProfitSnapshot(
                recipe_id=recipe.id,
                region=region,
                result_value=result_value,
                ingredients_cost=ingredient_cost,
                energy_required=Decimal(recipe.energy),
                energy_item_amount=energy_item_amount,
                energy_cost=energy_cost,
                total_cost=total_cost,
                profit=profit,
                margin_percent=margin,
                has_complete_prices=complete,
                calculated_at=calculated_at or _now(),
            )
            await self.db.merge(snapshot)

    async def _store_lots(
        self, region: str, item_id: str, lots: list[AuctionLot], observed_at: datetime
    ) -> None:
        buyouts = [per_unit_price(lot.buyout_price, lot.amount) for lot in lots if lot.buyout_price]
        bids = [per_unit_price(lot.current_price, lot.amount) for lot in lots if lot.current_price]
        await self.db.merge(
            AuctionCurrentPrice(
                region=region,
                item_id=item_id,
                best_buyout_unit_price=min(buyouts, default=None),
                best_bid_unit_price=min(bids, default=None),
                lots_total=len(lots),
                observed_at=observed_at,
            )
        )

    async def _store_trades(
        self, region: str, item_id: str, trades: list[AuctionTradeRecord], now: datetime
    ) -> None:
        trades_by_fingerprint = {
            _trade_fingerprint(region, item_id, trade): trade for trade in trades
        }
        if not trades_by_fingerprint:
            return

        existing_fingerprints = set(
            (
                await self.db.scalars(
                    select(AuctionTrade.source_fingerprint).where(
                        AuctionTrade.source_fingerprint.in_(trades_by_fingerprint)
                    )
                )
            ).all()
        )
        for fingerprint, trade in trades_by_fingerprint.items():
            if fingerprint in existing_fingerprints:
                continue
            self.db.add(
                AuctionTrade(
                    region=region,
                    item_id=item_id,
                    amount=trade.amount,
                    lot_price=trade.lot_price,
                    unit_price=per_unit_price(trade.lot_price, trade.amount),
                    sold_at=trade.sold_at,
                    source_fingerprint=fingerprint,
                    created_at=now,
                )
            )
        await self.db.flush()

    async def _rebuild_candles(self, region: str, item_id: str) -> None:
        trades = (
            await self.db.scalars(
                select(AuctionTrade)
                .where(AuctionTrade.region == region, AuctionTrade.item_id == item_id)
                .order_by(AuctionTrade.sold_at)
            )
        ).all()
        by_day: dict[datetime, list[AuctionTrade]] = defaultdict(list)
        by_week: dict[datetime, list[AuctionTrade]] = defaultdict(list)
        for trade in trades:
            time = trade.sold_at.astimezone(UTC)
            day = time.replace(hour=0, minute=0, second=0, microsecond=0)
            week = day - timedelta(days=day.weekday())
            by_day[day].append(trade)
            by_week[week].append(trade)
        for interval, groups in (("day", by_day), ("week", by_week)):
            for bucket_start, bucket_trades in groups.items():
                await self.db.merge(
                    _make_candle(region, item_id, interval, bucket_start, bucket_trades)
                )


def _component_cost(
    components: list[HideoutRecipeItem], prices: dict[str, Decimal | None]
) -> Decimal | None:
    cost = Decimal(0)
    for component in components:
        unit_price = prices.get(component.item_id)
        if unit_price is None:
            return None
        cost += Decimal(component.amount) * unit_price
    return cost


def _make_candle(
    region: str, item_id: str, interval: str, bucket_start: datetime, trades: list[AuctionTrade]
) -> AuctionPriceCandle:
    prices = sorted(trade.unit_price for trade in trades)
    volume = sum(trade.amount for trade in trades)
    turnover = sum(trade.lot_price for trade in trades)
    return AuctionPriceCandle(
        region=region,
        item_id=item_id,
        interval=interval,
        bucket_start=bucket_start,
        median_unit_price=_percentile(prices, Decimal("0.5")),
        vwap_unit_price=Decimal(turnover) / Decimal(volume),
        min_unit_price=prices[0],
        max_unit_price=prices[-1],
        percentile_10_unit_price=_percentile(prices, Decimal("0.1")),
        percentile_90_unit_price=_percentile(prices, Decimal("0.9")),
        trade_count=len(trades),
        volume=volume,
        turnover=turnover,
    )


def _percentile(values: list[Decimal], percentile: Decimal) -> Decimal:
    index = int((len(values) - 1) * percentile)
    return values[index]


def _trade_fingerprint(region: str, item_id: str, trade: AuctionTradeRecord) -> str:
    value = json.dumps(
        [region, item_id, trade.amount, trade.lot_price, trade.sold_at.isoformat()],
        separators=(",", ":"),
    )
    return hashlib.sha256(value.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)
