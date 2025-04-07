"""
Core order matching logic for the matching engine.
"""
from typing import Dict, List, Optional, Tuple, Any
import logging

from py_rs_quant.core.enums import OrderSide, OrderType, OrderStatus
from py_rs_quant.core.models import Order, PriceLevel
from py_rs_quant.core.utils import (
    min_quantity, update_quantities, calculate_price_level_total, 
    calculate_match_price, update_order_status
)

logger = logging.getLogger(__name__)


class Matcher:
    """
    Handles the core matching logic between buy and sell orders.
    Optimized for high-performance matching with minimal overhead.
    """
    
    __slots__ = ('order_book', 'trade_executor')
    
    def __init__(self, order_book, trade_executor):
        """
        Initialize a matcher.
        
        Args:
            order_book: The order book to match orders in
            trade_executor: The trade executor to use for creating trades
        """
        self.order_book = order_book
        self.trade_executor = trade_executor
    
    def match_buy_order(self, order: Order) -> None:
        """
        Match a buy order against the order book.
        Optimized for zero allocation and minimal function calls.
        
        Args:
            order: The buy order to match
        """
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
                    
                    # Execute trade using optimized trade executor
                    self.trade_executor.execute_trade_optimized(
                        buy_order=order,
                        sell_order=resting_order,
                        price=match_price,
                        quantity=match_quantity
                    )
                    
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
    
    def match_sell_order(self, order: Order) -> None:
        """
        Match a sell order against the order book.
        Optimized for zero allocation and minimal function calls.
        
        Args:
            order: The sell order to match
        """
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
                    
                    # Execute trade using optimized trade executor
                    self.trade_executor.execute_trade_optimized(
                        buy_order=resting_order,
                        sell_order=order,
                        price=match_price,
                        quantity=match_quantity
                    )
                    
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
    
    def clear_caches(self) -> None:
        """
        Clear cached compiled functions or other resources.
        """
        # Nothing to clear in base implementation
        pass 