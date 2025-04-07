#!/usr/bin/env python
"""
Plot benchmark results from the py-rs-quant benchmark tool.
"""
import json
import argparse
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


def load_benchmark_data(benchmark_file):
    """Load benchmark data from JSON file."""
    with open(benchmark_file, 'r') as f:
        data = json.load(f)
    return data


def plot_throughput_comparison(data, output_dir):
    """Create a bar chart comparing throughput of Python vs Rust implementations."""
    # Get data
    python_throughput = data['python_stats']['throughput']
    rust_throughput = data.get('rust_stats', {}).get('throughput', 0)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot data
    implementations = ['Python', 'Rust']
    throughputs = [python_throughput, rust_throughput]
    
    bars = ax.bar(implementations, throughputs, color=['#3498db', '#e74c3c'])
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 50000,
                f'{int(height):,}',
                ha='center', va='bottom', fontweight='bold')
    
    # Add improvement text if Rust data is available
    if 'rust_stats' in data:
        improvement = data['comparison']['throughput_improvement_factor']
        plt.text(1, rust_throughput/2, f"{improvement:.1f}x faster", 
                 ha='center', va='center', fontweight='bold', color='white', fontsize=14)
    
    # Customize the plot
    ax.set_title('Throughput Comparison: Python vs Rust\nOrders Processed Per Second', fontsize=16, fontweight='bold')
    ax.set_ylabel('Operations per second', fontsize=14)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Format y-axis ticks to show thousands separator
    ax.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{int(x):,}"))
    
    # Add some padding at the top
    ax.set_ylim(0, max(throughputs) * 1.15)
    
    # Add a descriptive note at the bottom
    plt.figtext(0.5, 0.01, 
                "Higher values indicate better performance (more orders processed per second)", 
                ha='center', fontsize=10, style='italic')
    
    # Save the figure
    output_path = Path(output_dir) / 'throughput_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved throughput comparison chart to {output_path}")
    
    # Close the figure
    plt.close(fig)
    
    return output_path


def plot_latency_comparison(data, output_dir):
    """Create a bar chart comparing latency metrics of Python vs Rust implementations."""
    # Get data
    python_stats = data['python_stats']
    rust_stats = data.get('rust_stats', {})
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Plot data
    metrics = ['Average', 'Median', 'p99', 'Min', 'Max']
    
    # Convert milliseconds to microseconds (1ms = 1000µs)
    python_values = [
        python_stats['avg_latency'] * 1000,
        python_stats['median_latency'] * 1000,
        python_stats['p99_latency'] * 1000,
        python_stats['min_latency'] * 1000,
        python_stats['max_latency'] * 1000
    ]
    
    # If Rust data is available, include it
    if rust_stats:
        # Convert milliseconds to microseconds (1ms = 1000µs)
        rust_values = [
            rust_stats['avg_latency'] * 1000,
            rust_stats['median_latency'] * 1000,
            rust_stats['p99_latency'] * 1000,
            rust_stats['min_latency'] * 1000,
            rust_stats['max_latency'] * 1000
        ]
        
        x = np.arange(len(metrics))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, python_values, width, label='Python', color='#3498db')
        bars2 = ax.bar(x + width/2, rust_values, width, label='Rust', color='#e74c3c')
        
        # Add value labels on top of bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                        f'{height:.1f}',
                        ha='center', va='bottom', rotation=90, fontsize=9)
        
        # Add improvement percentages between bars
        for i, (py_val, rust_val) in enumerate(zip(python_values, rust_values)):
            if py_val > 0 and rust_val > 0:
                improvement = (1 - rust_val/py_val) * 100
                plt.text(i, (py_val + rust_val)/2, f"{improvement:.1f}%", 
                        ha='center', va='center', fontweight='bold', fontsize=10)
    else:
        # Only Python data available
        x = np.arange(len(metrics))
        bars = ax.bar(x, python_values, color='#3498db')
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                    f'{height:.1f}',
                    ha='center', va='bottom', rotation=90, fontsize=9)
    
    # Customize the plot
    ax.set_title('Per-Order Processing Latency Comparison: Python vs Rust\nLower values indicate better performance', fontsize=16, fontweight='bold')
    ax.set_ylabel('Latency (microseconds, µs)', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=12)
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add some padding at the top
    ax.set_ylim(0, max(python_values) * 1.3)
    
    # Add a descriptive note at the bottom
    plt.figtext(0.5, 0.01, 
                "Latency values represent the time taken to process a single order through the matching engine\n(calculated as total processing time divided by number of orders)", 
                ha='center', fontsize=10, style='italic')
    
    # Save the figure
    output_path = Path(output_dir) / 'latency_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved latency comparison chart to {output_path}")
    
    # Close the figure
    plt.close(fig)
    
    return output_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Plot benchmark results')
    parser.add_argument('benchmark_file', type=str, help='JSON file containing benchmark results')
    parser.add_argument('--output-dir', type=str, default='benchmark_charts', help='Directory to save charts')
    
    args = parser.parse_args()
    
    # Load data
    data = load_benchmark_data(args.benchmark_file)
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate charts
    throughput_chart = plot_throughput_comparison(data, output_dir)
    latency_chart = plot_latency_comparison(data, output_dir)
    
    print("\nCharts successfully generated:")
    print(f"1. Throughput Comparison: {throughput_chart}")
    print(f"2. Latency Comparison: {latency_chart}")


if __name__ == "__main__":
    main() 