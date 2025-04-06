"""
FastAPI application for the trading system API.
"""
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from py_rs_quant.core.engine import MatchingEngine, OrderSide, OrderType, Order
from py_rs_quant.risk.manager import RiskManager, RiskCheckResult

# Create FastAPI app
app = FastAPI(title="Trading System API", description="API for the trading system")

# Create global instances of engines
matching_engine = MatchingEngine(use_rust=True)
risk_manager = RiskManager()

# Dictionary to store order details by ID
orders_by_id: Dict[int, Order] = {}

# Enum for API responses
class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


# Request and response models
class OrderRequest(BaseModel):
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None  # Required for limit orders, not for market orders
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "BTCUSD",
                "side": "buy",
                "order_type": "limit",
                "quantity": 1.0,
                "price": 50000.0
            }
        }


class OrderResponse(BaseModel):
    status: ResponseStatus
    order_id: Optional[int] = None
    message: Optional[str] = None


class OrderBookLevel(BaseModel):
    price: float
    quantity: float


class OrderBookResponse(BaseModel):
    status: ResponseStatus
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: int


class TradeModel(BaseModel):
    id: int
    buy_order_id: int
    sell_order_id: int
    price: float
    quantity: float
    timestamp: int


class TradesResponse(BaseModel):
    status: ResponseStatus
    trades: List[TradeModel]


# Helper to get the current timestamp in milliseconds
def get_timestamp() -> int:
    return int(time.time() * 1000)


# API endpoints
@app.post("/orders", response_model=OrderResponse)
async def create_order(order_request: OrderRequest):
    """Create a new order."""
    try:
        # Validate order side
        try:
            if order_request.side.lower() == "buy":
                side = OrderSide.BUY
                order_size = order_request.quantity
            elif order_request.side.lower() == "sell":
                side = OrderSide.SELL
                order_size = -order_request.quantity
            else:
                raise ValueError(f"Invalid side: {order_request.side}")
        except ValueError as e:
            return OrderResponse(
                status=ResponseStatus.ERROR,
                message=str(e)
            )
        
        # Validate order type
        try:
            if order_request.order_type.lower() == "market":
                order_type = OrderType.MARKET
                # Use current reference price for market orders (in a real system, this would be dynamic)
                price = risk_manager.reference_prices.get(order_request.symbol, 0.0)
                if price == 0.0:
                    return OrderResponse(
                        status=ResponseStatus.ERROR,
                        message=f"No reference price available for {order_request.symbol}"
                    )
            elif order_request.order_type.lower() == "limit":
                order_type = OrderType.LIMIT
                if order_request.price is None:
                    return OrderResponse(
                        status=ResponseStatus.ERROR,
                        message="Price is required for limit orders"
                    )
                price = order_request.price
            else:
                raise ValueError(f"Invalid order type: {order_request.order_type}")
        except ValueError as e:
            return OrderResponse(
                status=ResponseStatus.ERROR,
                message=str(e)
            )
        
        # Perform risk checks
        check_price_tolerance = order_request.order_type.lower() == "limit"
        risk_result = risk_manager.check_order(
            symbol=order_request.symbol,
            order_size=order_size,
            price=price,
            check_price_tolerance=check_price_tolerance
        )
        
        if risk_result != RiskCheckResult.PASSED:
            return OrderResponse(
                status=ResponseStatus.ERROR,
                message=f"Risk check failed: {risk_result.name}"
            )
        
        # Submit the order to the matching engine
        timestamp = get_timestamp()
        order_id = None
        
        if order_type == OrderType.MARKET:
            order_id = matching_engine.add_market_order(side, abs(order_size), timestamp)
        else:  # LIMIT
            order_id = matching_engine.add_limit_order(side, price, abs(order_size), timestamp)
        
        # Create an order object to track
        order = Order(
            order_id=order_id,
            side=side,
            order_type=order_type,
            price=price if order_type == OrderType.LIMIT else None,
            quantity=abs(order_size),
            timestamp=timestamp
        )
        orders_by_id[order_id] = order
        
        return OrderResponse(
            status=ResponseStatus.SUCCESS,
            order_id=order_id
        )
    except Exception as e:
        return OrderResponse(
            status=ResponseStatus.ERROR,
            message=f"Error processing order: {str(e)}"
        )


@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int):
    """Get order status by ID."""
    if order_id not in orders_by_id:
        raise HTTPException(status_code=404, detail=f"Order with ID {order_id} not found")
    
    order = orders_by_id[order_id]
    
    return OrderResponse(
        status=ResponseStatus.SUCCESS,
        order_id=order_id,
        message=f"Order status: {order.status.name}"
    )


@app.delete("/orders/{order_id}", response_model=OrderResponse)
async def cancel_order(order_id: int):
    """Cancel an order by ID."""
    if order_id not in orders_by_id:
        raise HTTPException(status_code=404, detail=f"Order with ID {order_id} not found")
    
    success = matching_engine.cancel_order(order_id)
    
    if success:
        order = orders_by_id[order_id]
        # Update status in our tracking dictionary
        order.status = OrderType.CANCELLED
        
        return OrderResponse(
            status=ResponseStatus.SUCCESS,
            order_id=order_id,
            message="Order cancelled successfully"
        )
    else:
        return OrderResponse(
            status=ResponseStatus.ERROR,
            order_id=order_id,
            message="Failed to cancel order"
        )


@app.get("/orderbook/{symbol}", response_model=OrderBookResponse)
async def get_orderbook(symbol: str):
    """Get the current order book for a symbol."""
    # In a real implementation, we would filter by symbol
    buy_orders, sell_orders = matching_engine.get_order_book_snapshot()
    
    # Convert to API response format
    bids = [OrderBookLevel(price=price, quantity=qty) for price, qty in buy_orders]
    asks = [OrderBookLevel(price=price, quantity=qty) for price, qty in sell_orders]
    
    return OrderBookResponse(
        status=ResponseStatus.SUCCESS,
        symbol=symbol,
        bids=bids,
        asks=asks,
        timestamp=get_timestamp()
    )


@app.get("/trades", response_model=TradesResponse)
async def get_trades():
    """Get all trades that have occurred."""
    trades = matching_engine.get_trades()
    
    # Convert to API response format
    trade_models = [
        TradeModel(
            id=t.id,
            buy_order_id=t.buy_order_id,
            sell_order_id=t.sell_order_id,
            price=t.price,
            quantity=t.quantity,
            timestamp=t.timestamp
        ) for t in trades
    ]
    
    return TradesResponse(
        status=ResponseStatus.SUCCESS,
        trades=trade_models
    )


# Initialize with some reference prices
@app.on_event("startup")
async def startup_event():
    """Initialize the API on startup."""
    # Set some reference prices
    risk_manager.update_reference_price("BTCUSD", 50000.0)
    risk_manager.update_reference_price("ETHUSD", 3000.0)
    
    # Set some risk limits
    risk_manager.max_position_size = {
        "BTCUSD": 10.0,
        "ETHUSD": 100.0
    }
    risk_manager.max_order_size = {
        "BTCUSD": 5.0,
        "ETHUSD": 50.0
    }
    risk_manager.max_exposure = 1000000.0  # $1M exposure limit
    
    print("Trading API initialized with reference prices and risk limits") 