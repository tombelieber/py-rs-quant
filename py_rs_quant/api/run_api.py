"""
Script to run the FastAPI server directly.
"""
import argparse
import logging
import sys
from typing import Optional, List
import uvicorn

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("api_server")


def parse_args(args: Optional[List[str]] = None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Trading System API Server")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="Host to bind the API server")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port to bind the API server")
    return parser.parse_args(args)


def run_api(args: Optional[List[str]] = None):
    """Run the API server."""
    parsed_args = parse_args(args)
    logger.info(f"Starting API server at http://{parsed_args.host}:{parsed_args.port}")
    uvicorn.run(
        "py_rs_quant.api.application:app",
        host=parsed_args.host,
        port=parsed_args.port,
        reload=True,  # Enable auto-reload during development
    )


if __name__ == "__main__":
    run_api(sys.argv[1:]) 