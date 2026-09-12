from datetime import datetime

from pydantic import BaseModel, Field


class TradePositionCreate(BaseModel):
    item_name: str = Field(min_length=1, max_length=255)
    quantity: int = Field(gt=0)
    purchase_total: int = Field(ge=0)
    purchased_at: datetime | None = None


class TradeSaleCreate(BaseModel):
    quantity: int = Field(gt=0)
    revenue_total: int = Field(ge=0)
    sold_at: datetime | None = None
