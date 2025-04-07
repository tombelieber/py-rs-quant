"""
Core matching engine components.
"""
from py_rs_quant.core.enums import OrderSide, OrderType, OrderStatus
from py_rs_quant.core.models import Order, Trade, PriceLevel
from py_rs_quant.core.order_book import OrderBook
from py_rs_quant.core.engine import MatchingEngine
from py_rs_quant.core.trade_execution import TradeExecutor
from py_rs_quant.core.statistics import PriceStatisticsCalculator
from py_rs_quant.core.matcher import Matcher
from py_rs_quant.core.order_processor import OrderProcessor

# Expose Rust engine if available
try:
    from py_rs_quant.core.rust_engine import RustMatchingEngine, is_rust_available
except ImportError:
    # Define a function that returns False when Rust is not available
    def is_rust_available():
        return False

__all__ = [
    'MatchingEngine',
    'RustMatchingEngine',
    'OrderSide',
    'OrderType',
    'OrderStatus',
    'Order',
    'Trade',
    'PriceLevel',
    'Matcher',
    'OrderProcessor',
    'OrderBook',
    'TradeExecutor',
    'PriceStatisticsCalculator',
    'is_rust_available'
]
