"""
Order-related API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from py_rs_quant.api.utils.utils import error_response, get_order_side, get_order_type
from py_rs_quant.api.dependencies.engines import (
    get_matching_engine, 
    get_risk_manager, 
    get_orders_storage
)
from py_rs_quant.api.models.requests import OrderRequest
from py_rs_quant.api.models.responses import OrderResponse
from py_rs_quant.api.services.trading import TradingService
from py_rs_quant.core.engine import MatchingEngine, OrderSide, OrderType
from py_rs_quant.risk.manager import RiskManager


# Create router
router = APIRouter(prefix="/orders", tags=["orders"])


def get_trading_service(
    matching_engine: MatchingEngine = Depends(get_matching_engine),
    risk_manager: RiskManager = Depends(get_risk_manager),
    orders_storage = Depends(get_orders_storage)
) -> TradingService:
    """Dependency for getting the trading service."""
    return TradingService(matching_engine, risk_manager, orders_storage)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_request: OrderRequest,
    trading_service: TradingService = Depends(get_trading_service)
):
    """
    Create a new order.
    
    Returns:
        OrderResponse: The created order
    """
    try:
        # Convert string values to enums
        side = get_order_side(order_request.side)
        order_type = get_order_type(order_request.order_type)
        
        # Place the order
        success, order_id, error_message = trading_service.place_order(
            symbol=order_request.symbol,
            side=side,
            order_type=order_type,
            quantity=order_request.quantity,
            price=order_request.price
        )
        
        if success:
            return OrderResponse(
                status="success",
                order_id=order_id
            )
        else:
            return error_response(error_message or "Unknown error")
    
    except Exception as e:
        return error_response(f"Error processing order: {str(e)}")


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    trading_service: TradingService = Depends(get_trading_service)
):
    """
    Get order status by ID.
    
    Args:
        order_id: The ID of the order to get
        
    Returns:
        OrderResponse: The order status
        
    Raises:
        HTTPException: If the order is not found
    """
    order = trading_service.get_order(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found"
        )
    
    return OrderResponse(
        status="success",
        order_id=order_id,
        message=f"Order status: {order.status.name}"
    )


@router.delete("/{order_id}", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    trading_service: TradingService = Depends(get_trading_service)
):
    """
    Cancel an order by ID.
    
    Args:
        order_id: The ID of the order to cancel
        
    Returns:
        OrderResponse: The cancellation result
        
    Raises:
        HTTPException: If the order is not found
    """
    success, error_message = trading_service.cancel_order(order_id)
    
    if success:
        return OrderResponse(
            status="success",
            order_id=order_id,
            message="Order cancelled successfully"
        )
    else:
        return OrderResponse(
            status="error",
            order_id=order_id,
            message=error_message or "Failed to cancel order"
        ) 