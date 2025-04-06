"""
Python implementation of the matching engine.
"""
from enum import Enum, auto
import time
from typing import Dict, List, Optional, Tuple, Union
import heapq

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


class Order:
    """Order class representing a trade order."""
    
    def __init__(self, 
                 order_id: int, 
                 side: OrderSide, 
                 order_type: OrderType, 
                 price: Optional[float], 
                 quantity: float, 
                 timestamp: Optional[int] = None,
                 symbol: Optional[str] = None):
        self.id = order_id
        self.side = side
        self.order_type = order_type
        self.price = price
        self.quantity = quantity
        self.filled_quantity = 0.0
        self.status = OrderStatus.NEW
        self.timestamp = timestamp if timestamp is not None else int(time.time() * 1000)
        self.symbol = symbol
    
    @property
    def remaining_quantity(self) -> float:
        """Return remaining quantity to be filled."""
        return self.quantity - self.filled_quantity
    
    def __repr__(self) -> str:
        return (f"Order(id={self.id}, side={self.side}, type={self.order_type}, "
                f"price={self.price}, quantity={self.quantity}, filled={self.filled_quantity}, "
                f"status={self.status}, symbol={self.symbol})")


class Trade:
    """Trade class representing a matched trade."""
    
    def __init__(self, 
                 trade_id: int, 
                 buy_order_id: int, 
                 sell_order_id: int, 
                 price: float, 
                 quantity: float, 
                 timestamp: Optional[int] = None,
                 symbol: Optional[str] = None):
        self.id = trade_id
        self.buy_order_id = buy_order_id
        self.sell_order_id = sell_order_id
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp if timestamp is not None else int(time.time() * 1000)
        self.symbol = symbol
    
    def __repr__(self) -> str:
        return (f"Trade(id={self.id}, buy_order_id={self.buy_order_id}, "
                f"sell_order_id={self.sell_order_id}, price={self.price}, "
                f"quantity={self.quantity}, timestamp={self.timestamp}, symbol={self.symbol})")


