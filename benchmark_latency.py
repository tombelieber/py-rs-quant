#!/usr/bin/env python
"""
Simple benchmark to measure the mean latency of key operations.
"""
import time
import statistics
from py_rs_quant.core import MatchingEngine, OrderSide, OrderType

def measure_latency(operation, iterations=10000, warmup=1000):
    """Measure the latency of an operation."""
    # Warmup phase
    for _ in range(warmup):
        operation()
    
    # Measurement phase
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        operation()
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # Convert to ms
    
    mean = statistics.mean(latencies)
    median = statistics.median(latencies)
    p99 = sorted(latencies)[int(iterations * 0.99)]
    
    return {
        "mean": mean,
        "median": median,
        "p99": p99,
        "min": min(latencies),
        "max": max(latencies)
    }

def main():
    """Run latency benchmarks."""
    print("Initializing engine...")
    engine = MatchingEngine(use_fast_path=True)
    
    # Define operations to benchmark
    operations = {
        "add_limit_buy": lambda: engine.add_limit_order(OrderSide.BUY, 100.0, 1.0),
        "add_limit_sell": lambda: engine.add_limit_order(OrderSide.SELL, 100.0, 1.0),
        "add_market_buy": lambda: engine.add_market_order(OrderSide.BUY, 1.0),
        "add_market_sell": lambda: engine.add_market_order(OrderSide.SELL, 1.0),
    }
    
    # Run benchmarks
    print("\nRunning latency benchmarks (fast path):")
    print("-" * 80)
    print(f"{'Operation':<20} {'Mean (ms)':<15} {'Median (ms)':<15} {'p99 (ms)':<15} {'Min (ms)':<15} {'Max (ms)':<15}")
    print("-" * 80)
    
    for name, operation in operations.items():
        result = measure_latency(operation)
        print(f"{name:<20} {result['mean']:<15.6f} {result['median']:<15.6f} {result['p99']:<15.6f} {result['min']:<15.6f} {result['max']:<15.6f}")
    
    # Reinitialize with standard path
    print("\nRunning latency benchmarks (standard path):")
    engine = MatchingEngine(use_fast_path=False)
    print("-" * 80)
    print(f"{'Operation':<20} {'Mean (ms)':<15} {'Median (ms)':<15} {'p99 (ms)':<15} {'Min (ms)':<15} {'Max (ms)':<15}")
    print("-" * 80)
    
    for name, operation in operations.items():
        result = measure_latency(operation)
        print(f"{name:<20} {result['mean']:<15.6f} {result['median']:<15.6f} {result['p99']:<15.6f} {result['min']:<15.6f} {result['max']:<15.6f}")

if __name__ == "__main__":
    main() 