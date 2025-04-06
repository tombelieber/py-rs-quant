"""
Risk management module for pre-trade risk checks.
"""
from enum import Enum
from typing import Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class RiskCheckResult(Enum):
    PASSED = 1
    FAILED_POSITION_LIMIT = 2
    FAILED_ORDER_SIZE = 3
    FAILED_EXPOSURE = 4
    FAILED_PRICE_TOLERANCE = 5


class RiskManager:
    """
    Risk management class to perform pre-trade risk checks for orders.
    """
    
    def __init__(
        self,
        max_position_size: Dict[str, float] = None,
        max_order_size: Dict[str, float] = None,
        max_exposure: float = None,
        price_tolerance: float = 0.1  # 10% price tolerance by default
    ):
        """
        Initialize the risk manager with risk limits.
        
        Args:
            max_position_size: Dictionary mapping symbol to maximum position size
            max_order_size: Dictionary mapping symbol to maximum order size
            max_exposure: Maximum exposure in base currency
            price_tolerance: Maximum allowed deviation from reference price (0.1 = 10%)
        """
        self.max_position_size = max_position_size or {}
        self.max_order_size = max_order_size or {}
        self.max_exposure = max_exposure
        self.price_tolerance = price_tolerance
        
        # Track current positions
        self.positions: Dict[str, float] = {}
        # Track current exposure
        self.current_exposure: float = 0.0
        # Track reference prices
        self.reference_prices: Dict[str, float] = {}
    
    def set_position(self, symbol: str, size: float) -> None:
        """Set the current position for a symbol."""
        self.positions[symbol] = size
    
    def update_reference_price(self, symbol: str, price: float) -> None:
        """Update the reference price for a symbol."""
        self.reference_prices[symbol] = price
    
    def check_position_limit(self, symbol: str, order_size: float) -> bool:
        """
        Check if adding the order would exceed position limits.
        
        Args:
            symbol: The trading symbol
            order_size: The order size (positive for buys, negative for sells)
            
        Returns:
            True if the order passes the position limit check, False otherwise.
        """
        if symbol not in self.max_position_size:
            return True  # No limit set
        
        current_position = self.positions.get(symbol, 0.0)
        new_position = current_position + order_size
        
        if abs(new_position) > self.max_position_size[symbol]:
            logger.warning(
                f"Position limit exceeded for {symbol}: current={current_position}, "
                f"order={order_size}, new={new_position}, limit={self.max_position_size[symbol]}"
            )
            return False
        
        return True
    
    def check_order_size(self, symbol: str, order_size: float) -> bool:
        """
        Check if the order size exceeds the maximum allowed.
        
        Args:
            symbol: The trading symbol
            order_size: The absolute order size
            
        Returns:
            True if the order passes the size check, False otherwise.
        """
        if symbol not in self.max_order_size:
            return True  # No limit set
        
        if abs(order_size) > self.max_order_size[symbol]:
            logger.warning(
                f"Order size limit exceeded for {symbol}: order={order_size}, "
                f"limit={self.max_order_size[symbol]}"
            )
            return False
        
        return True
    
    def check_exposure(self, symbol: str, order_size: float, price: float) -> bool:
        """
        Check if the order would exceed exposure limits.
        
        Args:
            symbol: The trading symbol
            order_size: The order size
            price: The order price
            
        Returns:
            True if the order passes the exposure check, False otherwise.
        """
        if self.max_exposure is None:
            return True  # No limit set
        
        order_exposure = abs(order_size * price)
        new_exposure = self.current_exposure + order_exposure
        
        if new_exposure > self.max_exposure:
            logger.warning(
                f"Exposure limit exceeded: current={self.current_exposure}, "
                f"order={order_exposure}, new={new_exposure}, limit={self.max_exposure}"
            )
            return False
        
        return True
    
    def check_price_tolerance(self, symbol: str, price: float) -> bool:
        """
        Check if the price is within tolerance of the reference price.
        
        Args:
            symbol: The trading symbol
            price: The order price
            
        Returns:
            True if the order passes the price tolerance check, False otherwise.
        """
        if symbol not in self.reference_prices:
            return True  # No reference price available
        
        reference_price = self.reference_prices[symbol]
        deviation = abs(price - reference_price) / reference_price
        
        if deviation > self.price_tolerance:
            logger.warning(
                f"Price tolerance exceeded for {symbol}: order_price={price}, "
                f"reference={reference_price}, deviation={deviation:.2%}, "
                f"tolerance={self.price_tolerance:.2%}"
            )
            return False
        
        return True
    
    def check_order(
        self, 
        symbol: str, 
        order_size: float,  # Positive for buys, negative for sells
        price: float,
        check_price_tolerance: bool = True
    ) -> RiskCheckResult:
        """
        Run all risk checks for an order.
        
        Args:
            symbol: The trading symbol
            order_size: The order size (positive for buys, negative for sells)
            price: The order price
            check_price_tolerance: Whether to check price tolerance
            
        Returns:
            RiskCheckResult enum indicating whether the order passed risk checks
        """
        # Check position limits
        if not self.check_position_limit(symbol, order_size):
            return RiskCheckResult.FAILED_POSITION_LIMIT
        
        # Check order size
        if not self.check_order_size(symbol, order_size):
            return RiskCheckResult.FAILED_ORDER_SIZE
        
        # Check exposure
        if not self.check_exposure(symbol, order_size, price):
            return RiskCheckResult.FAILED_EXPOSURE
        
        # Check price tolerance if required
        if check_price_tolerance and not self.check_price_tolerance(symbol, price):
            return RiskCheckResult.FAILED_PRICE_TOLERANCE
        
        return RiskCheckResult.PASSED
    
    def update_after_fill(self, symbol: str, filled_size: float, filled_price: float) -> None:
        """
        Update position and exposure after a fill.
        
        Args:
            symbol: The trading symbol
            filled_size: The filled size (positive for buys, negative for sells)
            filled_price: The fill price
        """
        # Update position
        current_position = self.positions.get(symbol, 0.0)
        self.positions[symbol] = current_position + filled_size
        
        # Update exposure (simplified approach - in reality would be more complex)
        fill_exposure = abs(filled_size * filled_price)
        self.current_exposure += fill_exposure
        
        logger.info(
            f"Position and exposure updated: symbol={symbol}, position={self.positions[symbol]}, "
            f"exposure={self.current_exposure}"
        ) 