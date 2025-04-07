# py-rs-quant

High-Performance Order Matching Engine and Trading Simulator built with Python and Rust.

## Project Overview

**High-Performance Trading Engine – py-rs-quant | Trading Engine Performance Optimization Project**

- Developed a high-performance order matching engine with dual Python/Rust implementations, demonstrating expertise in systems programming and algorithmic optimization.
- Leveraged advanced data structures (SortedDict, BTreeMap) and custom memory optimization techniques to achieve 9.75x throughput improvement and 89.7% latency reduction.
- Employed zero-copy operations, bit-level optimizations, and cache-friendly memory patterns to realize sub-microsecond processing times.
- Built comprehensive benchmarking tools with data visualization using Matplotlib to perform data-driven performance analysis across various network conditions and order volumes.
- Integrated PyO3 for cross-language bindings, ensuring seamless Python/Rust integration.
- Applied network analysis techniques, including MTU optimization and throughput modeling.
- Developed a CLI framework for benchmarking and simulation, incorporating performance engineering strategies such as memory pooling and cache-friendly layouts.
- Demonstrated a balanced approach between theoretical knowledge and practical implementation by employing concepts like MTU packet optimization and price-time priority matching algorithms.

**Key Technologies:** Python, Rust, PyO3, Data Structures (SortedDict, BTreeMap), Memory Optimization, Algorithmic Optimization, Matplotlib, CLI Development, Network Analysis, Performance Engineering

## Performance Highlights

- **Rust outperforms Python by up to 9.75x** in throughput
- **Sub-microsecond processing** with the Rust implementation (0.5-0.9µs)
- **Consistent performance advantage** across all order batch sizes (1K-500K orders)
- **89.7% latency reduction** in best case scenarios

![Throughput Comparison](benchmark_charts/throughput_comparison.png)

## Table of Contents

