# app/services/trading_service.py
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.purchase import Purchase
from app.models.sale import Sale
from app.schemas.trading import ItemProfitResponse


async def create_purchase(
    db: AsyncSession,
    item_name: str,
    quantity: int,
    total_price: Decimal,
    purchased_at: datetime | None,
) -> Purchase:
    purchase = Purchase(
        item_name=item_name,
        quantity=quantity,
        total_price=total_price,
        **({"purchased_at": purchased_at} if purchased_at is not None else {}),
    )
    db.add(purchase)
    await db.commit()
    await db.refresh(purchase)
    return purchase


async def create_sale(
    db: AsyncSession,
    item_name: str,
    quantity: int,
    total_price: Decimal,
    sold_at: datetime | None,
) -> Sale:
    sale = Sale(
        item_name=item_name,
        quantity=quantity,
        total_price=total_price,
        **({"sold_at": sold_at} if sold_at is not None else {}),
    )
    db.add(sale)
    await db.commit()
    await db.refresh(sale)
    return sale


async def get_item_profit(db: AsyncSession, item_name: str) -> ItemProfitResponse:
    bought_quantity, bought_cost_total = (
        await db.execute(
            select(
                func.coalesce(func.sum(Purchase.quantity), 0),
                func.coalesce(func.sum(Purchase.total_price), 0),
            ).where(Purchase.item_name == item_name)
        )
    ).one()

    sold_quantity, sold_revenue_total = (
        await db.execute(
            select(
                func.coalesce(func.sum(Sale.quantity), 0),
                func.coalesce(func.sum(Sale.total_price), 0),
            ).where(Sale.item_name == item_name)
        )
    ).one()

    avg_unit_cost = Decimal(bought_cost_total) / bought_quantity if bought_quantity > 0 else None
    remaining_stock = bought_quantity - sold_quantity
    remaining_stock_value = avg_unit_cost * remaining_stock if avg_unit_cost is not None else None
    cost_of_sold = avg_unit_cost * sold_quantity if avg_unit_cost is not None else Decimal(0)
    realized_profit = Decimal(sold_revenue_total) - cost_of_sold

    return ItemProfitResponse(
        item_name=item_name,
        bought_quantity=bought_quantity,
        bought_cost_total=Decimal(bought_cost_total),
        avg_unit_cost=avg_unit_cost,
        sold_quantity=sold_quantity,
        sold_revenue_total=Decimal(sold_revenue_total),
        remaining_stock=remaining_stock,
        remaining_stock_value=remaining_stock_value,
        realized_profit=realized_profit,
    )
