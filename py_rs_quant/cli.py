"""
Command-line interface for the trading simulator.
"""
import argparse
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from py_rs_quant.core.engine import MatchingEngine, OrderSide, OrderType
from py_rs_quant.risk.manager import RiskManager
from py_rs_quant.simulation.simulator import MarketSimulator, SimulationMode
from py_rs_quant.analytics.analyzer import PerformanceAnalyzer, TimeFrame


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("trading_simulator")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Trading System Simulator")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Simulator command
    sim_parser = subparsers.add_parser("simulate", help="Run a market simulation")
    sim_parser.add_argument("--mode", type=str, default="random", 
                            choices=["random", "mean_reverting", "trending", "stress_test"],
                            help="Simulation mode")
    sim_parser.add_argument("--duration", type=int, default=60,
                            help="Simulation duration in seconds")
    sim_parser.add_argument("--symbols", type=str, default="BTCUSD,ETHUSD",
                            help="Comma-separated list of symbols to simulate")
    sim_parser.add_argument("--order-rate", type=float, default=5.0,
                            help="Average orders per second")
    sim_parser.add_argument("--volatility", type=float, default=0.005,
                            help="Price volatility (as decimal, e.g., 0.01 = 1%)")
    sim_parser.add_argument("--initial-prices", type=str, default="BTCUSD:50000.0,ETHUSD:3000.0",
                            help="Initial prices (format: SYMBOL:PRICE,SYMBOL:PRICE,...)")
    sim_parser.add_argument("--market-order-pct", type=float, default=0.2,
                            help="Percentage of orders that are market orders")
    sim_parser.add_argument("--output", type=str, default=None,
                            help="Output file for simulation results (JSON)")
    sim_parser.add_argument("--use-rust", action="store_true", default=True,
                            help="Use Rust implementation for the matching engine")
    
    # Benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Run a performance benchmark")
    bench_parser.add_argument("--iterations", type=int, default=5,
                              help="Number of benchmark iterations")
    bench_parser.add_argument("--orders", type=int, default=10000,
                              help="Number of orders per iteration")
    bench_parser.add_argument("--output", type=str, default=None,
                              help="Output file for benchmark results (JSON)")
    
    # API command
    api_parser = subparsers.add_parser("api", help="Start the REST API server")
    api_parser.add_argument("--host", type=str, default="127.0.0.1",
                            help="Host to bind the API server")
    api_parser.add_argument("--port", type=int, default=8000,
                            help="Port to bind the API server")
    api_parser.add_argument("--use-rust", action="store_true", default=True,
                            help="Use Rust implementation for the matching engine")
    
    return parser.parse_args()


def mode_str_to_enum(mode_str: str) -> SimulationMode:
    """Convert a mode string to a SimulationMode enum."""
    mode_map = {
        "random": SimulationMode.RANDOM,
        "mean_reverting": SimulationMode.MEAN_REVERTING,
        "trending": SimulationMode.TRENDING,
        "stress_test": SimulationMode.STRESS_TEST,
    }
    return mode_map.get(mode_str.lower(), SimulationMode.RANDOM)


def parse_symbols_and_prices(symbols_str: str, prices_str: str) -> Dict[str, float]:
    """Parse symbols and prices from command line arguments."""
    symbols = symbols_str.split(",")
    
    prices = {}
    price_pairs = prices_str.split(",")
    for pair in price_pairs:
        if ":" in pair:
            symbol, price = pair.split(":")
            prices[symbol.strip()] = float(price.strip())
    
    # Ensure we have prices for all symbols
    result = {}
    for symbol in symbols:
        symbol = symbol.strip()
        result[symbol] = prices.get(symbol, 50000.0 if symbol == "BTCUSD" else 3000.0)
    
    return result


