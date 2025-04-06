"""
Python quantitative trading library with high-performance Rust components.

This package provides tools for building and analyzing trading systems, including
a matching engine for order book simulations.
"""

__version__ = "0.1.0"

# Core components
from py_rs_quant.core.engine import MatchingEngine, OrderSide, OrderType, OrderStatus, Order, Trade

# For backward compatibility, expose these at the top level
from py_rs_quant.simulation.simulator import MarketSimulator, SimulationMode
from py_rs_quant.analytics.analyzer import PerformanceAnalyzer
from py_rs_quant.risk.manager import RiskManager
