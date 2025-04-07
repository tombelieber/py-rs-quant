"""
Utility functions for the matching engine.
Includes performance optimizations using numba if available.
"""
import logging
from typing import Dict, Tuple, Optional, List, Any
from collections import OrderedDict

# Try to import numba for JIT compilation
try:
    from numba import njit, jit
    NUMBA_AVAILABLE = True
except ImportError:
    # Fallback implementation if numba is not available
    NUMBA_AVAILABLE = False
    # Create dummy decorators that do nothing
    def njit(func):
        return func
    def jit(func):
        return func

logger = logging.getLogger(__name__)

# JIT-compiled utility functions for critical operations
@njit(cache=True)
def min_quantity(a: float, b: float) -> float:
    """Fast minimum calculation for quantities."""
    return a if a < b else b

@njit(cache=True)
def update_quantities(order_filled: float, order_remaining: float, 
                     match_qty: float) -> Tuple[float, float]:
    """Update order quantities after a match."""
    order_filled += match_qty
    order_remaining -= match_qty
    return order_filled, order_remaining

@njit(cache=True)
def calculate_price_level_total(quantities: List[float]) -> float:
    """Calculate the total quantity at a price level."""
    total = 0.0
    for qty in quantities:
        total += qty
    return total

@njit(cache=True)
def calculate_match_price(price: float, is_neg: bool) -> float:
    """Calculate the match price, handling negated prices for buy orders."""
    return price if not is_neg else -price

@njit(cache=True)
def update_order_status(order_remaining: float, partial_status: int, filled_status: int) -> int:
    """Update an order's status based on remaining quantity."""
    return filled_status if order_remaining <= 0 else partial_status

# Cache implementation
class LRUCache:
    """Efficient LRU cache implementation using OrderedDict."""
    __slots__ = ['capacity', 'cache']
    
    def __init__(self, capacity: int = 1000):
        """Initialize the cache with a maximum capacity."""
        self.capacity = capacity
        # OrderedDict maintains insertion order and provides O(1) operations
        self.cache = OrderedDict()
    
    def get(self, key: Tuple[int, Any]) -> Optional[Any]:
        """Get an item from the cache."""
        if key not in self.cache:
            return None
        
        # Move to end (most recently used position)
        value = self.cache.pop(key)
        self.cache[key] = value
        return value
    
    def put(self, key: Tuple[int, Any], value: Any) -> None:
        """Add an item to the cache."""
        # Remove if already exists
        if key in self.cache:
            self.cache.pop(key)
        # Remove least recently used item if at capacity
        elif len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)  # Remove first item (oldest)
            
        # Add item (will be at the end - most recently used)
        self.cache[key] = value
    
    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()
    
    def size(self) -> int:
        """Return the current size of the cache."""
        return len(self.cache)
    
    def stats(self) -> Dict[str, int]:
        """Return cache statistics."""
        return {
            "size": len(self.cache),
            "capacity": self.capacity
        }

# Ultra-fast implementation of a fixed-size integer keyed cache
class ArrayCache:
    """Cache optimized for integer keys within a fixed range."""
    __slots__ = ['values', 'size', 'hit_count', 'miss_count']
    
    def __init__(self, size: int = 1024):
        """Initialize with a fixed size."""
        self.values = [None] * size
        self.size = size
        self.hit_count = 0
        self.miss_count = 0
    
    def get(self, key: int) -> Optional[Any]:
        """Get a value by key."""
        index = key % self.size
        value = self.values[index]
        
        if value is not None and value[0] == key:
            self.hit_count += 1
            return value[1]
        
        self.miss_count += 1
        return None
    
    def put(self, key: int, value: Any) -> None:
        """Store a value by key."""
        index = key % self.size
        self.values[index] = (key, value)
    
    def clear(self) -> None:
        """Clear the cache."""
        self.values = [None] * self.size
        
    def hit_ratio(self) -> float:
        """Calculate hit ratio."""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0

# JIT-compiled functions for critical paths
@jit(nopython=True)
def calculate_trade_qty(buy_remaining: float, sell_remaining: float) -> float:
    """Calculate trade quantity efficiently."""
    return min(buy_remaining, sell_remaining)


@jit(nopython=True)
def calculate_price_stats(prices, quantities):
    """Calculate price statistics efficiently."""
    if len(prices) == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    
    # Calculate weighted price
    total_qty = np.sum(quantities)
    if total_qty <= 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    
    weighted_price = np.sum(prices * quantities) / total_qty
    
    # Calculate other stats
    min_price = np.min(prices)
    max_price = np.max(prices)
    mean_price = np.mean(prices)
    
    # Calculate weighted standard deviation
    if len(prices) > 1:
        variance = np.sum(quantities * (prices - weighted_price) ** 2) / total_qty
        std_dev = np.sqrt(variance)
    else:
        std_dev = 0.0
    
    return min_price, max_price, mean_price, weighted_price, std_dev 