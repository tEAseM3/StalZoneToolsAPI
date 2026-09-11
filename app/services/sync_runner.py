import asyncio
import contextlib
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, settings
from app.db.database import SessionLocal
from app.models.sync_state import SyncState
from app.services.github_client import GitHubClient
from app.services.github_sync import GitHubSyncResult, GitHubSyncService, SourceSyncResult

logger = logging.getLogger(__name__)

SYNC_RUN_STATUS_STATE_KEY = "github_sync_run_status"


class SyncAlreadyRunningError(RuntimeError):
    """Raised when a second synchronization starts before the prior one finishes."""


@dataclass(frozen=True)
class SyncRunStatus:
    started_at: str | None = None
    finished_at: str | None = None
    is_running: bool = False
    error: str | None = None
    items: dict[str, Any] | None = None
    hideout_recipes: dict[str, Any] | None = None


SyncServiceFactory = Callable[[AsyncSession, GitHubClient], GitHubSyncService]


class GitHubSyncRunner:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
        app_settings: Settings = settings,
        client_factory: Callable[[], GitHubClient] | None = None,
        service_factory: SyncServiceFactory | None = None,
    ):
        self._session_factory = session_factory
        self._settings = app_settings
        self._client_factory = client_factory or self._make_client
        self._service_factory = service_factory or self._make_service
        self._lock = asyncio.Lock()

    async def run(self) -> GitHubSyncResult:
        if self._lock.locked():
            raise SyncAlreadyRunningError("GitHub item synchronization is already running")

        async with self._lock:
            started_at = _now()
            await self._save_status(SyncRunStatus(started_at=started_at, is_running=True))
            client = self._client_factory()
            try:
                async with self._session_factory() as db:
                    result = await self._service_factory(db, client).sync()
                await self._save_status(_success_status(started_at, result))
                logger.info(
                    "GitHub sources synchronized: items=%s recipes=%s",
                    result.items,
                    result.hideout_recipes,
                )
                return result
            except Exception as exc:
                logger.exception("GitHub source synchronization failed")
                await self._save_status(
                    SyncRunStatus(
                        started_at=started_at,
                        finished_at=_now(),
                        error=str(exc),
                    )
                )
                raise
            finally:
                await client.aclose()

    def _make_client(self) -> GitHubClient:
        return GitHubClient(
            repository=self._settings.GITHUB_REPOSITORY,
            token=self._settings.GITHUB_TOKEN,
        )

    def _make_service(self, db: AsyncSession, client: GitHubClient) -> GitHubSyncService:
        return GitHubSyncService(
            db=db,
            client=client,
            branch=self._settings.GITHUB_BRANCH,
            items_path=self._settings.GITHUB_ITEMS_PATH,
            hideout_recipes_path=self._settings.GITHUB_HIDEOUT_RECIPES_PATH,
            download_concurrency=self._settings.SYNC_DOWNLOAD_CONCURRENCY,
        )

    async def _save_status(self, status: SyncRunStatus) -> None:
        async with self._session_factory() as db:
            state = await db.get(SyncState, SYNC_RUN_STATUS_STATE_KEY)
            serialized = json.dumps(asdict(status), separators=(",", ":"))
            if state is None:
                db.add(SyncState(key=SYNC_RUN_STATUS_STATE_KEY, value=serialized))
            else:
                state.value = serialized
            await db.commit()


async def get_last_sync_status(db: AsyncSession) -> SyncRunStatus | None:
    state = await db.get(SyncState, SYNC_RUN_STATUS_STATE_KEY)
    if state is None:
        return None
    try:
        payload = json.loads(state.value)
        return SyncRunStatus(**payload)
    except TypeError, json.JSONDecodeError:
        logger.warning("Stored GitHub sync status has an invalid format")
        return None


async def run_sync_scheduler(
    runner: GitHubSyncRunner,
    interval_hours: int,
    run_on_startup: bool,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    if run_on_startup:
        await _run_once(runner)

    while True:
        await sleep(interval_hours * 60 * 60)
        await _run_once(runner)


async def _run_once(runner: GitHubSyncRunner) -> None:
    try:
        await runner.run()
    except SyncAlreadyRunningError:
        logger.warning("Skipped scheduled GitHub synchronization because another run is active")
    except Exception:
        # The runner persists the error. The scheduler must keep the API process alive.
        logger.exception("Scheduled GitHub synchronization failed")


def _success_status(started_at: str, result: GitHubSyncResult) -> SyncRunStatus:
    return SyncRunStatus(
        started_at=started_at,
        finished_at=_now(),
        items=_source_result_as_dict(result.items),
        hideout_recipes=_source_result_as_dict(result.hideout_recipes),
    )


def _source_result_as_dict(result: SourceSyncResult) -> dict[str, Any]:
    return asdict(result)


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def stop_scheduler(task: asyncio.Task[None]) -> None:
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
