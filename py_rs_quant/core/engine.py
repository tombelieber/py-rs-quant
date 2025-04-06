"""
Python implementation of the matching engine.
"""
from enum import Enum, auto
import time
from typing import Dict, List, Optional, Tuple, Union, Callable, Iterable
import heapq
from collections import defaultdict
from sortedcontainers import SortedDict  # For efficient order book management

# For now, use a Python implementation only
RUST_ENGINE_AVAILABLE = False

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
    """
    Represents a price level in the order book with multiple orders at the same price.
    Using this to avoid creating many small tuples during order matching.
    """
    __slots__ = ['price', 'orders']
    
    def __init__(self, price: float):
        self.price = price
        self.orders = []  # List of orders at this price level
        
    def add_order(self, order: Order) -> None:
        self.orders.append(order)
        
    def remove_order(self, order_id: int) -> bool:
        for i, order in enumerate(self.orders):
            if order.id == order_id:
                self.orders.pop(i)
                return True
        return False
        
    def total_quantity(self) -> float:
        return sum(order.remaining_quantity for order in self.orders)
    
    def __repr__(self) -> str:
        return f"PriceLevel(price={self.price}, orders={len(self.orders)}, qty={self.total_quantity()})"


class MatchingEngine:
    """
    Matching Engine class for order matching.
    """
    
    def __init__(self, use_rust: bool = False):
        # For now, ignore use_rust parameter since we're using Python implementation
        self.use_rust = False
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
        
        # Trade recycling pool for reducing GC pressure
        self._trade_pool = []
        self._max_pool_size = 1000
    
    def register_trade_callback(self, callback: Callable) -> None:
        """Register a callback to be called when a trade is executed."""
        self.trade_callback = callback
    
    def add_limit_order(self, side: OrderSide, price: float, quantity: float, timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """Add a limit order to the order book."""
        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        order_id = self.next_order_id
        self.next_order_id += 1
        
        order = Order(order_id, side, OrderType.LIMIT, price, quantity, ts, symbol)
        self.orders_by_id[order_id] = order
        
        # Process the order (match or add to book)
        self._process_order(order)
        
        return order_id
    
    def add_market_order(self, side: OrderSide, quantity: float, timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """Add a market order to the order book."""
        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        order_id = self.next_order_id
        self.next_order_id += 1
        
        order = Order(order_id, side, OrderType.MARKET, None, quantity, ts, symbol)
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
        order_ids = []
        for side, order_type, price, quantity, timestamp, symbol in orders:
            ts = timestamp if timestamp is not None else int(time.time() * 1000)
            order_id = self.next_order_id
            self.next_order_id += 1
            
            order = Order(order_id, side, order_type, price, quantity, ts, symbol)
            self.orders_by_id[order_id] = order
            order_ids.append(order_id)
            
            # Process each order
            self._process_order(order)
            
        return order_ids
    
    def _process_order(self, order: Order) -> None:
        """Process an order (match or add to book)."""
        if order.side == OrderSide.BUY:
            self._process_buy_order(order)
        else:  # SELL order
            self._process_sell_order(order)
    
    def _process_buy_order(self, order: Order) -> None:
        """Process a buy order efficiently."""
        # Try to match against sell orders
        if order.order_type == OrderType.MARKET:
            # Market orders match against any sell order
            for price in self.sell_price_levels:
                if order.remaining_quantity <= 0:
                    break
                    
                price_level = self.sell_price_levels[price]
                self._match_at_price_level(order, price_level)
                
                # Remove the price level if empty
                if not price_level.orders:
                    del self.sell_price_levels[price]
        else:
            # Limit orders match only if price is acceptable
            for price in self.sell_price_levels:
                if price > order.price or order.remaining_quantity <= 0:
                    break
                    
                price_level = self.sell_price_levels[price]
                self._match_at_price_level(order, price_level)
                
                # Remove the price level if empty
                if not price_level.orders:
                    del self.sell_price_levels[price]
        
        # If it's a limit order and not fully filled, add to the order book
        if order.order_type == OrderType.LIMIT and order.remaining_quantity > 0:
            neg_price = -order.price  # Negate for correct sorting (highest price first)
            
            # Get or create the price level
            if neg_price not in self.buy_price_levels:
                self.buy_price_levels[neg_price] = PriceLevel(order.price)
                
            # Add the order to the price level
            self.buy_price_levels[neg_price].add_order(order)
            self.order_price_map[order.id] = neg_price
    
    def _process_sell_order(self, order: Order) -> None:
        """Process a sell order efficiently."""
        # Try to match against buy orders
        if order.order_type == OrderType.MARKET:
            # Market orders match against any buy order
            for neg_price in self.buy_price_levels:
                if order.remaining_quantity <= 0:
                    break
                    
                price_level = self.buy_price_levels[neg_price]
                self._match_at_price_level(price_level, order)
                
                # Remove the price level if empty
                if not price_level.orders:
                    del self.buy_price_levels[neg_price]
        else:
            # Limit orders match only if price is acceptable
            for neg_price in self.buy_price_levels:
                price = -neg_price
                if price < order.price or order.remaining_quantity <= 0:
                    break
                    
                price_level = self.buy_price_levels[neg_price]
                self._match_at_price_level(price_level, order)
                
                # Remove the price level if empty
                if not price_level.orders:
                    del self.buy_price_levels[neg_price]
        
        # If it's a limit order and not fully filled, add to the order book
        if order.order_type == OrderType.LIMIT and order.remaining_quantity > 0:
            # Get or create the price level
            if order.price not in self.sell_price_levels:
                self.sell_price_levels[order.price] = PriceLevel(order.price)
                
            # Add the order to the price level
            self.sell_price_levels[order.price].add_order(order)
            self.order_price_map[order.id] = order.price
    
    def _match_at_price_level(self, buy_order_or_level, sell_order_or_level) -> None:
        """
        Match orders at a specific price level.
        
        Args:
            buy_order_or_level: Either a buy Order or a PriceLevel of buy orders
            sell_order_or_level: Either a sell Order or a PriceLevel of sell orders
        """
        if isinstance(buy_order_or_level, Order):
            # Single buy order against price level of sell orders
            buy_order = buy_order_or_level
            sell_level = sell_order_or_level
            
            # Match orders in time priority
            i = 0
            while i < len(sell_level.orders) and buy_order.remaining_quantity > 0:
                sell_order = sell_level.orders[i]
                
                # Calculate the trade quantity
                trade_qty = min(buy_order.remaining_quantity, sell_order.remaining_quantity)
                
                # Execute the trade at the sell order price
                self._execute_trade(buy_order, sell_order, sell_order.price, trade_qty)
                
                # Remove filled sell orders
                if sell_order.status == OrderStatus.FILLED:
                    sell_level.orders.pop(i)
                    # Don't increment i since we removed an order
                else:
                    i += 1  # Move to next order
                    
        elif isinstance(sell_order_or_level, Order):
            # Single sell order against price level of buy orders
            buy_level = buy_order_or_level
            sell_order = sell_order_or_level
            
            # Match orders in time priority
            i = 0
            while i < len(buy_level.orders) and sell_order.remaining_quantity > 0:
                buy_order = buy_level.orders[i]
                
                # Calculate the trade quantity
                trade_qty = min(buy_order.remaining_quantity, sell_order.remaining_quantity)
                
                # Execute the trade at the buy order price
                self._execute_trade(buy_order, sell_order, buy_order.price, trade_qty)
                
                # Remove filled buy orders
                if buy_order.status == OrderStatus.FILLED:
                    buy_level.orders.pop(i)
                    # Don't increment i since we removed an order
                else:
                    i += 1  # Move to next order
    
    def _execute_trade(self, buy_order: Order, sell_order: Order, price: float, quantity: float) -> None:
        """Execute a trade between a buy and sell order."""
        # Update the orders
        buy_order.filled_quantity += quantity
        buy_order.remaining_quantity -= quantity
        sell_order.filled_quantity += quantity
        sell_order.remaining_quantity -= quantity
        
        # Update order statuses
        if buy_order.filled_quantity >= buy_order.quantity:
            buy_order.status = OrderStatus.FILLED
            # Remove from price map if filled
            if buy_order.id in self.order_price_map:
                del self.order_price_map[buy_order.id]
        else:
            buy_order.status = OrderStatus.PARTIALLY_FILLED
            
        if sell_order.filled_quantity >= sell_order.quantity:
            sell_order.status = OrderStatus.FILLED
            # Remove from price map if filled
            if sell_order.id in self.order_price_map:
                del self.order_price_map[sell_order.id]
        else:
            sell_order.status = OrderStatus.PARTIALLY_FILLED
        
        # Create a trade record - reuse from pool if available
        if self._trade_pool:
            trade = self._trade_pool.pop()
            trade.trade_id = self.next_trade_id
            trade.buy_order_id = buy_order.id
            trade.sell_order_id = sell_order.id
            trade.price = price
            trade.quantity = quantity
            trade.symbol = buy_order.symbol
            trade.timestamp = max(buy_order.timestamp, sell_order.timestamp)
        else:
            trade = Trade(
                trade_id=self.next_trade_id,
                buy_order_id=buy_order.id,
                sell_order_id=sell_order.id,
                price=price,
                quantity=quantity,
                symbol=buy_order.symbol,
                timestamp=max(buy_order.timestamp, sell_order.timestamp)
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
            price_level = self.buy_price_levels.get(price)
            if price_level and price_level.remove_order(order_id):
                # If the price level is now empty, remove it
                if not price_level.orders:
                    del self.buy_price_levels[price]
                    
                # Update order status
                order.status = OrderStatus.CANCELLED
                
                # Remove from lookups
                del self.order_price_map[order_id]
                return True
        else:  # SELL order
            price_level = self.sell_price_levels.get(price)
            if price_level and price_level.remove_order(order_id):
                # If the price level is now empty, remove it
                if not price_level.orders:
                    del self.sell_price_levels[price]
                    
                # Update order status
                order.status = OrderStatus.CANCELLED
                
                # Remove from lookups
                del self.order_price_map[order_id]
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
        space_left = self._max_pool_size - len(self._trade_pool)
        if space_left <= 0:
            return
            
        # Add trades to the pool
        for trade in to_recycle[-space_left:]:
            self._trade_pool.append(trade) 