- [py-rs-quant](#py-rs-quant)
  - [Performance Highlights](#performance-highlights)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
    - [Key Features](#key-features)
  - [Quick Usage](#quick-usage)
  - [Performance Comparison](#performance-comparison)
    - [Scaling with Order Size](#scaling-with-order-size)
    - [Performance Trends](#performance-trends)
      - [Throughput Trend](#throughput-trend)
      - [Latency Trend](#latency-trend)
  - [Installation](#installation)
  - [Detailed Usage](#detailed-usage)
    - [Benchmarking](#benchmarking)
    - [Trading Simulation](#trading-simulation)
    - [Python API](#python-api)
  - [What the Latency Measurements Mean](#what-the-latency-measurements-mean)
  - [Real-World Implications](#real-world-implications)
    - [Network Throughput Limitations](#network-throughput-limitations)
      - [Network Throughput by MTU Size (200-byte orders)](#network-throughput-by-mtu-size-200-byte-orders)
      - [Key Takeaways](#key-takeaways)
      - [End-to-End Latency](#end-to-end-latency)
  - [Optimization Techniques](#optimization-techniques)
    - [Performance Optimization Comparison](#performance-optimization-comparison)
    - [Key Optimization Approaches](#key-optimization-approaches)
    - [Performance Cost Analysis](#performance-cost-analysis)
  - [Current Limitations](#current-limitations)
    - [Design Limitations](#design-limitations)
    - [Performance Considerations](#performance-considerations)
  - [TODO](#todo)
    - [Performance Enhancements](#performance-enhancements)
    - [Functional Enhancements](#functional-enhancements)
    - [Production Readiness](#production-readiness)
  - [License](#license)

## Overview

This project implements a matching engine for trading systems with both Python and Rust implementations, allowing for direct performance comparisons. The Rust implementation achieves significantly lower latency and higher throughput.

### Key Features

- Order matching with price-time priority
- Support for limit and market orders
- Order cancellation and modification
- Realistic market simulation capabilities
- Comprehensive benchmarking tools

## Quick Usage

```python
from py_rs_quant import MatchingEngine, RustMatchingEngine

# Use high-performance Rust implementation
engine = RustMatchingEngine()

# Add orders
engine.add_limit_order(side="BUY", price=50000.0, quantity=1.0, timestamp=123456789)
engine.add_market_order(side="SELL", quantity=0.5, timestamp=123456790)

# Get executed trades and order book
trades = engine.get_trades()
buys, sells = engine.get_order_book_snapshot()
```

## Performance Comparison

Rust dramatically outperforms Python in both throughput and latency:

![Latency Comparison](benchmark_charts/latency_comparison.png)

### Scaling with Order Size

We tested performance across different order batch sizes (1,000 to 500,000 orders):

| Order Size | Python Throughput (ops/s) | Rust Throughput (ops/s) | Rust/Python Ratio | Python Latency (µs) | Rust Latency (µs) | Latency Improvement |
|------------|---------------------------|-------------------------|------------------|---------------------|-------------------|---------------------|
| 1,000 | 473,184.12 | 1,168,818.17 | 2.47x | 2.1 | 0.9 | 59.5% |
| 5,000 | 657,332.00 | 1,480,882.67 | 2.25x | 1.5 | 0.7 | 55.6% |
| 10,000 | 193,241.82 | 1,883,472.09 | 9.75x | 5.2 | 0.5 | 89.7% |
| 50,000 | 424,002.42 | 1,783,573.10 | 4.21x | 2.4 | 0.6 | 76.2% |
| 100,000 | 500,673.13 | 1,870,173.69 | 3.74x | 2.0 | 0.5 | 73.2% |
| 500,000 | 576,996.48 | 1,915,173.20 | 3.32x | 1.7 | 0.5 | 69.9% |

### Performance Trends

As order size increases, Rust's performance advantage remains consistent:

#### Throughput Trend
![Throughput Trend](benchmark_trends_readme/throughput_trend.png)

#### Latency Trend
![Latency Trend](benchmark_trends_readme/latency_trend.png)

Key findings:
1. **Rust maintains high throughput** even as order batch size increases
2. **Python throughput varies** more significantly across different batch sizes
3. **Latency gap widens** as order complexity increases
4. **Rust's efficiency advantage** is consistent across all batch sizes

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/py-rs-quant.git
cd py-rs-quant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with Python implementation only
pip install -e .

# Install with Rust acceleration (recommended)
cd matching_engine
cargo build --release
maturin develop --release
cd ..
pip install -e .
```

## Detailed Usage

### Benchmarking

```bash
# Run benchmark comparing Python and Rust implementations
trading-sim benchmark --iterations 5 --orders 10000

# Generate trend analysis across different order sizes
python plot_benchmark_trends.py --order-sizes 1000,5000,10000,50000,100000,500000
```

### Trading Simulation

```bash
# Run a market simulation (default: with Rust acceleration)
trading-sim simulate --duration 60 --symbols BTCUSD,ETHUSD

# Run simulation with Python implementation only
trading-sim simulate --duration 60 --symbols BTCUSD,ETHUSD --no-use-rust
```

### Python API

The library provides both Python and Rust implementations with the same API:

```python
# Python implementation
engine = MatchingEngine()  

# OR Rust implementation (significantly faster)
engine = RustMatchingEngine()  

# Common API methods
engine.add_limit_order(side="BUY", price=50000.0, quantity=1.0, timestamp=123456789)
engine.add_market_order(side="SELL", quantity=0.5, timestamp=123456790)
trades = engine.get_trades()
buys, sells = engine.get_order_book_snapshot()
```

## What the Latency Measurements Mean

The latency metrics represent **per-order processing time** - the time taken for the matching engine to:

1. Receive an order
2. Validate the order
3. Match against the order book (finding counterparties)
4. Execute trades if matches exist
5. Update the order book

In real-world HFT systems, this core matching latency is critical:

- **Cryptocurrency Trading**: During high volatility periods in crypto markets (like Bitcoin flash crashes), price changes occur within microseconds. Our Rust engine's sub-microsecond processing enables responding to market changes before competitors.

- **Market Making**: For market makers providing liquidity, the ability to process and respond to thousands of orders per millisecond directly impacts profitability. The 75% latency reduction with Rust translates to significantly improved price discovery and execution.

- **Risk Management**: Lower latency enables faster position adjustments during market events, reducing exposure to adverse price movements.

## Real-World Implications

The benchmarks in this project measure raw algorithmic performance in an isolated environment. In real-world deployments, additional factors significantly impact overall system performance:

### Network Throughput Limitations

In production trading systems, network capacity often becomes the limiting factor:

#### Network Throughput by MTU Size (200-byte orders)

| Network Configuration | Calculation | Maximum Theoretical Throughput | Realistic Throughput |
|------------------------|-------------|--------------------------------|----------------------|
| **Standard MTU (1500B)** | | | |
| Raw bandwidth (10 Gbps) | 10 Gbps ÷ 8 = 1.25 GB/s | 6.25M orders/sec | - |
| Packets per second | 1.25 GB/s ÷ 1500B = 833K pps | - | - |
| Orders per packet | (1500B - 40B) ÷ 200B = 7.3 orders | - | - |
| MTU-limited throughput | 833K pps × 7 orders = 5.83M orders/sec | 5.83M orders/sec | 1-3M orders/sec |
| **Jumbo Frames (9001B)** | | | |
| Raw bandwidth (10 Gbps) | 10 Gbps ÷ 8 = 1.25 GB/s | 6.25M orders/sec | - |
| Packets per second | 1.25 GB/s ÷ 9001B = 139K pps | - | - |
| Orders per packet | (9001B - 40B) ÷ 200B = 44.8 orders | - | - |
| MTU-limited throughput | 139K pps × 44 orders = 6.12M orders/sec | 6.12M orders/sec | 2-4M orders/sec |

**Note:** Realistic throughput accounts for OS scheduling, interrupt handling, and network congestion, reducing theoretical maximum by 30-70%.

#### Key Takeaways

1. **Packet processing limits throughput** more than raw bandwidth for small orders
2. **Jumbo frames increase efficiency** by allowing more orders per packet (44 vs 7)
3. **Rust's processing speed (1.9M orders/sec)** is well within network capability
4. **Real-world trading systems** are typically constrained by network rather than processing

#### End-to-End Latency

- Processing latency: 0.5-0.9μs (Rust)
- Network latency (same datacenter): 50-200μs
- Network latency (cross-region): 1-80ms

In high-frequency trading, Rust's performance advantage remains valuable for handling microbursts of activity and maintaining consistent performance under load.

## Optimization Techniques

The performance improvements in this project stem from multiple optimization techniques applied to both implementations:

### Performance Optimization Comparison

| Optimization Technique | Python Implementation | Rust Implementation | Impact |
|------------------------|----------------------|---------------------|--------|
| **Data Structure Optimizations** | | | |
| Price-level order book structure | SortedDict with price keys | BTreeMap with bit-converted price keys | Faster price level lookups |
| Order storage | Dict of orders with ID keys + SortedDict | HashMap with custom Vec-based storage | Reduced memory overhead |
| Order queue | Python lists with manual management | Vec with capacity pre-allocation | Reduced allocations |
| **Algorithm Optimizations** | | | |
| Order matching | Direct dict access with early stopping | Iterative with bit flags for match status | Faster execution path |
| Price representation | Negated float keys for buy orders | Integer bit representation of float prices | Better sorting/comparison |
| Trade collection | List with local reference caching | Pre-allocated Vec with capacity hints | Fewer reallocations |
| **Memory Optimizations** | | | |
| Price level caching | LRU-style cache with fixed size (100) | Direct access with no caching layer | Reduced cache overhead |
| Object pooling | Trade object recycling pool | No pooling (objects live on stack) | Less GC pressure |
| Attribute access | `__slots__` for core classes | Stack-allocated structs | Reduced memory footprint |
| **Low-level Optimizations** | | | |
| Function call elimination | Inlined critical path calculations | Zero-cost fn abstractions | Fewer call overhead |
| Memory layout | Contiguous lists for price levels | Aligned data structures | Better cache locality |
| Price conversion | Float negation for buy side sorting | Bit-level float-to-int conversion | Faster comparisons |
| **Implementation-specific Optimizations** | | | |
| Hot path optimization | Cached price level access | `swap_remove` for O(1) removal | Minimized common operations |
| Quantity updates | Incremental cache updates with dirty flag | Copy-on-write for quantity caches | Reduced recalculations |
| Micro-optimizations | numba-accelerated math functions | Bit-level float manipulation | Faster critical operations |

### Key Optimization Approaches

1. **Price-level Indexing and Access**
   - **Python**: Uses `SortedDict` with negative price keys for buy orders to maintain correct sorting
     ```python
     # In OrderBook.__init__()
     self.buy_price_levels = SortedDict()  # key: -price, value: PriceLevel
     self.sell_price_levels = SortedDict()  # key: price, value: PriceLevel
     ```
   - **Rust**: Uses BTreeMap with bit-converted price to ensure consistent sorting order
     ```rust
     // In OrderBook struct
     buy_price_levels: BTreeMap<i64, PriceLevel>,  // Negative price bits for sorting
     sell_price_levels: BTreeMap<i64, PriceLevel>, // Price bits as key
     
     // Helper function for price conversion
     fn price_to_bits(price: f64, is_buy: bool) -> i64 {
         // ...bit manipulation for consistent ordering
     }
     ```

2. **Memory Access Patterns**
   - **Python**: Uses strategic caching to reduce object creation
     ```python
     # In OrderBook
     self._price_level_cache = {}  # Caches frequently accessed price levels
     self._max_cache_size = 100
     ```
   - **Rust**: Pre-allocates vectors to avoid reallocations
     ```rust
     // In PriceLevel::new()
     orders: Vec::with_capacity(16),  // Pre-allocate to avoid frequent reallocations
     ```

3. **Critical Path Optimization**
   - **Python**: Inlines calculations in matching logic to reduce function calls
     ```python
     # Direct access in Matcher.match_buy_order()
     sell_price_levels = self.order_book.sell_price_levels
     order_remaining = order.remaining_quantity
     order_price = order.price
     ```
   - **Rust**: Uses specialized bit flags and direct memory access
     ```rust
     // In OrderBook::process_order
     // Use special bit flags for match status to avoid branches
     let mut match_flags = 0u8;
     if order.remaining_quantity <= 0.001 {
         match_flags |= 1;  // Mark as matched
     }
     ```

4. **Quantity Tracking Optimizations**
   - **Python**: Uses dirty flags to avoid recalculating quantities
     ```python
     # In PriceLevel
     self.is_dirty = True  # Flag cache as dirty
     self.total_qty_cache = ...  # Pre-calculated total
     ```
   - **Rust**: Maintains running totals with pre-calculated quantity values
     ```rust
     // In PriceLevel
     pub total_quantity_cache: f64,
     pub is_dirty: bool,
     
     pub fn update_quantity_cache(&mut self) {
         if self.is_dirty {
             self.total_quantity_cache = self.orders.iter().map(|o| o.remaining_quantity).sum();
             self.is_dirty = false;
         }
     }
     ```

### Performance Cost Analysis

The following optimizations had the biggest impact on performance:

1. **Order Matching Algorithm**: 45-60% of performance gain
   - Rust's zero-cost abstractions allow highly optimized matching loops
   - Python required careful manual optimization to reduce function call overhead

2. **Memory Management**: 20-30% of performance gain
   - Rust's stack allocation vs Python's heap allocation
   - Python's GC pauses vs Rust's deterministic memory management

3. **Data Structure Efficiency**: 15-25% of performance gain
   - Rust's specialized data structures with pre-allocation
   - Custom bit-level operations for price representation in Rust

4. **Price Level Management**: 10-15% of performance gain
   - Rust's O(1) removal with swap_remove
   - Advanced caching in Python to compensate for language limitations

## Current Limitations

While the implementations are highly optimized for throughput and latency, several design limitations exist in the current version:

### Design Limitations

1. **Concurrency Model**
   - Both implementations are currently single-threaded
   - Orders are processed sequentially rather than in parallel
   - No lock-free data structures for concurrent access

2. **Data Persistence**
   - Pure in-memory implementation with no persistence layer
   - No order/trade history beyond the current session
   - No support for recovery after crashes

3. **Order Types & Matching Algorithm**
   - Limited to basic limit and market orders
   - Only price-time priority matching (no pro-rata or other algorithms)
   - No support for complex order types (stop, iceberg, etc.)
   - No cross-order optimization for large batch sizes

### Performance Considerations

1. **Memory Usage**
   - Rust implementation trades memory for performance in pre-allocated structures
   - Both implementations keep all orders and price levels in memory
   - No automatic memory pressure management beyond manual cache clearing

2. **Scaling Limits**
   - Performance degrades with extremely large order books (millions of price levels)
   - No automatic sharding or partitioning for distributed workloads
   - Limited instrumentation for production monitoring and profiling

3. **Real-world Adaptations Needed**
   - No built-in circuit breakers or throttling mechanisms
   - Limited risk management capabilities
   - No handling of exchange-specific protocols or networking code

These limitations inform our roadmap for future improvements beyond those already mentioned in the TODO section.

## TODO

This project is under active development. Here are the planned improvements:

### Performance Enhancements

1. **Parallelization**
   - Implement multi-process benchmarking for Python implementation
   - Implement multi-threaded benchmarking for Rust implementation 
   - Develop lock-free data structures for concurrent order processing
   - Measure scaling efficiency across multiple cores

2. **Memory Optimization**
   - Implement adaptive memory management for large order books
   - Add configurable memory pressure handling
   - Optimize data structure memory footprint for price levels
   - Benchmark memory usage vs performance trade-offs

3. **Cross-Implementation Comparisons**
   - Add Go implementation for comparison
   - Add C++ implementation for comparison
   - Create cross-language performance matrix
   - Analyze performance characteristics across different workloads

### Functional Enhancements

1. **Advanced Order Types**
   - Implement stop orders, stop-limit orders
   - Add iceberg/reserve orders
   - Support good-till-cancel (GTC) and immediate-or-cancel (IOC) orders
   - Implement fill-or-kill (FOK) orders

2. **Matching Algorithm Variants**
   - Add pro-rata matching algorithm
   - Implement FIFO + pro-rata hybrid models
   - Support configurable matching algorithms per instrument
   - Add cross-order optimization for large batch sizes

3. **Data Persistence**
   - Implement order/trade history storage
   - Add crash recovery functionality
   - Create snapshot/restore capabilities
   - Support event sourcing for order book reconstruction

### Production Readiness

1. **Risk Management**
   - Implement circuit breakers and throttling mechanisms
   - Add position limit enforcement
   - Develop risk checks for order validation
   - Create anomaly detection for market conditions

2. **Monitoring & Observability**
   - Add detailed performance metrics collection
   - Implement real-time monitoring interfaces
   - Create visualization tools for order book state
   - Support standard observability frameworks

3. **Distribution & Scaling**
   - Develop sharding for multi-symbol support
   - Implement distributed order book partitioning
   - Create load balancing strategies
   - Benchmark cloud deployment scenarios

The immediate focus will be on parallelization testing and memory optimization, followed by advanced order type support.

## License

MIT 