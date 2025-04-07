"""
Order book implementation for the matching engine.
"""
from typing import Dict, List, Optional, Tuple, Any
from sortedcontainers import SortedDict
import logging
import time

from py_rs_quant.core.enums import OrderSide
from py_rs_quant.core.models import Order, PriceLevel

logger = logging.getLogger(__name__)


class OrderBook:
    """
    Manages the order book for a single instrument.
    Handles adding and removing orders at price levels.
    
    Optimized for high-performance trading with minimal overhead.
    """
    
    __slots__ = (
        'buy_price_levels', 'sell_price_levels', 'orders_by_id', 
        'order_price_map', '_price_level_cache', '_cache_hits', 
        '_cache_misses', '_max_cache_size'
    )
    
    def __init__(self):
        # Use SortedDict for more efficient order book operations
        # For buy orders (highest price first), we'll use negative price as the key
        self.buy_price_levels = SortedDict()  # key: -price, value: PriceLevel
        # For sell orders (lowest price first)
        self.sell_price_levels = SortedDict()  # key: price, value: PriceLevel
        
        # Lookups for faster access to orders
        self.orders_by_id = {}  # Dict mapping order_id to Order
        self.order_price_map = {}  # Dict mapping order_id to price for faster cancellation
        
        # Price level caching
        self._price_level_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._max_cache_size = 100
    
    def add_order(self, order: Order) -> None:
        """
        Add an order to the book with optimized performance.
        
        Args:
            order: The order to add
        """
        # Add to lookup maps
        self.orders_by_id[order.id] = order
        
        if order.side == OrderSide.BUY:
            neg_price = -order.price  # Negate for correct sorting (highest price first)
            price_dict = self.buy_price_levels
            
            # Direct dictionary lookup with conditional price level creation
            if neg_price in price_dict:
                price_level = price_dict[neg_price]
            else:
                # Create new price level
                price_level = PriceLevel(neg_price)
                price_dict[neg_price] = price_level
                
                # Cache for frequently accessed price levels
                cache_key = (id(price_dict), neg_price)
                if len(self._price_level_cache) < self._max_cache_size:
                    self._price_level_cache[cache_key] = price_level
            
            # Add to price level and price map
            price_level.orders.append(order)
            price_level.total_qty_cache += order.remaining_quantity
            self.order_price_map[order.id] = neg_price
        else:  # SELL order
            price = order.price
            price_dict = self.sell_price_levels
            
            # Direct dictionary lookup with conditional price level creation
            if price in price_dict:
                price_level = price_dict[price]
            else:
                # Create new price level
                price_level = PriceLevel(price)
                price_dict[price] = price_level
                
                # Cache for frequently accessed price levels
                cache_key = (id(price_dict), price)
                if len(self._price_level_cache) < self._max_cache_size:
                    self._price_level_cache[cache_key] = price_level
            
            # Add to price level and price map
            price_level.orders.append(order)
            price_level.total_qty_cache += order.remaining_quantity
            self.order_price_map[order.id] = price
    
    def remove_order(self, order_id: int) -> Optional[Order]:
        """
        Remove an order from the book with optimized performance.
        
        Args:
            order_id: The ID of the order to remove
            
        Returns:
            The removed order or None if not found
        """
        # Fast fail if order doesn't exist
        if order_id not in self.orders_by_id:
            return None
            
        order = self.orders_by_id[order_id]
        price = self.order_price_map.get(order_id)
        
        if price is None:
            return None
            
        # Select the right price book based on order side
        if order.side == OrderSide.BUY:
            price_dict = self.buy_price_levels
        else:
            price_dict = self.sell_price_levels
            
        cache_key = (id(price_dict), price)
        
        # Get price level directly from dictionary
        price_level = price_dict.get(price)
        if not price_level:
            return None
            
        # Try to remove order from price level
        removed = False
        for i, o in enumerate(price_level.orders):
            if o.id == order_id:
                price_level.orders.pop(i)
                price_level.is_dirty = True  # Flag cache as dirty
                removed = True
                break
                
        if not removed:
            return None
            
        # Clean up empty price levels
        if not price_level.orders:
            del price_dict[price]
            if cache_key in self._price_level_cache:
                del self._price_level_cache[cache_key]
                
        # Remove from lookup dictionaries
        del self.order_price_map[order_id]
        del self.orders_by_id[order_id]
        
        return order
    
    def get_order(self, order_id: int) -> Optional[Order]:
        """Get an order by its ID."""
        return self.orders_by_id.get(order_id)
    
    def get_orders_at_price(self, side: OrderSide, price: float) -> List[Order]:
        """Get all orders at a specific price level."""
        if side == OrderSide.BUY:
            neg_price = -price
            if neg_price in self.buy_price_levels:
                price_level = self.buy_price_levels[neg_price]
                return price_level.orders.copy()
        else:
            if price in self.sell_price_levels:
                price_level = self.sell_price_levels[price]
                return price_level.orders.copy()
            
        return []
    
    def get_price_levels(self, side: OrderSide) -> List[Tuple[float, float]]:
        """
        Get all price levels for a side.
        
        Returns:
            List of (price, quantity) tuples
        """
        result = []
        
        if side == OrderSide.BUY:
            for neg_price in self.buy_price_levels:
                price_level = self.buy_price_levels[neg_price]
                result.append((-neg_price, price_level.get_total_quantity()))
        else:
            for price in self.sell_price_levels:
                price_level = self.sell_price_levels[price]
                result.append((price, price_level.get_total_quantity()))
                
        return result
    
    def get_order_book_snapshot(self) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """
        Get a snapshot of the current order book.
        
        Returns:
            Tuple of (buy_orders, sell_orders) where each is a list of (price, quantity) tuples
        """
        return self.get_price_levels(OrderSide.BUY), self.get_price_levels(OrderSide.SELL)
    
    def get_snapshot(self) -> Dict[str, Any]:
        """
        Get a comprehensive snapshot of the order book in dictionary format.
        
        Returns:
            Dictionary with buy and sell sides, each containing lists of price levels
            with detailed information including price, quantity, and number of orders
        """
        buy_levels, sell_levels = self.get_order_book_snapshot()
        
        # Create a more detailed representation
        return {
            "timestamp": int(time.time() * 1000),
            "buy_side": [
                {"price": price, "quantity": quantity, "order_count": len(self.get_orders_at_price(OrderSide.BUY, price))}
                for price, quantity in buy_levels
            ],
            "sell_side": [
                {"price": price, "quantity": quantity, "order_count": len(self.get_orders_at_price(OrderSide.SELL, price))}
                for price, quantity in sell_levels
            ],
            "spread": sell_levels[0][0] - buy_levels[0][0] if sell_levels and buy_levels else None,
            "mid_price": (sell_levels[0][0] + buy_levels[0][0]) / 2 if sell_levels and buy_levels else None,
            "total_orders": len(self.orders_by_id)
        }
    
    def clear_caches(self) -> None:
        """
        Clear caches to free memory.
        Call this periodically if memory usage is a concern.
        """
        self._price_level_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cache performance."""
        total_lookups = self._cache_hits + self._cache_misses
        hit_ratio = self._cache_hits / total_lookups if total_lookups > 0 else 0.0
        
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_ratio": hit_ratio,
            "cache_size": len(self._price_level_cache),
            "max_cache_size": self._max_cache_size
        } 