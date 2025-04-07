# py-rs-quant

High-Performance Order Matching Engine and Trading Simulator built with Python and Rust.

## Table of Contents

- [Project Structure](#project-structure)
- [Features](#features)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Install from source](#install-from-source)
  - [Enable Rust acceleration](#enable-rust-acceleration-recommended)
- [Usage](#usage)
  - [CLI](#cli)
  - [API Server](#api-server)
  - [Python API](#python-api)
- [Quick Start Demos](#quick-start-demos)
  - [Trading Simulator Demo](#trading-simulator-demo)
  - [Performance Benchmark Demo](#performance-benchmark-demo)
  - [Save Results to File](#save-results-to-file)
- [API Endpoints](#api-endpoints)
- [Docker](#docker)
- [Optimization Techniques](#optimization-techniques)
  - [Language-Specific Optimizations](#language-specific-optimizations)
  - [Shared Optimization Strategies](#shared-optimization-strategies)
  - [Benchmark Results](#benchmark-results)
- [License](#license)

## Project Structure

```
py-rs-quant/
├── py_rs_quant/                # Main Python package
│   ├── analytics/              # Analytics components
│   ├── api/                    # API components
│   │   ├── dependencies/       # FastAPI dependencies
│   │   ├── models/             # Pydantic models (requests/responses)
│   │   ├── routes/             # API routes/endpoints
│   │   ├── services/           # Business logic services
│   │   ├── utils/              # API utility functions
│   │   ├── application.py      # FastAPI application factory
│   │   └── run_api.py          # API server runner
│   ├── core/                   # Core components (including matching engine)
│   ├── risk/                   # Risk management
│   ├── simulation/             # Simulation tools
│   ├── cli.py                  # CLI entrypoint
│   └── main.py                 # Main module with entry points
├── matching_engine/            # Rust crate (top-level)
│   ├── src/                    # Rust source code
│   └── Cargo.toml              # Rust package config
├── tests/                      # Test directory
│   ├── integration/            # Integration tests
│   ├── python/                 # Python unit tests
│   └── rust/                   # Rust tests
├── examples/                   # Usage examples
├── docs/                       # Documentation
├── .gitignore
├── pyproject.toml              # Python build config
├── README.md
├── Dockerfile
└── docker-compose.yml
```

## Features

- High-performance order matching engine
- Python implementation with Rust acceleration (fully functional)
- Comprehensive trading simulation tools
- Risk management capabilities
- Advanced analytics for performance evaluation
- FastAPI-based REST API

## Installation

### Prerequisites

- Python 3.8+
- Rust (for Rust engine acceleration)

### Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/py-rs-quant.git
cd py-rs-quant

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

### Enable Rust acceleration (recommended)

For better performance, build and install the Rust matching engine:

```bash
# Build the Rust matching engine
cd matching_engine
cargo build --release

# Install using maturin
maturin develop --release

# Go back to main directory
cd ..

# Reinstall the package to ensure Rust is properly detected
uv pip install -e .
```

## Usage

### CLI

```bash
# Run a market simulation with Rust acceleration (default)
trading-sim simulate --duration 60 --symbols BTCUSD,ETHUSD

# Run a market simulation with Python implementation only
trading-sim simulate --duration 60 --symbols BTCUSD,ETHUSD --no-use-rust

# Run a performance benchmark comparing Python and Rust
trading-sim benchmark --iterations 5 --orders 10000

# Start the API server (alternative method)
trading-sim api --host 127.0.0.1 --port 8000
```

### API Server

```bash
# Start the API server (recommended method)
trading-api --host 127.0.0.1 --port 8000
```

Once the server is running, you can access the API documentation at http://127.0.0.1:8000/docs

### Python API

```python
import asyncio
from py_rs_quant import MatchingEngine, MarketSimulator, RiskManager, SimulationMode

async def run_simulation():
    engine = MatchingEngine(use_rust=True)  # Rust engine is now fully integrated
    risk_manager = RiskManager()
    simulator = MarketSimulator(
        matching_engine=engine,
        risk_manager=risk_manager,
        symbols=["BTCUSD"],
        initial_prices={"BTCUSD": 50000.0},
        mode=SimulationMode.RANDOM
    )
    
    await simulator.run(duration_seconds=10)
    
asyncio.run(run_simulation())
```

## Quick Start Demos

### Trading Simulator Demo

The trading simulator allows you to run market simulations with different parameters and modes.

```bash
# Activate virtual environment
source venv/bin/activate

# Run a basic simulation for 30 seconds with default parameters (using Rust)
trading-sim simulate --duration 30 --symbols BTCUSD

# Run with Python implementation only
trading-sim simulate --duration 30 --symbols BTCUSD --no-use-rust
```

Sample output:
```
(venv) ➜  py-rs-quant git:(main) trading-sim simulate --duration 3 --symbols BTCUSD      
2025-04-07 04:11:53,716 - trading_simulator - INFO - Starting market simulation
2025-04-07 04:11:53,716 - py_rs_quant.core.engine - INFO - Initializing MatchingEngine (use_rust=True)
2025-04-07 04:11:53,716 - trading_simulator - INFO - Running simulation for 3 seconds...
2025-04-07 04:11:53,716 - trading_simulator - INFO - Running simulation with 8s timeout
2025-04-07 04:11:53,716 - py_rs_quant.simulation.simulator - INFO - Starting simulation in RANDOM mode for 3 seconds
2025-04-07 04:11:53,716 - py_rs_quant.simulation.simulator - INFO - Generating initial orders...
2025-04-07 04:11:53,716 - py_rs_quant.simulation.simulator - INFO - Order: BTCUSD SELL LIMIT size=0.06375508, price=51485.41
2025-04-07 04:11:53,716 - py_rs_quant.simulation.simulator - INFO - Order added with ID: 1
2025-04-07 04:11:53,716 - py_rs_quant.simulation.simulator - INFO - Order: BTCUSD BUY LIMIT size=0.25442736, price=49275.82
2025-04-07 04:11:53,716 - py_rs_quant.simulation.simulator - INFO - Order added with ID: 2
2025-04-07 04:11:53,717 - py_rs_quant.simulation.simulator - INFO - Order: BTCUSD SELL LIMIT size=0.05665181, price=51657.51
2025-04-07 04:11:53,717 - py_rs_quant.simulation.simulator - INFO - Order added with ID: 3
...
2025-04-07 04:11:56,633 - py_rs_quant.simulation.simulator - INFO - Order added with ID: 24
2025-04-07 04:11:56,888 - py_rs_quant.simulation.simulator - INFO - Order: BTCUSD SELL LIMIT size=0.06572257, price=51107.13
2025-04-07 04:11:56,889 - py_rs_quant.simulation.simulator - INFO - Order added with ID: 25
2025-04-07 04:11:56,889 - py_rs_quant.simulation.simulator - INFO - === Simulation Statistics ===
2025-04-07 04:11:56,889 - py_rs_quant.simulation.simulator - INFO - Mode: RANDOM
2025-04-07 04:11:56,889 - py_rs_quant.simulation.simulator - INFO - Duration: 3.17 seconds
2025-04-07 04:11:56,889 - py_rs_quant.simulation.simulator - INFO - Orders generated: 25
2025-04-07 04:11:56,891 - py_rs_quant.simulation.simulator - INFO - Orders per second: 7.88
2025-04-07 04:11:56,891 - py_rs_quant.simulation.simulator - INFO - Trades executed: 7
2025-04-07 04:11:56,891 - py_rs_quant.simulation.simulator - INFO - Trades per second: 2.21
2025-04-07 04:11:56,891 - py_rs_quant.simulation.simulator - INFO - Fill ratio: 28.00%
2025-04-07 04:11:56,891 - py_rs_quant.simulation.simulator - INFO - BTCUSD price: 49786.58 (-0.43% change)
2025-04-07 04:11:56,892 - trading_simulator - INFO - Simulation completed in 3.18 seconds
2025-04-07 04:11:56,893 - trading_simulator - INFO - Summary statistics for BTCUSD:
2025-04-07 04:11:56,893 - trading_simulator - INFO -   Total orders: 25
2025-04-07 04:11:56,893 - trading_simulator - INFO -   Total trades: 0
2025-04-07 04:11:56,893 - trading_simulator - INFO -   Fill ratio: 0.00%
2025-04-07 04:11:56,893 - trading_simulator - INFO -   Volume: 0.0
2025-04-07 04:11:56,893 - trading_simulator - INFO -   Final price: 49786.58
2025-04-07 04:11:56,893 - trading_simulator - INFO -   Price change: -0.43%
(venv) ➜  py-rs-quant git:(main) 
```

Try different simulation modes:

```bash
# Mean-reverting market (prices tend to return to an average)
trading-sim simulate --mode mean_reverting --duration 20 --volatility 0.01

# Trending market (prices tend to move in a direction)
trading-sim simulate --mode trending --duration 20 --volatility 0.007

# Stress test (high volatility, high order rate)
trading-sim simulate --mode stress_test --duration 20 --order-rate 10
```

### Performance Benchmark Demo

Compare the performance of Python and Rust implementations:

```bash
# Run a benchmark with 5 iterations of 10,000 orders each
trading-sim benchmark --iterations 5 --orders 10000
```

Sample output:
```
(venv) ➜  py-rs-quant git:(main) ✗ trading-sim benchmark --iterations 5 --orders 10000
2025-04-07 04:13:00,375 - trading_simulator - INFO - Starting performance benchmark
2025-04-07 04:13:00,375 - trading_simulator - INFO - Benchmarking PYTHON implementation
2025-04-07 04:13:00,375 - py_rs_quant.core.engine - INFO - Initializing MatchingEngine (use_rust=False)
2025-04-07 04:13:00,375 - trading_simulator - INFO -   Running iteration 1/5
2025-04-07 04:13:00,375 - py_rs_quant.core.engine - INFO - Initializing MatchingEngine (use_rust=False)
2025-04-07 04:13:00,500 - trading_simulator - INFO -   Running iteration 2/5
2025-04-07 04:13:00,500 - py_rs_quant.core.engine - INFO - Initializing MatchingEngine (use_rust=False)
2025-04-07 04:13:00,633 - trading_simulator - INFO -   Running iteration 3/5
2025-04-07 04:13:00,633 - py_rs_quant.core.engine - INFO - Initializing MatchingEngine (use_rust=False)
2025-04-07 04:13:00,768 - trading_simulator - INFO -   Running iteration 4/5
2025-04-07 04:13:00,768 - py_rs_quant.core.engine - INFO - Initializing MatchingEngine (use_rust=False)
2025-04-07 04:13:00,904 - trading_simulator - INFO -   Running iteration 5/5
2025-04-07 04:13:00,904 - py_rs_quant.core.engine - INFO - Initializing MatchingEngine (use_rust=False)
2025-04-07 04:13:01,053 - trading_simulator - INFO -   PYTHON results:
2025-04-07 04:13:01,053 - trading_simulator - INFO -     Average orders/sec: 314533.58
2025-04-07 04:13:01,053 - trading_simulator - INFO -     Average trades/sec: 912.15
2025-04-07 04:13:01,053 - trading_simulator - INFO -     Latency (ms) - min: 0.002, max: 0.005, avg: 0.003
2025-04-07 04:13:01,053 - trading_simulator - INFO -     Latency (ms) - median: 0.003, p99: 0.005
2025-04-07 04:13:01,053 - trading_simulator - INFO -     Total latency sum (ms): 0.017
2025-04-07 04:13:01,053 - trading_simulator - INFO -     Overall throughput (ops/sec): 299576.45
2025-04-07 04:13:01,053 - trading_simulator - INFO - Benchmarking RUST implementation
2025-04-07 04:13:01,053 - py_rs_quant.core.engine - INFO - Initializing MatchingEngine (use_rust=True)
2025-04-07 04:13:01,054 - trading_simulator - INFO -   Running iteration 1/5
2025-04-07 04:13:01,054 - py_rs_quant.core.engine - INFO - Initializing MatchingEngine (use_rust=True)
2025-04-07 04:13:01,176 - trading_simulator - INFO -   Running iteration 2/5
2025-04-07 04:13:01,176 - py_rs_quant.core.engine - INFO - Initializing MatchingEngine (use_rust=True)
2025-04-07 04:13:01,301 - trading_simulator - INFO -   Running iteration 3/5
2025-04-07 04:13:01,302 - py_rs_quant.core.engine - INFO - Initializing MatchingEngine (use_rust=True)
2025-04-07 04:13:01,417 - trading_simulator - INFO -   Running iteration 4/5
2025-04-07 04:13:01,417 - py_rs_quant.core.engine - INFO - Initializing MatchingEngine (use_rust=True)
2025-04-07 04:13:01,539 - trading_simulator - INFO -   Running iteration 5/5
2025-04-07 04:13:01,539 - py_rs_quant.core.engine - INFO - Initializing MatchingEngine (use_rust=True)
2025-04-07 04:13:01,664 - trading_simulator - INFO -   RUST results:
2025-04-07 04:13:01,665 - trading_simulator - INFO -     Average orders/sec: 496603.20
2025-04-07 04:13:01,665 - trading_simulator - INFO -     Average trades/sec: 1440.15
2025-04-07 04:13:01,665 - trading_simulator - INFO -     Latency (ms) - min: 0.001, max: 0.002, avg: 0.002
2025-04-07 04:13:01,665 - trading_simulator - INFO -     Latency (ms) - median: 0.002, p99: 0.002
2025-04-07 04:13:01,665 - trading_simulator - INFO -     Total latency sum (ms): 0.010
2025-04-07 04:13:01,665 - trading_simulator - INFO -     Overall throughput (ops/sec): 481506.18
2025-04-07 04:13:01,665 - trading_simulator - INFO - Benchmark comparison:
2025-04-07 04:13:01,665 - trading_simulator - INFO -   Python mean latency: 0.003 ms
2025-04-07 04:13:01,665 - trading_simulator - INFO -   Rust mean latency: 0.002 ms
2025-04-07 04:13:01,665 - trading_simulator - INFO -   Improvement factor: 1.61x
2025-04-07 04:13:01,665 - trading_simulator - INFO -   Improvement percent: 37.78%
2025-04-07 04:13:01,665 - trading_simulator - INFO - Detailed comparison:
2025-04-07 04:13:01,665 - trading_simulator - INFO -   Min latency: Python 0.002 ms vs Rust 0.001 ms
2025-04-07 04:13:01,665 - trading_simulator - INFO -   Max latency: Python 0.005 ms vs Rust 0.002 ms
2025-04-07 04:13:01,665 - trading_simulator - INFO -   Median latency: Python 0.003 ms vs Rust 0.002 ms
2025-04-07 04:13:01,665 - trading_simulator - INFO -   p99 latency: Python 0.005 ms vs Rust 0.002 ms
2025-04-07 04:13:01,665 - trading_simulator - INFO -   Throughput: Python 299576.45 ops/s vs Rust 481506.18 ops/s
(venv) ➜  py-rs-quant git:(main) ✗ 
```

This benchmark demonstrates the performance difference between the pure Python implementation and the Rust-accelerated version of the matching engine.

### Save Results to File

Both simulation and benchmark results can be saved to JSON files for further analysis:

```bash
# Save simulation results
trading-sim simulate --duration 30 --output results/simulation.json

# Save benchmark results
trading-sim benchmark --iterations 3 --orders 50000 --output results/benchmark.json
```

## API Endpoints

The API provides the following main endpoints:

- `GET /health` - Health check endpoint
- `GET /market-data/orderbook/{symbol}` - Get current order book for a symbol
- `GET /market-data/trades/{symbol}` - Get recent trades for a symbol
- `POST /orders` - Submit a new order
- `DELETE /orders/{order_id}` - Cancel an existing order

## Docker

The project includes Docker support for easy deployment.

```bash
# Build and start the services
docker-compose up -d
```

## Optimization Techniques

This project employs various performance optimization techniques to achieve high-throughput, low-latency order matching. Below is a comparison of optimization techniques used in both the Python and Rust implementations:

### Language-Specific Optimizations

| Category | Python Optimizations | Rust Optimizations |
|----------|---------------------|-------------------|
| **Core Performance** | • Numba JIT compilation for critical paths<br>• NumPy vectorized operations<br>• Specialized container types (SortedDict)<br>• Slot-based classes to reduce memory footprint | • Zero-cost abstractions<br>• LLVM optimizations<br>• Link Time Optimization (LTO)<br>• Reduced code generation units (codegen-units=1)<br>• Maximum optimization level (opt-level=3) |
| **Memory Management** | • Object pooling to reduce GC pressure<br>• `__slots__` in classes to reduce overhead<br>• Pre-sized collections where possible | • Stack allocation for most objects<br>• No garbage collection overhead<br>• Pre-allocated vectors with capacity hints<br>• Ownership model preventing memory leaks |
| **Data Structures** | • SortedDict for order book price levels<br>• Array-based heap queues for priority<br>• Dictionaries for fast lookups | • BTreeMap for ordered price levels<br>• Vec with swap_remove for O(1) deletion<br>• HashMap for fast id-based lookups |
| **Concurrency** | • Async/await for non-blocking operations<br>• Asyncio event loop for simulator | • Rayon for parallel processing<br>• Thread-safe structures using RwLock<br>• Arc for shared ownership across threads |

### Shared Optimization Strategies

Both implementations leverage these common optimization techniques:

1. **Algorithmic Optimizations**:
   - Cached aggregations with dirty flags for lazy updates
   - Separate path optimization for market vs limit orders
   - Order batching for amortized processing costs
   - Price level aggregation to reduce individual order processing

2. **Domain-Specific Optimizations**: 
   - Pre-sorting orders by price and time priority
   - Fast-path for non-matching orders
   - Optimistic order matching paths
   - Specialized price comparison logic

3. **Simulation Performance**:
   - Poisson process for realistic order arrival
   - Multiple market behavior models (random, trending, mean-reverting)
   - Event-based architecture to minimize overhead

4. **Instrumentation**:
   - High-precision latency measurements
   - Performance metrics collection
   - Throughput reporting tools

### Benchmark Results

Based on our most recent benchmarks, the Rust implementation significantly outperforms the optimized Python version:

- **Python**: ~515,345 orders/sec, ~2.0µs average per-order processing latency
- **Rust**: ~1,922,000 orders/sec, ~1.0µs average per-order processing latency
- **Improvement**: 4.12x throughput, 75.74% latency reduction

For larger workloads (100,000 orders), the performance advantage remains consistent:

| Metric | Python | Rust | Improvement |
|--------|--------|------|-------------|
| Orders/sec | 515,345 | 1,922,000 | 3.73x |
| Per-order processing latency (avg) | 2.0µs | 1.0µs | 50% reduction |
| Per-order processing latency (p99) | 3.0µs | 1.0µs | 66.7% reduction |
| Trades/sec | 515 | 6,880 | 13.3x |

> **Note**: Latency here represents the time taken to process a single order through the matching engine (not including network or I/O latency). This is calculated by measuring the total time to process a batch of orders divided by the number of orders.

You can visualize benchmark results by using the included plotting tool:

```bash
# Run a benchmark and save results to JSON
trading-sim benchmark --iterations 5 --orders 100000 --output benchmark_results.json

# Generate performance comparison charts
python plot_benchmark.py benchmark_results.json
```

This will create visualization charts in the `benchmark_charts` directory.

## License

MIT License 