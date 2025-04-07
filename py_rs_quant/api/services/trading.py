"""
Trading service for handling business logic.
"""
from typing import Dict, List, Optional, Tuple

from py_rs_quant.api.utils.utils import get_timestamp
from py_rs_quant.core.engine import MatchingEngine, Order, OrderSide, OrderType, Trade
from py_rs_quant.risk.manager import RiskManager, RiskCheckResult


class TradingService:
    """Service for trading operations."""
    
    def __init__(
        self,
        matching_engine: MatchingEngine,
        risk_manager: RiskManager,
        orders_storage: Dict[int, Order]
    ):
        self.matching_engine = matching_engine
        self.risk_manager = risk_manager
        self.orders_storage = orders_storage
    
    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Place a new order.
        
        Returns:
            Tuple[bool, Optional[int], Optional[str]]: 
                - Success status
                - Order ID if successful, None otherwise
                - Error message if failed, None otherwise
        """
        try:
            # Convert to correct sign based on side
            order_size = quantity if side == OrderSide.BUY else -quantity
            
            # For market orders, get reference price
            if order_type == OrderType.MARKET:
                # Use reference price for market orders
                price = self.risk_manager.reference_prices.get(symbol, 0.0)
                if price == 0.0:
                    return False, None, f"No reference price available for {symbol}"
            
            # Perform risk checks
            check_price_tolerance = order_type == OrderType.LIMIT
            risk_result = self.risk_manager.check_order(
                symbol=symbol,
                order_size=order_size,
                price=price,
                check_price_tolerance=check_price_tolerance
            )
            
            if risk_result != RiskCheckResult.PASSED:
                return False, None, f"Risk check failed: {risk_result.name}"
            
            # Submit order to matching engine
            timestamp = get_timestamp()
            order_id = None
            
            if order_type == OrderType.MARKET:
                order_id = self.matching_engine.add_market_order(side, abs(order_size), timestamp)
            else:  # LIMIT
                order_id = self.matching_engine.add_limit_order(side, price, abs(order_size), timestamp)
            
            # Create and store order
            order = Order(
                order_id=order_id,
                side=side,
                order_type=order_type,
                price=price if order_type == OrderType.LIMIT else None,
                quantity=abs(order_size),
                timestamp=timestamp
            )
            self.orders_storage[order_id] = order
            
            return True, order_id, None
            
        except Exception as e:
            return False, None, f"Error processing order: {str(e)}"
    
    def cancel_order(self, order_id: int) -> Tuple[bool, Optional[str]]:
        """
        Cancel an order.
        
        Returns:
            Tuple[bool, Optional[str]]: 
                - Success status
                - Error message if failed, None otherwise
        """
        if order_id not in self.orders_storage:
            return False, f"Order with ID {order_id} not found"
        
        success = self.matching_engine.cancel_order(order_id)
        
        if success:
            order = self.orders_storage[order_id]
            # Update status in our tracking dictionary
            order.status = OrderType.CANCELLED
            return True, None
        else:
            return False, "Failed to cancel order"
    
    def get_order(self, order_id: int) -> Optional[Order]:
        """Get an order by ID."""
        return self.orders_storage.get(order_id)
    
    def get_order_book(self, symbol: str) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """
        Get order book for a symbol.
        
        Returns:
            Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
                - List of (price, quantity) for bids
                - List of (price, quantity) for asks
        """
        # In a real implementation, we would filter by symbol
        return self.matching_engine.get_order_book_snapshot(symbol)
    
    def get_trades(self) -> List[Trade]:
        """Get all trades."""
        return self.matching_engine.get_trades() 