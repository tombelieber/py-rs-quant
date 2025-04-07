# Benchmark Summary

Comparison of Python and Rust implementations across different order sizes

| Order Size | Python Throughput (ops/s) | Rust Throughput (ops/s) | Rust/Python Ratio | Python Latency (µs) | Rust Latency (µs) | Latency Improvement |
|------------|---------------------------|-------------------------|------------------|---------------------|-------------------|---------------------|
| 1,000 | 473,184.12 | 1,168,818.17 | 2.47x | 2.1 | 0.9 | 59.5% |
| 5,000 | 657,332.00 | 1,480,882.67 | 2.25x | 1.5 | 0.7 | 55.6% |
| 10,000 | 193,241.82 | 1,883,472.09 | 9.75x | 5.2 | 0.5 | 89.7% |
| 50,000 | 424,002.42 | 1,783,573.10 | 4.21x | 2.4 | 0.6 | 76.2% |
| 100,000 | 500,673.13 | 1,870,173.69 | 3.74x | 2.0 | 0.5 | 73.2% |
| 500,000 | 576,996.48 | 1,915,173.20 | 3.32x | 1.7 | 0.5 | 69.9% |

> **Note**: Latency represents the time taken to process a single order through the matching engine, measured in microseconds (µs). Lower latency is better.
> Throughput is measured in operations per second (ops/s). Higher throughput is better.
