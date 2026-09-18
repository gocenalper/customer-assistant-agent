import os

from langchain_core.tools import tool
from api.model import StockInfo
from urllib.parse import quote
from pydantic import ValidationError
import httpx

@tool
async def get_stock(sku: str) -> StockInfo | dict[str, str]:
    """Called when the user asks about stock information of a product.
     Never call this for any other reason"""
    base_url = os.getenv("STOCK_SERVICE_URL", "http://localhost:8081")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{base_url.rstrip('/')}/stocks/{quote(sku, safe='')}"
        )
        response.raise_for_status()

        data = response.json()

        try:
            return StockInfo.model_validate(data)
        except ValidationError:
            return {
                "error": "invalid_stock_response",
                "message": "Stok servisinden beklenen formatta veri alınamadı."
            }

TOOLSET = [get_stock]