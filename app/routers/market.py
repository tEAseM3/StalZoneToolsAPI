from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_permissions
from app.db.database import get_db
from app.models.user import User
from app.schemas.craft_records import CraftRecordCreate, CraftSaleCreate
from app.services import craft_records, market

router = APIRouter(tags=["Market"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
ItemMarketAccess = Annotated[object, Depends(require_permissions("items:read", "auction:read"))]
CraftMarketAccess = Annotated[object, Depends(require_permissions("hideout:read", "auction:read"))]
TradingReadAccess = Annotated[User, Depends(require_permissions("trading:read"))]
TradingWriteAccess = Annotated[User, Depends(require_permissions("trading:write"))]


@router.get("/market/items")
async def find_items(
    name: Annotated[str, Query(min_length=1, max_length=255)],
    page: Annotated[int, Query(ge=1)] = 1,
    db: DbSession = None,
    _: ItemMarketAccess = None,
):
    return await market.search_items(db, name, page)


@router.get("/market/items/top")
async def get_top_buy_items(
    sort: Literal["score", "price", "discount", "volume"] = "score",
    order: Literal["asc", "desc"] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    db: DbSession = None,
    _: ItemMarketAccess = None,
):
    return await market.top_buy_items(db, sort, order, page)


@router.get("/market/items/profitable")
async def get_profitable_buy_items(
    sort: Literal["profit", "margin", "price", "volume"] = "profit",
    order: Literal["asc", "desc"] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    db: DbSession = None,
    _: ItemMarketAccess = None,
):
    return await market.profitable_buy_items(db, sort, order, page)


@router.get("/hideout/crafts")
async def find_crafts(
    name: Annotated[str, Query(min_length=1, max_length=255)],
    page: Annotated[int, Query(ge=1)] = 1,
    db: DbSession = None,
    _: CraftMarketAccess = None,
):
    return await market.search_crafts(db, name, page)


@router.get("/hideout/crafts/top")
async def get_top_crafts(
    sort: Literal["profit", "margin", "cost", "price"] = "profit",
    order: Literal["asc", "desc"] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    db: DbSession = None,
    _: CraftMarketAccess = None,
):
    return await market.top_crafts(db, sort, order, page)


@router.get("/craft-records")
async def get_craft_records(
    db: DbSession = None,
    current_user: TradingReadAccess = None,
):
    return await craft_records.list_records(db, current_user.id)


@router.get("/craft-records/suggestions")
async def get_craft_record_suggestions(
    query: Annotated[str, Query(min_length=1, max_length=255)],
    db: DbSession = None,
    current_user: TradingReadAccess = None,
):
    return {"items": await craft_records.suggestions(db, current_user.id, query)}


@router.post("/craft-records")
async def create_craft_record(
    data: CraftRecordCreate,
    db: DbSession = None,
    current_user: TradingWriteAccess = None,
):
    return await craft_records.create_record(db, current_user.id, data)


@router.post("/craft-records/{record_id}/sales")
async def create_craft_sale(
    record_id: int,
    data: CraftSaleCreate,
    db: DbSession = None,
    current_user: TradingWriteAccess = None,
):
    return await craft_records.add_sale(db, current_user.id, record_id, data)
