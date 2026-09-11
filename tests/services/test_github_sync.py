from copy import deepcopy

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.hideout_recipe import HideoutRecipe
from app.models.item import Item
from app.models.sync_state import SyncState
from app.services.github_client import GitHubCommit, GitHubTreeEntry
from app.services.github_sync import (
    HIDEOUT_RECIPES_STATE_KEY,
    ITEMS_STATE_KEY,
    GitHubSyncError,
    GitHubSyncService,
)


def _translation(key: str, english: str) -> dict:
    return {"key": key, "lines": {"en": english, "ru": "Русский"}}


def _item_source(item_id: str = "tea") -> dict:
    return {
        "id": item_id,
        "category": "consumables",
        "name": _translation(f"items.{item_id}.name", item_id.title()),
        "infoBlocks": [],
    }


def _recipe_source(energy: int = 100) -> dict:
    return {
        "perks": [{"id": "cooking", "name": _translation("perks.cooking", "Cooking")}],
        "recipes": [
            {
                "bench": "kitchen_table",
                "category": _translation("categories.food", "Food"),
                "result": [{"item": "tea", "amount": 1}],
                "ingredients": [{"item": "water", "amount": 2}],
                "energy": energy,
                "requirements": {"perks": {"cooking": 1}, "features": ["kitchen_table"]},
            }
        ],
    }


class FakeGitHubClient:
    def __init__(self, tree: list[GitHubTreeEntry], raw_sources: dict[str, dict]):
        self.commit = GitHubCommit(sha="commit-1", tree_sha="tree-1")
        self.tree = tree
        self.raw_sources = raw_sources
        self.downloaded_paths: list[str] = []

    async def get_latest_commit(self, branch: str) -> GitHubCommit:
        assert branch == "main"
        return self.commit

    async def get_tree(self, tree_sha: str) -> list[GitHubTreeEntry]:
        assert tree_sha == self.commit.tree_sha
        return self.tree

    async def download_raw(self, commit_sha: str, path: str) -> dict:
        assert commit_sha == self.commit.sha
        self.downloaded_paths.append(path)
        return deepcopy(self.raw_sources[path])


def _service(db_session, client: FakeGitHubClient) -> GitHubSyncService:
    return GitHubSyncService(
        db=db_session,
        client=client,
        branch="main",
        items_path="global/items",
        hideout_recipes_path="global/hideout_recipes.json",
        download_concurrency=2,
    )


async def test_sync_downloads_sources_then_skips_unchanged_tree(db_session):
    item_path = "global/items/consumables/tea.json"
    recipe_path = "global/hideout_recipes.json"
    client = FakeGitHubClient(
        tree=[
            GitHubTreeEntry(path=item_path, sha="item-1"),
            GitHubTreeEntry(path="global/items/_variants/tea/1.json", sha="variant-1"),
            GitHubTreeEntry(path=recipe_path, sha="recipes-1"),
        ],
        raw_sources={item_path: _item_source(), recipe_path: _recipe_source()},
    )
    service = _service(db_session, client)

    result = await service.sync()

    assert result.items.added == 1
    assert result.hideout_recipes.added == 1
    assert client.downloaded_paths == [item_path, recipe_path]
    item = await db_session.get(Item, "tea")
    recipe = await db_session.scalar(
        select(HideoutRecipe)
        .options(selectinload(HideoutRecipe.components))
        .where(HideoutRecipe.source_index == 0)
    )
    assert item is not None
    assert recipe is not None
    assert {component.item_id for component in recipe.components} == {"tea", "water"}
    assert (await db_session.get(SyncState, ITEMS_STATE_KEY)).value == "tree-1"
    assert (await db_session.get(SyncState, HIDEOUT_RECIPES_STATE_KEY)).value == "recipes-1"

    unchanged = await service.sync()

    assert unchanged.items.skipped is True
    assert unchanged.hideout_recipes.skipped is True
    assert client.downloaded_paths == [item_path, recipe_path]


async def test_sync_refreshes_changed_recipe_blob_without_downloading_unchanged_item(db_session):
    item_path = "global/items/consumables/tea.json"
    recipe_path = "global/hideout_recipes.json"
    client = FakeGitHubClient(
        tree=[
            GitHubTreeEntry(path=item_path, sha="item-1"),
            GitHubTreeEntry(path=recipe_path, sha="recipes-1"),
        ],
        raw_sources={item_path: _item_source(), recipe_path: _recipe_source()},
    )
    service = _service(db_session, client)
    await service.sync()

    client.commit = GitHubCommit(sha="commit-2", tree_sha="tree-2")
    client.tree[1] = GitHubTreeEntry(path=recipe_path, sha="recipes-2")
    client.raw_sources[recipe_path] = _recipe_source(energy=250)

    result = await service.sync()

    assert result.items.added == 0
    assert result.items.updated == 0
    assert result.items.skipped is False
    assert result.hideout_recipes.added == 1
    assert result.hideout_recipes.deleted == 1
    assert client.downloaded_paths == [item_path, recipe_path, recipe_path]
    recipe = await db_session.scalar(select(HideoutRecipe).where(HideoutRecipe.source_index == 0))
    assert recipe is not None
    assert recipe.energy == 250


async def test_sync_rejects_duplicate_item_ids(db_session):
    first_path = "global/items/consumables/tea.json"
    second_path = "global/items/consumables/tea-copy.json"
    recipe_path = "global/hideout_recipes.json"
    client = FakeGitHubClient(
        tree=[
            GitHubTreeEntry(path=first_path, sha="item-1"),
            GitHubTreeEntry(path=second_path, sha="item-2"),
            GitHubTreeEntry(path=recipe_path, sha="recipes-1"),
        ],
        raw_sources={
            first_path: _item_source("tea"),
            second_path: _item_source("tea"),
            recipe_path: _recipe_source(),
        },
    )

    with pytest.raises(GitHubSyncError, match="appears in both"):
        await _service(db_session, client).sync()

    assert await db_session.get(Item, "tea") is None
