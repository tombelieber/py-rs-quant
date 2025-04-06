"""
Utility functions for the API.
"""
import time
from typing import Any, Dict

from py_rs_quant.api.models.enums import ResponseStatus
from py_rs_quant.api.models.responses import OrderResponse
from py_rs_quant.core.engine import OrderSide, OrderType


def get_timestamp() -> int:
    """Get the current timestamp in milliseconds."""
    return int(time.time() * 1000)


def success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a success response."""
    return {"status": ResponseStatus.SUCCESS, **data}


def error_response(message: str) -> OrderResponse:
    """Create an error response."""
    return OrderResponse(
        status=ResponseStatus.ERROR,
        message=message
    )


def get_order_side(side_str: str) -> OrderSide:
    """Convert a string side to OrderSide enum."""
    if side_str.lower() == "buy":
        return OrderSide.BUY
    elif side_str.lower() == "sell":
        return OrderSide.SELL
    else:
        raise ValueError(f"Invalid side: {side_str}")


def get_order_type(type_str: str) -> OrderType:
    """Convert a string order type to OrderType enum."""
    if type_str.lower() == "market":
        return OrderType.MARKET
    elif type_str.lower() == "limit":
        return OrderType.LIMIT
    else:
        raise ValueError(f"Invalid order type: {type_str}") 