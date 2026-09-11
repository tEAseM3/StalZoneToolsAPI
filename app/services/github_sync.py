import asyncio
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.hideout_perk import HideoutPerk
from app.models.hideout_recipe import HideoutRecipe
from app.models.hideout_recipe_item import HideoutRecipeItem
from app.models.item import Item
from app.models.item_attribute import ItemAttribute
from app.models.sync_state import SyncState
from app.services.github_client import GitHubClient, GitHubTreeEntry
from app.services.hideout_recipe_parser import parse_hideout_recipes
from app.services.item_parser import parse_item

ITEMS_STATE_KEY = "github_items_tree_sha"
HIDEOUT_RECIPES_STATE_KEY = "github_hideout_recipes_blob_sha"


class GitHubSyncError(RuntimeError):
    """Raised when a GitHub source cannot safely be applied to the database."""


@dataclass(frozen=True)
class SourceSyncResult:
    added: int = 0
    updated: int = 0
    deleted: int = 0
    skipped: bool = False


@dataclass(frozen=True)
class GitHubSyncResult:
    items: SourceSyncResult
    hideout_recipes: SourceSyncResult


class GitHubSyncService:
    def __init__(
        self,
        db: AsyncSession,
        client: GitHubClient,
        branch: str,
        items_path: str,
        hideout_recipes_path: str,
        download_concurrency: int,
    ):
        self.db = db
        self.client = client
        self.branch = branch
        self.items_path = items_path.rstrip("/")
        self.hideout_recipes_path = hideout_recipes_path
        self.download_concurrency = download_concurrency

    async def sync(self) -> GitHubSyncResult:
        commit = await self.client.get_latest_commit(self.branch)
        tree = await self.client.get_tree(commit.tree_sha)
        item_entries = _find_item_entries(tree, self.items_path)
        hideout_entry = _find_tree_entry(tree, self.hideout_recipes_path)
        if hideout_entry is None:
            raise GitHubSyncError(
                f"Hideout recipe source '{self.hideout_recipes_path}' was not found in GitHub tree"
            )

        items_result = await self._sync_items(commit.sha, commit.tree_sha, item_entries)
        recipes_result = await self._sync_hideout_recipes(commit.sha, hideout_entry)
        return GitHubSyncResult(items=items_result, hideout_recipes=recipes_result)

    async def _sync_items(
        self, commit_sha: str, tree_sha: str, entries: list[GitHubTreeEntry]
    ) -> SourceSyncResult:
        state = await self.db.get(SyncState, ITEMS_STATE_KEY)
        if state is not None and state.value == tree_sha:
            return SourceSyncResult(skipped=True)

        existing_items = (
            await self.db.scalars(select(Item).options(selectinload(Item.attributes)))
        ).all()
        existing_by_path = {item.source_path: item for item in existing_items}
        entry_paths = {entry.path for entry in entries}
        entries_to_download = [
            entry
            for entry in entries
            if entry.path not in existing_by_path
            or existing_by_path[entry.path].source_sha != entry.sha
        ]
        downloaded = await self._download_items(commit_sha, entries_to_download)
        self._validate_item_ids(downloaded, existing_by_path, entry_paths)

        deleted_paths = set(existing_by_path) - entry_paths
        if deleted_paths:
            await self.db.execute(delete(Item).where(Item.source_path.in_(deleted_paths)))
            await self.db.flush()

        added = 0
        updated = 0
        for entry, parsed in downloaded:
            existing = existing_by_path.get(entry.path)
            if existing is None:
                self.db.add(_make_item(entry, parsed))
                added += 1
            elif existing.id != parsed.id:
                await self.db.delete(existing)
                await self.db.flush()
                self.db.add(_make_item(entry, parsed))
                updated += 1
            else:
                _update_item(existing, entry, parsed)
                updated += 1

        await self._set_state(ITEMS_STATE_KEY, tree_sha)
        await self.db.commit()
        return SourceSyncResult(added=added, updated=updated, deleted=len(deleted_paths))

    async def _sync_hideout_recipes(
        self, commit_sha: str, entry: GitHubTreeEntry
    ) -> SourceSyncResult:
        state = await self.db.get(SyncState, HIDEOUT_RECIPES_STATE_KEY)
        if state is not None and state.value == entry.sha:
            return SourceSyncResult(skipped=True)

        raw_source = await self.client.download_raw(commit_sha, entry.path)
        parsed_source = parse_hideout_recipes(raw_source)
        previous_count = await self.db.scalar(select(func.count()).select_from(HideoutRecipe))
        await self.db.execute(delete(HideoutRecipe))
        await self.db.execute(delete(HideoutPerk))
        await self.db.flush()

        self.db.add_all(
            [
                HideoutPerk(
                    id=perk.id,
                    name=perk.name,
                    description=perk.description,
                    raw=perk.raw,
                )
                for perk in parsed_source.perks
            ]
        )
        for recipe in parsed_source.recipes:
            model = HideoutRecipe(
                source_index=recipe.source_index,
                bench=recipe.bench,
                category_key=recipe.category_key,
                category_name=recipe.category_name,
                subcategory_key=recipe.subcategory_key,
                subcategory_name=recipe.subcategory_name,
                energy=recipe.energy,
                required_perks=recipe.required_perks,
                required_features=recipe.required_features,
                raw=recipe.raw,
                source_sha=entry.sha,
            )
            model.components = [
                HideoutRecipeItem(
                    component_type=component.component_type,
                    item_id=component.item_id,
                    amount=component.amount,
                    sort_order=component.sort_order,
                )
                for component in recipe.components
            ]
            self.db.add(model)

        await self._set_state(HIDEOUT_RECIPES_STATE_KEY, entry.sha)
        await self.db.commit()
        return SourceSyncResult(added=len(parsed_source.recipes), deleted=previous_count or 0)

    async def _download_items(
        self, commit_sha: str, entries: list[GitHubTreeEntry]
    ) -> list[tuple[GitHubTreeEntry, Any]]:
        semaphore = asyncio.Semaphore(self.download_concurrency)

        async def download(entry: GitHubTreeEntry) -> tuple[GitHubTreeEntry, Any]:
            async with semaphore:
                raw_item = await self.client.download_raw(commit_sha, entry.path)
            return entry, parse_item(raw_item)

        return await asyncio.gather(*(download(entry) for entry in entries))

    def _validate_item_ids(
        self,
        downloaded: list[tuple[GitHubTreeEntry, Any]],
        existing_by_path: dict[str, Item],
        entry_paths: set[str],
    ) -> None:
        ids_by_path: dict[str, str] = {
            path: item.id for path, item in existing_by_path.items() if path in entry_paths
        }
        for entry, parsed in downloaded:
            ids_by_path[entry.path] = parsed.id

        seen: dict[str, str] = {}
        for path, item_id in ids_by_path.items():
            previous_path = seen.get(item_id)
            if previous_path is not None and previous_path != path:
                raise GitHubSyncError(
                    f"Item id '{item_id}' appears in both '{previous_path}' and '{path}'"
                )
            seen[item_id] = path

    async def _set_state(self, key: str, value: str) -> None:
        state = await self.db.get(SyncState, key)
        if state is None:
            self.db.add(SyncState(key=key, value=value))
        else:
            state.value = value


