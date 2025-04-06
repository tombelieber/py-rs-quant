"""
Python implementation of the matching engine.
"""
from enum import Enum, auto
import time
from typing import Dict, List, Optional, Tuple, Union, Callable, Iterable, Any
import heapq
from collections import defaultdict
from sortedcontainers import SortedDict  # For efficient order book management
import numpy as np
from numba import jit
import logging

# For now, use a Python implementation only
RUST_ENGINE_AVAILABLE = False

logger = logging.getLogger(__name__)

class OrderSide(Enum):
    BUY = 1
    SELL = 2


class OrderType(Enum):
    MARKET = 1
    LIMIT = 2


class OrderStatus(Enum):
    NEW = 1
    PARTIALLY_FILLED = 2
    FILLED = 3
    CANCELLED = 4
    REJECTED = 5


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
    """
    Represents an order in the order book.
    """
    __slots__ = ['id', 'side', 'order_type', 'price', 'quantity', 'filled_quantity', 'status', 'timestamp', 'symbol', 'remaining_quantity']
    
    def __init__(self, order_id: int, side: OrderSide, order_type: OrderType, price: Optional[float], quantity: float, timestamp: Optional[int] = None, symbol: Optional[str] = None) -> None:
        self.id = order_id
        self.side = side
        self.order_type = order_type
        self.price = price
        self.quantity = quantity
        self.filled_quantity = 0.0
        self.status = OrderStatus.NEW
        self.timestamp = timestamp or int(time.time() * 1000)
        self.symbol = symbol
        self.remaining_quantity = quantity  # Cache remaining quantity for performance
        
    def __repr__(self) -> str:
        price_str = f", price={self.price}" if self.price is not None else ""
        return f"Order(id={self.id}, side={self.side}, type={self.order_type}{price_str}, qty={self.quantity}, filled={self.filled_quantity})"


class PriceLevel:
    """Price level for aggregating orders at the same price."""
    
    def __init__(self, price: float):
        """Initialize with the price for this level."""
        self.price = price
        self.orders = []
        self.total_qty_cache = 0.0  # Cache for total quantity
        self.is_dirty = True  # Flag to indicate if cache needs update
    
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


