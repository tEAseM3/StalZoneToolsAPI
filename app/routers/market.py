from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_permissions
from app.db.database import get_db
from app.models.user import User
from app.schemas.portfolio import TradePositionCreate, TradeSaleCreate
from app.services import market, portfolio

router = APIRouter(tags=["Market"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
ItemMarketAccess = Annotated[object, Depends(require_permissions("items:read", "auction:read"))]
CraftMarketAccess = Annotated[object, Depends(require_permissions("hideout:read", "auction:read"))]
PortfolioReadAccess = Annotated[User, Depends(require_permissions("portfolio:read"))]
PortfolioWriteAccess = Annotated[User, Depends(require_permissions("portfolio:write"))]


@router.get("/market/items")
async def find_items(
    name: Annotated[str, Query(min_length=1, max_length=255)],
    region: Literal["RU", "EU", "NA", "SEA", "NEA"],
    page: Annotated[int, Query(ge=1)] = 1,
    db: DbSession = None,
    _: ItemMarketAccess = None,
):
    return await market.search_items(db, region, name, page)


@router.get("/market/items/top")
async def get_top_buy_items(
    region: Literal["EU"] = "EU",
    page: Annotated[int, Query(ge=1)] = 1,
    db: DbSession = None,
    _: ItemMarketAccess = None,
):
    return await market.top_buy_items(db, region, page)


@router.get("/market/items/{item_id}")
async def get_item_market(
    item_id: str,
    region: Literal["RU", "EU", "NA", "SEA", "NEA"],
    interval: Literal["day", "week"] = "day",
    db: DbSession = None,
    _: ItemMarketAccess = None,
):
    result = await market.item_market_details(db, region, item_id, interval)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return result


@router.get("/market/positions")
async def get_trade_positions(
    db: DbSession = None,
    current_user: PortfolioReadAccess = None,
):
    return await portfolio.list_positions(db, current_user.id, "EU")


@router.post("/market/positions", status_code=status.HTTP_201_CREATED)
async def create_trade_position(
    data: TradePositionCreate,
    db: DbSession = None,
    current_user: PortfolioWriteAccess = None,
):
    return await portfolio.create_position(db, current_user.id, "EU", data)


@router.post("/market/positions/{position_id}/sales", status_code=status.HTTP_201_CREATED)
async def record_trade_sale(
    position_id: int,
    data: TradeSaleCreate,
    db: DbSession = None,
    current_user: PortfolioWriteAccess = None,
):
    return await portfolio.add_sale(db, current_user.id, position_id, data)


@router.get("/hideout/crafts")
async def find_crafts(
    name: Annotated[str, Query(min_length=1, max_length=255)],
    region: Literal["RU", "EU", "NA", "SEA", "NEA"],
    page: Annotated[int, Query(ge=1)] = 1,
    db: DbSession = None,
    _: CraftMarketAccess = None,
):
    return await market.search_crafts(db, region, name, page)


@router.get("/hideout/crafts/top")
async def get_top_crafts(
    region: Literal["RU", "EU", "NA", "SEA", "NEA"],
    page: Annotated[int, Query(ge=1)] = 1,
    db: DbSession = None,
    _: CraftMarketAccess = None,
):
    return await market.top_crafts(db, region, page)


@router.get("/hideout/crafts/{recipe_id}/chain")
async def get_craft_chain(
    recipe_id: int,
    region: Literal["RU", "EU", "NA", "SEA", "NEA"],
    db: DbSession = None,
    _: CraftMarketAccess = None,
):
    result = await market.craft_chain(db, region, recipe_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return result


@router.get("/hideout/crafts/reprocess")
async def get_reprocess_options(
    item_id: str,
    region: Literal["RU", "EU", "NA", "SEA", "NEA"],
    db: DbSession = None,
    _: CraftMarketAccess = None,
):
    return {"item_id": item_id, "crafts": await market.reprocess_options(db, region, item_id)}
