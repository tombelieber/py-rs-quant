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
- Python implementation with Rust acceleration (in development)
- Comprehensive trading simulation tools
- Risk management capabilities
- Advanced analytics for performance evaluation
- FastAPI-based REST API

## Installation

### Prerequisites

- Python 3.8+
- Rust (optional, for Rust engine)

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

## Usage

### CLI

```bash
# Run a market simulation
trading-sim simulate --duration 60 --symbols BTCUSD,ETHUSD

# Run a performance benchmark
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
    engine = MatchingEngine(use_rust=False)  # Rust engine integration in progress
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