"""
Trade execution logic for the matching engine.
"""
from typing import List, Optional, Callable, Dict, Any
import logging
import time

from py_rs_quant.core.enums import OrderStatus
from py_rs_quant.core.models import Trade, Order

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    Handles trade execution and maintains trade history.
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
    
    def execute_trade_optimized(self, buy_order: Order, sell_order: Order, price: float, quantity: float) -> None:
        """
        Ultra-optimized trade execution with minimal overhead.
        
        Args:
            buy_order: The buy order
            sell_order: The sell order
            price: The execution price
            quantity: The execution quantity
        """
        # Create trade with minimal overhead
        trade_id = self.next_trade_id
        self.next_trade_id += 1
        
        # Use pool if available for zero-allocation
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
        callback = self.trade_callback
        if callback is not None:
            callback(trade)
    
    def get_executed_trades(self) -> List[Trade]:
        """
        Get all executed trades since last call, clearing the internal trade list.
        
        Returns:
            List of trades executed since last call
        """
        trades = self.trades.copy()  # Make a copy to return
        self.trades = []  # Clear the internal list
        return trades
    
    def get_trades(self, symbol: Optional[str] = None, limit: int = 100) -> List[Trade]:
        """
        Get recent trades without clearing the internal list.
        
        Args:
            symbol: Optional symbol to filter by
            limit: Maximum number of trades to return
            
        Returns:
            List of trades
        """
        # Optimized trade retrieval
        if symbol is None:
            # Return most recent trades up to limit
            if limit < len(self.trades):
                return self.trades[-limit:]
            return self.trades.copy()
        else:
            # Filter trades by symbol
            filtered_trades = [t for t in self.trades if t.symbol == symbol]
            # Return most recent filtered trades up to limit
            if limit < len(filtered_trades):
                return filtered_trades[-limit:]
            return filtered_trades
    
    def recycle_trades(self, count_or_trades: any) -> None:
        """
        Recycle trades to reduce garbage collection pressure.
        
        Args:
            count_or_trades: Either a count of recent trades to recycle, or a list of trades
        """
        if isinstance(count_or_trades, int):
            # Recycle recent trades by count
            trades_to_recycle = []
            count = min(count_or_trades, len(self.trades))
            
            if count > 0:
                trades_to_recycle = self.trades[-count:]
                self.trades = self.trades[:-count]
                
            # Return to pool
            for trade in trades_to_recycle:
                if len(self._trade_pool) < self._max_trade_pool_size:
                    self._trade_pool.append(trade)
        else:
            # Recycle specific trades
            for trade in count_or_trades:
                if trade in self.trades:
                    self.trades.remove(trade)
                    
                if len(self._trade_pool) < self._max_trade_pool_size:
                    self._trade_pool.append(trade)
    
    def get_trade_stats(self) -> Dict[str, Any]:
        """
        Get statistics about trade execution.
        
        Returns:
            Dictionary with trade statistics
        """
        return {
            "trade_count": len(self.trades),
            "trade_pool_size": len(self._trade_pool),
            "max_trade_pool_size": self._max_trade_pool_size,
            "next_trade_id": self.next_trade_id,
            "timestamp": int(time.time() * 1000)
        }
    
    def get_pool_stats(self) -> Dict[str, int]:
        """Get statistics about the trade pool."""
        return {
            "trade_pool_size": len(self._trade_pool),
            "max_trade_pool_size": self._max_trade_pool_size
        } 