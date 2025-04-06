"""
Main entry point for the trading system.
This module provides wrappers around the CLI and API functionality.
"""
import asyncio
import sys
from typing import Optional, List


def run_api(args: Optional[List[str]] = None):
    """Run the API server with the given arguments."""
    from py_rs_quant.api.run_api import run_api as _run_api
    _run_api(args)


def run_cli(args: Optional[List[str]] = None):
    """Run the CLI with the given arguments."""
    from py_rs_quant.cli import main
    sys.exit(asyncio.run(main(args)))


if __name__ == "__main__":
    # Default to CLI mode if run directly
    run_cli() 