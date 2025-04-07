"""
Order processing logic for the matching engine.
"""
import time
import logging
from typing import Dict, List, Optional, Tuple, Any

from py_rs_quant.core.enums import OrderSide, OrderType, OrderStatus
from py_rs_quant.core.models import Order
from py_rs_quant.core.matcher import Matcher

logger = logging.getLogger(__name__)


class OrderProcessor:
    """
    Handles order creation, validation, and lifecycle management.
    """
    
    __slots__ = (
        'next_order_id', 'matcher', '_order_pool', '_max_order_pool_size'
    )
    
    def __init__(self, matcher: Matcher):
        """
        Initialize an OrderProcessor.
        
        Args:
            matcher: The matcher to use for matching orders
        """
        self.next_order_id = 1
        self.matcher = matcher
        
        # Object recycling pools for reducing GC pressure
        self._order_pool = []
        self._max_order_pool_size = 2000
    
    def create_limit_order(self, side: OrderSide, price: float, quantity: float, 
                          timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """
        Create and process a limit order.
        
        Args:
            side: Buy or sell side
            price: Limit price
            quantity: Order quantity
            timestamp: Optional timestamp (milliseconds since epoch)
            symbol: Optional trading symbol
            
        Returns:
            The order ID
        """
        # Direct assignment instead of conditionals for performance
        order_id = self.next_order_id
        self.next_order_id += 1
        ts = timestamp or int(time.time() * 1000)
        
        # Only log in debug mode with lazy evaluation
        if __debug__ and logger.isEnabledFor(logging.DEBUG):
            logger.debug("Adding limit order: id=%d, side=%s, price=%f, qty=%f, symbol=%s", 
                        order_id, side.name, price, quantity, symbol or '')
        
        # Inline order creation for performance
        if self._order_pool:
            order = self._order_pool.pop()
            order.id = order_id
            order.side = side
            order.order_type = OrderType.LIMIT
            order.price = price
            order.quantity = quantity
            order.filled_quantity = 0.0
            order.remaining_quantity = quantity
            order.status = OrderStatus.NEW
            order.timestamp = ts
            order.symbol = symbol
        else:
            order = Order(order_id, side, OrderType.LIMIT, price, quantity, ts, symbol)
        
        # Process the order through the matcher
        if side == OrderSide.BUY:
            self.matcher.match_buy_order(order)
        else:
            self.matcher.match_sell_order(order)
        
        return order_id
    
    def create_market_order(self, side: OrderSide, quantity: float,
                           timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """
        Create and process a market order.
        
        Args:
            side: Buy or sell side
            quantity: Order quantity
            timestamp: Optional timestamp (milliseconds since epoch)
            symbol: Optional trading symbol
            
        Returns:
            The order ID
        """
        # Direct assignment instead of conditionals for performance
        order_id = self.next_order_id
        self.next_order_id += 1
        ts = timestamp or int(time.time() * 1000)
        
        # Only log in debug mode with lazy evaluation
        if __debug__ and logger.isEnabledFor(logging.DEBUG):
            logger.debug("Adding market order: id=%d, side=%s, qty=%f, symbol=%s", 
                        order_id, side.name, quantity, symbol or '')
        
        # Inline order creation for performance
        if self._order_pool:
            order = self._order_pool.pop()
            order.id = order_id
            order.side = side
            order.order_type = OrderType.MARKET
            order.price = None
            order.quantity = quantity
            order.filled_quantity = 0.0
            order.remaining_quantity = quantity
            order.status = OrderStatus.NEW
            order.timestamp = ts
            order.symbol = symbol
        else:
            order = Order(order_id, side, OrderType.MARKET, None, quantity, ts, symbol)
        
        # Process the order through the matcher
        if side == OrderSide.BUY:
            self.matcher.match_buy_order(order)
        else:
            self.matcher.match_sell_order(order)
        
        return order_id
    
    def batch_create_orders(self, orders: List[Tuple[OrderSide, OrderType, Optional[float], float, Optional[int], Optional[str]]]) -> List[int]:
        """
        Efficiently process multiple orders at once.
        
        Args:
            orders: List of tuples containing (side, order_type, price, quantity, timestamp, symbol)
        
        Returns:
            List of order IDs created
        """
        order_objects = []
        order_ids = []
        
        # Create all order objects first
        current_timestamp = int(time.time() * 1000)
        for side, order_type, price, quantity, timestamp, symbol in orders:
            ts = timestamp if timestamp is not None else current_timestamp
            order_id = self.next_order_id
            self.next_order_id += 1
            
            # Get order from pool or create new
            if self._order_pool:
                order = self._order_pool.pop()
                # Reset order properties
                order.id = order_id
                order.side = side
                order.order_type = order_type
                order.price = price
                order.quantity = quantity
                order.filled_quantity = 0.0
                order.remaining_quantity = quantity
                order.status = OrderStatus.NEW
                order.timestamp = ts
                order.symbol = symbol
            else:
                # Create new if pool is empty
                order = Order(order_id, side, order_type, price, quantity, ts, symbol)
                
            order_objects.append(order)
            order_ids.append(order_id)
        
        # Process each order with optimized methods
        for order in order_objects:
            if order.side == OrderSide.BUY:
                self.matcher.match_buy_order(order)
            else:
                self.matcher.match_sell_order(order)
        
        return order_ids
    
    def cancel_order(self, order_id: int) -> bool:
        """
        Cancel an order by its ID.
        
        Args:
            order_id: The ID of the order to cancel
            
        Returns:
            True if the order was cancelled, False otherwise
        """
        # Get order book from matcher
        order_book = self.matcher.order_book
        
        # Direct optimization of order cancellation
        order_dict = order_book.orders_by_id
        if order_id not in order_dict:
            return False
            
        order = order_dict[order_id]
        price_map = order_book.order_price_map
        
        # Get the price level
        price_value = price_map.get(order_id)
        if price_value is None:
            return False
            
        # Determine which price level dictionary to use
        if order.side == OrderSide.BUY:
            price_levels = order_book.buy_price_levels
        else:
            price_levels = order_book.sell_price_levels
            
        # Get the price level
        price_level = price_levels.get(price_value)
        if not price_level:
            return False
            
        # Find and remove the order
        for i, o in enumerate(price_level.orders):
            if o.id == order_id:
                price_level.orders.pop(i)
                price_level.is_dirty = True
                break
        else:
            # Order not found in price level
            return False
            
        # Remove from lookup dictionaries
        del order_dict[order_id]
        del price_map[order_id]
        
        # Check if price level is now empty
        if not price_level.orders:
            del price_levels[price_value]
            
            # Remove from cache if present
            cache_key = (id(price_levels), price_value)
            cache = order_book._price_level_cache
            if cache_key in cache:
                del cache[cache_key]
        
        # Update order status and recycle
        order.status = OrderStatus.CANCELLED
        if len(self._order_pool) < self._max_order_pool_size:
            self._order_pool.append(order)
            
        return True
        
    def get_order_pool_stats(self) -> Dict[str, int]:
        """Get statistics about the order pool."""
        return {
            "order_pool_size": len(self._order_pool),
            "max_order_pool_size": self._max_order_pool_size
        } 