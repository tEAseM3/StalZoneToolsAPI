from dataclasses import dataclass
from typing import Any

import httpx


class GitHubClientError(RuntimeError):
    """Raised when the GitHub API or raw-content endpoint cannot be read."""


@dataclass(frozen=True)
class GitHubCommit:
    sha: str
    tree_sha: str


@dataclass(frozen=True)
class GitHubTreeEntry:
    path: str
    sha: str


class GitHubClient:
    api_base_url = "https://api.github.com"
    raw_base_url = "https://raw.githubusercontent.com"

    def __init__(
        self,
        repository: str,
        token: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.repository = repository
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        self._owns_client = client is None
        self._headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_latest_commit(self, branch: str) -> GitHubCommit:
        payload = await self._get_json(f"/repos/{self.repository}/commits/{branch}")
        try:
            return GitHubCommit(sha=payload["sha"], tree_sha=payload["commit"]["tree"]["sha"])
        except (KeyError, TypeError) as exc:
            raise GitHubClientError("GitHub returned an invalid commit payload") from exc

    async def get_tree(self, tree_sha: str) -> list[GitHubTreeEntry]:
        payload = await self._get_json(
            f"/repos/{self.repository}/git/trees/{tree_sha}", params={"recursive": "1"}
        )
        tree = payload.get("tree") if isinstance(payload, dict) else None
        if not isinstance(tree, list):
            raise GitHubClientError("GitHub returned an invalid tree payload")

        entries: list[GitHubTreeEntry] = []
        for entry in tree:
            if not isinstance(entry, dict) or entry.get("type") != "blob":
                continue
            path, sha = entry.get("path"), entry.get("sha")
            if isinstance(path, str) and isinstance(sha, str):
                entries.append(GitHubTreeEntry(path=path, sha=sha))
        return entries

    async def download_raw(self, commit_sha: str, path: str) -> dict[str, Any]:
        url = f"{self.raw_base_url}/{self.repository}/{commit_sha}/{path}"
        try:
            response = await self._client.get(url, headers=self._headers)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GitHubClientError(f"Unable to download GitHub source '{path}'") from exc
        if not isinstance(payload, dict):
            raise GitHubClientError(f"GitHub source '{path}' must contain a JSON object")
        return payload

    async def _get_json(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        try:
            response = await self._client.get(
                f"{self.api_base_url}{path}", headers=self._headers, params=params
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GitHubClientError(f"Unable to read GitHub API path '{path}'") from exc
        if not isinstance(payload, dict):
            raise GitHubClientError(f"GitHub API path '{path}' returned invalid JSON")
        return payload
