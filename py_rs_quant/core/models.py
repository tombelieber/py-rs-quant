"""
Data models for the matching engine.
"""
import time
from typing import Optional

from py_rs_quant.core.enums import OrderSide, OrderType, OrderStatus


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