from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_permissions
from app.db.database import get_db
from app.services import market

router = APIRouter(tags=["Market"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
ItemMarketAccess = Annotated[object, Depends(require_permissions("items:read", "auction:read"))]
CraftMarketAccess = Annotated[object, Depends(require_permissions("hideout:read", "auction:read"))]


@router.get("/market/items")
async def find_items(
    name: Annotated[str, Query(min_length=1, max_length=255)],
    region: Literal["RU", "EU", "NA", "SEA", "NEA"],
    page: Annotated[int, Query(ge=1)] = 1,
    db: DbSession = None,
    _: ItemMarketAccess = None,
):
    return await market.search_items(db, region, name, page)


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
