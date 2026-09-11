import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, settings
from app.db.database import SessionLocal
from app.services.auction_client import AuctionClient
from app.services.auction_sync import AuctionSyncService

logger = logging.getLogger(__name__)


class AuctionSyncRunner:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
        app_settings: Settings = settings,
        client_factory: Callable[[], AuctionClient] | None = None,
    ):
        self._session_factory = session_factory
        self._settings = app_settings
        self._client_factory = client_factory or self._make_client
        self._lock = asyncio.Lock()

    async def run(self) -> int:
        if self._lock.locked():
            return 0
        async with self._lock:
            client = self._client_factory()
            try:
                regions = _regions(self._settings.AUCTION_REGIONS)
                request_budget = self._settings.AUCTION_REQUESTS_PER_MINUTE // len(regions)
                async with self._session_factory() as db:
                    service = AuctionSyncService(
                        db,
                        client,
                        lots_refresh_minutes=self._settings.AUCTION_LOTS_REFRESH_MINUTES,
                        history_refresh_hours=self._settings.AUCTION_HISTORY_REFRESH_HOURS,
                    )
                    await service.ensure_recipe_candidates(regions)
                    return sum(
                        [await service.sync_due(region, request_budget) for region in regions]
                    )
            finally:
                await client.aclose()

    def _make_client(self) -> AuctionClient:
        return AuctionClient(
            base_url=self._settings.STALZONE_API_BASE_URL,
            requests_per_minute=self._settings.AUCTION_REQUESTS_PER_MINUTE,
        )


async def run_auction_scheduler(
    runner: AuctionSyncRunner,
    interval_minutes: int,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    while True:
        try:
            requests_used = await runner.run()
            logger.info("Auction synchronization completed with %s requests", requests_used)
        except Exception:
            logger.exception("Auction synchronization failed")
        await sleep(interval_minutes * 60)


async def stop_auction_scheduler(task: asyncio.Task[None]) -> None:
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def _regions(value: str) -> list[str]:
    regions = [region.strip().upper() for region in value.split(",") if region.strip()]
    if not regions:
        raise ValueError("AUCTION_REGIONS must contain at least one region")
    return regions
