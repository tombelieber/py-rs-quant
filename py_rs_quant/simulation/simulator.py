"""
Market simulation module for generating orders and simulating market activity.
"""
import random
import time
import asyncio
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, Callable
import logging

import numpy as np

from py_rs_quant.core.engine import MatchingEngine, OrderSide, OrderType, Order, Trade
from py_rs_quant.risk.manager import RiskManager, RiskCheckResult

logger = logging.getLogger(__name__)


class SimulationMode(Enum):
    """Simulation modes for different market scenarios."""
    RANDOM = 1  # Random order generation
    MEAN_REVERTING = 2  # Mean-reverting price model
    TRENDING = 3  # Trending market
    STRESS_TEST = 4  # High volume, volatility stress test


class MarketSimulator:
    """
    Market simulator for generating orders and simulating market activity.
    """
    
    def __init__(
        self,
        matching_engine: MatchingEngine,
        risk_manager: Optional[RiskManager] = None,
        symbols: List[str] = None,
        initial_prices: Dict[str, float] = None,
        mode: SimulationMode = SimulationMode.RANDOM,
        order_rate: float = 1.0,  # Orders per second
        volatility: float = 0.02,  # Price volatility (standard deviation)
        tick_size: float = 0.01,  # Minimum price movement
        enable_market_orders: bool = True,
        market_order_pct: float = 0.1,  # Percentage of orders that are market orders
    ):
        """
        Initialize the market simulator.
        
        Args:
            matching_engine: The matching engine to use
            risk_manager: Optional risk manager for pre-trade checks
            symbols: List of symbols to simulate
            initial_prices: Initial prices for each symbol
            mode: Simulation mode to use
            order_rate: Average number of orders per second
            volatility: Price volatility as standard deviation
            tick_size: Minimum price movement
            enable_market_orders: Whether to generate market orders
            market_order_pct: Percentage of orders that are market orders
        """
        self.matching_engine = matching_engine
        self.risk_manager = risk_manager
        self.symbols = symbols or ["BTCUSD"]
        self.initial_prices = initial_prices or {symbol: 50000.0 for symbol in self.symbols}
        self.mode = mode
        self.order_rate = order_rate
        self.volatility = volatility
        self.tick_size = tick_size
        self.enable_market_orders = enable_market_orders
        self.market_order_pct = market_order_pct
        
        # Current reference prices
        self.current_prices = self.initial_prices.copy()
        
        # For mean-reverting and trending models
        self.mean_levels = self.initial_prices.copy()
        self.trends = {symbol: 0.0 for symbol in self.symbols}  # No trend by default
        
        # Statistics
        self.orders_generated = 0
        self.trades_generated = 0
        self.start_time = 0
        self.end_time = 0
        
        # Running flag
        self.running = False
        
        # Callbacks
        self.on_order_callback = None
        self.on_trade_callback = None
    
    async def run(self, duration_seconds: int = 60, print_stats: bool = True):
        """
        Run the simulation for a specified duration.
        
        Args:
            duration_seconds: Duration in seconds to run
            print_stats: Whether to print statistics after simulation
        """
        self.running = True
        self.start_time = time.time()
        self.orders_generated = 0
        self.trades_generated = 0
        
        logger.info(f"Starting simulation in {self.mode.name} mode for {duration_seconds} seconds")
        
        # Update risk manager with initial prices if available
        if self.risk_manager:
            for symbol, price in self.current_prices.items():
                self.risk_manager.update_reference_price(symbol, price)
        
        # Main simulation loop
        end_time = self.start_time + duration_seconds
        
        while self.running and time.time() < end_time:
            # Calculate delay based on order rate (Poisson process)
            delay = random.expovariate(self.order_rate)
            await asyncio.sleep(delay)
            
            # Generate and process a new order
            await self._generate_next_order()
            
            # Update statistics
            self.orders_generated += 1
        
        self.running = False
        self.end_time = time.time()
        
        if print_stats:
            self.print_stats()
    
    def stop(self):
        """Stop the simulation."""
        self.running = False
        logger.info("Simulation stopped")
    
    def print_stats(self):
        """Print simulation statistics."""
        elapsed_time = self.end_time - self.start_time if self.end_time else time.time() - self.start_time
        
        logger.info("=== Simulation Statistics ===")
        logger.info(f"Mode: {self.mode.name}")
        logger.info(f"Duration: {elapsed_time:.2f} seconds")
        logger.info(f"Orders generated: {self.orders_generated}")
        logger.info(f"Orders per second: {self.orders_generated / elapsed_time:.2f}")
        
        # Get trades from the matching engine
        trades = self.matching_engine.get_trades()
        num_trades = len(trades)
        
        logger.info(f"Trades executed: {num_trades}")
        logger.info(f"Trades per second: {num_trades / elapsed_time:.2f}")
        logger.info(f"Fill ratio: {num_trades / max(1, self.orders_generated):.2%}")
        
        # Calculate price statistics
        for symbol, price in self.current_prices.items():
            initial_price = self.initial_prices[symbol]
            price_change = (price - initial_price) / initial_price
            logger.info(f"{symbol} price: {price:.2f} ({price_change:+.2%} change)")
    
    def register_order_callback(self, callback: Callable[[Order], None]):
        """Register a callback to be called when an order is generated."""
        self.on_order_callback = callback
    
    def register_trade_callback(self, callback: Callable[[Trade], None]):
        """Register a callback to be called when a trade is executed."""
        self.on_trade_callback = callback
        # Register the callback with the matching engine
        self.matching_engine.register_trade_callback(callback)
    
    async def _generate_next_order(self):
        """Generate the next order based on the simulation mode."""
        # Select a random symbol
        symbol = random.choice(self.symbols)
        
        # Update the current price based on the simulation mode
        self._update_price(symbol)
        
        # Determine order type (market or limit)
        is_market_order = self.enable_market_orders and random.random() < self.market_order_pct
        
        # Determine order side (buy or sell)
        is_buy = random.random() < 0.5
        
        # Determine order size (log-normal distribution)
        size_factor = random.lognormvariate(0, 0.5)  # mean=1, stddev depends on the second parameter
        base_size = 0.1 if symbol == "BTCUSD" else 1.0  # Example: smaller size for BTC, larger for ETH
        order_size = round(base_size * size_factor, 8)  # Round to 8 decimal places
        
        # Create order
        if is_market_order:
            order_type = OrderType.MARKET
            price = None
        else:
            order_type = OrderType.LIMIT
            
            # For limit orders, set price relative to current price
            current_price = self.current_prices[symbol]
            
            # Add some random offset for limit orders
            if is_buy:
                # Buy orders are typically below current price
                offset_factor = -random.lognormvariate(-1, 0.5)  # Negative offset for buys
            else:
                # Sell orders are typically above current price
                offset_factor = random.lognormvariate(-1, 0.5)  # Positive offset for sells
            
            # Apply offset and round to tick size
            price_offset = current_price * offset_factor
            price = round((current_price + price_offset) / self.tick_size) * self.tick_size
            
            # Ensure price is positive
            price = max(self.tick_size, price)
        
        # Create order side
        side = OrderSide.BUY if is_buy else OrderSide.SELL
        
        # Log the order
        logger.debug(
            f"Generated order: symbol={symbol}, side={'BUY' if is_buy else 'SELL'}, "
            f"type={'MARKET' if is_market_order else 'LIMIT'}, "
            f"size={order_size}, price={price}"
        )
        
        # Apply risk checks if risk manager is available
        if self.risk_manager:
            order_size_signed = order_size if is_buy else -order_size
            check_price = price if price is not None else self.current_prices[symbol]
            
            risk_result = self.risk_manager.check_order(
                symbol=symbol,
                order_size=order_size_signed,
                price=check_price,
                check_price_tolerance=not is_market_order
            )
            
            if risk_result != RiskCheckResult.PASSED:
                logger.debug(f"Order rejected by risk manager: {risk_result.name}")
                return
        
        # Submit to matching engine
        timestamp = int(time.time() * 1000)
        order_id = None
        
        try:
            if is_market_order:
                order_id = self.matching_engine.add_market_order(side, order_size, timestamp, symbol)
            else:
                order_id = self.matching_engine.add_limit_order(side, price, order_size, timestamp, symbol)
            
            # Call the order callback if registered
            if self.on_order_callback:
                order = Order(
                    order_id=order_id,
                    side=side,
                    order_type=order_type,
                    price=price,
                    quantity=order_size,
                    timestamp=timestamp,
                    symbol=symbol
                )
                self.on_order_callback(order)
        except Exception as e:
            logger.error(f"Error submitting order: {e}")
    
    def _update_price(self, symbol: str):
        """Update the current price based on the simulation mode."""
        current_price = self.current_prices[symbol]
        
        if self.mode == SimulationMode.RANDOM:
            # Simple random walk
            price_change = current_price * self.volatility * random.normalvariate(0, 1)
            new_price = current_price + price_change
        
        elif self.mode == SimulationMode.MEAN_REVERTING:
            # Mean-reverting process (Ornstein-Uhlenbeck)
            mean_level = self.mean_levels[symbol]
            mean_reversion_speed = 0.1  # Strength of mean reversion
            
            # Calculate drift towards mean
            drift = mean_reversion_speed * (mean_level - current_price)
            
            # Random component
            diffusion = self.volatility * current_price * random.normalvariate(0, 1)
            
            # Update price
            new_price = current_price + drift + diffusion
        
        elif self.mode == SimulationMode.TRENDING:
            # Trending market with random walk
            trend = self.trends[symbol]  # Percentage trend per step
            trend_component = current_price * trend
            random_component = current_price * self.volatility * random.normalvariate(0, 1)
            
            new_price = current_price + trend_component + random_component
        
        elif self.mode == SimulationMode.STRESS_TEST:
            # High volatility stress test
            stress_volatility = self.volatility * 3  # 3x normal volatility
            price_change = current_price * stress_volatility * random.normalvariate(0, 1)
            new_price = current_price + price_change
        
        else:
            # Default to current price if unknown mode
            new_price = current_price
        
        # Ensure price is positive and rounded to tick size
        new_price = max(self.tick_size, round(new_price / self.tick_size) * self.tick_size)
        
        # Update current price
        self.current_prices[symbol] = new_price
        
        # Update risk manager if available
        if self.risk_manager:
            self.risk_manager.update_reference_price(symbol, new_price)
        
        return new_price


