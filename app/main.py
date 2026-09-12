import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import app.db.base_models  # noqa: F401
from app.core.config import settings
from app.exceptions.base import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.routers import auth, market, trading, user
from app.services.auction_runner import (
    AuctionSyncRunner,
    run_auction_scheduler,
    stop_auction_scheduler,
)
from app.services.sync_runner import GitHubSyncRunner, run_sync_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    runner = GitHubSyncRunner()
    scheduler_task = asyncio.create_task(
        run_sync_scheduler(
            runner,
            interval_hours=settings.SYNC_INTERVAL_HOURS,
            run_on_startup=settings.SYNC_RUN_ON_STARTUP,
        )
    )
    auction_scheduler_task = asyncio.create_task(
        run_auction_scheduler(
            AuctionSyncRunner(),
            interval_minutes=settings.AUCTION_SYNC_INTERVAL_MINUTES,
        )
    )
    app.state.sync_runner = runner
    app.state.sync_scheduler_task = scheduler_task
    app.state.auction_scheduler_task = auction_scheduler_task
    try:
        yield
    finally:
        await stop_scheduler(scheduler_task)
        await stop_auction_scheduler(auction_scheduler_task)


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(market.router)
app.include_router(trading.router)


@app.exception_handler(NotFoundError)
def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
def conflict_handler(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ForbiddenError)
def forbidden_handler(request: Request, exc: ForbiddenError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(UnauthorizedError)
def unauthorized_handler(request: Request, exc: UnauthorizedError):
    return JSONResponse(status_code=401, content={"detail": str(exc)})
