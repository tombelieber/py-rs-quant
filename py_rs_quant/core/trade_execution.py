"""
Trade execution logic for the matching engine.
"""
from typing import List, Optional, Callable
import logging

from py_rs_quant.core.enums import OrderStatus
from py_rs_quant.core.models import Trade, Order

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    Handles trade execution and maintains trade history.
    """
    
    def __init__(self):
        self.next_trade_id = 1
        self.trades = []
        self.trade_callback = None
        
        # Object recycling pools for reducing GC pressure
        self._trade_pool = []
        self._max_trade_pool_size = 1000
    
    def register_trade_callback(self, callback: Callable) -> None:
        """Register a callback to be called when a trade is executed."""
        self.trade_callback = callback
    
    def execute_trade(self, buy_order: Order, sell_order: Order, price: float, quantity: float) -> Trade:
        """
        Execute a trade between two orders.
        
        Args:
            buy_order: The buy order
            sell_order: The sell order
            price: The execution price
            quantity: The execution quantity
            
        Returns:
            The executed trade
        """
        # Update the orders
        buy_order.filled_quantity += quantity
        buy_order.remaining_quantity -= quantity
        sell_order.filled_quantity += quantity
        sell_order.remaining_quantity -= quantity
        
        # Update order statuses
        if buy_order.filled_quantity >= buy_order.quantity:
            buy_order.status = OrderStatus.FILLED
        else:
            buy_order.status = OrderStatus.PARTIALLY_FILLED
            
        if sell_order.filled_quantity >= sell_order.quantity:
            sell_order.status = OrderStatus.FILLED
        else:
            sell_order.status = OrderStatus.PARTIALLY_FILLED
        
        # Create a trade record - reuse from pool if available
        if self._trade_pool:
            trade = self._trade_pool.pop()
            trade.trade_id = self.next_trade_id
            trade.buy_order_id = buy_order.id
            trade.sell_order_id = sell_order.id
            trade.price = price
            trade.quantity = quantity
            trade.symbol = buy_order.symbol or sell_order.symbol
            trade.timestamp = max(buy_order.timestamp, sell_order.timestamp)
        else:
            trade = Trade(
                trade_id=self.next_trade_id,
                buy_order_id=buy_order.id,
                sell_order_id=sell_order.id,
                price=price,
                quantity=quantity,
                symbol=buy_order.symbol or sell_order.symbol,
                timestamp=max(buy_order.timestamp, sell_order.timestamp)
            )
        self.next_trade_id += 1
        
        # Add to trades list
        self.trades.append(trade)
        
        # Call the trade callback if registered
        if self.trade_callback:
            self.trade_callback(trade)
            
        return trade
    
    def get_trades(self, symbol: Optional[str] = None, limit: int = 100) -> List[Trade]:
        """
        Get recent trades.
        
        Args:
            symbol: Optional symbol to filter by
            limit: Maximum number of trades to return
            
        Returns:
            List of trades
        """
        if symbol is None:
            # Return all trades up to the limit
            return self.trades[-limit:]
        else:
            # Filter trades by symbol
            filtered_trades = [t for t in self.trades if t.symbol == symbol]
            return filtered_trades[-limit:]
    
    def recycle_trades(self, to_recycle: List[Trade]) -> None:
        """
        Recycle trades to reduce garbage collection pressure.
        Call this after processing trades to return them to the pool.
        """
        # Only recycle if we have space in the pool
        space_left = self._max_trade_pool_size - len(self._trade_pool)
        if space_left <= 0:
            return
            
        # Add trades to the pool
        for trade in to_recycle[-space_left:]:
            self._trade_pool.append(trade)
            
    def get_pool_stats(self) -> dict:
        """Get statistics about the trade pool."""
        return {
            "trade_pool_size": len(self._trade_pool),
            "max_trade_pool_size": self._max_trade_pool_size
        } 