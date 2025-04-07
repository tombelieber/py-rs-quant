"""
Trade execution logic for the matching engine.
"""
import time
from typing import List, Optional, Callable
import logging

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
    
    def execute_trade_fast(self, buy_order: Order, sell_order: Order, price: float, quantity: float) -> None:
        """
        Fast path for executing trades with minimal overhead.
        Does not return the trade object to avoid an allocation.
        
        Args:
            buy_order: The buy order
            sell_order: The sell order
            price: The execution price
            quantity: The execution quantity
        """
        # Update order quantities directly
        buy_order.filled_quantity += quantity
        buy_order.remaining_quantity -= quantity
        sell_order.filled_quantity += quantity
        sell_order.remaining_quantity -= quantity
        
        # Update statuses with minimal branching
        buy_filled = buy_order.filled_quantity >= buy_order.quantity
        sell_filled = sell_order.filled_quantity >= sell_order.quantity
        
        # Use direct status assignment instead of conditionals
        buy_order.status = OrderStatus.FILLED if buy_filled else OrderStatus.PARTIALLY_FILLED
        sell_order.status = OrderStatus.FILLED if sell_filled else OrderStatus.PARTIALLY_FILLED
        
        # Get trade from pool or create new directly
        trade_id = self.next_trade_id
        self.next_trade_id += 1
        
        # Create trade with direct assignment
        if self._trade_pool:
            trade = self._trade_pool.pop()
            trade.trade_id = trade_id
            trade.buy_order_id = buy_order.id
            trade.sell_order_id = sell_order.id
            trade.price = price
            trade.quantity = quantity
            # Use first non-None symbol
            trade.symbol = buy_order.symbol if buy_order.symbol is not None else sell_order.symbol
            trade.timestamp = max(buy_order.timestamp, sell_order.timestamp)
        else:
            # Inline Trade construction to avoid function call
            trade = Trade(
                trade_id=trade_id,
                buy_order_id=buy_order.id,
                sell_order_id=sell_order.id,
                price=price,
                quantity=quantity,
                symbol=buy_order.symbol if buy_order.symbol is not None else sell_order.symbol,
                timestamp=max(buy_order.timestamp, sell_order.timestamp)
            )
        
        # Add directly to trades list
        self.trades.append(trade)
        
        # Fast path for callback
        callback = self.trade_callback
        if callback is not None:
            callback(trade)
    
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
    
    def get_trades_fast(self, limit: int = 100) -> List[Trade]:
        """
        Fast path for getting all recent trades without symbol filtering.
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of most recent trades
        """
        # Direct slice of trades list for maximum performance
        if limit >= len(self.trades):
            return self.trades[:]  # Return a copy of all trades
        else:
            return self.trades[-limit:]  # Return only the most recent trades
    
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
    
    def recycle_trades_fast(self, num_trades: int) -> None:
        """
        Fast path for recycling the most recent trades.
        
        Args:
            num_trades: Number of most recent trades to recycle
        """
        # Exit early if no space in pool or no trades
        if len(self._trade_pool) >= self._max_trade_pool_size or len(self.trades) == 0:
            return
            
        # Calculate how many trades we can recycle
        num_to_recycle = min(
            num_trades,
            len(self.trades),
            self._max_trade_pool_size - len(self._trade_pool)
        )
        
        # Recycle most recent trades
        for i in range(num_to_recycle):
            self._trade_pool.append(self.trades.pop())
            
    def get_pool_stats(self) -> dict:
        """Get statistics about the trade pool."""
        return {
            "trade_pool_size": len(self._trade_pool),
            "max_trade_pool_size": self._max_trade_pool_size
        } 