class MatchingEngine:
    """
    Matching Engine class for order matching.
    """
    
    def __init__(self, use_rust: bool = False):
        # For now, ignore use_rust parameter since we're using Python implementation
        self.use_rust = False
        logger.info(f"Initializing MatchingEngine (use_rust={use_rust}, but using Python implementation)")
        self.next_order_id = 1
        self.next_trade_id = 1
        
        # Use SortedDict for more efficient order book operations
        # For buy orders (highest price first), we'll use negative price as the key
        self.buy_price_levels = SortedDict()  # key: -price, value: PriceLevel
        # For sell orders (lowest price first)
        self.sell_price_levels = SortedDict()  # key: price, value: PriceLevel
        
        # Lookups for faster access to orders
        self.orders_by_id = {}  # Dict mapping order_id to Order
        self.order_price_map = {}  # Dict mapping order_id to price for faster cancellation
        
        self.trades = []
        self.trade_callback = None
        
        # Object recycling pools for reducing GC pressure
        self._trade_pool = []
        self._order_pool = []
        self._max_trade_pool_size = 1000
        self._max_order_pool_size = 2000
        
        # Price level caching
        self._price_level_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._max_cache_size = 100
        
        # Reusable arrays for order removal
        self._orders_to_remove = []
    
    def register_trade_callback(self, callback: Callable) -> None:
        """Register a callback to be called when a trade is executed."""
        self.trade_callback = callback
    
    def get_order_from_pool(self, order_id: int, side: OrderSide, order_type: OrderType, 
                           price: Optional[float], quantity: float, 
                           timestamp: Optional[int] = None, symbol: Optional[str] = None) -> Order:
        """Get an order object from the pool or create a new one."""
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
            order.timestamp = timestamp or int(time.time() * 1000)
            order.symbol = symbol
            return order
        
        # Create new if pool is empty
        return Order(order_id, side, order_type, price, quantity, timestamp, symbol)
    
    def add_limit_order(self, side: OrderSide, price: float, quantity: float, timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """Add a limit order to the order book."""
        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        order_id = self.next_order_id
        self.next_order_id += 1
        
        logger.debug(f"Adding limit order: id={order_id}, side={side.name}, price={price}, qty={quantity}, symbol={symbol}")
        
        # Get order from pool or create new
        order = self.get_order_from_pool(order_id, side, OrderType.LIMIT, price, quantity, ts, symbol)
        self.orders_by_id[order_id] = order
        
        # For limit orders that can cross immediately, store the price for efficient lookup
        if side == OrderSide.BUY:
            self.order_price_map[order_id] = -price  # Negate for correct sorting
        else:
            self.order_price_map[order_id] = price
        
        # Process the order (match or add to book)
        self._process_order(order)
        
        return order_id
    
    def add_market_order(self, side: OrderSide, quantity: float, timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """Add a market order to the order book."""
        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        order_id = self.next_order_id
        self.next_order_id += 1
        
        logger.debug(f"Adding market order: id={order_id}, side={side.name}, qty={quantity}, symbol={symbol}")
        
        # Get order from pool or create new
        order = self.get_order_from_pool(order_id, side, OrderType.MARKET, None, quantity, ts, symbol)
        self.orders_by_id[order_id] = order
        
        # Process the order (match or add to book)
        self._process_order(order)
        
        return order_id
    
    def batch_add_orders(self, orders: List[Tuple[OrderSide, OrderType, Optional[float], float, Optional[int], Optional[str]]]) -> List[int]:
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
            order = self.get_order_from_pool(order_id, side, order_type, price, quantity, ts, symbol)
            self.orders_by_id[order_id] = order
            order_objects.append(order)
            order_ids.append(order_id)
        
        # Batch process orders using optimized matching
        self.batch_match(order_objects)
        
        return order_ids
    
    def batch_match(self, orders_to_match: List[Order]) -> None:
        """
        Pre-sort and batch match orders for better efficiency.
        
        Args:
            orders_to_match: List of orders to match
        """
        # Group by side
        buy_orders = [o for o in orders_to_match if o.side == OrderSide.BUY]
        sell_orders = [o for o in orders_to_match if o.side == OrderSide.SELL]
        
        # Skip if no orders
        if not buy_orders and not sell_orders:
            return
        
        # Sort by priority (market orders first, then by price)
        if buy_orders:
            buy_orders.sort(key=lambda o: (
                0 if o.order_type == OrderType.MARKET else 1,
                -(o.price or float('-inf')),
                o.timestamp
            ))
        
        if sell_orders:
            sell_orders.sort(key=lambda o: (
                0 if o.order_type == OrderType.MARKET else 1,
                o.price or float('inf'),
                o.timestamp
            ))
        
        # Process in optimized order
        for order in buy_orders:
            self._process_buy_order(order)
        
        for order in sell_orders:
            self._process_sell_order(order)
    
    def _process_order(self, order: Order) -> None:
        """Process an order (match or add to book)."""
        try:
            if order.side == OrderSide.BUY:
                self._process_buy_order(order)
            else:  # SELL order
                self._process_sell_order(order)
        except Exception as e:
            logger.error(f"Error processing order: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Ensure the order doesn't get lost if there's an error
            if order.order_type == OrderType.LIMIT and order.remaining_quantity > 0:
                if order.side == OrderSide.BUY:
                    price_key = -order.price
                    price_level = self._get_or_create_price_level(self.buy_price_levels, price_key)
                else:
                    price_key = order.price
                    price_level = self._get_or_create_price_level(self.sell_price_levels, price_key)
                
                price_level.add_order(order)
                self.order_price_map[order.id] = price_key
    
    def _get_or_create_price_level(self, price_dict: SortedDict, price: float, create_new: bool = True) -> Optional[PriceLevel]:
        """
        Get or create a price level with caching for hot price points.
        
        Args:
            price_dict: Dictionary of price levels
            price: Price to look up
            create_new: Whether to create a new price level if not found
            
        Returns:
            The price level or None if not found and create_new is False
        """
        # Check cache first
        cache_key = (id(price_dict), price)
        
        if cache_key in self._price_level_cache:
            self._cache_hits += 1
            return self._price_level_cache[cache_key]
        
        self._cache_misses += 1
        
        # Not in cache, look in dictionary
        if price in price_dict:
            level = price_dict[price]
        elif create_new:
            level = PriceLevel(price)
            price_dict[price] = level
        else:
            return None
        
        # Add to cache if not full
        if len(self._price_level_cache) < self._max_cache_size:
            self._price_level_cache[cache_key] = level
        
        return level
    
    def _process_buy_order(self, order: Order) -> None:
        """Process a buy order efficiently."""
        # Try to match against sell orders
        if order.order_type == OrderType.MARKET:
            # Market orders match against any sell order
            self._orders_to_remove.clear()
            
            for price in self.sell_price_levels:
                if order.remaining_quantity <= 0:
                    break
                    
                price_level = self._get_or_create_price_level(self.sell_price_levels, price, create_new=False)
                if not price_level:
                    continue
                    
                self._match_at_price_level(order, price_level)
                
                # Mark for removal if empty
                if not price_level.orders:
                    self._orders_to_remove.append(price)
            
            # Remove empty price levels in batch
            for price in self._orders_to_remove:
                del self.sell_price_levels[price]
                # Remove from cache if present
                cache_key = (id(self.sell_price_levels), price)
                if cache_key in self._price_level_cache:
                    del self._price_level_cache[cache_key]
                    
        else:
            # Limit orders match only if price is acceptable
            self._orders_to_remove.clear()
            
            for price in self.sell_price_levels:
                if price > order.price or order.remaining_quantity <= 0:
                    break
                    
                price_level = self._get_or_create_price_level(self.sell_price_levels, price, create_new=False)
                if not price_level:
                    continue
                    
                self._match_at_price_level(order, price_level)
                
                # Mark for removal if empty
                if not price_level.orders:
                    self._orders_to_remove.append(price)
            
            # Remove empty price levels in batch
            for price in self._orders_to_remove:
                del self.sell_price_levels[price]
                # Remove from cache if present
                cache_key = (id(self.sell_price_levels), price)
                if cache_key in self._price_level_cache:
                    del self._price_level_cache[cache_key]
        
        # If it's a limit order and not fully filled, add to the order book
        if order.order_type == OrderType.LIMIT and order.remaining_quantity > 0:
            neg_price = -order.price  # Negate for correct sorting (highest price first)
            
            # Get or create the price level
            price_level = self._get_or_create_price_level(self.buy_price_levels, neg_price)
                
            # Add the order to the price level
            price_level.add_order(order)
            self.order_price_map[order.id] = neg_price
    
    def _process_sell_order(self, order: Order) -> None:
        """Process a sell order efficiently."""
        # Try to match against buy orders
        if order.order_type == OrderType.MARKET:
            # Market orders match against any buy order
            self._orders_to_remove.clear()
            
            for neg_price in self.buy_price_levels:
                if order.remaining_quantity <= 0:
                    break
                    
                price_level = self._get_or_create_price_level(self.buy_price_levels, neg_price, create_new=False)
                if not price_level:
                    continue
                    
                self._match_at_price_level(order, price_level)
                
                # Mark for removal if empty
                if not price_level.orders:
                    self._orders_to_remove.append(neg_price)
            
            # Remove empty price levels in batch
            for neg_price in self._orders_to_remove:
                del self.buy_price_levels[neg_price]
                # Remove from cache if present
                cache_key = (id(self.buy_price_levels), neg_price)
                if cache_key in self._price_level_cache:
                    del self._price_level_cache[cache_key]
                    
        else:
            # Limit orders match only if price is acceptable
            self._orders_to_remove.clear()
            
            for neg_price in self.buy_price_levels:
                price = -neg_price
                if price < order.price or order.remaining_quantity <= 0:
                    break
                    
                price_level = self._get_or_create_price_level(self.buy_price_levels, neg_price, create_new=False)
                if not price_level:
                    continue
                    
                self._match_at_price_level(order, price_level)
                
                # Mark for removal if empty
                if not price_level.orders:
                    self._orders_to_remove.append(neg_price)
            
            # Remove empty price levels in batch
            for neg_price in self._orders_to_remove:
                del self.buy_price_levels[neg_price]
                # Remove from cache if present
                cache_key = (id(self.buy_price_levels), neg_price)
                if cache_key in self._price_level_cache:
                    del self._price_level_cache[cache_key]
        
        # If it's a limit order and not fully filled, add to the order book
        if order.order_type == OrderType.LIMIT and order.remaining_quantity > 0:
            # Get or create the price level
            price_level = self._get_or_create_price_level(self.sell_price_levels, order.price)
                
            # Add the order to the price level
            price_level.add_order(order)
            self.order_price_map[order.id] = order.price
    
    def _match_at_price_level(self, active_order: Order, price_level: PriceLevel) -> None:
        """
        Match an active order against a price level.
        
        Args:
            active_order: The order to match
            price_level: The price level to match against
        """
        try:
            # First check that parameters are of the correct type
            if not isinstance(price_level, PriceLevel) or not isinstance(active_order, Order):
                logger.error(f"Invalid parameters to _match_at_price_level: active_order={type(active_order)}, price_level={type(price_level)}")
                return
                
            # Safety check to prevent infinite recursion
            if not hasattr(price_level, 'orders') or len(price_level.orders) == 0 or active_order.remaining_quantity <= 0:
                return
            
            # Match against resting orders in the price level
            for resting_order in list(price_level.orders):  # Make a copy to prevent concurrent modification
                # Skip if either order is fully matched
                if active_order.remaining_quantity <= 0 or resting_order.remaining_quantity <= 0:
                    continue
                
                # Determine the quantity to match
                match_quantity = min(active_order.remaining_quantity, resting_order.remaining_quantity)
                
                # Determine the match price (price of the resting order)
                match_price = price_level.price if resting_order.side == OrderSide.SELL else -price_level.price
                
                # Execute the trade
                self._execute_trade(
                    buy_id=active_order.id if active_order.side == OrderSide.BUY else resting_order.id,
                    sell_id=active_order.id if active_order.side == OrderSide.SELL else resting_order.id,
                    price=abs(match_price),
                    quantity=match_quantity,
                    timestamp=max(active_order.timestamp, resting_order.timestamp),
                    active_order=active_order,
                    resting_order=resting_order
                )
                
                # Remove fully matched resting orders
                if resting_order.remaining_quantity <= 0:
                    price_level.remove_order(resting_order.id)
                    if resting_order.id in self.orders_by_id:
                        del self.orders_by_id[resting_order.id]
                    if resting_order.id in self.order_price_map:
                        del self.order_price_map[resting_order.id]
                
                # Break if active order is fully matched
                if active_order.remaining_quantity <= 0:
                    break
        except Exception as e:
            logger.error(f"Error matching at price level: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _execute_trade(self, buy_id: int, sell_id: int, price: float, quantity: float, timestamp: int, active_order: Order, resting_order: Order) -> None:
        """Execute a trade between two orders."""
        # Update the orders
        active_order.filled_quantity += quantity
        active_order.remaining_quantity -= quantity
        resting_order.filled_quantity += quantity
        resting_order.remaining_quantity -= quantity
        
        # Update order statuses
        if active_order.filled_quantity >= active_order.quantity:
            active_order.status = OrderStatus.FILLED
            # Remove from price map if filled
            if active_order.id in self.order_price_map:
                del self.order_price_map[active_order.id]
        else:
            active_order.status = OrderStatus.PARTIALLY_FILLED
            
        if resting_order.filled_quantity >= resting_order.quantity:
            resting_order.status = OrderStatus.FILLED
            # Remove from price map if filled
            if resting_order.id in self.order_price_map:
                del self.order_price_map[resting_order.id]
        else:
            resting_order.status = OrderStatus.PARTIALLY_FILLED
        
        # Create a trade record - reuse from pool if available
        if self._trade_pool:
            trade = self._trade_pool.pop()
            trade.trade_id = self.next_trade_id
            trade.buy_order_id = buy_id
            trade.sell_order_id = sell_id
            trade.price = price
            trade.quantity = quantity
            trade.symbol = active_order.symbol
            trade.timestamp = timestamp
        else:
            trade = Trade(
                trade_id=self.next_trade_id,
                buy_order_id=buy_id,
                sell_order_id=sell_id,
                price=price,
                quantity=quantity,
                symbol=active_order.symbol,
                timestamp=timestamp
            )
        self.next_trade_id += 1
        
        # Add to trades list
        self.trades.append(trade)
        
        # Call the trade callback if registered
        if self.trade_callback:
            self.trade_callback(trade)
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancel an order by its ID."""
        if order_id not in self.orders_by_id or order_id not in self.order_price_map:
            return False
            
        order = self.orders_by_id[order_id]
        price = self.order_price_map[order_id]
        
        # Determine which book to search
        if order.side == OrderSide.BUY:
            price_level = self._get_or_create_price_level(self.buy_price_levels, price, create_new=False)
            if price_level and price_level.remove_order(order_id):
                # If the price level is now empty, remove it
                if not price_level.orders:
                    del self.buy_price_levels[price]
                    # Also remove from cache
                    cache_key = (id(self.buy_price_levels), price)
                    if cache_key in self._price_level_cache:
                        del self._price_level_cache[cache_key]
                    
                # Update order status
                order.status = OrderStatus.CANCELLED
                
                # Add to order pool for reuse
                if len(self._order_pool) < self._max_order_pool_size:
                    self._order_pool.append(order)
                
                # Remove from lookups
                del self.order_price_map[order_id]
                del self.orders_by_id[order_id]
                return True
        else:  # SELL order
            price_level = self._get_or_create_price_level(self.sell_price_levels, price, create_new=False)
            if price_level and price_level.remove_order(order_id):
                # If the price level is now empty, remove it
                if not price_level.orders:
                    del self.sell_price_levels[price]
                    # Also remove from cache
                    cache_key = (id(self.sell_price_levels), price)
                    if cache_key in self._price_level_cache:
                        del self._price_level_cache[cache_key]
                    
                # Update order status
                order.status = OrderStatus.CANCELLED
                
                # Add to order pool for reuse
                if len(self._order_pool) < self._max_order_pool_size:
                    self._order_pool.append(order)
                
                # Remove from lookups
                del self.order_price_map[order_id]
                del self.orders_by_id[order_id]
                return True
                
        return False
    
    def get_order_book_snapshot(self) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """
        Get a snapshot of the order book.
        Returns a tuple of (buy_orders, sell_orders), where each is a list of (price, quantity) tuples.
        """
        # For buy orders, combine quantities at each price level
        buy_tuples = []
        for neg_price, price_level in self.buy_price_levels.items():
            price = -neg_price  # Convert back to positive
            buy_tuples.append((price, price_level.total_quantity()))
            
        # For sell orders, combine quantities at each price level
        sell_tuples = []
        for price, price_level in self.sell_price_levels.items():
            sell_tuples.append((price, price_level.total_quantity()))
            
        return (buy_tuples, sell_tuples)
    
    def get_price_statistics(self) -> Dict[str, Any]:
        """
        Calculate price statistics for the order book using numpy.
        
        Returns:
            Dictionary of price statistics
        """
        # Extract prices and quantities from both sides of the book
        buy_prices = []
        buy_quantities = []
        for neg_price, price_level in self.buy_price_levels.items():
            price = -neg_price  # Convert back to positive
            buy_prices.append(price)
            buy_quantities.append(price_level.total_quantity())
            
        sell_prices = []
        sell_quantities = []
        for price, price_level in self.sell_price_levels.items():
            sell_prices.append(price)
            sell_quantities.append(price_level.total_quantity())
            
        # Use numpy for calculations if we have enough data
        if len(buy_prices) > 0 or len(sell_prices) > 0:
            # Convert to numpy arrays
            if buy_prices:
                buy_prices_np = np.array(buy_prices)
                buy_quantities_np = np.array(buy_quantities)
                buy_min, buy_max, buy_mean, buy_weighted, buy_std = calculate_price_stats(buy_prices_np, buy_quantities_np)
            else:
                buy_min = buy_max = buy_mean = buy_weighted = buy_std = 0.0
                
            if sell_prices:
                sell_prices_np = np.array(sell_prices)
                sell_quantities_np = np.array(sell_quantities)
                sell_min, sell_max, sell_mean, sell_weighted, sell_std = calculate_price_stats(sell_prices_np, sell_quantities_np)
            else:
                sell_min = sell_max = sell_mean = sell_weighted = sell_std = 0.0
                
            # Calculate midpoint if both sides have orders
            if buy_prices and sell_prices:
                best_bid = max(buy_prices)
                best_ask = min(sell_prices)
                midpoint = (best_bid + best_ask) / 2
                spread = best_ask - best_bid
            else:
                midpoint = 0.0
                spread = 0.0
                
            return {
                "buy_side": {
                    "min": buy_min,
                    "max": buy_max,
                    "mean": buy_mean,
                    "weighted_mean": buy_weighted,
                    "std_dev": buy_std,
                    "depth": len(buy_prices),
                    "total_quantity": sum(buy_quantities)
                },
                "sell_side": {
                    "min": sell_min,
                    "max": sell_max,
                    "mean": sell_mean,
                    "weighted_mean": sell_weighted,
                    "std_dev": sell_std,
                    "depth": len(sell_prices),
                    "total_quantity": sum(sell_quantities)
                },
                "midpoint": midpoint,
                "spread": spread
            }
        else:
            # Return default values if no prices
            return {
                "buy_side": {"min": 0.0, "max": 0.0, "mean": 0.0, "weighted_mean": 0.0, "std_dev": 0.0, "depth": 0, "total_quantity": 0.0},
                "sell_side": {"min": 0.0, "max": 0.0, "mean": 0.0, "weighted_mean": 0.0, "std_dev": 0.0, "depth": 0, "total_quantity": 0.0},
                "midpoint": 0.0,
                "spread": 0.0
            }
    
    def get_order(self, order_id: int) -> Optional[Order]:
        """Get an order by its ID."""
        return self.orders_by_id.get(order_id)
    
    def get_trades(self) -> List[Trade]:
        """Get all trades that have occurred."""
        return self.trades
    
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
    
    def clear_caches(self) -> None:
        """
        Clear caches to free memory.
        Call this periodically if memory usage is a concern.
        """
        self._price_level_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        
    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about cache performance."""
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_ratio": self._cache_hits / (self._cache_hits + self._cache_misses) if (self._cache_hits + self._cache_misses) > 0 else 0.0,
            "cache_size": len(self._price_level_cache),
            "max_cache_size": self._max_cache_size,
            "order_pool_size": len(self._order_pool),
            "trade_pool_size": len(self._trade_pool)
        } 