"""
Simple simulation example using the py-rs-quant package.
"""
import asyncio
import json

from py_rs_quant import MatchingEngine, RiskManager, MarketSimulator, SimulationMode

async def run_simple_simulation():
    """Run a simple market simulation."""
    # Set up the trading components
    matching_engine = MatchingEngine(use_rust=True)
    risk_manager = RiskManager()
    
    # Configure the symbols and prices
    symbols = ["BTCUSD", "ETHUSD"]
    initial_prices = {"BTCUSD": 50000.0, "ETHUSD": 3000.0}
    
    # Set up risk limits
    risk_manager.max_position_size = {symbol: 100.0 for symbol in symbols}
    risk_manager.max_order_size = {symbol: 10.0 for symbol in symbols}
    risk_manager.max_exposure = 5000000.0
    
    # Create the simulator
    simulator = MarketSimulator(
        matching_engine=matching_engine,
        risk_manager=risk_manager,
        symbols=symbols,
        initial_prices=initial_prices,
        mode=SimulationMode.RANDOM,
        order_rate=5.0,
        volatility=0.005,
        enable_market_orders=True,
        market_order_pct=0.2
    )
    
    # Track trades and orders
    trades = []
    orders = []
    
    def on_trade(trade):
        trades.append(trade)
        print(f"Trade: {trade}")
    
    def on_order(order):
        orders.append(order)
    
    simulator.register_trade_callback(on_trade)
    simulator.register_order_callback(on_order)
    
    # Run the simulation for 10 seconds
    print("Starting simulation...")
    await simulator.run(duration_seconds=10, print_stats=True)
    print("Simulation completed.")
    
    # Print summary
    print(f"Generated {len(orders)} orders and {len(trades)} trades")
    
    # Get the final order book
    buy_orders, sell_orders = matching_engine.get_order_book_snapshot()
    print(f"Final order book - Buy orders: {len(buy_orders)}, Sell orders: {len(sell_orders)}")
    
    return simulator.current_prices

if __name__ == "__main__":
    final_prices = asyncio.run(run_simple_simulation())
    print(f"Final prices: {json.dumps(final_prices, indent=2)}") 