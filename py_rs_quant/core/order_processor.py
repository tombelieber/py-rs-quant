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
    Optimized for high-performance with minimal allocation overhead.
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
    
    def create_order(self, 
                    side: OrderSide, 
                    order_type: OrderType,
                    price: Optional[float], 
                    quantity: float,
                    timestamp: Optional[int] = None, 
                    symbol: Optional[str] = None) -> Order:
        """
        Create an order object with minimal allocation overhead.
        
        Args:
            side: Buy or sell side
            order_type: Market or limit order type
            price: Limit price (None for market orders)
            quantity: Order quantity
            timestamp: Optional timestamp (milliseconds since epoch)
            symbol: Optional trading symbol
            
        Returns:
            The created Order object
        """
        order_id = self.next_order_id
        self.next_order_id += 1
        ts = timestamp or int(time.time() * 1000)
        
        # Only log in debug mode with lazy evaluation
        if __debug__ and logger.isEnabledFor(logging.DEBUG):
            order_type_name = order_type.name
            side_name = side.name
            price_str = f", price={price}" if price is not None else ""
            logger.debug(f"Creating {order_type_name} {side_name} order: id={order_id}{price_str}, qty={quantity}, symbol={symbol or ''}")
        
        # Create order from pool if available to reduce GC pressure
        if self._order_pool:
            order = self._order_pool.pop()
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
            order = Order(order_id, side, order_type, price, quantity, ts, symbol)
            
        return order
    
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
        # Create order object
        order = self.create_order(
            side=side,
            order_type=OrderType.LIMIT,
            price=price,
            quantity=quantity,
            timestamp=timestamp,
            symbol=symbol
        )
        
        # Process the order through the matcher
        if side == OrderSide.BUY:
            self.matcher.match_buy_order(order)
        else:
            self.matcher.match_sell_order(order)
        
        return order.id
    
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
        # Create order object
        order = self.create_order(
            side=side,
            order_type=OrderType.MARKET,
            price=None,
            quantity=quantity,
            timestamp=timestamp,
            symbol=symbol
        )
        
        # Process the order through the matcher
        if side == OrderSide.BUY:
            self.matcher.match_buy_order(order)
        else:
            self.matcher.match_sell_order(order)
        
        return order.id
    
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
            
            # Create order
            order = self.create_order(
                side=side,
                order_type=order_type,
                price=price,
                quantity=quantity,
                timestamp=ts,
                symbol=symbol
            )
                
            order_objects.append(order)
            order_ids.append(order.id)
        
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
        
        # Early exit if order not found
        if order_id not in order_book.orders_by_id:
            return False
            
        order = order_book.orders_by_id[order_id]
        
        # Remove from order book
        removed_order = order_book.remove_order(order_id)
        if not removed_order:
            return False
        
        # Update order status and recycle
        order.status = OrderStatus.CANCELLED
        self._recycle_order(order)
            
        return True
    
    def _recycle_order(self, order: Order) -> None:
        """
        Return an order to the object pool for reuse.
        
        Args:
            order: The order to recycle
        """
        if len(self._order_pool) < self._max_order_pool_size:
            self._order_pool.append(order)
    
    def get_order_pool_stats(self) -> Dict[str, int]:
        """Get statistics about the order pool."""
        return {
            "order_pool_size": len(self._order_pool),
            "max_order_pool_size": self._max_order_pool_size
        } 