from decimal import Decimal

from pydantic import BaseModel, Field


class CraftRecordCreate(BaseModel):
    item_name: str = Field(min_length=1, max_length=255)
    quantity: int = Field(gt=0)


class CraftSaleCreate(BaseModel):
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0, max_digits=20, decimal_places=4)
