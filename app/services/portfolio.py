from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions.base import ConflictError, NotFoundError
from app.models.auction_current_price import AuctionCurrentPrice
from app.models.item import Item
from app.models.user_trade_position import UserTradePosition
from app.models.user_trade_sale import UserTradeSale
from app.schemas.portfolio import TradePositionCreate, TradeSaleCreate


async def create_position(
    db: AsyncSession, user_id: int, region: str, data: TradePositionCreate
) -> dict:
    items = (await db.scalars(select(Item).where(Item.name.ilike(data.item_name)).limit(2))).all()
    if not items:
        raise NotFoundError("Item with this name was not found")
    if len(items) > 1:
        raise ConflictError("Several items have this name; use a more specific item name")

    item = items[0]
    position = UserTradePosition(
        user_id=user_id,
        item_id=item.id,
        item_name=item.name,
        region=region,
        purchased_quantity=data.quantity,
        purchase_total=data.purchase_total,
        purchased_at=data.purchased_at or datetime.now(UTC),
    )
    db.add(position)
    await db.commit()
    await db.refresh(position, attribute_names=["sales"])
    return await position_view(db, position)


async def add_sale(db: AsyncSession, user_id: int, position_id: int, data: TradeSaleCreate) -> dict:
    position = await db.scalar(
        select(UserTradePosition)
        .where(UserTradePosition.id == position_id, UserTradePosition.user_id == user_id)
        .options(selectinload(UserTradePosition.sales))
        .with_for_update()
    )
    if position is None:
        raise NotFoundError("Trade position was not found")

    sold_quantity = sum(sale.quantity for sale in position.sales)
    remaining_quantity = position.purchased_quantity - sold_quantity
    if data.quantity > remaining_quantity:
        raise ConflictError(f"Only {remaining_quantity} item(s) remain in this position")

    position.sales.append(
        UserTradeSale(
            quantity=data.quantity,
            revenue_total=data.revenue_total,
            sold_at=data.sold_at or datetime.now(UTC),
        )
    )
    await db.commit()
    return await position_view(db, position)


async def list_positions(db: AsyncSession, user_id: int, region: str) -> dict:
    positions = (
        await db.scalars(
            select(UserTradePosition)
            .where(UserTradePosition.user_id == user_id, UserTradePosition.region == region)
            .options(selectinload(UserTradePosition.sales))
            .order_by(UserTradePosition.purchased_at.desc())
        )
    ).all()
    return {"positions": [await position_view(db, position) for position in positions]}


async def position_view(db: AsyncSession, position: UserTradePosition) -> dict:
    current_price = await db.get(
        AuctionCurrentPrice, {"region": position.region, "item_id": position.item_id}
    )
    sold_quantity = sum(sale.quantity for sale in position.sales)
    sold_revenue = sum(sale.revenue_total for sale in position.sales)
    remaining_quantity = position.purchased_quantity - sold_quantity
    purchase_total = Decimal(position.purchase_total)
    allocated_sold_cost = (
        purchase_total * Decimal(sold_quantity) / Decimal(position.purchased_quantity)
    )
    realized_profit = Decimal(sold_revenue) - allocated_sold_cost
    current_unit_price, valuation_source = _current_unit_price(current_price)
    remaining_market_value = (
        current_unit_price * Decimal(remaining_quantity) if current_unit_price is not None else None
    )
    total_profit = (
        Decimal(sold_revenue) + remaining_market_value - purchase_total
        if remaining_market_value is not None
        else None
    )
    return {
        "id": position.id,
        "item_id": position.item_id,
        "item_name": position.item_name,
        "region": position.region,
        "purchased_quantity": position.purchased_quantity,
        "purchase_total": position.purchase_total,
        "purchase_unit_price": purchase_total / Decimal(position.purchased_quantity),
        "purchased_at": position.purchased_at,
        "sold_quantity": sold_quantity,
        "sold_revenue": sold_revenue,
        "remaining_quantity": remaining_quantity,
        "realized_profit": realized_profit,
        "current_unit_price": current_unit_price,
        "valuation_source": valuation_source,
        "remaining_market_value": remaining_market_value,
        "total_profit": total_profit,
        "total_profit_percent": total_profit / purchase_total * 100
        if total_profit is not None and purchase_total
        else None,
        "sales": [
            {
                "id": sale.id,
                "quantity": sale.quantity,
                "revenue_total": sale.revenue_total,
                "unit_price": Decimal(sale.revenue_total) / Decimal(sale.quantity),
                "sold_at": sale.sold_at,
            }
            for sale in position.sales
        ],
    }


def _current_unit_price(
    current_price: AuctionCurrentPrice | None,
) -> tuple[Decimal | None, str | None]:
    if current_price is None:
        return None, None
    if current_price.best_bid_unit_price is not None:
        return current_price.best_bid_unit_price, "best_bid"
    if current_price.best_buyout_unit_price is not None:
        return current_price.best_buyout_unit_price, "best_buyout"
    return None, None
