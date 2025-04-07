#!/usr/bin/env python
"""
Plot benchmark trends across different order sizes.
Run multiple benchmarks with varying order counts and plot the results.
"""
import json
import argparse
import subprocess
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import time
import os

def run_benchmark(iterations, orders, output_file=None):
    """Run a benchmark with the specified parameters."""
    if output_file is None:
        output_file = f"benchmark_orders_{orders}.json"
    
    print(f"\n=== Running benchmark with {iterations} iterations and {orders} orders ===")
    cmd = [
        "python", "-m", "py_rs_quant.cli", "benchmark", 
        "--iterations", str(iterations),
        "--orders", str(orders),
        "--output", output_file,
        "--no-plot"  # Disable automatic plotting for individual benchmarks
    ]
    
    subprocess.run(cmd, check=True)
    return output_file


def load_benchmark_data(benchmark_file):
    """Load benchmark data from JSON file."""
    with open(benchmark_file, 'r') as f:
        data = json.load(f)
    return data


def run_all_benchmarks(iterations, order_sizes, output_dir):
    """Run benchmarks for all specified order sizes."""
    results = {}
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    for orders in order_sizes:
        output_file = os.path.join(output_dir, f"benchmark_orders_{orders}.json")
        run_benchmark(iterations, orders, output_file)
        results[orders] = load_benchmark_data(output_file)
    
    return results


