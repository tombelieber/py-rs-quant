"""
Core matching engine module.
"""
from py_rs_quant.core.enums import OrderSide, OrderType, OrderStatus
from py_rs_quant.core.models import Order, Trade
from py_rs_quant.core.engine import MatchingEngine

# For backwards compatibility
from py_rs_quant.core.engine import RUST_ENGINE_AVAILABLE

__all__ = [
    'MatchingEngine',
    'OrderSide',
    'OrderType',
    'OrderStatus',
    'Order',
    'Trade',
    'RUST_ENGINE_AVAILABLE'
]
