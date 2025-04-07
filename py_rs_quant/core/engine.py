"""
Core matching engine implementation.
"""
import time
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable

from py_rs_quant.core.enums import OrderSide, OrderType, OrderStatus
from py_rs_quant.core.models import Order, Trade
from py_rs_quant.core.order_book import OrderBook
from py_rs_quant.core.trade_execution import TradeExecutor
from py_rs_quant.core.statistics import PriceStatisticsCalculator
from py_rs_quant.core.matcher import Matcher
from py_rs_quant.core.order_processor import OrderProcessor

logger = logging.getLogger(__name__)


class MatchingEngine:
    """
    High-performance matching engine for limit and market orders.
    
    This engine has been optimized for ultra-low latency performance
    with optimizations for memory management, function call elimination,
    and critical path optimization.
    """
    
    __slots__ = (
        'order_book', 'trade_executor', 'statistics', 'matcher', 'order_processor',
        '_order_pool', '_trade_pool', '_max_trade_pool_size'
    )
    
    def __init__(self):
        """Initialize a new matching engine."""
        # Core components
        self.order_book = OrderBook()
        self.statistics = PriceStatisticsCalculator(self.order_book)
        self.trade_executor = TradeExecutor()
        
        # Delegate to specialized components
        self.matcher = Matcher(self.order_book, self.trade_executor)
        self.order_processor = OrderProcessor(self.matcher)
        
        # Trade object pool for memory management
        self._trade_pool = []
        self._max_trade_pool_size = 10000
    
    def register_trade_callback(self, callback: Callable) -> None:
        """
        Register a callback to be called when a trade is executed.
        This method forwards to the TradeExecutor.
        
        Args:
            callback: The callback function that takes a Trade object
        """
        self.trade_executor.register_trade_callback(callback)
    
    def add_limit_order(self, side: OrderSide, price: float, quantity: float, 
                        timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """
        Add a limit order to the matching engine.
        
        Args:
            side: Buy or sell side
            price: Limit price
            quantity: Order quantity
            timestamp: Optional timestamp (milliseconds since epoch)
            symbol: Optional trading symbol
            
        Returns:
            The order ID
        """
        return self.order_processor.create_limit_order(side, price, quantity, timestamp, symbol)
    
    def add_market_order(self, side: OrderSide, quantity: float,
                        timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """
        Add a market order to the matching engine.
        
        Args:
            side: Buy or sell side
            quantity: Order quantity
            timestamp: Optional timestamp (milliseconds since epoch)
            symbol: Optional trading symbol
            
        Returns:
            The order ID
        """
        return self.order_processor.create_market_order(side, quantity, timestamp, symbol)
    
    def batch_add_orders(self, orders: List[Tuple[OrderSide, OrderType, Optional[float], float, Optional[int], Optional[str]]]) -> List[int]:
        """
        Efficiently process multiple orders at once.
        
        Args:
            orders: List of tuples containing (side, order_type, price, quantity, timestamp, symbol)
        
        Returns:
            List of order IDs created
        """
        return self.order_processor.batch_create_orders(orders)
    
    def cancel_order(self, order_id: int) -> bool:
        """
        Cancel an order by its ID.
        
        Args:
            order_id: The ID of the order to cancel
            
        Returns:
            True if the order was cancelled, False otherwise
        """
        return self.order_processor.cancel_order(order_id)
    
    def get_order_book_snapshot(self) -> Dict[str, Any]:
        """
        Get a complete snapshot of the current order book state.
        
        Returns:
            Dictionary with buy and sell sides, each containing lists of price levels
        """
        return self.order_book.get_snapshot()
    
    def get_order(self, order_id: int) -> Optional[Order]:
        """
        Get an order by its ID.
        
        Args:
            order_id: The order ID to look up
            
        Returns:
            The Order object or None if not found
        """
        return self.order_book.orders_by_id.get(order_id)
    
    def get_trades(self) -> List[Trade]:
        """
        Get all trades executed since last call.
        
        Returns:
            List of executed trades
        """
        return self.trade_executor.get_executed_trades()
    
    def clear_caches(self) -> None:
        """
        Clear internal caches to free memory.
        This should be called periodically in high-throughput systems.
        """
        # Reset order book caches
        self.order_book.clear_caches()
        
        # Clear trade recycling pool
        self._trade_pool.clear()
        
        # Reset cached compiled functions
        self.matcher.clear_caches()
    
    def recycle_trades(self, trades: List[Trade]) -> None:
        """
        Return trade objects to the pool for reuse.
        This significantly reduces GC pressure in high-frequency systems.
        
        Args:
            trades: List of trade objects to recycle
        """
        if len(self._trade_pool) >= self._max_trade_pool_size:
            return
            
        self._trade_pool.extend(trades[:self._max_trade_pool_size - len(self._trade_pool)])
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current statistics about the matching engine.
        
        Returns:
            Dictionary with various statistics
        """
        stats = {
            "timestamp": int(time.time() * 1000),
            "orderbook": {
                "buy_levels": len(self.order_book.buy_price_levels),
                "sell_levels": len(self.order_book.sell_price_levels),
                "total_orders": len(self.order_book.orders_by_id)
            },
            "price_stats": self.statistics.calculate_price_statistics(),
            "memory_pools": {
                "trade_pool_size": len(self._trade_pool),
                "max_trade_pool_size": self._max_trade_pool_size,
            }
        }
        
        # Add order processor stats
        stats["memory_pools"].update(self.order_processor.get_order_pool_stats())
        
        return stats 