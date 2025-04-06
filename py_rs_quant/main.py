"""
Main entry point for the trading system.
This module provides a wrapper around the CLI functionality.
"""
import asyncio
import sys
from py_rs_quant.cli import main

if __name__ == "__main__":
    # Run the CLI with the current arguments
    sys.exit(asyncio.run(main())) 