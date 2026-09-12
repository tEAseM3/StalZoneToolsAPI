# app/schemas/trading.py
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PurchaseCreate(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., gt=0)
    total_price: Decimal = Field(..., gt=0)
    purchased_at: datetime | None = None  # None -> сервер поставит "сейчас"


class PurchaseResponse(BaseModel):
    id: int
    item_name: str
    quantity: int
    total_price: Decimal
    purchased_at: datetime

    class Config:
        from_attributes = True


class SaleCreate(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., gt=0)
    total_price: Decimal = Field(..., gt=0)
    sold_at: datetime | None = None


class SaleResponse(BaseModel):
    id: int
    item_name: str
    quantity: int
    total_price: Decimal
    sold_at: datetime

    class Config:
        from_attributes = True


class ItemProfitResponse(BaseModel):
    item_name: str
    bought_quantity: int
    bought_cost_total: Decimal
    avg_unit_cost: Decimal | None
    sold_quantity: int
    sold_revenue_total: Decimal
    remaining_stock: int
    remaining_stock_value: Decimal | None
    realized_profit: Decimal
