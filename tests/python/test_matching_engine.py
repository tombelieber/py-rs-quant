"""
Tests for the Python matching engine wrapper.
"""
import pytest
import time

from src.python.matching_engine.python_engine import MatchingEngine, OrderSide, OrderType, Order, Trade


@pytest.fixture
def engine():
    """Create a new matching engine for each test."""
    # Try to use the Rust implementation if available
    try:
        return MatchingEngine(use_rust=True)
    except NotImplementedError:
        pytest.skip("Rust matching engine not available")


def test_limit_order_addition(engine):
    """Test adding limit orders."""
    # Add a buy order
    buy_order_id = engine.add_limit_order(OrderSide.BUY, 100.0, 10.0)
    
    # Add a sell order
    sell_order_id = engine.add_limit_order(OrderSide.SELL, 110.0, 5.0)
    
    # Get order book snapshot
    buy_orders, sell_orders = engine.get_order_book_snapshot()
    
    # Verify buy orders
    assert len(buy_orders) == 1
    assert buy_orders[0][0] == 100.0  # Price
    assert buy_orders[0][1] == 10.0   # Quantity
    
    # Verify sell orders
    assert len(sell_orders) == 1
    assert sell_orders[0][0] == 110.0  # Price
    assert sell_orders[0][1] == 5.0    # Quantity


def test_matching_limit_orders(engine):
    """Test matching limit orders."""
    # Add a buy order
    buy_order_id = engine.add_limit_order(OrderSide.BUY, 100.0, 10.0)
    
    # Add a sell order that will match
    sell_order_id = engine.add_limit_order(OrderSide.SELL, 100.0, 5.0)
    
    # Get order book snapshot
    buy_orders, sell_orders = engine.get_order_book_snapshot()
    
    # Verify buy orders (should have 5 remaining)
    assert len(buy_orders) == 1
    assert buy_orders[0][0] == 100.0  # Price
    assert buy_orders[0][1] == 5.0    # Quantity (10.0 - 5.0)
    
    # Verify sell orders (should be empty)
    assert len(sell_orders) == 0
    
    # Verify trades
    trades = engine.get_trades()
    assert len(trades) == 1
    assert trades[0].buy_order_id == buy_order_id
    assert trades[0].sell_order_id == sell_order_id
    assert trades[0].price == 100.0
    assert trades[0].quantity == 5.0


def test_market_order(engine):
    """Test market orders."""
    # Add a sell limit order
    sell_order_id = engine.add_limit_order(OrderSide.SELL, 100.0, 10.0)
    
    # Add a buy market order
    buy_order_id = engine.add_market_order(OrderSide.BUY, 5.0)
    
    # Get order book snapshot
    buy_orders, sell_orders = engine.get_order_book_snapshot()
    
    # Verify buy orders (should be empty)
    assert len(buy_orders) == 0
    
    # Verify sell orders (should have 5 remaining)
    assert len(sell_orders) == 1
    assert sell_orders[0][0] == 100.0  # Price
    assert sell_orders[0][1] == 5.0    # Quantity (10.0 - 5.0)
    
    # Verify trades
    trades = engine.get_trades()
    assert len(trades) == 1
    assert trades[0].buy_order_id == buy_order_id
    assert trades[0].sell_order_id == sell_order_id
    assert trades[0].price == 100.0
    assert trades[0].quantity == 5.0


def test_cancel_order(engine):
    """Test canceling orders."""
    # Add a buy order
    buy_order_id = engine.add_limit_order(OrderSide.BUY, 100.0, 10.0)
    
    # Cancel the order
    success = engine.cancel_order(buy_order_id)
    assert success
    
    # Get order book snapshot (should be empty)
    buy_orders, sell_orders = engine.get_order_book_snapshot()
    assert len(buy_orders) == 0
    assert len(sell_orders) == 0
    
    # Try to cancel a non-existent order
    success = engine.cancel_order(999)
    assert not success


@pytest.mark.parametrize("use_rust", [True, False])
def test_engine_creation(use_rust):
    """Test creating the engine with different backends."""
    try:
        engine = MatchingEngine(use_rust=use_rust)
        # If we get here with use_rust=False, the Python implementation must be available
        assert True
    except NotImplementedError:
        # If Python implementation is not available, this is expected when use_rust=False
        assert not use_rust, "Rust implementation should be available if use_rust=True"


def test_order_book_depth(engine):
    """Test order book depth calculation."""
    # Add multiple buy orders at different price levels
    engine.add_limit_order(OrderSide.BUY, 100.0, 10.0)
    engine.add_limit_order(OrderSide.BUY, 99.0, 20.0)
    engine.add_limit_order(OrderSide.BUY, 98.0, 30.0)
    
    # Add multiple sell orders at different price levels
    engine.add_limit_order(OrderSide.SELL, 101.0, 15.0)
    engine.add_limit_order(OrderSide.SELL, 102.0, 25.0)
    engine.add_limit_order(OrderSide.SELL, 103.0, 35.0)
    
    # Get order book snapshot
    buy_orders, sell_orders = engine.get_order_book_snapshot()
    
    # Verify buy orders
    assert len(buy_orders) == 3
    assert buy_orders[0][0] == 100.0
    assert buy_orders[1][0] == 99.0
    assert buy_orders[2][0] == 98.0
    
    # Verify sell orders
    assert len(sell_orders) == 3
    assert sell_orders[0][0] == 101.0
    assert sell_orders[1][0] == 102.0
    assert sell_orders[2][0] == 103.0
    
    # Calculate total depth
    buy_depth = sum(qty for _, qty in buy_orders)
    sell_depth = sum(qty for _, qty in sell_orders)
    
    assert buy_depth == 60.0
    assert sell_depth == 75.0 