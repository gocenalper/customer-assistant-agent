import uuid

from langchain_core.tools import tool
from api.model import StockInfo
from clients import stock_service
from pydantic import ValidationError
import httpx

@tool
async def get_stock(sku: str) -> StockInfo | dict[str, str]:
    """Called when the user asks about stock information of a product.
     Never call this for any other reason"""
    try:
        return await stock_service.fetch_stock(sku)
    except ValidationError:
        return {
            "error": "invalid_stock_response",
            "message": "Stok servisinden beklenen formatta veri alınamadı."
        }

@tool(response_format="content_and_artifact")
async def initiate_refund(
    orderId: uuid.UUID, reason: str
) -> tuple[dict[str, object], dict[str, object] | None]:
    """Request a full refund for an order. Small refunds are executed automatically;
    larger ones wait for an operator's decision. The returned status is the final
    outcome: REFUNDED means the refund was made, REJECTED means the operator declined it."""
    try:
        refund = await stock_service.prepare_refund(orderId, reason)
        # The artifact marks success for the graph; a plain dict survives checkpointing.
        data = refund.model_dump(mode="json")
        return data, data

    except httpx.HTTPStatusError as error:
        return {
            "error": "refund_request_failed",
            "message": "İade hazırlama isteği servis tarafından reddedildi.",
            "status_code": error.response.status_code,
        }, None
    except httpx.RequestError:
        return {
            "error": "refund_service_unavailable",
            "message": "İade servisine ulaşılamadı.",
        }, None
    except ValueError:
        # Includes malformed JSON and Pydantic ValidationError.
        return {
            "error": "invalid_refund_response",
            "message": "İade servisinden geçerli yanıt alınamadı.",
        }, None


TOOLSET = [get_stock, initiate_refund]
