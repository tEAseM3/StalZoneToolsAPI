from datetime import UTC, datetime

import httpx

from app.services.auction_client import AuctionClient


async def test_auction_client_reads_lots_and_history_with_bearer_token():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/lots"):
            return httpx.Response(
                200,
                json={"total": 1, "lots": [{"amount": 2, "currentPrice": 80, "buyoutPrice": 100}]},
            )
        return httpx.Response(
            200,
            json={
                "total": 1,
                "prices": [{"amount": 2, "price": 100, "time": "2026-01-01T00:00:00Z"}],
            },
        )

    async def token_provider() -> str:
        return "token"

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = AuctionClient(
            "https://eapi.stalcraft.net",
            requests_per_minute=200,
            client=http_client,
            token_provider=token_provider,
        )
        lots_total, lots = await client.get_lots("RU", "tea")
        history_total, history = await client.get_history("RU", "tea")

    assert lots_total == 1
    assert lots[0].buyout_price == 100
    assert history_total == 1
    assert history[0].sold_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert all(request.headers["Authorization"] == "Bearer token" for request in requests)
