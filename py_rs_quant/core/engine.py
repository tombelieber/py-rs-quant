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
    
    def __init__(self, use_rust: bool = False):
        self.use_rust = use_rust and RUST_ENGINE_AVAILABLE
        
        if use_rust and not RUST_ENGINE_AVAILABLE:
            logger.warning("Rust implementation requested but not available. Using Python implementation instead.")
        
        logger.info(f"Initializing MatchingEngine (use_rust={self.use_rust})")
        
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
        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        order_id = self.next_order_id
        self.next_order_id += 1
        
        logger.debug(f"Adding limit order: id={order_id}, side={side.name}, price={price}, qty={quantity}, symbol={symbol}")
        
        if self.use_rust:
            # Use Rust implementation
            try:
                # Convert OrderSide enum to PyOrderSide
                rust_side = matching_engine.PyOrderSide.Buy if side == OrderSide.BUY else matching_engine.PyOrderSide.Sell
                # The Rust implementation doesn't use the symbol in the add_limit_order method
                rust_order_id = self.rust_engine.add_limit_order(rust_side, price, quantity, ts)
                logger.debug(f"Rust engine returned order ID: {rust_order_id}")
                return rust_order_id
            except Exception as e:
                logger.error(f"Error using Rust engine for limit order: {e}")
                # Fall back to Python implementation
                logger.warning("Falling back to Python implementation")
        
        # Python implementation
        # Get order from pool or create new
        order = self.get_order_from_pool(order_id, side, OrderType.LIMIT, price, quantity, ts, symbol)
        
        # Process the order (match or add to book)
        self._process_order(order)
        
        return order_id
    
    def add_market_order(self, side: OrderSide, quantity: float, timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """Add a market order to the order book."""
        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        order_id = self.next_order_id
        self.next_order_id += 1
        
        logger.debug(f"Adding market order: id={order_id}, side={side.name}, qty={quantity}, symbol={symbol}")
        
        if self.use_rust:
            # Use Rust implementation
            try:
                # Convert OrderSide enum to PyOrderSide
                rust_side = matching_engine.PyOrderSide.Buy if side == OrderSide.BUY else matching_engine.PyOrderSide.Sell
                # The Rust implementation doesn't use the symbol in the add_market_order method
                rust_order_id = self.rust_engine.add_market_order(rust_side, quantity, ts)
                logger.debug(f"Rust engine returned order ID: {rust_order_id}")
                return rust_order_id
            except Exception as e:
                logger.error(f"Error using Rust engine for market order: {e}")
                # Fall back to Python implementation
                logger.warning("Falling back to Python implementation")
        
        # Python implementation
        # Get order from pool or create new
        order = self.get_order_from_pool(order_id, side, OrderType.MARKET, None, quantity, ts, symbol)
        
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
                self.order_book.add_order(order)
    
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
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancel an order by its ID."""
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
        
        # Use the trade executor to get trades
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
            "max_order_pool_size": self._max_order_pool_size
        } 