async def run_simulation_example():
    """Run a simple example simulation."""
    # Create the matching engine and risk manager
    matching_engine = MatchingEngine(use_rust=True)
    risk_manager = RiskManager()
    
    # Set up risk limits
    risk_manager.max_position_size = {"BTCUSD": 100.0, "ETHUSD": 1000.0}
    risk_manager.max_order_size = {"BTCUSD": 10.0, "ETHUSD": 100.0}
    risk_manager.max_exposure = 5000000.0
    
    # Set up the simulator
    simulator = MarketSimulator(
        matching_engine=matching_engine,
        risk_manager=risk_manager,
        symbols=["BTCUSD", "ETHUSD"],
        initial_prices={"BTCUSD": 50000.0, "ETHUSD": 3000.0},
        mode=SimulationMode.MEAN_REVERTING,
        order_rate=5.0,  # 5 orders per second
        volatility=0.005,  # 0.5% volatility
        enable_market_orders=True,
        market_order_pct=0.2  # 20% market orders
    )
    
    # Register callbacks for monitoring
    def on_order(order):
        print(f"New order: {order}")
    
    simulator.register_order_callback(on_order)
    
    # Run the simulation for 10 seconds
    print("Starting simulation...")
    await simulator.run(duration_seconds=10)
    
    # Print final order book snapshot
    buy_orders, sell_orders = matching_engine.get_order_book_snapshot()
    print("\nFinal Order Book:")
    print("Buy orders:")
    for price, qty in buy_orders:
        print(f"  {qty} @ {price:.2f}")
    print("Sell orders:")
    for price, qty in sell_orders:
        print(f"  {qty} @ {price:.2f}")
    
    # Print trades
    trades = matching_engine.get_trades()
    print(f"\nTotal trades: {len(trades)}")
    for trade in trades[:5]:  # Print first 5 trades
        print(f"  {trade}")
    
    print("\nSimulation complete!")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run the example
    asyncio.run(run_simulation_example()) 