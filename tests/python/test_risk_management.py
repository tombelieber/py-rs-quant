"""
Tests for the risk management module.
"""
import pytest
from src.python.risk_management.risk_manager import RiskManager, RiskCheckResult


@pytest.fixture
def risk_manager():
    """Create a new risk manager for each test."""
    # Create a risk manager with some limits
    manager = RiskManager(
        max_position_size={"BTCUSD": 10.0, "ETHUSD": 100.0},
        max_order_size={"BTCUSD": 5.0, "ETHUSD": 50.0},
        max_exposure=1000000.0,
        price_tolerance=0.1
    )
    
    # Set up reference prices
    manager.update_reference_price("BTCUSD", 50000.0)
    manager.update_reference_price("ETHUSD", 3000.0)
    
    return manager


def test_position_limit(risk_manager):
    """Test position limit checks."""
    # Set current position
    risk_manager.set_position("BTCUSD", 7.0)
    
    # Check order that would exceed position limit
    result = risk_manager.check_order("BTCUSD", 4.0, 50000.0)
    assert result == RiskCheckResult.FAILED_POSITION_LIMIT
    
    # Check order that would not exceed position limit
    result = risk_manager.check_order("BTCUSD", 2.0, 50000.0)
    assert result == RiskCheckResult.PASSED
    
    # Check sell order that brings position below limit
    result = risk_manager.check_order("BTCUSD", -5.0, 50000.0)
    assert result == RiskCheckResult.PASSED


def test_order_size_limit(risk_manager):
    """Test order size limit checks."""
    # Check order that would exceed size limit
    result = risk_manager.check_order("BTCUSD", 6.0, 50000.0)
    assert result == RiskCheckResult.FAILED_ORDER_SIZE
    
    # Check order that would not exceed size limit
    result = risk_manager.check_order("BTCUSD", 4.0, 50000.0)
    assert result == RiskCheckResult.PASSED
    
    # Check sell order size
    result = risk_manager.check_order("BTCUSD", -6.0, 50000.0)
    assert result == RiskCheckResult.FAILED_ORDER_SIZE


def test_exposure_limit(risk_manager):
    """Test exposure limit checks."""
    # Set a lower exposure limit for the test
    risk_manager.max_exposure = 200000.0
    
    # Check order that would exceed exposure limit
    # 5 BTC at $50,000 = $250,000 > $200,000 limit
    result = risk_manager.check_order("BTCUSD", 5.0, 50000.0)
    assert result == RiskCheckResult.FAILED_EXPOSURE
    
    # Check order that would not exceed exposure limit
    # 3 BTC at $50,000 = $150,000 < $200,000 limit
    result = risk_manager.check_order("BTCUSD", 3.0, 50000.0)
    assert result == RiskCheckResult.PASSED


def test_price_tolerance(risk_manager):
    """Test price tolerance checks."""
    # Set reference price
    reference_price = 50000.0
    risk_manager.update_reference_price("BTCUSD", reference_price)
    
    # Check order with price outside tolerance
    # $50,000 * 1.15 = $57,500 > $50,000 * 1.1 = $55,000 (10% tolerance)
    result = risk_manager.check_order("BTCUSD", 1.0, reference_price * 1.15)
    assert result == RiskCheckResult.FAILED_PRICE_TOLERANCE
    
    # Check order with price inside tolerance
    # $50,000 * 1.05 = $52,500 < $50,000 * 1.1 = $55,000 (10% tolerance)
    result = risk_manager.check_order("BTCUSD", 1.0, reference_price * 1.05)
    assert result == RiskCheckResult.PASSED


def test_update_after_fill(risk_manager):
    """Test updating positions and exposure after fills."""
    # Initial state
    initial_exposure = risk_manager.current_exposure
    
    # Fill a buy order
    risk_manager.update_after_fill("BTCUSD", 2.0, 50000.0)
    
    # Check position was updated
    assert risk_manager.positions["BTCUSD"] == 2.0
    
    # Check exposure was updated (2 BTC at $50,000 = $100,000)
    assert risk_manager.current_exposure == initial_exposure + 100000.0
    
    # Fill a sell order
    risk_manager.update_after_fill("BTCUSD", -1.0, 50000.0)
    
    # Check position was updated
    assert risk_manager.positions["BTCUSD"] == 1.0
    
    # Check exposure was updated (1 BTC at $50,000 = $50,000 more exposure)
    assert risk_manager.current_exposure == initial_exposure + 100000.0 + 50000.0


def test_all_checks_together(risk_manager):
    """Test all risk checks together."""
    # Set up initial state
    risk_manager.set_position("BTCUSD", 8.0)
    risk_manager.current_exposure = 500000.0
    
    # This order should pass all checks
    result = risk_manager.check_order("BTCUSD", 1.0, 50000.0)
    assert result == RiskCheckResult.PASSED
    
    # This order should fail position limit
    result = risk_manager.check_order("BTCUSD", 3.0, 50000.0)
    assert result == RiskCheckResult.FAILED_POSITION_LIMIT
    
    # This order should fail order size
    result = risk_manager.check_order("BTCUSD", 6.0, 50000.0)
    assert result == RiskCheckResult.FAILED_ORDER_SIZE
    
    # Set a lower exposure limit
    risk_manager.max_exposure = 600000.0
    
    # This order should fail exposure limit (500000 + 3*50000 = 650000 > 600000)
    result = risk_manager.check_order("BTCUSD", 3.0, 50000.0)
    assert result == RiskCheckResult.FAILED_POSITION_LIMIT  # Position limit fails first
    
    # Set position to pass position limit check
    risk_manager.set_position("BTCUSD", 5.0)
    
    # Now exposure limit should fail
    result = risk_manager.check_order("BTCUSD", 3.0, 50000.0)
    assert result == RiskCheckResult.FAILED_EXPOSURE
    
    # This order should fail price tolerance
    result = risk_manager.check_order("BTCUSD", 1.0, 60000.0)
    assert result == RiskCheckResult.FAILED_PRICE_TOLERANCE 