def _find_item_entries(entries: list[GitHubTreeEntry], items_path: str) -> list[GitHubTreeEntry]:
    prefix = f"{items_path}/"
    return [
        entry
        for entry in entries
        if entry.path.startswith(prefix)
        and entry.path.endswith(".json")
        and "/_variants/" not in entry.path
    ]


def _find_tree_entry(entries: list[GitHubTreeEntry], path: str) -> GitHubTreeEntry | None:
    return next((entry for entry in entries if entry.path == path), None)


def _make_item(entry: GitHubTreeEntry, parsed: Any) -> Item:
    item = Item(
        id=parsed.id,
        source_path=entry.path,
        category=parsed.category,
        name=parsed.name,
        description=parsed.description,
        color=parsed.color,
        status_state=parsed.status_state,
        raw=parsed.raw,
        source_sha=entry.sha,
    )
    item.attributes = _make_item_attributes(parsed)
    return item


def _update_item(item: Item, entry: GitHubTreeEntry, parsed: Any) -> None:
    item.category = parsed.category
    item.name = parsed.name
    item.description = parsed.description
    item.color = parsed.color
    item.status_state = parsed.status_state
    item.raw = parsed.raw
    item.source_sha = entry.sha
    item.attributes = _make_item_attributes(parsed)


def _make_item_attributes(parsed: Any) -> list[ItemAttribute]:
    return [
        ItemAttribute(
            key=attribute.key,
            label=attribute.label,
            value_text=attribute.value_text,
            value_numeric=attribute.value_numeric,
            unit_label=attribute.unit_label,
            sort_order=attribute.sort_order,
        )
        for attribute in parsed.attributes
    ]
