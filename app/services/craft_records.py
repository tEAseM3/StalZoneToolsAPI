from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions.base import ConflictError, NotFoundError
from app.models.auction_current_price import AuctionCurrentPrice
from app.models.craft_profit_snapshot import CraftProfitSnapshot
from app.models.craft_record import CraftRecord
from app.models.craft_sale import CraftSale
from app.models.hideout_recipe import HideoutRecipe
from app.models.hideout_recipe_item import HideoutRecipeItem
from app.models.item import Item
from app.schemas.craft_records import CraftRecordCreate, CraftSaleCreate

AUCTION_SELL_COMMISSION = Decimal("0.05")


async def create_record(db: AsyncSession, user_id: int, data: CraftRecordCreate) -> dict:
    item = await _find_item(db, data.item_name)
    market_price = await _market_price(db, item.id)
    recipe_unit_cost = await _recipe_unit_cost(db, item.id)
    if recipe_unit_cost is None and market_price is None:
        raise ConflictError("No current price is available for this item")
    unit_cost = market_price if market_price is not None else recipe_unit_cost
    cost_source = "market" if market_price is not None else "recipe"
    record = CraftRecord(
        user_id=user_id,
        item_id=item.id,
        item_name=item.name,
        quantity=data.quantity,
        unit_cost=unit_cost,
        cost_source=cost_source,
        market_unit_price=market_price,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record, attribute_names=["sales"])
    return _record_view(record)


async def add_sale(
    db: AsyncSession, user_id: int, record_id: int, data: CraftSaleCreate
) -> dict:
    record = await db.scalar(
        select(CraftRecord)
        .where(CraftRecord.id == record_id, CraftRecord.user_id == user_id)
        .options(selectinload(CraftRecord.sales))
        .with_for_update()
    )
    if record is None:
        raise NotFoundError("Craft record was not found")
    sold_quantity = sum(sale.quantity for sale in record.sales)
    if data.quantity > record.quantity - sold_quantity:
        raise ConflictError(f"Only {record.quantity - sold_quantity} item(s) remain in this record")
    record.sales.append(CraftSale(quantity=data.quantity, unit_price=data.unit_price))
    await db.commit()
    return _record_view(record)


async def list_records(db: AsyncSession, user_id: int) -> dict:
    records = (
        await db.scalars(
            select(CraftRecord)
            .where(CraftRecord.user_id == user_id)
            .options(selectinload(CraftRecord.sales))
            .order_by(CraftRecord.created_at.desc())
        )
    ).all()
    return {"records": [_record_view(record) for record in records]}


async def suggestions(db: AsyncSession, user_id: int, query: str) -> list[str]:
    return (
        await db.scalars(
            select(CraftRecord.item_name)
            .where(CraftRecord.user_id == user_id, CraftRecord.item_name.ilike(f"%{query}%"))
            .distinct()
            .order_by(CraftRecord.item_name)
            .limit(10)
        )
    ).all()


async def _find_item(db: AsyncSession, name: str) -> Item:
    items = (await db.scalars(select(Item).where(Item.name.ilike(name)).limit(2))).all()
    if not items:
        raise NotFoundError("Item with this exact name was not found")
    if len(items) > 1:
        raise ConflictError("Several items have this name; use the exact full name")
    return items[0]


async def _market_price(db: AsyncSession, item_id: str) -> Decimal | None:
    current = await db.get(AuctionCurrentPrice, {"region": "EU", "item_id": item_id})
    if current is None:
        return None
    return current.best_buyout_unit_price or current.best_bid_unit_price


async def _recipe_unit_cost(db: AsyncSession, item_id: str) -> Decimal | None:
    recipes = (
        await db.scalars(
            select(HideoutRecipe)
            .join(HideoutRecipeItem)
            .where(
                HideoutRecipeItem.component_type == "result",
                HideoutRecipeItem.item_id == item_id,
            )
            .options(selectinload(HideoutRecipe.components))
            .distinct()
        )
    ).unique().all()
    costs = []
    for recipe in recipes:
        snapshot = await db.get(CraftProfitSnapshot, {"recipe_id": recipe.id, "region": "EU"})
        result_quantity = sum(
            (
                component.amount
                for component in recipe.components
                if component.component_type == "result" and component.item_id == item_id
            ),
            Decimal(0),
        )
        if (
            snapshot
            and snapshot.has_complete_prices
            and snapshot.total_cost is not None
            and result_quantity
        ):
            costs.append(snapshot.total_cost / result_quantity)
    return min(costs, default=None)


def _record_view(record: CraftRecord) -> dict:
    sold_quantity = sum(sale.quantity for sale in record.sales)
    gross_revenue = sum((sale.unit_price * sale.quantity for sale in record.sales), Decimal(0))
    auction_fee = gross_revenue * AUCTION_SELL_COMMISSION
    revenue = gross_revenue - auction_fee
    cost_of_sold = record.unit_cost * sold_quantity
    total_cost = record.unit_cost * record.quantity
    return {
        "id": record.id,
        "item_id": record.item_id,
        "item_name": record.item_name,
        "quantity": record.quantity,
        "unit_cost": record.unit_cost,
        "total_cost": total_cost,
        "cost_source": record.cost_source,
        "market_unit_price": record.market_unit_price,
        "sold_quantity": sold_quantity,
        "remaining_quantity": record.quantity - sold_quantity,
        "gross_revenue": gross_revenue,
        "auction_fee": auction_fee,
        "net_revenue": revenue,
        "realized_profit": revenue - cost_of_sold,
        "created_at": record.created_at,
        "sales": [
            {
                "id": sale.id,
                "quantity": sale.quantity,
                "unit_price": sale.unit_price,
                "revenue": sale.unit_price * sale.quantity,
                "sold_at": sale.sold_at,
            }
            for sale in record.sales
        ],
    }
