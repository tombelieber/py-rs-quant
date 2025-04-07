"""
Trade execution logic for the matching engine.
"""
from typing import List, Optional, Callable
import logging
import time

from py_rs_quant.core.enums import OrderStatus
from py_rs_quant.core.models import Trade, Order

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    Handles trade execution and maintains trade history.
    Optimized for high-performance trading with low latency.
    """
    
    __slots__ = ('next_trade_id', 'trades', 'trade_callback', '_trade_pool', '_max_trade_pool_size')
    
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
        Execute a trade between two orders with optimized performance.
        
        Args:
            buy_order: The buy order
            sell_order: The sell order
            price: The execution price
            quantity: The execution quantity
            
        Returns:
            The created Trade object
        """
        # Create trade with minimal overhead
        trade_id = self.next_trade_id
        self.next_trade_id += 1
        
        # Use object pool to reduce GC pressure
        if self._trade_pool:
            trade = self._trade_pool.pop()
            trade.trade_id = trade_id
            trade.buy_order_id = buy_order.id
            trade.sell_order_id = sell_order.id
            trade.price = price
            trade.quantity = quantity
            trade.symbol = buy_order.symbol or sell_order.symbol
            trade.timestamp = max(buy_order.timestamp, sell_order.timestamp)
        else:
            trade = Trade(
                trade_id=trade_id,
                buy_order_id=buy_order.id,
                sell_order_id=sell_order.id,
                price=price,
                quantity=quantity,
                symbol=buy_order.symbol or sell_order.symbol,
                timestamp=max(buy_order.timestamp, sell_order.timestamp)
            )
        
        # Add to trade history
        self.trades.append(trade)
        
        # Invoke callback if registered
        if self.trade_callback is not None:
            self.trade_callback(trade)
            
        return trade
    
    def get_trades(self, symbol: Optional[str] = None, limit: int = 100, clear: bool = False) -> List[Trade]:
        """
        Get recent trades with filtering options.
        
        Args:
            symbol: Optional symbol to filter by
            limit: Maximum number of trades to return
            clear: Whether to clear the internal trade list after retrieval
            
        Returns:
            List of trades
        """
        # Filter by symbol if needed
        if symbol is None:
            result = self.trades
        else:
            result = [t for t in self.trades if t.symbol == symbol]
        
        # Apply limit if needed
        if limit < len(result):
            result = result[-limit:]
        else:
            result = result.copy()
            
        # Clear internal trades list if requested
        if clear:
            self.trades = []
            
        return result
    
    def recycle_trades(self, trades: List[Trade]) -> None:
        """
        Return trade objects to the pool for reuse.
        This significantly reduces GC pressure in high-frequency systems.
        
        Args:
            trades: List of trade objects to recycle
        """
        # Early exit if the pool is already full
        if len(self._trade_pool) >= self._max_trade_pool_size:
            return
            
        # Add trades to the pool up to the maximum size
        remaining_capacity = self._max_trade_pool_size - len(self._trade_pool)
        trades_to_add = trades[:remaining_capacity]
        
        # Remove trades from the internal list if they're there
        for trade in trades_to_add:
            if trade in self.trades:
                self.trades.remove(trade)
                
        # Add to pool
        self._trade_pool.extend(trades_to_add) 