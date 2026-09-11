import httpx
import pytest

from app.services.github_client import GitHubClient, GitHubClientError


@pytest.mark.asyncio
async def test_github_client_reads_commit_tree_and_raw_json():
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if request.url.path.endswith("/commits/main"):
            return httpx.Response(
                200,
                json={"sha": "commit-sha", "commit": {"tree": {"sha": "tree-sha"}}},
            )
        if request.url.path.endswith("/git/trees/tree-sha"):
            return httpx.Response(
                200,
                json={
                    "tree": [
                        {"path": "global/items/tea.json", "sha": "item-sha", "type": "blob"},
                        {"path": "global/items", "sha": "dir-sha", "type": "tree"},
                    ]
                },
            )
        if request.url.path.endswith("/commit-sha/global/items/tea.json"):
            return httpx.Response(200, json={"id": "tea"})
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GitHubClient("owner/repository", client=http_client)
        commit = await client.get_latest_commit("main")
        tree = await client.get_tree(commit.tree_sha)
        raw = await client.download_raw(commit.sha, tree[0].path)

    assert commit.sha == "commit-sha"
    assert tree[0].path == "global/items/tea.json"
    assert raw == {"id": "tea"}
    assert any("recursive=1" in url for url in requested_urls)


@pytest.mark.asyncio
async def test_github_client_raises_domain_error_for_invalid_commit_payload():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    ) as http_client:
        client = GitHubClient("owner/repository", client=http_client)

        with pytest.raises(GitHubClientError, match="invalid commit payload"):
            await client.get_latest_commit("main")
