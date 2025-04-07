"""
Python implementation of the matching engine.
"""
import time
from typing import Dict, List, Optional, Tuple, Callable, Any
import logging

# Ensure we have the matching_engine module imported inside the namespace
import matching_engine

from py_rs_quant.core.enums import OrderSide, OrderType, OrderStatus
from py_rs_quant.core.models import Order, Trade, PriceLevel
from py_rs_quant.core.order_book import OrderBook
from py_rs_quant.core.trade_execution import TradeExecutor
from py_rs_quant.core.statistics import PriceStatisticsCalculator
from py_rs_quant.core.utils import (
    calculate_trade_qty, min_quantity, update_quantities, 
    calculate_price_level_total, calculate_match_price, update_order_status
)

logger = logging.getLogger(__name__)

# For now, use a Python implementation only
try:
    from matching_engine import PyOrderBook
    RUST_ENGINE_AVAILABLE = True
except ImportError:
    RUST_ENGINE_AVAILABLE = False

# Add this for better logging
if not RUST_ENGINE_AVAILABLE:
    logger.warning("Rust matching engine not available, using Python implementation. For better performance, install the Rust matching engine.")


class MatchingEngine:
    """
    Matching Engine class for order matching.
    """
    
    __slots__ = (
        'use_rust', 'rust_engine', 'next_order_id', 'order_book', 
        'trade_executor', '_order_pool', '_max_order_pool_size', 
        '_use_fast_path'
    )
    
    def __init__(self, use_rust: bool = False, use_fast_path: bool = True):
        self.use_rust = use_rust and RUST_ENGINE_AVAILABLE
        self._use_fast_path = use_fast_path  # Flag to control fast path usage
        
        if use_rust and not RUST_ENGINE_AVAILABLE:
            logger.warning("Rust implementation requested but not available. Using Python implementation instead.")
        
        logger.info(f"Initializing MatchingEngine (use_rust={self.use_rust}, use_fast_path={self._use_fast_path})")
        
        if self.use_rust:
            # Initialize Rust implementation
            self.rust_engine = PyOrderBook()
        
        self.next_order_id = 1
        self.order_book = OrderBook()
        self.trade_executor = TradeExecutor()
        
        # Object recycling pools for reducing GC pressure
        self._order_pool = []
        self._max_order_pool_size = 2000
    
    def register_trade_callback(self, callback: Callable) -> None:
        """Register a callback to be called when a trade is executed."""
        self.trade_executor.register_trade_callback(callback)
    
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
        # For critical path performance, avoid function calls, logging, and unnecessary operations
        order_id = self.next_order_id
        self.next_order_id += 1
        ts = timestamp or int(time.time() * 1000)  # Direct assignment is faster
        
        # Only log in debug mode with lazy evaluation to avoid string formatting overhead
        if __debug__ and logger.isEnabledFor(logging.DEBUG):
            logger.debug("Adding limit order: id=%d, side=%s, price=%f, qty=%f, symbol=%s", 
                        order_id, side.name, price, quantity, symbol or '')
        
        if self.use_rust:
            # Rust implementation (unchanged)
            try:
                rust_side = matching_engine.PyOrderSide.Buy if side == OrderSide.BUY else matching_engine.PyOrderSide.Sell
                rust_order_id = self.rust_engine.add_limit_order(rust_side, price, quantity, ts)
                return rust_order_id
            except Exception as e:
                if logger.isEnabledFor(logging.ERROR):
                    logger.error("Error using Rust engine for limit order: %s", e)
                # Fall back to Python implementation
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("Falling back to Python implementation")
        
        # Fast implementation without function calls in critical path
        if self._use_fast_path:
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
                
            # Directly process order, bypassing function calls
            if side == OrderSide.BUY:
                self._process_buy_order_fastpath(order)
            else:
                self._process_sell_order_fastpath(order)
        else:
            # Standard path - unchanged
            order = self.get_order_from_pool(order_id, side, OrderType.LIMIT, price, quantity, ts, symbol)
            self._process_order(order)
        
        return order_id
    
    # Ultra-optimized versions that avoid function calls
    def _process_buy_order_fastpath(self, order):
        """Ultra-optimized buy order processing without function calls."""
        # Direct access to avoid attribute lookups
        sell_price_levels = self.order_book.sell_price_levels
        order_remaining = order.remaining_quantity
        order_price = order.price
        
        # Match against existing sell orders
        if sell_price_levels:
            # Direct iteration over dictionary keys instead of creating a list
            for price in sell_price_levels:
                if order_remaining <= 0:
                    break
                    
                if order.order_type == OrderType.LIMIT and price > order_price:
                    break
                    
                price_level = sell_price_levels.get(price)
                if not price_level or not price_level.orders:
                    continue
                
                # Match without further function calls
                price_level_orders = price_level.orders
                match_price = price
                
                # Pre-check the orders to avoid unnecessary processing
                if not price_level_orders:
                    continue
                
                i = 0
                while i < len(price_level_orders):
                    resting_order = price_level_orders[i]
                    resting_remaining = resting_order.remaining_quantity
                    
                    if resting_remaining <= 0:
                        # Remove empty orders inline instead of accumulating them
                        price_level_orders.pop(i)
                        price_level.is_dirty = True
                        
                        # Remove from lookups directly
                        order_id = resting_order.id
                        orders_by_id = self.order_book.orders_by_id
                        price_map = self.order_book.order_price_map
                        if order_id in orders_by_id:
                            del orders_by_id[order_id]
                        if order_id in price_map:
                            del price_map[order_id]
                        continue
                        
                    if order_remaining <= 0:
                        break
                        
                    # Calculate match quantity using numba-optimized function
                    match_quantity = min_quantity(order_remaining, resting_remaining)
                    
                    # Update order quantities using numba-optimized function
                    order.filled_quantity, order_remaining = update_quantities(
                        order.filled_quantity, order_remaining, match_quantity)
                    order.remaining_quantity = order_remaining
                    
                    resting_order.filled_quantity, resting_order.remaining_quantity = update_quantities(
                        resting_order.filled_quantity, resting_remaining, match_quantity)
                    
                    # Set status using numba-optimized function
                    order.status = update_order_status(
                        order_remaining, OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED)
                    resting_order.status = update_order_status(
                        resting_order.remaining_quantity, OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED)
                    
                    # Create trade
                    trade_id = self.trade_executor.next_trade_id
                    self.trade_executor.next_trade_id += 1
                    
                    # Use pool if available
                    if self.trade_executor._trade_pool:
                        trade = self.trade_executor._trade_pool.pop()
                        trade.trade_id = trade_id
                        trade.buy_order_id = order.id
                        trade.sell_order_id = resting_order.id
                        trade.price = match_price
                        trade.quantity = match_quantity
                        trade.symbol = order.symbol or resting_order.symbol
                        trade.timestamp = max(order.timestamp, resting_order.timestamp)
                    else:
                        trade = Trade(
                            trade_id=trade_id,
                            buy_order_id=order.id,
                            sell_order_id=resting_order.id,
                            price=match_price,
                            quantity=match_quantity,
                            symbol=order.symbol or resting_order.symbol,
                            timestamp=max(order.timestamp, resting_order.timestamp)
                        )
                    
                    # Add trade to list and handle callback
                    self.trade_executor.trades.append(trade)
                    callback = self.trade_executor.trade_callback
                    if callback is not None:
                        callback(trade)
                    
                    # Remove if fully matched, otherwise move to next
                    if resting_order.remaining_quantity <= 0:
                        price_level_orders.pop(i)
                        price_level.is_dirty = True
                        
                        # Remove from lookups directly
                        order_id = resting_order.id
                        orders_by_id = self.order_book.orders_by_id
                        price_map = self.order_book.order_price_map
                        if order_id in orders_by_id:
                            del orders_by_id[order_id]
                        if order_id in price_map:
                            del price_map[order_id]
                    else:
                        i += 1
                    
                    # Break if active order is fully matched
                    if order_remaining <= 0:
                        break
                
                # Remove empty price level
                if not price_level_orders:
                    del sell_price_levels[price]
                    # Remove from cache if present
                    cache = self.order_book._price_level_cache
                    cache_key = (id(sell_price_levels), price)
                    if cache_key in cache:
                        del cache[cache_key]
        
        # If limit order and not fully filled, add to book
        if order.order_type == OrderType.LIMIT and order_remaining > 0:
            # Add directly to avoid function call overhead
            order_book = self.order_book
            neg_price = -order_price  # Negate for buy orders
            
            # Add to lookup dictionaries
            order_book.orders_by_id[order.id] = order
            order_book.order_price_map[order.id] = neg_price
            
            # Get or create price level
            price_dict = order_book.buy_price_levels
            if neg_price in price_dict:
                price_level = price_dict[neg_price]
            else:
                price_level = PriceLevel(neg_price)
                price_dict[neg_price] = price_level
                
                # Add to cache if space available
                cache = order_book._price_level_cache
                if len(cache) < order_book._max_cache_size:
                    cache_key = (id(price_dict), neg_price)
                    cache[cache_key] = price_level
            
            # Add to price level
            price_level.orders.append(order)
            price_level.total_qty_cache += order_remaining
    
    def _process_sell_order_fastpath(self, order):
        """Ultra-optimized sell order processing without function calls."""
        # Direct access to avoid attribute lookups
        buy_price_levels = self.order_book.buy_price_levels  
        order_remaining = order.remaining_quantity
        order_price = order.price
        
        # Match against existing buy orders
        if buy_price_levels:
            # Direct iteration over dictionary keys instead of creating a list
            for neg_price in buy_price_levels:
                if order_remaining <= 0:
                    break
                
                price = -neg_price  # Convert back to positive price
                if order.order_type == OrderType.LIMIT and price < order_price:
                    break
                
                price_level = buy_price_levels.get(neg_price)
                if not price_level or not price_level.orders:
                    continue
                
                # Match without further function calls
                price_level_orders = price_level.orders
                match_price = price
                
                # Pre-check the orders to avoid unnecessary processing
                if not price_level_orders:
                    continue
                
                i = 0
                while i < len(price_level_orders):
                    resting_order = price_level_orders[i]
                    resting_remaining = resting_order.remaining_quantity
                    
                    if resting_remaining <= 0:
                        # Remove empty orders inline instead of accumulating them
                        price_level_orders.pop(i)
                        price_level.is_dirty = True
                        
                        # Remove from lookups directly
                        order_id = resting_order.id
                        orders_by_id = self.order_book.orders_by_id
                        price_map = self.order_book.order_price_map
                        if order_id in orders_by_id:
                            del orders_by_id[order_id]
                        if order_id in price_map:
                            del price_map[order_id]
                        continue
                        
                    if order_remaining <= 0:
                        break
                        
                    # Calculate match quantity using numba-optimized function
                    match_quantity = min_quantity(order_remaining, resting_remaining)
                    
                    # Update order quantities using numba-optimized function
                    order.filled_quantity, order_remaining = update_quantities(
                        order.filled_quantity, order_remaining, match_quantity)
                    order.remaining_quantity = order_remaining
                    
                    resting_order.filled_quantity, resting_order.remaining_quantity = update_quantities(
                        resting_order.filled_quantity, resting_remaining, match_quantity)
                    
                    # Set status using numba-optimized function
                    order.status = update_order_status(
                        order_remaining, OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED)
                    resting_order.status = update_order_status(
                        resting_order.remaining_quantity, OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED)
                    
                    # Create trade
                    trade_id = self.trade_executor.next_trade_id
                    self.trade_executor.next_trade_id += 1
                    
                    # Use pool if available
                    if self.trade_executor._trade_pool:
                        trade = self.trade_executor._trade_pool.pop()
                        trade.trade_id = trade_id
                        trade.buy_order_id = resting_order.id
                        trade.sell_order_id = order.id
                        trade.price = match_price
                        trade.quantity = match_quantity
                        trade.symbol = order.symbol or resting_order.symbol
                        trade.timestamp = max(order.timestamp, resting_order.timestamp)
                    else:
                        trade = Trade(
                            trade_id=trade_id,
                            buy_order_id=resting_order.id,
                            sell_order_id=order.id,
                            price=match_price,
                            quantity=match_quantity,
                            symbol=order.symbol or resting_order.symbol,
                            timestamp=max(order.timestamp, resting_order.timestamp)
                        )
                    
                    # Add trade to list and handle callback
                    self.trade_executor.trades.append(trade)
                    callback = self.trade_executor.trade_callback
                    if callback is not None:
                        callback(trade)
                    
                    # Remove if fully matched, otherwise move to next
                    if resting_order.remaining_quantity <= 0:
                        price_level_orders.pop(i)
                        price_level.is_dirty = True
                        
                        # Remove from lookups directly
                        order_id = resting_order.id
                        orders_by_id = self.order_book.orders_by_id
                        price_map = self.order_book.order_price_map
                        if order_id in orders_by_id:
                            del orders_by_id[order_id]
                        if order_id in price_map:
                            del price_map[order_id]
                    else:
                        i += 1
                    
                    # Break if active order is fully matched
                    if order_remaining <= 0:
                        break
                
                # Remove empty price level
                if not price_level_orders:
                    del buy_price_levels[neg_price]
                    # Remove from cache if present
                    cache = self.order_book._price_level_cache
                    cache_key = (id(buy_price_levels), neg_price)
                    if cache_key in cache:
                        del cache[cache_key]
        
        # If limit order and not fully filled, add to book
        if order.order_type == OrderType.LIMIT and order_remaining > 0:
            # Add directly to avoid function call overhead
            order_book = self.order_book
            
            # Add to lookup dictionaries
            order_book.orders_by_id[order.id] = order
            order_book.order_price_map[order.id] = order_price
            
            # Get or create price level
            price_dict = order_book.sell_price_levels
            if order_price in price_dict:
                price_level = price_dict[order_price]
            else:
                price_level = PriceLevel(order_price)
                price_dict[order_price] = price_level
                
                # Add to cache if space available
                cache = order_book._price_level_cache
                if len(cache) < order_book._max_cache_size:
                    cache_key = (id(price_dict), order_price)
                    cache[cache_key] = price_level
            
            # Add to price level
            price_level.orders.append(order)
            price_level.total_qty_cache += order_remaining
    
    def add_market_order(self, side: OrderSide, quantity: float, timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """Add a market order to the order book."""
        # Direct assignment instead of conditional for performance
        order_id = self.next_order_id
        self.next_order_id += 1
        ts = timestamp or int(time.time() * 1000)
        
        # Only log in debug mode with lazy evaluation to avoid string formatting overhead
        if __debug__ and logger.isEnabledFor(logging.DEBUG):
            logger.debug("Adding market order: id=%d, side=%s, qty=%f, symbol=%s", 
                        order_id, side.name, quantity, symbol or '')
        
        if self.use_rust:
            # Use Rust implementation
            try:
                rust_side = matching_engine.PyOrderSide.Buy if side == OrderSide.BUY else matching_engine.PyOrderSide.Sell
                rust_order_id = self.rust_engine.add_market_order(rust_side, quantity, ts)
                return rust_order_id
            except Exception as e:
                if logger.isEnabledFor(logging.ERROR):
                    logger.error("Error using Rust engine for market order: %s", e)
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("Falling back to Python implementation")
        
        # Fast implementation without function calls
        if self._use_fast_path:
            # Inline order creation
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
                
            # Direct routing to appropriate fastpath
            if side == OrderSide.BUY:
                self._process_buy_order_fastpath(order)
            else:
                self._process_sell_order_fastpath(order)
        else:
            # Standard path through function calls
            order = self.get_order_from_pool(order_id, side, OrderType.MARKET, None, quantity, ts, symbol)
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
            order_objects.append(order)
            order_ids.append(order_id)
        
        # Batch process orders using optimized matching
        if self._use_fast_path:
            self.batch_match_fast(order_objects)
        else:
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
    
    def batch_match_fast(self, orders_to_match: List[Order]) -> None:
        """
        Fast path for batch matching orders.
        
        Args:
            orders_to_match: List of orders to match
        """
        # Group by side using list comprehensions for speed
        buy_orders = [o for o in orders_to_match if o.side == OrderSide.BUY]
        sell_orders = [o for o in orders_to_match if o.side == OrderSide.SELL]
        
        # Exit early if no orders
        if not buy_orders and not sell_orders:
            return
        
        # Custom sorting for better performance
        def sort_buy_orders(orders):
            market_orders = []
            limit_orders = []
            
            # Split into market and limit orders
            for order in orders:
                if order.order_type == OrderType.MARKET:
                    market_orders.append(order)
                else:
                    limit_orders.append(order)
            
            # Sort limit orders by price (highest first) and timestamp
            if limit_orders:
                limit_orders.sort(key=lambda o: (-o.price, o.timestamp))
            
            # Combine with market orders first
            return market_orders + limit_orders
        
        def sort_sell_orders(orders):
            market_orders = []
            limit_orders = []
            
            # Split into market and limit orders
            for order in orders:
                if order.order_type == OrderType.MARKET:
                    market_orders.append(order)
                else:
                    limit_orders.append(order)
            
            # Sort limit orders by price (lowest first) and timestamp
            if limit_orders:
                limit_orders.sort(key=lambda o: (o.price, o.timestamp))
            
            # Combine with market orders first
            return market_orders + limit_orders
        
        # Sort orders efficiently
        buy_orders_sorted = sort_buy_orders(buy_orders)
        sell_orders_sorted = sort_sell_orders(sell_orders)
        
        # Process buy orders first
        for order in buy_orders_sorted:
            self._process_buy_order_fast(order)
        
        # Then process sell orders
        for order in sell_orders_sorted:
            self._process_sell_order_fast(order)
    
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
                self.order_book.add_order(order)
    
    def _process_order_fast(self, order: Order) -> None:
        """Fast path for processing an order."""
        try:
            if order.side == OrderSide.BUY:
                self._process_buy_order_fast(order)
            else:  # SELL order
                self._process_sell_order_fast(order)
        except Exception as e:
            logger.error(f"Error processing order (fast path): {e}")
            # Ensure the order doesn't get lost
            if order.order_type == OrderType.LIMIT and order.remaining_quantity > 0:
                self.order_book.add_order_fast(order)
    
    def _process_buy_order(self, order: Order) -> None:
        """Process a buy order efficiently."""
        # Try to match against sell orders
        if order.order_type == OrderType.MARKET:
            # Market orders match against any sell order
            for price in list(self.order_book.sell_price_levels.keys()):
                if order.remaining_quantity <= 0:
                    break
                    
                price_level = self.order_book._get_or_create_price_level(self.order_book.sell_price_levels, price, create_new=False)
                if not price_level:
                    continue
                    
                self._match_at_price_level(order, price_level)
                    
        else:
            # Limit orders match only if price is acceptable
            for price in list(self.order_book.sell_price_levels.keys()):
                if price > order.price or order.remaining_quantity <= 0:
                    break
                    
                price_level = self.order_book._get_or_create_price_level(self.order_book.sell_price_levels, price, create_new=False)
                if not price_level:
                    continue
                    
                self._match_at_price_level(order, price_level)
        
        # If it's a limit order and not fully filled, add to the order book
        if order.order_type == OrderType.LIMIT and order.remaining_quantity > 0:
            self.order_book.add_order(order)
    
    def _process_buy_order_fast(self, order: Order) -> None:
        """Fast path for processing a buy order."""
        # Direct access to order book for performance
        sell_price_levels = self.order_book.sell_price_levels
        order_remaining = order.remaining_quantity
        
        # Fast path for market orders
        if order.order_type == OrderType.MARKET:
            # Iterate through sorted sell prices
            for price in list(sell_price_levels.keys()):
                if order_remaining <= 0:
                    break
                
                # Get price level directly from dictionary
                price_level = sell_price_levels.get(price)
                if not price_level or not price_level.orders:
                    continue
                
                # Match at this price level
                self._match_at_price_level_fast(order, price_level)
                order_remaining = order.remaining_quantity  # Update after matching
        else:
            # Fast path for limit orders - only match if price is acceptable
            order_price = order.price
            
            for price in list(sell_price_levels.keys()):
                if price > order_price or order_remaining <= 0:
                    break
                
                # Get price level directly
                price_level = sell_price_levels.get(price)
                if not price_level or not price_level.orders:
                    continue
                
                # Match at this price level
                self._match_at_price_level_fast(order, price_level)
                order_remaining = order.remaining_quantity  # Update after matching
        
        # If limit order and not fully filled, add to book
        if order.order_type == OrderType.LIMIT and order_remaining > 0:
            self.order_book.add_order_fast(order)
    
    def _process_sell_order(self, order: Order) -> None:
        """Process a sell order efficiently."""
        # Try to match against buy orders
        if order.order_type == OrderType.MARKET:
            # Market orders match against any buy order
            for neg_price in list(self.order_book.buy_price_levels.keys()):
                if order.remaining_quantity <= 0:
                    break
                    
                price_level = self.order_book._get_or_create_price_level(self.order_book.buy_price_levels, neg_price, create_new=False)
                if not price_level:
                    continue
                    
                self._match_at_price_level(order, price_level)
                    
        else:
            # Limit orders match only if price is acceptable
            for neg_price in list(self.order_book.buy_price_levels.keys()):
                price = -neg_price
                if price < order.price or order.remaining_quantity <= 0:
                    break
                    
                price_level = self.order_book._get_or_create_price_level(self.order_book.buy_price_levels, neg_price, create_new=False)
                if not price_level:
                    continue
                    
                self._match_at_price_level(order, price_level)
        
        # If it's a limit order and not fully filled, add to the order book
        if order.order_type == OrderType.LIMIT and order.remaining_quantity > 0:
            self.order_book.add_order(order)
    
    def _process_sell_order_fast(self, order: Order) -> None:
        """Fast path for processing a sell order."""
        # Direct access to order book for performance
        buy_price_levels = self.order_book.buy_price_levels
        order_remaining = order.remaining_quantity
        
        # Fast path for market orders
        if order.order_type == OrderType.MARKET:
            # Iterate through sorted buy prices (negated)
            for neg_price in list(buy_price_levels.keys()):
                if order_remaining <= 0:
                    break
                
                # Get price level directly from dictionary
                price_level = buy_price_levels.get(neg_price)
                if not price_level or not price_level.orders:
                    continue
                
                # Match at this price level
                self._match_at_price_level_fast(order, price_level)
                order_remaining = order.remaining_quantity  # Update after matching
        else:
            # Fast path for limit orders - only match if price is acceptable
            order_price = order.price
            
            for neg_price in list(buy_price_levels.keys()):
                price = -neg_price  # Convert back to positive price
                if price < order_price or order_remaining <= 0:
                    break
                
                # Get price level directly
                price_level = buy_price_levels.get(neg_price)
                if not price_level or not price_level.orders:
                    continue
                
                # Match at this price level
                self._match_at_price_level_fast(order, price_level)
                order_remaining = order.remaining_quantity  # Update after matching
        
        # If limit order and not fully filled, add to book
        if order.order_type == OrderType.LIMIT and order_remaining > 0:
            self.order_book.add_order_fast(order)
    
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
            orders_to_remove = []
            for resting_order in list(price_level.orders):  # Make a copy to prevent concurrent modification
                # Skip if either order is fully matched
                if active_order.remaining_quantity <= 0 or resting_order.remaining_quantity <= 0:
                    continue
                
                # Determine the quantity to match
                match_quantity = min(active_order.remaining_quantity, resting_order.remaining_quantity)
                
                # Determine the match price (price of the resting order)
                match_price = price_level.price if resting_order.side == OrderSide.SELL else -price_level.price
                
                # Execute the trade
                buy_order = active_order if active_order.side == OrderSide.BUY else resting_order
                sell_order = active_order if active_order.side == OrderSide.SELL else resting_order
                
                self.trade_executor.execute_trade(
                    buy_order=buy_order,
                    sell_order=sell_order,
                    price=abs(match_price),
                    quantity=match_quantity
                )
                
                # Remove fully matched resting orders
                if resting_order.remaining_quantity <= 0:
                    orders_to_remove.append(resting_order.id)
                
                # Break if active order is fully matched
                if active_order.remaining_quantity <= 0:
                    break
            
            # Remove fully matched orders in batch
            for order_id in orders_to_remove:
                self.order_book.remove_order(order_id)
                
        except Exception as e:
            logger.error(f"Error matching at price level: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _match_at_price_level_fast(self, active_order: Order, price_level: PriceLevel) -> None:
        """Fast path for matching at a price level with minimal overhead."""
        # Avoid type checks and error handling in hot path for performance
        active_remaining = active_order.remaining_quantity
        
        if active_remaining <= 0 or not price_level.orders:
            return
        
        orders_to_remove = []
        price_level_orders = price_level.orders  # Local reference to avoid attribute lookup
        
        # Pre-determine if this is a sell price level
        is_sell_level = price_level_orders[0].side == OrderSide.SELL if price_level_orders else False
        match_price = abs(price_level.price if is_sell_level else -price_level.price)
        
        # Process all orders at this level
        for resting_order in price_level_orders[:]:  # Use a slice to avoid copying the whole list
            resting_remaining = resting_order.remaining_quantity
            
            if resting_remaining <= 0:
                continue
                
            # Calculate match quantity
            match_quantity = min(active_remaining, resting_remaining)
            
            # Determine which is buy and which is sell
            if active_order.side == OrderSide.BUY:
                self.trade_executor.execute_trade_fast(
                    buy_order=active_order,
                    sell_order=resting_order,
                    price=match_price,
                    quantity=match_quantity
                )
            else:
                self.trade_executor.execute_trade_fast(
                    buy_order=resting_order,
                    sell_order=active_order,
                    price=match_price,
                    quantity=match_quantity
                )
            
            # Update active remaining quantity
            active_remaining = active_order.remaining_quantity
            
            # Add to removal list if fully matched
            if resting_order.remaining_quantity <= 0:
                orders_to_remove.append(resting_order.id)
                
            # Break early if active order is fully matched
            if active_remaining <= 0:
                break
                
        # Use fast path to remove orders in batch
        for order_id in orders_to_remove:
            self.order_book.remove_order_fast(order_id)
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancel an order by its ID."""
        if self._use_fast_path:
            order = self.order_book.remove_order_fast(order_id)
        else:
            order = self.order_book.remove_order(order_id)
            
        if order:
            order.status = OrderStatus.CANCELLED
            
            # Add to order pool for reuse
            if len(self._order_pool) < self._max_order_pool_size:
                self._order_pool.append(order)
                
            return True
        return False
    
    def get_order_book_snapshot(self, symbol: Optional[str] = None) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """
        Get a snapshot of the current order book.
        
        Args:
            symbol: Optional symbol to filter by
            
        Returns:
            Tuple of (buy_orders, sell_orders) where each is a list of (price, quantity) tuples
        """
        if self.use_rust:
            try:
                # The Rust implementation doesn't take a symbol parameter for get_order_book_snapshot
                buy_levels, sell_levels = self.rust_engine.get_order_book_snapshot()
                return buy_levels, sell_levels
            except Exception as e:
                logger.error(f"Error getting order book from Rust engine: {e}")
                # Fall back to Python implementation
                logger.warning("Falling back to Python implementation for order book snapshot")
        
        # Get order book from the order book manager
        buy_levels, sell_levels = self.order_book.get_order_book_snapshot()
        
        # Filter by symbol if needed
        if symbol is not None:
            # This is not efficient, but it's a rare operation
            # In a real system, we would have separate order books per symbol
            buy_levels = [(price, qty) for price, qty in buy_levels 
                         if self._any_order_at_price_matches_symbol(OrderSide.BUY, price, symbol)]
            sell_levels = [(price, qty) for price, qty in sell_levels 
                          if self._any_order_at_price_matches_symbol(OrderSide.SELL, price, symbol)]
            
        return buy_levels, sell_levels
        
    def _any_order_at_price_matches_symbol(self, side: OrderSide, price: float, symbol: str) -> bool:
        """Check if any order at the given price matches the symbol."""
        orders = self.order_book.get_orders_at_price(side, price)
        return any(order.symbol == symbol for order in orders if order.symbol is not None)
        
    def get_trades(self, symbol: Optional[str] = None, limit: int = 100) -> List[Trade]:
        """
        Get recent trades.
        
        Args:
            symbol: Optional symbol to filter by
            limit: Maximum number of trades to return
            
        Returns:
            List of trades
        """
        if self.use_rust:
            try:
                # The Rust implementation doesn't have filter parameters on get_trades
                rust_trades = self.rust_engine.get_trades()
                # Filter by symbol if needed
                if symbol is not None:
                    rust_trades = [t for t in rust_trades if getattr(t, 'symbol', None) == symbol]
                # Limit if needed
                return rust_trades[-limit:]
            except Exception as e:
                logger.error(f"Error getting trades from Rust engine: {e}")
                # Fall back to Python implementation
                logger.warning("Falling back to Python implementation for get_trades")
        
        # Use fast path if no symbol filtering needed
        if self._use_fast_path and symbol is None:
            return self.trade_executor.get_trades_fast(limit)
            
        # Use regular path for symbol filtering
        return self.trade_executor.get_trades(symbol, limit)
    
    def get_price_statistics(self) -> Dict[str, Any]:
        """
        Calculate price statistics for the order book.
        
        Returns:
            Dictionary of price statistics
        """
        # Get order book snapshot
        buy_levels, sell_levels = self.order_book.get_order_book_snapshot()
        
        # Use the statistics calculator
        return PriceStatisticsCalculator.calculate_from_price_levels(buy_levels, sell_levels)
    
    def get_order(self, order_id: int) -> Optional[Order]:
        """Get an order by its ID."""
        return self.order_book.get_order(order_id)
    
    def recycle_trades(self, to_recycle: List[Trade]) -> None:
        """
        Recycle trades to reduce garbage collection pressure.
        Call this after processing trades to return them to the pool.
        """
        if self._use_fast_path and isinstance(to_recycle, int):
            # Fast path for recycling recent trades by count
            self.trade_executor.recycle_trades_fast(to_recycle)
        else:
            # Regular path for recycling specific trades
            self.trade_executor.recycle_trades(to_recycle)
    
    def clear_caches(self) -> None:
        """
        Clear caches to free memory.
        Call this periodically if memory usage is a concern.
        """
        self.order_book.clear_caches()
        
    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about cache performance."""
        book_stats = self.order_book.get_cache_stats()
        trade_stats = self.trade_executor.get_pool_stats()
        
        return {
            **book_stats,
            **trade_stats,
            "order_pool_size": len(self._order_pool),
            "max_order_pool_size": self._max_order_pool_size,
            "using_fast_path": self._use_fast_path
        }
    
    def set_use_fast_path(self, enabled: bool) -> None:
        """Enable or disable fast path optimizations."""
        self._use_fast_path = enabled
        logger.info(f"Fast path optimizations {'enabled' if enabled else 'disabled'}")
        
    def get_performance_mode(self) -> str:
        """Get the current performance mode of the engine."""
        if self.use_rust:
            return "Rust (High Performance)"
        elif self._use_fast_path:
            return "Python with fast path optimizations"
        else:
            return "Python (standard)" 