class MatchingEngine:
    """
    Matching Engine class for order matching.
    """
    
    def __init__(self, use_rust: bool = False):
        # For now, ignore use_rust parameter since we're using Python implementation
        self.use_rust = False
        self.next_order_id = 1
        self.next_trade_id = 1
        self.buy_orders = []  # List of (price, timestamp, order) tuples for buy orders, price high to low
        self.sell_orders = []  # List of (price, timestamp, order) tuples for sell orders, price low to high
        self.trades = []
        self.trade_callback = None
    
    def register_trade_callback(self, callback):
        """Register a callback to be called when a trade is executed."""
        self.trade_callback = callback
    
    def add_limit_order(self, side: OrderSide, price: float, quantity: float, timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """Add a limit order to the order book."""
        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        order_id = self.next_order_id
        self.next_order_id += 1
        
        order = Order(order_id, side, OrderType.LIMIT, price, quantity, ts, symbol)
        
        # Process the order (match or add to book)
        self._process_order(order)
        
        return order_id
    
    def add_market_order(self, side: OrderSide, quantity: float, timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """Add a market order to the order book."""
        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        order_id = self.next_order_id
        self.next_order_id += 1
        
        order = Order(order_id, side, OrderType.MARKET, None, quantity, ts, symbol)
        
        # Process the order (match or add to book)
        self._process_order(order)
        
        return order_id
    
    def _process_order(self, order: Order) -> None:
        """Process an order (match or add to book)."""
        if order.side == OrderSide.BUY:
            # Try to match against sell orders
            while order.remaining_quantity > 0 and self.sell_orders:
                # For market orders, match against any sell order
                # For limit orders, match only if the price is acceptable
                if (order.order_type == OrderType.MARKET or 
                    (order.order_type == OrderType.LIMIT and order.price >= self.sell_orders[0][0])):
                    
                    _, _, match_order = self.sell_orders[0]
                    
                    # Calculate the trade quantity
                    trade_qty = min(order.remaining_quantity, match_order.remaining_quantity)
                    
                    # Execute the trade at the sell order price
                    self._execute_trade(order, match_order, match_order.price, trade_qty)
                    
                    # Remove filled sell orders
                    if match_order.status == OrderStatus.FILLED:
                        heapq.heappop(self.sell_orders)
                else:
                    # No more matches possible
                    break
                    
            # If it's a limit order and not fully filled, add to the order book
            if order.order_type == OrderType.LIMIT and order.remaining_quantity > 0:
                # For buy orders, use negative price for the heap to get highest first
                heapq.heappush(self.buy_orders, (-order.price, order.timestamp, order.id, order))
                
        else:  # SELL order
            # Try to match against buy orders
            while order.remaining_quantity > 0 and self.buy_orders:
                # For market orders, match against any buy order
                # For limit orders, match only if the price is acceptable
                if (order.order_type == OrderType.MARKET or 
                    (order.order_type == OrderType.LIMIT and order.price <= -self.buy_orders[0][0])):
                    
                    _, _, _, match_order = self.buy_orders[0]
                    
                    # Calculate the trade quantity
                    trade_qty = min(order.remaining_quantity, match_order.remaining_quantity)
                    
                    # Execute the trade at the buy order price
                    self._execute_trade(match_order, order, match_order.price, trade_qty)
                    
                    # Remove filled buy orders
                    if match_order.status == OrderStatus.FILLED:
                        heapq.heappop(self.buy_orders)
                else:
                    # No more matches possible
                    break
            
            # If it's a limit order and not fully filled, add to the order book
            if order.order_type == OrderType.LIMIT and order.remaining_quantity > 0:
                heapq.heappush(self.sell_orders, (order.price, order.timestamp, order.id, order))
    
    def _execute_trade(self, buy_order: Order, sell_order: Order, price: float, quantity: float) -> None:
        """Execute a trade between a buy and sell order."""
        # Update the orders
        buy_order.filled_quantity += quantity
        sell_order.filled_quantity += quantity
        
        # Update order statuses
        if buy_order.filled_quantity >= buy_order.quantity:
            buy_order.status = OrderStatus.FILLED
        else:
            buy_order.status = OrderStatus.PARTIALLY_FILLED
            
        if sell_order.filled_quantity >= sell_order.quantity:
            sell_order.status = OrderStatus.FILLED
        else:
            sell_order.status = OrderStatus.PARTIALLY_FILLED
            
        # Create a trade record
        trade = Trade(
            trade_id=self.next_trade_id,
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            price=price,
            quantity=quantity,
            symbol=buy_order.symbol
        )
        self.next_trade_id += 1
        
        # Add to trades list
        self.trades.append(trade)
        
        # Call the trade callback if registered
        if self.trade_callback:
            self.trade_callback(trade)
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancel an order by its ID."""
        # Search in buy orders
        for i, (_, _, order_id_in_heap, order) in enumerate(self.buy_orders):
            if order.id == order_id:
                order.status = OrderStatus.CANCELLED
                self.buy_orders.pop(i)
                heapq.heapify(self.buy_orders)  # Re-establish heap property
                return True
                
        # Search in sell orders
        for i, (_, _, order_id_in_heap, order) in enumerate(self.sell_orders):
            if order.id == order_id:
                order.status = OrderStatus.CANCELLED
                self.sell_orders.pop(i)
                heapq.heapify(self.sell_orders)  # Re-establish heap property
                return True
                
        return False
    
    def get_order_book_snapshot(self) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """
        Get a snapshot of the order book.
        Returns a tuple of (buy_orders, sell_orders), where each is a list of (price, quantity) tuples.
        """
        # Combine quantities at the same price level for buy orders
        buy_levels = {}
        for neg_price, _, _, order in self.buy_orders:
            price = -neg_price  # Convert back to positive
            buy_levels[price] = buy_levels.get(price, 0) + order.remaining_quantity
            
        # Combine quantities at the same price level for sell orders
        sell_levels = {}
        for price, _, _, order in self.sell_orders:
            sell_levels[price] = sell_levels.get(price, 0) + order.remaining_quantity
            
        # Convert to sorted lists of (price, quantity) tuples
        buy_tuples = [(price, qty) for price, qty in buy_levels.items()]
        buy_tuples.sort(reverse=True)  # Sort by price, highest first
        
        sell_tuples = [(price, qty) for price, qty in sell_levels.items()]
        sell_tuples.sort()  # Sort by price, lowest first
        
        return (buy_tuples, sell_tuples)
    
    def get_trades(self) -> List[Trade]:
        """Get all trades that have occurred."""
        return self.trades 