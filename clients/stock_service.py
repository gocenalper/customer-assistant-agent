import os
import uuid
from urllib.parse import quote

import httpx

from api.model import StockInfo, RefundResponse


def _client() -> httpx.AsyncClient:
    base_url = os.getenv("STOCK_SERVICE_URL", "http://localhost:8081")
    return httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=10.0)


async def fetch_stock(sku: str) -> StockInfo:
    async with _client() as client:
        response = await client.get(f"/stocks/{quote(sku, safe='')}")
    response.raise_for_status()
    return StockInfo.model_validate(response.json())


async def prepare_refund(order_id: uuid.UUID, reason: str) -> RefundResponse:
    async with _client() as client:
        response = await client.post(
            "/refunds/prepare",
            json={"orderId": str(order_id), "reason": reason},
        )
    response.raise_for_status()
    return RefundResponse.model_validate(response.json())


async def _transition_refund(refund_request_id: str, action: str) -> RefundResponse:
    async with _client() as client:
        response = await client.post(f"/refunds/{quote(refund_request_id, safe='')}/{action}")
    response.raise_for_status()
    return RefundResponse.model_validate(response.json())


async def approve_refund(refund_request_id: str) -> RefundResponse:
    return await _transition_refund(refund_request_id, "approve")


async def reject_refund(refund_request_id: str) -> RefundResponse:
    return await _transition_refund(refund_request_id, "reject")


async def execute_refund(refund_request_id: str) -> RefundResponse:
    return await _transition_refund(refund_request_id, "execute")
