import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

from app.core.auth import get_access_token


class AuctionApiError(RuntimeError):
    """Raised when the official auction API cannot provide a valid response."""


class AuctionRateLimiter:
    def __init__(self, requests_per_minute: int):
        self._interval = 60 / requests_per_minute
        self._next_request_at = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            delay = max(0.0, self._next_request_at - now)
            self._next_request_at = max(now, self._next_request_at) + self._interval
            if delay:
                await asyncio.sleep(delay)


@dataclass(frozen=True)
class AuctionLot:
    amount: int
    current_price: int | None
    buyout_price: int | None


@dataclass(frozen=True)
class AuctionTradeRecord:
    amount: int
    lot_price: int
    sold_at: datetime


TokenProvider = Callable[[], Awaitable[str]]


class AuctionClient:
    def __init__(
        self,
        base_url: str,
        requests_per_minute: int,
        client: httpx.AsyncClient | None = None,
        token_provider: TokenProvider | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        self._owns_client = client is None
        self._token_provider = token_provider or _get_token
        self._token: str | None = None
        self._limiter = AuctionRateLimiter(requests_per_minute)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_lots(self, region: str, item_id: str) -> tuple[int, list[AuctionLot]]:
        payload = await self._get(region, item_id, "lots")
        lots = payload.get("lots")
        if not isinstance(lots, list):
            raise AuctionApiError("Auction lots response has an invalid 'lots' field")
        return _get_total(payload), [_parse_lot(lot) for lot in lots]

    async def get_history(self, region: str, item_id: str) -> tuple[int, list[AuctionTradeRecord]]:
        payload = await self._get(region, item_id, "history")
        prices = payload.get("prices")
        if not isinstance(prices, list):
            raise AuctionApiError("Auction history response has an invalid 'prices' field")
        return _get_total(payload), [_parse_trade(price) for price in prices]

    async def _get(self, region: str, item_id: str, resource: str) -> dict[str, Any]:
        await self._limiter.acquire()
        token = await self._get_token()
        response = await self._client.get(
            f"{self._base_url}/{region}/{resource_path(item_id, resource)}",
            params={"limit": 200},
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 401:
            self._token = None
            token = await self._get_token()
            await self._limiter.acquire()
            response = await self._client.get(
                f"{self._base_url}/{region}/{resource_path(item_id, resource)}",
                params={"limit": 200},
                headers={"Authorization": f"Bearer {token}"},
            )
        try:
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AuctionApiError(f"Unable to get auction {resource} for '{item_id}'") from exc
        if not isinstance(payload, dict):
            raise AuctionApiError("Auction API returned a non-object JSON payload")
        return payload

    async def _get_token(self) -> str:
        if self._token is None:
            self._token = await self._token_provider()
        return self._token


async def _get_token() -> str:
    return await asyncio.to_thread(get_access_token)


def resource_path(item_id: str, resource: str) -> str:
    return f"auction/{item_id}/{resource}"


def _get_total(payload: dict[str, Any]) -> int:
    total = payload.get("total")
    if not isinstance(total, int) or total < 0:
        raise AuctionApiError("Auction response has an invalid 'total' field")
    return total


def _parse_lot(raw_lot: object) -> AuctionLot:
    if not isinstance(raw_lot, dict):
        raise AuctionApiError("Auction lot must be an object")
    amount = _require_positive_int(raw_lot, "amount")
    return AuctionLot(
        amount=amount,
        current_price=_optional_nonnegative_int(raw_lot.get("currentPrice")),
        buyout_price=_optional_nonnegative_int(raw_lot.get("buyoutPrice")),
    )


def _parse_trade(raw_trade: object) -> AuctionTradeRecord:
    if not isinstance(raw_trade, dict):
        raise AuctionApiError("Auction trade must be an object")
    time = raw_trade.get("time")
    if not isinstance(time, str):
        raise AuctionApiError("Auction trade has an invalid 'time'")
    try:
        sold_at = datetime.fromisoformat(time.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuctionApiError("Auction trade has an invalid ISO timestamp") from exc
    return AuctionTradeRecord(
        amount=_require_positive_int(raw_trade, "amount"),
        lot_price=_require_nonnegative_int(raw_trade, "price"),
        sold_at=sold_at,
    )


def per_unit_price(price: int, amount: int) -> Decimal:
    return Decimal(price) / Decimal(amount)


def _require_positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise AuctionApiError(f"Auction response has an invalid '{field}' field")
    return value


def _require_nonnegative_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AuctionApiError(f"Auction response has an invalid '{field}' field")
    return value


def _optional_nonnegative_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AuctionApiError("Auction lot has an invalid price field")
    return value
