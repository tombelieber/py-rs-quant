"""
Python wrapper for the Rust matching engine.
"""
from enum import Enum, auto
import time
from typing import Dict, List, Optional, Tuple, Union

# Will import the Rust module once it's built
try:
    from matching_engine import PyOrderBook, PyOrderSide, PyOrderType, PyOrderStatus, PyTrade
    RUST_ENGINE_AVAILABLE = True
except ImportError:
    print("Warning: Rust matching engine not available. Using Python implementation.")
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
                 timestamp: Optional[int] = None):
        self.id = order_id
        self.side = side
        self.order_type = order_type
        self.price = price
        self.quantity = quantity
        self.filled_quantity = 0.0
        self.status = OrderStatus.NEW
        self.timestamp = timestamp if timestamp is not None else int(time.time() * 1000)
    
    @property
    def remaining_quantity(self) -> float:
        """Return remaining quantity to be filled."""
        return self.quantity - self.filled_quantity
    
    def __repr__(self) -> str:
        return (f"Order(id={self.id}, side={self.side}, type={self.order_type}, "
                f"price={self.price}, quantity={self.quantity}, filled={self.filled_quantity}, "
                f"status={self.status})")


class Trade:
    """Trade class representing a matched trade."""
    
    def __init__(self, 
                 trade_id: int, 
                 buy_order_id: int, 
                 sell_order_id: int, 
                 price: float, 
                 quantity: float, 
                 timestamp: Optional[int] = None):
        self.id = trade_id
        self.buy_order_id = buy_order_id
        self.sell_order_id = sell_order_id
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp if timestamp is not None else int(time.time() * 1000)
    
    def __repr__(self) -> str:
        return (f"Trade(id={self.id}, buy_order_id={self.buy_order_id}, "
                f"sell_order_id={self.sell_order_id}, price={self.price}, "
                f"quantity={self.quantity}, timestamp={self.timestamp})")


class MatchingEngine:
    """
    Matching Engine class that wraps the Rust implementation if available,
    otherwise falls back to a Python implementation.
    """
    
    def __init__(self, use_rust: bool = True):
        self.use_rust = use_rust and RUST_ENGINE_AVAILABLE
        
        if self.use_rust:
            self._engine = PyOrderBook()
            # Map Python enums to Rust enums
            self._py_to_rust_side = {
                OrderSide.BUY: PyOrderSide.Buy,
                OrderSide.SELL: PyOrderSide.Sell
            }
        else:
            # We'll implement a Python version later if needed
            # For now, we'll raise an error if Rust is not available
            if not RUST_ENGINE_AVAILABLE:
                raise NotImplementedError("Python matching engine not implemented yet. Install Rust engine.")
    
    def add_limit_order(self, side: OrderSide, price: float, quantity: float, timestamp: Optional[int] = None) -> int:
        """Add a limit order to the order book."""
        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        
        if self.use_rust:
            rust_side = self._py_to_rust_side[side]
            return self._engine.add_limit_order(rust_side, price, quantity, ts)
        else:
            # Python implementation would go here
            raise NotImplementedError("Python matching engine not implemented yet.")
    
    def add_market_order(self, side: OrderSide, quantity: float, timestamp: Optional[int] = None) -> int:
        """Add a market order to the order book."""
        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        
        if self.use_rust:
            rust_side = self._py_to_rust_side[side]
            return self._engine.add_market_order(rust_side, quantity, ts)
        else:
            # Python implementation would go here
            raise NotImplementedError("Python matching engine not implemented yet.")
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancel an order by its ID."""
        if self.use_rust:
            return self._engine.cancel_order(order_id)
        else:
            # Python implementation would go here
            raise NotImplementedError("Python matching engine not implemented yet.")
    
    def get_order_book_snapshot(self) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """
        Get a snapshot of the order book.
        Returns a tuple of (buy_orders, sell_orders), where each is a list of (price, quantity) tuples.
        """
        if self.use_rust:
            return self._engine.get_order_book_snapshot()
        else:
            # Python implementation would go here
            raise NotImplementedError("Python matching engine not implemented yet.")
    
    def get_trades(self) -> List[Trade]:
        """Get all trades that have occurred."""
        if self.use_rust:
            rust_trades = self._engine.get_trades()
            # Convert Rust trades to Python trades
            return [
                Trade(
                    trade_id=t.id,
                    buy_order_id=t.buy_order_id,
                    sell_order_id=t.sell_order_id,
                    price=t.price,
                    quantity=t.quantity,
                    timestamp=t.timestamp
                ) for t in rust_trades
            ]
        else:
            # Python implementation would go here
            raise NotImplementedError("Python matching engine not implemented yet.") 