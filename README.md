# py-rs-quant

High-Performance Order Matching Engine and Trading Simulator built with Python and Rust.

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
2025-04-07 02:44:54,076 - trading_simulator - INFO - Starting market simulation
2025-04-07 02:44:54,076 - trading_simulator - INFO - Running simulation for 30 seconds...
2025-04-07 02:44:54,076 - py_rs_quant.simulation.simulator - INFO - Starting simulation in RANDOM mode for 30 seconds
...
2025-04-07 02:45:24,076 - py_rs_quant.simulation.simulator - INFO - === Simulation Statistics ===
2025-04-07 02:45:24,076 - py_rs_quant.simulation.simulator - INFO - Mode: RANDOM
2025-04-07 02:45:24,076 - py_rs_quant.simulation.simulator - INFO - Duration: 30.12 seconds
2025-04-07 02:45:24,076 - py_rs_quant.simulation.simulator - INFO - Orders generated: 153
2025-04-07 02:45:24,076 - py_rs_quant.simulation.simulator - INFO - Orders per second: 5.08
2025-04-07 02:45:24,076 - py_rs_quant.simulation.simulator - INFO - Trades executed: 87
2025-04-07 02:45:24,076 - py_rs_quant.simulation.simulator - INFO - Trades per second: 2.89
2025-04-07 02:45:24,076 - py_rs_quant.simulation.simulator - INFO - Fill ratio: 56.86%
2025-04-07 02:45:24,076 - py_rs_quant.simulation.simulator - INFO - BTCUSD price: 49889.69 (-0.22% change)
2025-04-07 02:45:24,076 - trading_simulator - INFO - Summary statistics for BTCUSD:
2025-04-07 02:45:24,076 - trading_simulator - INFO -   Total orders: 153
2025-04-07 02:45:24,076 - trading_simulator - INFO -   Total trades: 87
2025-04-07 02:45:24,076 - trading_simulator - INFO -   Fill ratio: 35.94%
2025-04-07 02:45:24,076 - trading_simulator - INFO -   Volume: 4.32658973
2025-04-07 02:45:24,076 - trading_simulator - INFO -   Final price: 49889.69
2025-04-07 02:45:24,076 - trading_simulator - INFO -   Price change: -0.22%
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
2025-04-07 02:21:37,678 - trading_simulator - INFO - Starting performance benchmark
2025-04-07 02:21:37,678 - trading_simulator - INFO - Benchmarking PYTHON implementation
2025-04-07 02:21:37,678 - trading_simulator - INFO -   Running iteration 1/5
...
2025-04-07 02:21:38,087 - trading_simulator - INFO -   PYTHON results:
2025-04-07 02:21:38,087 - trading_simulator - INFO -     Average orders/sec: 1048635.67
2025-04-07 02:21:38,087 - trading_simulator - INFO -     Average trades/sec: 0.00
2025-04-07 02:21:38,087 - trading_simulator - INFO - Benchmarking RUST implementation
...
2025-04-07 02:21:38,087 - trading_simulator - INFO -   RUST results:
2025-04-07 02:21:38,087 - trading_simulator - INFO -     Average orders/sec: 1228736.62
2025-04-07 02:21:38,087 - trading_simulator - INFO -     Average trades/sec: 0.00
2025-04-07 02:21:38,087 - trading_simulator - INFO - Benchmark comparison:
2025-04-07 02:21:38,087 - trading_simulator - INFO -   Python mean latency: 0.001 ms
2025-04-07 02:21:38,087 - trading_simulator - INFO -   Rust mean latency: 0.001 ms
2025-04-07 02:21:38,087 - trading_simulator - INFO -   Improvement factor: 1.22x
2025-04-07 02:21:38,087 - trading_simulator - INFO -   Improvement percent: 17.71%
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

## License

MIT License 