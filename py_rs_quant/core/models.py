"""
Data models for the matching engine.
"""
import time
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


class Trade:
    """Trade model representing an executed trade between two orders."""
    # Ordered for cache line efficiency
    __slots__ = [
        'trade_id', 'buy_order_id', 'sell_order_id',  # IDs are accessed most
        'price', 'quantity',                          # Trade details
        'timestamp', 'symbol'                         # Metadata
    ]
    
    def __init__(self, 
                 trade_id: int, 
                 buy_order_id: int, 
                 sell_order_id: int, 
                 price: float, 
                 quantity: float,
                 symbol: Optional[str] = None,
                 timestamp: int = 0):
        """Initialize a trade."""
        # Frequently accessed fields
        self.trade_id = trade_id
        self.buy_order_id = buy_order_id
        self.sell_order_id = sell_order_id
        
        # Trade details
        self.price = price
        self.quantity = quantity
        
        # Metadata
        self.timestamp = timestamp
        self.symbol = symbol
        
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (f"Trade(id={self.trade_id}, buy_id={self.buy_order_id}, "
                f"sell_id={self.sell_order_id}, price={self.price}, qty={self.quantity})")


class PriceLevel:
    """Price level model representing all orders at a specific price."""
    # Optimize field order for cache efficiency
    __slots__ = [
        'price', 'orders', 'total_qty_cache', 'is_dirty'
    ]
    
    def __init__(self, price: float):
        """Initialize a price level."""
        self.price = price
        self.orders: List[Order] = []
        self.total_qty_cache: float = 0.0
        self.is_dirty: bool = False
        
    def add_order(self, order: Order) -> None:
        """Add an order to this price level."""
        self.orders.append(order)
        self.total_qty_cache += order.remaining_quantity
        
    def remove_order(self, order_id: int) -> bool:
        """Remove an order from this price level."""
        for i, order in enumerate(self.orders):
            if order.id == order_id:
                removed = self.orders.pop(i)
                self.is_dirty = True  # Mark for total quantity recalculation
                return True
        return False
    
    def get_total_quantity(self) -> float:
        """Get the total quantity of all orders at this price level."""
        if self.is_dirty:
            # Recalculate the total quantity
            self.total_qty_cache = sum(order.remaining_quantity for order in self.orders)
            self.is_dirty = False
        return self.total_qty_cache
    
    def __len__(self) -> int:
        """Number of orders at this price level."""
        return len(self.orders)
    
    def __bool__(self) -> bool:
        """Check if there are any orders at this price level."""
        return bool(self.orders)
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"PriceLevel(price={self.price}, orders={len(self.orders)}, qty={self.get_total_quantity()})"


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