def plot_throughput_trend(results, order_sizes, output_dir):
    """Plot throughput trend across different order sizes."""
    python_throughput = []
    rust_throughput = []
    
    for size in order_sizes:
        data = results[size]
        python_throughput.append(data["python_stats"]["throughput"])
        if "rust_stats" in data:
            rust_throughput.append(data["rust_stats"]["throughput"])
    
    # Increase figure size to avoid overlapping
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot Python data
    ax.plot(order_sizes, python_throughput, 'o-', color='#3498db', linewidth=2, 
            markersize=8, label='Python')
    
    # Plot Rust data if available
    if rust_throughput:
        ax.plot(order_sizes, rust_throughput, 'o-', color='#e74c3c', linewidth=2,
                markersize=8, label='Rust')
    
    # Add data annotations
    for i, size in enumerate(order_sizes):
        # Add vertical offset to prevent overlap with lines
        y_offset = 0.03 * max(python_throughput)
        ax.annotate(f"{int(python_throughput[i]):,}", 
                   (size, python_throughput[i]),
                   textcoords="offset points",
                   xytext=(0, 10),
                   ha='center')
        
        if rust_throughput:
            ax.annotate(f"{int(rust_throughput[i]):,}", 
                       (size, rust_throughput[i]),
                       textcoords="offset points",
                       xytext=(0, 10),
                       ha='center')
    
    # Customize the plot
    ax.set_title('Throughput vs Order Size', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Number of Orders per Iteration', fontsize=14, labelpad=10)
    ax.set_ylabel('Operations per second', fontsize=14, labelpad=10)
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Improve legend placement to avoid overlap
    ax.legend(fontsize=12, loc='upper left', bbox_to_anchor=(0.02, 0.98))
    
    # Use log scale for x-axis if the range is large
    if max(order_sizes) / min(order_sizes) > 10:
        ax.set_xscale('log')
        # Add custom x tick labels
        ax.set_xticks(order_sizes)
        ax.set_xticklabels([f"{size:,}" for size in order_sizes], rotation=45)
    
    # Format y-axis ticks to show thousands separator
    ax.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{int(x):,}"))
    
    # Add more padding for the figure
    plt.tight_layout(pad=2.0)
    
    # Add a descriptive note at the bottom
    plt.figtext(0.5, 0.01, 
                "Orders processed per second at different batch sizes\nHigher values indicate better performance", 
                ha='center', fontsize=10, style='italic')
    
    # Save the figure
    output_path = Path(output_dir) / 'throughput_trend.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved throughput trend chart to {output_path}")
    
    # Close the figure
    plt.close(fig)
    
    return output_path


def plot_latency_trend(results, order_sizes, output_dir):
    """Plot latency trend across different order sizes."""
    # Extract latency metrics
    python_avg_latency = []
    python_p99_latency = []
    rust_avg_latency = []
    rust_p99_latency = []
    
    for size in order_sizes:
        data = results[size]
        # Convert to microseconds
        python_avg_latency.append(data["python_stats"]["avg_latency"] * 1000)
        python_p99_latency.append(data["python_stats"]["p99_latency"] * 1000)
        
        if "rust_stats" in data:
            rust_avg_latency.append(data["rust_stats"]["avg_latency"] * 1000)
            rust_p99_latency.append(data["rust_stats"]["p99_latency"] * 1000)
    
    # Create plot for average latency - increase figure size
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot Python data
    ax.plot(order_sizes, python_avg_latency, 'o-', color='#3498db', linewidth=2, 
            markersize=8, label='Python (Avg)')
    ax.plot(order_sizes, python_p99_latency, 's--', color='#2980b9', linewidth=2, 
            markersize=8, label='Python (p99)')
    
    # Plot Rust data if available
    if rust_avg_latency:
        ax.plot(order_sizes, rust_avg_latency, 'o-', color='#e74c3c', linewidth=2,
                markersize=8, label='Rust (Avg)')
        ax.plot(order_sizes, rust_p99_latency, 's--', color='#c0392b', linewidth=2,
                markersize=8, label='Rust (p99)')
    
    # Add data annotations with improved positioning
    for i, size in enumerate(order_sizes):
        # Add vertical offset to prevent overlap
        ax.annotate(f"{python_avg_latency[i]:.1f} µs", 
                   (size, python_avg_latency[i]),
                   textcoords="offset points",
                   xytext=(0, 10),
                   ha='center')
        
        if rust_avg_latency:
            ax.annotate(f"{rust_avg_latency[i]:.1f} µs", 
                       (size, rust_avg_latency[i]),
                       textcoords="offset points",
                       xytext=(0, 10),
                       ha='center')
    
    # Customize the plot
    ax.set_title('Per-Order Processing Latency vs Order Size', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Number of Orders per Iteration', fontsize=14, labelpad=10)
    ax.set_ylabel('Latency (microseconds, µs)', fontsize=14, labelpad=10)
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Improve legend placement
    ax.legend(fontsize=12, loc='upper left', bbox_to_anchor=(0.02, 0.98))
    
    # Use log scale for x-axis if the range is large
    if max(order_sizes) / min(order_sizes) > 10:
        ax.set_xscale('log')
        # Add custom x tick labels
        ax.set_xticks(order_sizes)
        ax.set_xticklabels([f"{size:,}" for size in order_sizes], rotation=45)
    
    # Add better padding
    plt.tight_layout(pad=2.0)
    
    # Add a descriptive note at the bottom
    plt.figtext(0.5, 0.01, 
                "Latency represents the time taken to process a single order through the matching engine\nLower values indicate better performance", 
                ha='center', fontsize=10, style='italic')
    
    # Save the figure
    output_path = Path(output_dir) / 'latency_trend.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved latency trend chart to {output_path}")
    
    # Close the figure
    plt.close(fig)
    
    return output_path


def generate_summary_table(results, order_sizes, output_dir):
    """Generate a summary table of benchmark results."""
    rows = []
    rows.append("| Order Size | Python Throughput (ops/s) | Rust Throughput (ops/s) | Rust/Python Ratio | Python Latency (µs) | Rust Latency (µs) | Latency Improvement |")
    rows.append("|------------|---------------------------|-------------------------|------------------|---------------------|-------------------|---------------------|")
    
    for size in order_sizes:
        data = results[size]
        py_throughput = data["python_stats"]["throughput"]
        py_latency = data["python_stats"]["avg_latency"] * 1000  # Convert to µs
        
        if "rust_stats" in data:
            rust_throughput = data["rust_stats"]["throughput"]
            rust_latency = data["rust_stats"]["avg_latency"] * 1000  # Convert to µs
            ratio = rust_throughput / py_throughput
            latency_improve = data["comparison"]["latency_improvement_percent"]
            
            row = f"| {size:,} | {py_throughput:,.2f} | {rust_throughput:,.2f} | {ratio:.2f}x | {py_latency:.1f} | {rust_latency:.1f} | {latency_improve:.1f}% |"
        else:
            row = f"| {size:,} | {py_throughput:,.2f} | N/A | N/A | {py_latency:.1f} | N/A | N/A |"
        
        rows.append(row)
    
    # Write to markdown file
    summary_path = Path(output_dir) / 'benchmark_summary.md'
    with open(summary_path, 'w') as f:
        f.write("# Benchmark Summary\n\n")
        f.write("Comparison of Python and Rust implementations across different order sizes\n\n")
        f.write("\n".join(rows))
        f.write("\n\n")
        f.write("> **Note**: Latency represents the time taken to process a single order through the matching engine, measured in microseconds (µs). Lower latency is better.\n")
        f.write("> Throughput is measured in operations per second (ops/s). Higher throughput is better.\n")
    
    print(f"Saved benchmark summary to {summary_path}")
    return summary_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run benchmarks with multiple order sizes and plot trends')
    parser.add_argument('--iterations', type=int, default=5,
                        help='Number of iterations for each benchmark')
    parser.add_argument('--order-sizes', type=str, default="1000,10000,100000",
                        help='Comma-separated list of order sizes to benchmark')
    parser.add_argument('--output-dir', type=str, default="benchmark_trends",
                        help='Directory to save results and charts')
    
    args = parser.parse_args()
    
    # Parse order sizes
    order_sizes = [int(size) for size in args.order_sizes.split(',')]
    
    # Create timestamp for the run
    timestamp = int(time.time())
    output_dir = f"{args.output_dir}_{timestamp}"
    
    # Run all benchmarks
    print(f"Starting benchmark series with order sizes: {order_sizes}")
    print(f"Each benchmark will run with {args.iterations} iterations")
    results = run_all_benchmarks(args.iterations, order_sizes, output_dir)
    
    # Generate charts
    throughput_chart = plot_throughput_trend(results, order_sizes, output_dir)
    latency_chart = plot_latency_trend(results, order_sizes, output_dir)
    
    # Generate summary table
    summary_table = generate_summary_table(results, order_sizes, output_dir)
    
    print("\nBenchmark series completed!")
    print(f"Results saved to: {output_dir}/")
    print(f"Throughput trend: {throughput_chart}")
    print(f"Latency trend: {latency_chart}")
    print(f"Summary table: {summary_table}")


if __name__ == "__main__":
    main() 