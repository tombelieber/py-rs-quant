"""
Data models for the matching engine.
"""
import time
import array
import numpy as np
from typing import Optional, List, Dict, Any, Tuple

from py_rs_quant.core.enums import OrderSide, OrderType, OrderStatus

# Struct-like array for ultra-fast quantity operations
class QuantityArray:
    """Array-based storage for order quantities to optimize cache locality."""
    __slots__ = ['data', 'capacity', 'size']
    
    def __init__(self, capacity: int = 1024):
        """Initialize with fixed capacity."""
        # Use numpy array for SIMD vectorization
        self.data = np.zeros((capacity, 3), dtype=np.float64)  # [quantity, filled, remaining]
        self.capacity = capacity
        self.size = 0
    
    def add(self, quantity: float) -> int:
        """Add a new quantity record and return its index."""
        if self.size >= self.capacity:
            self._grow()
        
        idx = self.size
        self.data[idx, 0] = quantity  # Total quantity
        self.data[idx, 1] = 0.0       # Filled quantity
        self.data[idx, 2] = quantity  # Remaining quantity
        self.size += 1
        return idx
    
    def update_filled(self, idx: int, match_qty: float) -> None:
        """Update filled and remaining quantities after a match."""
        self.data[idx, 1] += match_qty  # Increase filled
        self.data[idx, 2] -= match_qty  # Decrease remaining
    
    def get_remaining(self, idx: int) -> float:
        """Get remaining quantity."""
        return self.data[idx, 2]
    
    def get_filled(self, idx: int) -> float:
        """Get filled quantity."""
        return self.data[idx, 1]
    
    def _grow(self) -> None:
        """Increase capacity when full."""
        new_capacity = self.capacity * 2
        new_data = np.zeros((new_capacity, 3), dtype=np.float64)
        new_data[:self.size] = self.data[:self.size]
        self.data = new_data
        self.capacity = new_capacity


class Trade:
    """
    Represents a trade between two orders.
    """
    __slots__ = ['trade_id', 'buy_order_id', 'sell_order_id', 'price', 'quantity', 'timestamp', 'symbol']
    
    def __init__(self, trade_id: int, buy_order_id: int, sell_order_id: int, price: float, quantity: float, symbol: Optional[str] = None, timestamp: Optional[int] = None) -> None:
        self.trade_id = trade_id
        self.buy_order_id = buy_order_id
        self.sell_order_id = sell_order_id
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp or int(time.time() * 1000)
        self.symbol = symbol
        
    def __repr__(self) -> str:
        return f"Trade(id={self.trade_id}, buy_id={self.buy_order_id}, sell_id={self.sell_order_id}, price={self.price}, qty={self.quantity})"


class Order:
    """Order model representing a buy or sell order in the order book."""
    # Ordered for cache line efficiency: frequently accessed fields first
    __slots__ = [
        'id', 'remaining_quantity', 'price', 'side',  # Most frequently accessed
        'filled_quantity', 'quantity', 'status',      # Moderate access frequency
        'order_type', 'timestamp', 'symbol'           # Less frequently accessed
    ]
    
    def __init__(self, 
                 id: int, 
                 side: OrderSide, 
                 order_type: OrderType, 
                 price: Optional[float], 
                 quantity: float, 
                 timestamp: int = 0,
                 symbol: Optional[str] = None):
        """Initialize an order."""
        # Frequently accessed fields
        self.id = id
        self.remaining_quantity = quantity
        self.price = price
        self.side = side
        
        # Moderate access frequency
        self.filled_quantity = 0.0
        self.quantity = quantity
        self.status = OrderStatus.NEW
        
        # Less frequently accessed
        self.order_type = order_type
        self.timestamp = timestamp
        self.symbol = symbol
        
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (f"Order(id={self.id}, side={self.side.name}, type={self.order_type.name}, "
                f"price={self.price}, qty={self.quantity}, filled={self.filled_quantity}, "
                f"remaining={self.remaining_quantity}, status={self.status.name})")


class PriceLevel:
    """Price level for aggregating orders at the same price."""
    
    def __init__(self, price: float, use_arrays: bool = False):
        """Initialize with the price for this level."""
        self.price = price
        self.orders = []
        self.total_qty_cache = 0.0  # Cache for total quantity
        self.is_dirty = True  # Flag to indicate if cache needs update
        
        # Optional array-based storage for ultra-performance
        self._using_arrays = use_arrays
        self._array_quantities = QuantityArray(64) if use_arrays else None
    
    def add_order(self, order):
        """Add an order to this price level."""
        self.orders.append(order)
        self.total_qty_cache += order.remaining_quantity
        
    def remove_order(self, order_id):
        """Remove an order from this price level by ID."""
        for i, order in enumerate(self.orders):
            if order.id == order_id:
                self.orders.pop(i)
                self.is_dirty = True  # Invalidate cache
                return order
        return None
    
    def update_qty_cache(self):
        """Update the cached total quantity if needed."""
        if self.is_dirty:
            self.total_qty_cache = sum(order.remaining_quantity for order in self.orders)
            self.is_dirty = False
    
    def total_quantity(self):
        """Get the total quantity at this price level."""
        self.update_qty_cache()
        return self.total_qty_cache
    
    def __repr__(self) -> str:
        return f"PriceLevel(price={self.price}, orders={len(self.orders)}, qty={self.total_quantity()})"


# Cache statistics class
class CacheStats:
    """Statistics for cache performance."""
    __slots__ = ['hits', 'misses', 'total']
    
    def __init__(self):
        """Initialize cache statistics."""
        self.hits = 0
        self.misses = 0
        self.total = 0
        
    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hits += 1
        self.total += 1
        
    def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses += 1
        self.total += 1
        
    def hit_ratio(self) -> float:
        """Calculate the cache hit ratio."""
        if self.total == 0:
            return 0.0
        return self.hits / self.total
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total": self.total,
            "hit_ratio": self.hit_ratio()
        } 