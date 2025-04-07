#!/usr/bin/env python
"""
Improved benchmark script with more consistent parameters and longer warmup.
"""
import time
import random
import statistics
import matplotlib.pyplot as plt
from py_rs_quant.core import MatchingEngine, OrderSide, OrderType

def generate_fixed_orders(num_orders, seed=42):
    """Generate a consistent set of orders using a fixed seed."""
    random.seed(seed)  # Use fixed seed for reproducibility
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

def benchmark_engine(use_fast_path=True, num_orders=10000, batch_size=100, 
                    num_runs=3, fixed_orders=None):
    """
    Benchmark the engine with multiple runs for more reliable results.
    
    Args:
        use_fast_path: Whether to use the fast path optimization
        num_orders: Number of orders to process
        batch_size: Batch size for processing orders
        num_runs: Number of benchmark runs to average
        fixed_orders: Pre-generated orders for consistent comparison
    
    Returns:
        Dictionary with benchmark results
    """
    print(f"Testing with {num_orders} orders, fast path: {use_fast_path}, runs: {num_runs}")
    
    all_elapsed = []
    all_buy_orders = []
    all_sell_orders = []
    all_trades = []
    
    # Generate orders once if not provided
    if fixed_orders is None:
        fixed_orders = generate_fixed_orders(num_orders)
    
    for run in range(num_runs):
        # Initialize engine
        engine = MatchingEngine(use_rust=False, use_fast_path=use_fast_path)
        
        # Process orders in batches
        start_time = time.time()
        
        for i in range(0, num_orders, batch_size):
            batch = fixed_orders[i:i+batch_size]
            
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
        
        all_elapsed.append(elapsed)
        all_buy_orders.append(len(buy_orders))
        all_sell_orders.append(len(sell_orders))
        all_trades.append(len(trades))
    
    # Calculate averages
    avg_elapsed = statistics.mean(all_elapsed)
    avg_buy_orders = statistics.mean(all_buy_orders)
    avg_sell_orders = statistics.mean(all_sell_orders)
    avg_trades = statistics.mean(all_trades)
    
    print(f"Average processing time: {avg_elapsed:.4f} seconds")
    print(f"Orders per second: {num_orders / avg_elapsed:.2f}")
    print(f"Average buy orders: {avg_buy_orders:.1f}")
    print(f"Average sell orders: {avg_sell_orders:.1f}")
    print(f"Average trades: {avg_trades:.1f}")
    print(f"Performance mode: {'Fast Path' if use_fast_path else 'Standard'}")
    print()
    
    return {
        "elapsed": avg_elapsed,
        "orders_per_second": num_orders / avg_elapsed,
        "buy_orders": avg_buy_orders,
        "sell_orders": avg_sell_orders,
        "trades": avg_trades
    }

def run_comparative_benchmark(sizes=[1000, 5000, 10000, 20000], runs_per_test=3):
    """Run comprehensive benchmark with multiple sizes and runs per test."""
    results_fast = []
    results_standard = []
    
    for size in sizes:
        print(f"===== Testing with {size} orders =====")
        
        # Generate fixed orders for consistent comparison
        fixed_orders = generate_fixed_orders(size)
        
        # Run with fast path
        result_fast = benchmark_engine(use_fast_path=True, num_orders=size, 
                                     num_runs=runs_per_test, fixed_orders=fixed_orders)
        results_fast.append(result_fast)
        
        # Run with standard path
        result_standard = benchmark_engine(use_fast_path=False, num_orders=size, 
                                         num_runs=runs_per_test, fixed_orders=fixed_orders)
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

def plot_comparative_results(sizes, results_fast, results_standard):
    """Plot comparative results between fast and standard paths."""
    plt.figure(figsize=(12, 10))
    
    # Create subplot for orders per second
    plt.subplot(2, 1, 1)
    
    # Extract orders per second
    ops_fast = [r["orders_per_second"] for r in results_fast]
    ops_std = [r["orders_per_second"] for r in results_standard]
    
    # Plot bars
    plt.bar([x - 0.2 for x in range(len(sizes))], ops_fast, width=0.4, label='Fast Path', color='green')
    plt.bar([x + 0.2 for x in range(len(sizes))], ops_std, width=0.4, label='Standard Path', color='blue')
    
    # Add labels and title
    plt.xlabel('Number of Orders')
    plt.ylabel('Orders per Second')
    plt.title('Performance Comparison: Fast Path vs Standard Path')
    plt.xticks(range(len(sizes)), [f"{size:,}" for size in sizes])
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Create subplot for speedup
    plt.subplot(2, 1, 2)
    
    # Calculate speedups
    speedups = [fast["orders_per_second"]/standard["orders_per_second"] 
               for fast, standard in zip(results_fast, results_standard)]
    
    # Plot speedup line
    plt.plot(range(len(sizes)), speedups, marker='o', linestyle='-', color='red', linewidth=2)
    plt.axhline(y=1.0, color='gray', linestyle='--', alpha=0.7)
    
    # Add labels
    plt.xlabel('Number of Orders')
    plt.ylabel('Speedup (Fast Path / Standard Path)')
    plt.title('Performance Speedup Factor')
    plt.xticks(range(len(sizes)), [f"{size:,}" for size in sizes])
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Add text labels with speedup values
    for i, speedup in enumerate(speedups):
        plt.text(i, speedup + 0.05, f"{speedup:.2f}x", ha='center')
    
    # Adjust layout and save
    plt.tight_layout()
    plt.savefig('improved_performance_comparison.png')
    plt.close()
    
    print("Results plot saved to 'improved_performance_comparison.png'")

if __name__ == "__main__":
    # Extended warmup - important for JIT compilation
    print("Performing warmup...")
    for _ in range(3):
        warmup_orders = generate_fixed_orders(2000)
        # Warm up fast path
        engine_fast = MatchingEngine(use_fast_path=True)
        for side, order_type, price, quantity in warmup_orders:
            if order_type == OrderType.LIMIT:
                engine_fast.add_limit_order(side, price, quantity)
            else:
                engine_fast.add_market_order(side, quantity)
                
        # Warm up standard path
        engine_std = MatchingEngine(use_fast_path=False)
        for side, order_type, price, quantity in warmup_orders:
            if order_type == OrderType.LIMIT:
                engine_std.add_limit_order(side, price, quantity)
            else:
                engine_std.add_market_order(side, quantity)
    
    print("Warmup complete.\n")
    print("===== RUNNING IMPROVED COMPARISON BENCHMARK =====\n")
    
    # Testing sizes - smaller increments for more granular results
    sizes = [1000, 5000, 10000, 15000]
    
    # Run benchmarks with 3 runs per test for more reliable results
    results_fast, results_standard, speedups = run_comparative_benchmark(
        sizes=sizes, runs_per_test=3
    )
    
    # Plot results
    try:
        plot_comparative_results(sizes, results_fast, results_standard)
    except Exception as e:
        print(f"Could not generate plot: {e}") 