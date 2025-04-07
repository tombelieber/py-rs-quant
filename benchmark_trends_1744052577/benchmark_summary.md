# Benchmark Summary

Comparison of Python and Rust implementations across different order sizes

| Order Size | Python Throughput (ops/s) | Rust Throughput (ops/s) | Rust/Python Ratio | Python Latency (µs) | Rust Latency (µs) | Latency Improvement |
|------------|---------------------------|-------------------------|------------------|---------------------|-------------------|---------------------|
| 1,000 | 671,604.43 | 2,018,627.39 | 3.01x | 1.5 | 0.5 | 66.7% |
| 5,000 | 682,706.67 | 2,219,255.43 | 3.25x | 1.5 | 0.5 | 69.2% |
| 10,000 | 324,408.04 | 2,261,811.91 | 6.97x | 3.1 | 0.4 | 85.7% |
| 50,000 | 528,644.83 | 1,984,661.39 | 3.75x | 1.9 | 0.5 | 73.4% |
| 100,000 | 580,658.31 | 1,974,050.23 | 3.40x | 1.7 | 0.5 | 70.6% |
| 500,000 | 578,121.20 | 1,945,816.87 | 3.37x | 1.7 | 0.5 | 70.3% |

> **Note**: Latency represents the time taken to process a single order through the matching engine, measured in microseconds (µs). Lower latency is better.
> Throughput is measured in operations per second (ops/s). Higher throughput is better.
