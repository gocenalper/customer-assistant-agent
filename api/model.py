from typing import TypedDict

from pydantic import BaseModel

class UserMessage(BaseModel):
    """The structure of the user message"""
    message: str


class LLMResponse(BaseModel):
    """The structure of the user message"""
    response: str

class StockInfo(BaseModel):
    """Stock information"""
    sku: str
    name: str
    quantity: int