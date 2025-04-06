"""
Request models for the API.
"""
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class OrderRequest(BaseModel):
    """Request model for creating a new order."""
    symbol: str = Field(..., description="The trading symbol")
    side: str = Field(..., description="Order side: buy or sell")
    order_type: str = Field(..., description="Order type: market or limit")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, gt=0, description="Order price (required for limit orders)")
    
    @field_validator('side')
    def validate_side(cls, v):
        """Validate side is buy or sell."""
        if v.lower() not in ['buy', 'sell']:
            raise ValueError(f"side must be buy or sell, got {v}")
        return v.lower()
    
    @field_validator('order_type')
    def validate_order_type(cls, v):
        """Validate order_type is market or limit."""
        if v.lower() not in ['market', 'limit']:
            raise ValueError(f"order_type must be market or limit, got {v}")
        return v.lower()
    
    @field_validator('price')
    def validate_price_for_limit_orders(cls, v, values):
        """Validate price is provided for limit orders."""
        if 'order_type' in values.data and values.data['order_type'] == 'limit' and v is None:
            raise ValueError("price is required for limit orders")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "symbol": "BTCUSD",
                "side": "buy",
                "order_type": "limit",
                "quantity": 1.0,
                "price": 50000.0
            }
        }
    } 