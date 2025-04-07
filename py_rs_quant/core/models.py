"""
Data models for the matching engine.
"""
from typing import Optional, List

from py_rs_quant.core.enums import OrderSide, OrderType, OrderStatus

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

