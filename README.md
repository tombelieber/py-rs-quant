# High-Performance Order Matching Engine and Trading Simulator

A high-performance trading system simulation platform implemented in Python with performance-critical components optimized in Rust. This project demonstrates advanced techniques for building efficient financial systems by combining the ease of use and rapid development of Python with the performance benefits of Rust.

## Features

- **High-performance order matching engine** implemented in Rust, exposed to Python via PyO3
- **Comprehensive order book management** supporting limit and market orders
- **Risk management system** with position limits, order size checks, and exposure controls
- **RESTful API** built with FastAPI for submitting orders and querying market data
- **Market simulation tools** for generating realistic market conditions and order flow
- **Performance analytics** to measure and visualize system metrics
- **Performance benchmarks** comparing Python and Rust implementations
- **Docker containerization** for easy deployment and testing

## System Architecture

The system consists of several key components:

1. **Order Matching Engine (Rust)**: The core order matching algorithm implemented in Rust for high performance.
2. **Python Engine Wrapper**: Python wrapper around the Rust engine allowing for easy integration.
3. **Risk Management Module**: Pre-trade risk checks and position monitoring.
4. **API Server**: RESTful API for order submission and market data queries.
5. **Simulation Controller**: Tools for generating realistic market conditions and order flow.
6. **Analytics Engine**: Statistics and visualization of system performance.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Rust (latest stable version)
- Cargo (Rust's package manager)
- Docker (optional, for containerized deployment)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/py-rs-quant.git
   cd py-rs-quant
   ```

2. **Install development dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Build the Rust extension**:
   ```bash
   maturin develop
   ```

### Running the system

The system can be run in several modes:

#### 1. API Server

Start the REST API server:

```bash
python -m src.python.cli api --host 127.0.0.1 --port 8000
```

Then you can access the API documentation at: http://127.0.0.1:8000/docs

#### 2. Market Simulation

Run a market simulation:

```bash
python -m src.python.cli simulate --mode mean_reverting --duration 60 --order-rate 5.0
```

Available simulation modes:
- `random`: Random price movements
- `mean_reverting`: Mean-reverting price model
- `trending`: Trending market
- `stress_test`: High volatility stress test

#### 3. Performance Benchmark

Run a performance benchmark comparing Python and Rust implementations:

```bash
python -m src.python.cli benchmark --iterations 5 --orders 10000
```

### Docker Deployment

The system can be easily run using Docker:

```bash
docker-compose up api  # Start the API server
docker-compose up simulator  # Run a simulation
docker-compose up benchmark  # Run a benchmark
```

## API Documentation

The API provides the following endpoints:

- **POST /orders**: Submit a new order
- **GET /orders/{order_id}**: Get the status of an order
- **DELETE /orders/{order_id}**: Cancel an order
- **GET /orderbook/{symbol}**: Get the current order book for a symbol
- **GET /trades**: Get the list of executed trades

For detailed API documentation, start the API server and visit: http://127.0.0.1:8000/docs

## Performance Comparison

The Rust implementation of the order matching engine offers significant performance improvements over a pure Python implementation. The benchmark module can be used to quantify these differences.

Typical benchmark results show:
- **Order processing throughput**: 5-15x improvement
- **Latency**: 3-10x reduction in order processing latency
- **Memory usage**: Reduced memory footprint

## Development

### Project Structure

```
py-rs-quant/
├── src/
│   ├── python/
│   │   ├── api/              # FastAPI REST API
│   │   │   ├── api.py        # FastAPI REST API
│   │   │   └── main.py       # Main entry point
│   │   ├── matching_engine/  # Python wrapper for the matching engine
│   │   ├── risk_management/  # Risk management module
│   │   ├── analytics/        # Analytics and statistics
│   │   ├── simulation/       # Market simulation tools
│   │   ├── cli.py            # Command-line interface
│   │   └── main.py           # Main entry point
│   └── rust/
│       └── matching_engine/  # Rust implementation of the matching engine
├── tests/
│   ├── python/               # Python tests
│   └── rust/                 # Rust tests
├── docs/                     # Documentation
├── deployment/               # Deployment configurations
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker Compose configuration
├── pyproject.toml            # Python project configuration
└── README.md                 # This file
```

### Testing

Run the test suite:

```bash
pytest
```

For Rust-specific tests:

```bash
cd src/rust/matching_engine && cargo test
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The Rust community for PyO3 and tools for Python/Rust interoperability
- FastAPI for the excellent API framework
- The quant finance community for insights into market dynamics 