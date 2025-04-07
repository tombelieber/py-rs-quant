#!/usr/bin/env python
"""
Profiling script for the matching engine.
"""
import cProfile
import pstats
import random
import time
from py_rs_quant.core import MatchingEngine, OrderSide, OrderType

def generate_random_orders(num_orders):
    """Generate a realistic mix of orders for testing."""
    orders = []
    for i in range(num_orders):
        # Random price around 100.0 with some spread
        price = 95.0 + random.random() * 10.0
        # Random quantity between 1 and 10
        quantity = 1.0 + random.random() * 9.0
        # Slightly more buys than sells to ensure some matches
        side = OrderSide.BUY if random.random() < 0.52 else OrderSide.SELL
        # 80% limit orders, 20% market orders
        order_type = OrderType.LIMIT if random.random() < 0.8 else OrderType.MARKET
        # For market orders, price is None
        if order_type == OrderType.MARKET:
            price = None
        
        orders.append((side, order_type, price, quantity))
    
    return orders

def test_engine_performance(num_orders=10000, batch_size=100):
    """Test the performance of the matching engine."""
    print(f"Testing with {num_orders} orders in batches of {batch_size}")
    
    # Initialize engine
    engine = MatchingEngine(use_rust=False)  # Force Python implementation
    
    # Generate orders
    all_orders = generate_random_orders(num_orders)
    
    # Process orders in batches to simulate realistic load
    start_time = time.time()
    
    for i in range(0, num_orders, batch_size):
        batch = all_orders[i:i+batch_size]
        
        # Add each order individually
        for side, order_type, price, quantity in batch:
            if order_type == OrderType.LIMIT:
                engine.add_limit_order(side, price, quantity)
            else:
                engine.add_market_order(side, quantity)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # Get stats
    buy_orders, sell_orders = engine.get_order_book_snapshot()
    trades = engine.get_trades()
    
    print(f"Processed {num_orders} orders in {elapsed:.2f} seconds")
    print(f"Orders per second: {num_orders / elapsed:.2f}")
    print(f"Resulting buy orders: {len(buy_orders)}")
    print(f"Resulting sell orders: {len(sell_orders)}")
    print(f"Resulting trades: {len(trades)}")
    
    return elapsed

if __name__ == "__main__":
    # Run a small warmup to handle any initialization overhead
    test_engine_performance(1000, 100)
    
    print("\nRunning full profiling...\n")
    
    # Profile the main test
    cProfile.run('test_engine_performance(10000, 100)', 'engine_stats.prof')
    
    # Print the profiling results
    p = pstats.Stats('engine_stats.prof')
    p.strip_dirs().sort_stats('cumtime').print_stats(20)  # Show top 20 time-consuming functions
    
    print("\nTo visualize profiling results in a web browser run:")
    print("pip install snakeviz")
    print("snakeviz engine_stats.prof") 