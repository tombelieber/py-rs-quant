"""
Market data API endpoints.
"""
from fastapi import APIRouter, Depends

from py_rs_quant.api.utils.utils import get_timestamp
from py_rs_quant.api.dependencies.engines import (
    get_matching_engine, 
    get_risk_manager, 
    get_orders_storage
)
from py_rs_quant.api.models.responses import (
    OrderBookLevel, 
    OrderBookResponse, 
    TradeModel, 
    TradesResponse
)
from py_rs_quant.api.services.trading import TradingService


# Create router
router = APIRouter(tags=["market_data"])


def get_trading_service(
    matching_engine = Depends(get_matching_engine),
    risk_manager = Depends(get_risk_manager),
    orders_storage = Depends(get_orders_storage)
) -> TradingService:
    """Dependency for getting the trading service."""
    return TradingService(matching_engine, risk_manager, orders_storage)


@router.get("/orderbook/{symbol}", response_model=OrderBookResponse)
async def get_orderbook(
    symbol: str,
    trading_service: TradingService = Depends(get_trading_service)
):
    """
    Get the current order book for a symbol.
    
    Args:
        symbol: The trading symbol
        
    Returns:
        OrderBookResponse: The order book snapshot
    """
    buy_orders, sell_orders = trading_service.get_order_book(symbol)
    
    # Convert to API response format
    bids = [OrderBookLevel(price=price, quantity=qty) for price, qty in buy_orders]
    asks = [OrderBookLevel(price=price, quantity=qty) for price, qty in sell_orders]
    
    return OrderBookResponse(
        status="success",
        symbol=symbol,
        bids=bids,
        asks=asks,
        timestamp=get_timestamp()
    )


@router.get("/trades", response_model=TradesResponse)
async def get_trades(
    trading_service: TradingService = Depends(get_trading_service)
):
    """
    Get all trades that have occurred.
    
    Returns:
        TradesResponse: List of trades
    """
    trades = trading_service.get_trades()
    
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
        status="success",
        trades=trade_models
    ) 