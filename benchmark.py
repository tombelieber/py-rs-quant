#!/usr/bin/env python
"""
Benchmark script to compare the performance of fast path vs standard path.
"""
import time
import random
import matplotlib.pyplot as plt
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

def benchmark_engine(use_fast_path=True, num_orders=10000, batch_size=100):
    """Benchmark the engine with or without fast path."""
    print(f"Testing with {num_orders} orders in batches of {batch_size}, fast path: {use_fast_path}")
    
    # Initialize engine
    engine = MatchingEngine(use_rust=False, use_fast_path=use_fast_path)
    
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
    print(f"Performance mode: {engine.get_performance_mode()}")
    print()
    
    cache_stats = engine.get_cache_stats()
    
    return {
        "elapsed": elapsed,
        "orders_per_second": num_orders / elapsed,
        "buy_orders": len(buy_orders),
        "sell_orders": len(sell_orders),
        "trades": len(trades),
        "cache_hit_ratio": cache_stats.get("hit_ratio", 0)
    }

def run_size_comparison(sizes=[1000, 5000, 10000, 20000]):
    """Run comparison with different order sizes."""
    results_fast = []
    results_standard = []
    
    for size in sizes:
        print(f"===== Testing with {size} orders =====")
        # Run with fast path
        result_fast = benchmark_engine(use_fast_path=True, num_orders=size)
        results_fast.append(result_fast)
        
        # Run with standard path
        result_standard = benchmark_engine(use_fast_path=False, num_orders=size)
        results_standard.append(result_standard)
        
        print("-------------------------------------")
    
    # Calculate speedup for each size
    speedups = [fast["orders_per_second"]/standard["orders_per_second"] 
                for fast, standard in zip(results_fast, results_standard)]
    
    # Print speedup summary
    print("\n===== SPEEDUP SUMMARY =====")
    for i, size in enumerate(sizes):
        print(f"Orders: {size:,} - Speedup: {speedups[i]:.2f}x")
    
    return results_fast, results_standard, speedups

def plot_results(sizes, results_fast, results_standard):
    """Plot comparative results."""
    plt.figure(figsize=(12, 6))
    
    # Extract orders per second
    ops_fast = [r["orders_per_second"] for r in results_fast]
    ops_std = [r["orders_per_second"] for r in results_standard]
    
    # Plot
    plt.bar([x - 0.2 for x in range(len(sizes))], ops_fast, width=0.4, label='Fast Path', color='green')
    plt.bar([x + 0.2 for x in range(len(sizes))], ops_std, width=0.4, label='Standard Path', color='blue')
    
    # Add labels and title
    plt.xlabel('Number of Orders')
    plt.ylabel('Orders per Second')
    plt.title('Performance Comparison: Fast Path vs Standard Path')
    plt.xticks(range(len(sizes)), [f"{size:,}" for size in sizes])
    plt.legend()
    
    # Save the plot
    plt.savefig('performance_comparison.png')
    plt.close()
    
    print("Results plot saved to 'performance_comparison.png'")

if __name__ == "__main__":
    # Small warmup
    benchmark_engine(use_fast_path=True, num_orders=1000)
    benchmark_engine(use_fast_path=False, num_orders=1000)
    
    print("\n===== RUNNING COMPARISON BENCHMARK =====\n")
    
    # Testing sizes
    sizes = [1000, 5000, 10000, 20000]
    
    # Run benchmarks
    results_fast, results_standard, speedups = run_size_comparison(sizes)
    
    # Plot results if matplotlib is available
    try:
        plot_results(sizes, results_fast, results_standard)
    except Exception as e:
        print(f"Could not generate plot: {e}") 