async def run_simulation(args):
    """Run a market simulation based on command line arguments."""
    logger.info("Starting market simulation")
    
    # Parse symbols and initial prices
    symbol_prices = parse_symbols_and_prices(args.symbols, args.initial_prices)
    symbols = list(symbol_prices.keys())
    
    # Create matching engine and risk manager
    matching_engine = MatchingEngine(use_rust=args.use_rust)
    risk_manager = RiskManager()
    
    # Set up risk limits
    risk_manager.max_position_size = {symbol: 100.0 for symbol in symbols}
    risk_manager.max_order_size = {symbol: 10.0 for symbol in symbols}
    risk_manager.max_exposure = 5000000.0
    
    # Create performance analyzer
    analyzer = PerformanceAnalyzer()
    
    # Set up the simulator
    simulator = MarketSimulator(
        matching_engine=matching_engine,
        risk_manager=risk_manager,
        symbols=symbols,
        initial_prices=symbol_prices,
        mode=mode_str_to_enum(args.mode),
        order_rate=args.order_rate,
        volatility=args.volatility,
        enable_market_orders=True,
        market_order_pct=args.market_order_pct
    )
    
    # Register callbacks for analytics
    def on_order(order):
        analyzer.add_order(order)
    
    def on_trade(trade):
        analyzer.add_trade(trade)
    
    simulator.register_order_callback(on_order)
    simulator.register_trade_callback(on_trade)
    
    # Run the simulation
    logger.info(f"Running simulation for {args.duration} seconds...")
    start_time = time.time()
    
    # Add initial prices to the analyzer
    for symbol, price in symbol_prices.items():
        timestamp = int(start_time * 1000)
        analyzer.add_price(symbol, timestamp, price)
    
    try:
        await simulator.run(duration_seconds=args.duration, print_stats=True)
    except KeyboardInterrupt:
        logger.info("Simulation interrupted")
        simulator.stop()
    
    elapsed = time.time() - start_time
    logger.info(f"Simulation completed in {elapsed:.2f} seconds")
    
    # Collect order book snapshots for analytics
    for symbol in symbols:
        buy_orders, sell_orders = matching_engine.get_order_book_snapshot()
        timestamp = int(time.time() * 1000)
        analyzer.add_order_book_snapshot(timestamp, symbol, buy_orders, sell_orders)
        
        # Add final price
        analyzer.add_price(symbol, timestamp, simulator.current_prices[symbol])
    
    # Print summary statistics
    for symbol in symbols:
        summary = analyzer.get_summary_statistics(symbol)
        logger.info(f"Summary statistics for {symbol}:")
        logger.info(f"  Total orders: {summary['total_orders']}")
        logger.info(f"  Total trades: {summary['total_trades']}")
        logger.info(f"  Fill ratio: {summary['fill_ratio']:.2%}")
        logger.info(f"  Volume: {summary['volume']}")
        logger.info(f"  Final price: {summary['price_stats']['end']}")
        logger.info(f"  Price change: {summary['price_stats']['pct_change']:+.2%}")
    
    # Save results to file if requested
    if args.output:
        results = {}
        for symbol in symbols:
            results[symbol] = analyzer.export_metrics_to_dict(symbol)
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Simulation results saved to {args.output}")
    
    return 0


