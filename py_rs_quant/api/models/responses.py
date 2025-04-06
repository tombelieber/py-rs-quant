"""
Response models for the API.
"""
from typing import List, Optional

from pydantic import BaseModel, Field

from py_rs_quant.api.models.enums import ResponseStatus


class OrderResponse(BaseModel):
    """Response model for order operations."""
    status: ResponseStatus
    order_id: Optional[int] = Field(None, description="The ID of the order")
    message: Optional[str] = Field(None, description="Additional message (usually for errors)")


class OrderBookLevel(BaseModel):
    """Model for a level in the order book."""
    price: float = Field(..., description="Price level")
    quantity: float = Field(..., description="Quantity at this price level")


class OrderBookResponse(BaseModel):
    """Response model for order book requests."""
    status: ResponseStatus
    symbol: str = Field(..., description="The trading symbol")
    bids: List[OrderBookLevel] = Field(default_factory=list, description="Buy orders")
    asks: List[OrderBookLevel] = Field(default_factory=list, description="Sell orders")
    timestamp: int = Field(..., description="Timestamp of the order book snapshot")


class TradeModel(BaseModel):
    """Model for a trade."""
    id: int = Field(..., description="Trade ID")
    buy_order_id: int = Field(..., description="ID of the buy order")
    sell_order_id: int = Field(..., description="ID of the sell order")
    price: float = Field(..., description="Trade price")
    quantity: float = Field(..., description="Trade quantity")
    timestamp: int = Field(..., description="Trade timestamp")


class TradesResponse(BaseModel):
    """Response model for trade requests."""
    status: ResponseStatus
    trades: List[TradeModel] = Field(default_factory=list, description="List of trades") 