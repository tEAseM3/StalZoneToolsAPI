# app/api/routes/trading.py
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.trading import (
    ItemProfitResponse,
    PurchaseCreate,
    PurchaseResponse,
    SaleCreate,
    SaleResponse,
)
from app.services import trading_service

router = APIRouter(prefix="/trading", tags=["Trading"])


@router.post("/purchases", response_model=PurchaseResponse)
async def add_purchase(payload: PurchaseCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    return await trading_service.create_purchase(
        db,
        item_name=payload.item_name,
        quantity=payload.quantity,
        total_price=payload.total_price,
        purchased_at=payload.purchased_at,
    )


@router.post("/sales", response_model=SaleResponse)
async def add_sale(payload: SaleCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    return await trading_service.create_sale(
        db,
        item_name=payload.item_name,
        quantity=payload.quantity,
        total_price=payload.total_price,
        sold_at=payload.sold_at,
    )


@router.get("/items/{item_name}/profit", response_model=ItemProfitResponse)
async def get_profit(item_name: str, db: Annotated[AsyncSession, Depends(get_db)]):
    return await trading_service.get_item_profit(db, item_name)
