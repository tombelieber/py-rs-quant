"""
py_rs_quant - High-Performance Order Matching Engine and Trading Simulator
"""

__version__ = "0.1.0"

# Import key components to make them available at the package level
from py_rs_quant.core.engine import MatchingEngine, Order, Trade, OrderSide, OrderType, OrderStatus
from py_rs_quant.risk.manager import RiskManager
from py_rs_quant.simulation.simulator import MarketSimulator, SimulationMode
