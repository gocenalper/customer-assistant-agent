from typing import TypedDict, Literal

from pydantic import BaseModel

class UserMessage(BaseModel):
    """The structure of the user message"""
    message: str


class LLMResponse(BaseModel):
    """The structure of the user message"""
    response: str
    thread_id: str
    pending_approval: "RefundResponse | None" = None

class ApprovalDecision(BaseModel):
    """The operator's decision on a refund waiting for approval"""
    approved: bool

class StockInfo(BaseModel):
    """Stock information"""
    sku: str
    name: str
    quantity: int

class RefundResponse(BaseModel):
    """The structure of the refund request"""
    refundRequestId: str
    orderId: str
    amountKurus: int
    currency: str
    requiresApproval: bool
    status: Literal["PENDING_APPROVAL", "READY", "APPROVED", "REJECTED", "REFUNDED"]