async def run_benchmark(args):
    """Run a performance benchmark comparing Python and Rust implementations."""
    logger.info("Starting performance benchmark")
    
    benchmark_results = {
        "python": [],
        "rust": [],
        "comparison": {}
    }
    
    # Create the analyzers for tracking performance
    analyzer = PerformanceAnalyzer()
    
    # Run benchmarks for both implementations
    for engine_type in ["python", "rust"]:
        use_rust = engine_type == "rust"
        
        logger.info(f"Benchmarking {engine_type.upper()} implementation")
        
        # Create matching engine and risk manager
        matching_engine = MatchingEngine(use_rust=use_rust)
        
        # Run iterations
        iteration_results = []
        
        for i in range(args.iterations):
            logger.info(f"  Running iteration {i+1}/{args.iterations}")
            
            # Reset the engine
            matching_engine = MatchingEngine(use_rust=use_rust)
            
            # Generate and process orders
            start_time = time.time()
            order_count = 0
            
            # Track the best prices for limit orders
            bid_price = 50000.0
            ask_price = 50100.0
            
            # Submit orders
            for j in range(args.orders):
                # Alternate between buy and sell
                is_buy = j % 2 == 0
                side = OrderSide.BUY if is_buy else OrderSide.SELL
                
                # Use limit orders
                price = bid_price if is_buy else ask_price
                
                # Randomize prices slightly to prevent perfect matching
                price_offset = (j % 10) * 0.1
                price = price + price_offset if is_buy else price - price_offset
                
                # Submit the order
                order_id = matching_engine.add_limit_order(side, price, 1.0, int(time.time() * 1000))
                order_count += 1
                
                # Periodically update prices
                if j % 100 == 0:
                    bid_price = 50000.0 + (j / args.orders) * 100.0
                    ask_price = bid_price + 100.0
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            # Get trades
            trades = matching_engine.get_trades()
            
            # Record iteration results
            iteration_result = {
                "iteration": i + 1,
                "orders_processed": order_count,
                "trades_executed": len(trades),
                "elapsed_time": elapsed,
                "orders_per_second": order_count / elapsed,
                "trades_per_second": len(trades) / elapsed if elapsed > 0 else 0
            }
            
            iteration_results.append(iteration_result)
            
            # Add latency measurement
            analyzer.add_latency_measurement(
                f"{engine_type}_matching", 
                (elapsed * 1000) / order_count  # Convert to ms per order
            )
            
            # Allow some time between iterations
            await asyncio.sleep(0.1)
        
        # Calculate averages
        avg_orders_per_second = sum(r["orders_per_second"] for r in iteration_results) / len(iteration_results)
        avg_trades_per_second = sum(r["trades_per_second"] for r in iteration_results) / len(iteration_results)
        
        logger.info(f"  {engine_type.upper()} results:")
        logger.info(f"    Average orders/sec: {avg_orders_per_second:.2f}")
        logger.info(f"    Average trades/sec: {avg_trades_per_second:.2f}")
        
        benchmark_results[engine_type] = iteration_results
    
    # Compare implementations
    comparison = analyzer.compare_python_vs_rust()
    
    benchmark_results["comparison"] = {
        "python_mean_latency": comparison["python_mean"],
        "rust_mean_latency": comparison["rust_mean"],
        "improvement_factor": comparison["improvement_factor"],
        "improvement_percent": comparison["improvement_percent"]
    }
    
    logger.info("Benchmark comparison:")
    logger.info(f"  Python mean latency: {comparison['python_mean']:.3f} ms")
    logger.info(f"  Rust mean latency: {comparison['rust_mean']:.3f} ms")
    logger.info(f"  Improvement factor: {comparison['improvement_factor']:.2f}x")
    logger.info(f"  Improvement percent: {comparison['improvement_percent']:.2f}%")
    
    # Save results to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(benchmark_results, f, indent=2)
        
        logger.info(f"Benchmark results saved to {args.output}")
    
    return 0


def start_api_server(args):
    """Start the REST API server."""
    # Import here to avoid circular imports
    from py_rs_quant.api.run_api import run_api
    
    # Replace arguments with the ones from this command
    import sys
    sys.argv = [sys.argv[0], "--host", args.host, "--port", str(args.port)]
    
    # Run the API server
    run_api()
    
    return 0


async def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    if args.command == "simulate":
        return await run_simulation(args)
    elif args.command == "benchmark":
        return await run_benchmark(args)
    elif args.command == "api":
        # Run directly without await since it's not async anymore
        return start_api_server(args)
    else:
        # If no command specified, show help
        parse_args(["--help"])
        return 1


# Add this function for script execution
def run_cli():
    """Run the CLI from a script entry point."""
    import asyncio
    asyncio.run(main())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 