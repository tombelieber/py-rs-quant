"""
Dependencies for engines used in the API.
"""
from typing import Dict


from py_rs_quant.core.engine import MatchingEngine, Order
from py_rs_quant.risk.manager import RiskManager


# Global instances that will be initialized at startup
_matching_engine: MatchingEngine = None
_risk_manager: RiskManager = None

# Orders storage
_orders_by_id: Dict[int, Order] = {}


def initialize_engines(use_rust: bool = True):
    """Initialize the engines globally. Called during application startup."""
    global _matching_engine, _risk_manager
    
    _matching_engine = MatchingEngine(use_rust=use_rust)
    _risk_manager = RiskManager()
    
    # Initialize reference prices and risk limits
    _risk_manager.update_reference_price("BTCUSD", 50000.0)
    _risk_manager.update_reference_price("ETHUSD", 3000.0)
    
    # Set risk limits
    _risk_manager.max_position_size = {
        "BTCUSD": 10.0,
        "ETHUSD": 100.0
    }
    _risk_manager.max_order_size = {
        "BTCUSD": 5.0,
        "ETHUSD": 50.0
    }
    _risk_manager.max_exposure = 1000000.0  # $1M exposure limit


def get_matching_engine() -> MatchingEngine:
    """Dependency for getting the matching engine."""
    return _matching_engine


def get_risk_manager() -> RiskManager:
    """Dependency for getting the risk manager."""
    return _risk_manager


def get_orders_storage() -> Dict[int, Order]:
    """Dependency for getting the orders storage."""
    return _orders_by_id 