"""
Rust implementation of the matching engine.
"""
import time
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable

try:
    import matching_engine
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    
from py_rs_quant.core.enums import OrderSide, OrderType, OrderStatus
from py_rs_quant.core.models import Order, Trade

logger = logging.getLogger(__name__)


class RustMatchingEngine:
    """
    High-performance matching engine using Rust implementation.
    
    This engine provides ultra-low latency performance by leveraging
    Rust's zero-cost abstractions and memory safety.
    """
    
    def __init__(self):
        """Initialize a new Rust matching engine."""
        if not RUST_AVAILABLE:
            raise ImportError("Rust matching engine is not available. Please install it with 'cd matching_engine && maturin develop --release'")
            
        self._rust_engine = matching_engine.PyOrderBook()
        self._next_trade_id = 1
        
    def add_limit_order(self, side: OrderSide, price: float, quantity: float, 
                        timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """
        Add a limit order to the matching engine.
        
        Args:
            side: Buy or sell side
            price: Limit price
            quantity: Order quantity
            timestamp: Optional timestamp (milliseconds since epoch)
            symbol: Optional trading symbol
            
        Returns:
            The order ID
        """
        # Convert Python enums to Rust enums
        rust_side = matching_engine.PyOrderSide.Buy if side == OrderSide.BUY else matching_engine.PyOrderSide.Sell
        
        # Use current timestamp if not provided
        timestamp = timestamp or int(time.time() * 1000)
        
        # Call Rust implementation
        return self._rust_engine.add_limit_order(rust_side, price, quantity, timestamp)
    
    def add_market_order(self, side: OrderSide, quantity: float,
                        timestamp: Optional[int] = None, symbol: Optional[str] = None) -> int:
        """
        Add a market order to the matching engine.
        
        Args:
            side: Buy or sell side
            quantity: Order quantity
            timestamp: Optional timestamp (milliseconds since epoch)
            symbol: Optional trading symbol
            
        Returns:
            The order ID
        """
        # Convert Python enums to Rust enums
        rust_side = matching_engine.PyOrderSide.Buy if side == OrderSide.BUY else matching_engine.PyOrderSide.Sell
        
        # Use current timestamp if not provided
        timestamp = timestamp or int(time.time() * 1000)
        
        # Call Rust implementation
        return self._rust_engine.add_market_order(rust_side, quantity, timestamp)
    
    def batch_add_orders(self, orders: List[Tuple[OrderSide, OrderType, Optional[float], float, Optional[int], Optional[str]]]) -> List[int]:
        """
        Efficiently process multiple orders at once.
        
        Args:
            orders: List of tuples containing (side, order_type, price, quantity, timestamp, symbol)
        
        Returns:
            List of order IDs created
        """
        # Not directly supported in Rust interface, so we'll implement it here
        results = []
        for side, order_type, price, quantity, timestamp, symbol in orders:
            if order_type == OrderType.LIMIT:
                order_id = self.add_limit_order(side, price, quantity, timestamp, symbol)
            else:
                order_id = self.add_market_order(side, quantity, timestamp, symbol)
            results.append(order_id)
        return results
    
    def cancel_order(self, order_id: int) -> bool:
        """
        Cancel an order by its ID.
        
        Args:
            order_id: The ID of the order to cancel
            
        Returns:
            True if the order was cancelled, False otherwise
        """
        return self._rust_engine.cancel_order(order_id)
    
    def get_order_book_snapshot(self) -> Dict[str, Any]:
        """
        Get a complete snapshot of the current order book state.
        
        Returns:
            Dictionary with buy and sell sides, each containing lists of price levels
        """
        # Convert Rust snapshot to Python format
        buy_levels, sell_levels = self._rust_engine.get_order_book_snapshot()
        
        # Format similar to Python implementation
        return {
            "timestamp": int(time.time() * 1000),
            "buy_side": [
                {"price": price, "quantity": quantity, "order_count": 1}
                for price, quantity in buy_levels
            ],
            "sell_side": [
                {"price": price, "quantity": quantity, "order_count": 1}
                for price, quantity in sell_levels
            ],
            "spread": sell_levels[0][0] - buy_levels[0][0] if sell_levels and buy_levels else None,
            "mid_price": (sell_levels[0][0] + buy_levels[0][0]) / 2 if sell_levels and buy_levels else None,
            "total_orders": len(buy_levels) + len(sell_levels)
        }
    
    def get_trades(self) -> List[Trade]:
        """
        Get all trades executed since last call.
        
        Returns:
            List of executed trades
        """
        # Convert Rust trades to Python Trade objects
        rust_trades = self._rust_engine.get_trades()
        python_trades = []
        
        for rust_trade in rust_trades:
            # Create Python Trade object from Rust trade
            # When trade is a custom PyTrade object, we need to access its properties directly
            try:
                # Try accessing attributes directly first
                trade = Trade(
                    trade_id=rust_trade.trade_id if hasattr(rust_trade, 'trade_id') else self._next_trade_id,
                    buy_order_id=rust_trade.buy_order_id if hasattr(rust_trade, 'buy_order_id') else 0,
                    sell_order_id=rust_trade.sell_order_id if hasattr(rust_trade, 'sell_order_id') else 0,
                    price=rust_trade.price if hasattr(rust_trade, 'price') else 0.0,
                    quantity=rust_trade.quantity if hasattr(rust_trade, 'quantity') else 0.0,
                    symbol=rust_trade.symbol if hasattr(rust_trade, 'symbol') else "",
                    timestamp=rust_trade.timestamp if hasattr(rust_trade, 'timestamp') else int(time.time() * 1000)
                )
                self._next_trade_id += 1
            except AttributeError:
                # If attributes aren't accessible, try another approach
                logger.warning(f"Unable to access Rust trade attributes directly: {rust_trade}")
                self._next_trade_id += 1
                trade = Trade(
                    trade_id=self._next_trade_id,
                    buy_order_id=0,
                    sell_order_id=0,
                    price=0.0,
                    quantity=0.0,
                    timestamp=int(time.time() * 1000)
                )
            
            python_trades.append(trade)
            
        return python_trades
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current statistics about the matching engine.
        
        Returns:
            Dictionary with various statistics
        """
        # Basic statistics for Rust implementation
        buy_levels, sell_levels = self._rust_engine.get_order_book_snapshot()
        
        return {
            "timestamp": int(time.time() * 1000),
            "orderbook": {
                "buy_levels": len(buy_levels),
                "sell_sides": len(sell_levels),
                "total_orders": len(buy_levels) + len(sell_levels)
            },
            "implementation": "Rust"
        }
    
    def register_trade_callback(self, callback: Callable) -> None:
        """
        Register a callback to be called when a trade is executed.
        Note: This functionality may be limited in the Rust implementation.
        
        Args:
            callback: The callback function that takes a Trade object
        """
        logger.warning("Trade callbacks are not fully supported in Rust implementation")


def is_rust_available() -> bool:
    """Check if the Rust matching engine is available."""
    return RUST_AVAILABLE 