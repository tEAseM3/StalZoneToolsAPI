import asyncio
from contextlib import asynccontextmanager

import pytest

from app.services.github_sync import GitHubSyncResult, SourceSyncResult
from app.services.sync_runner import (
    GitHubSyncRunner,
    get_last_sync_status,
    run_sync_scheduler,
)


class FakeClient:
    def __init__(self):
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class SuccessfulSyncService:
    async def sync(self) -> GitHubSyncResult:
        return GitHubSyncResult(
            items=SourceSyncResult(added=2),
            hideout_recipes=SourceSyncResult(added=3),
        )


class FailingSyncService:
    async def sync(self) -> GitHubSyncResult:
        raise RuntimeError("GitHub is unavailable")


def _session_factory(db_session):
    @asynccontextmanager
    async def factory():
        yield db_session

    return factory


async def test_runner_persists_success_status(db_session):
    client = FakeClient()
    runner = GitHubSyncRunner(
        session_factory=_session_factory(db_session),
        client_factory=lambda: client,
        service_factory=lambda db, sync_client: SuccessfulSyncService(),
    )

    result = await runner.run()
    status = await get_last_sync_status(db_session)

    assert result.items.added == 2
    assert status is not None
    assert status.is_running is False
    assert status.error is None
    assert status.items == {"added": 2, "updated": 0, "deleted": 0, "skipped": False}
    assert status.hideout_recipes == {"added": 3, "updated": 0, "deleted": 0, "skipped": False}
    assert client.closed is True


async def test_runner_persists_failure_status_and_reraises(db_session):
    client = FakeClient()
    runner = GitHubSyncRunner(
        session_factory=_session_factory(db_session),
        client_factory=lambda: client,
        service_factory=lambda db, sync_client: FailingSyncService(),
    )

    with pytest.raises(RuntimeError, match="GitHub is unavailable"):
        await runner.run()

    status = await get_last_sync_status(db_session)
    assert status is not None
    assert status.is_running is False
    assert status.error == "GitHub is unavailable"
    assert status.finished_at is not None
    assert client.closed is True


async def test_scheduler_runs_immediately_then_waits_for_next_interval():
    class FakeRunner:
        def __init__(self):
            self.calls = 0

        async def run(self) -> GitHubSyncResult:
            self.calls += 1
            return GitHubSyncResult(SourceSyncResult(), SourceSyncResult())

    runner = FakeRunner()

    async def sleep(_: float) -> None:
        await asyncio.Event().wait()

    task = asyncio.create_task(run_sync_scheduler(runner, 24, True, sleep))
    while runner.calls == 0:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert runner.calls == 1
