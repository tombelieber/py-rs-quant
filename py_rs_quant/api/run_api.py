"""
Script to run the FastAPI server directly.
"""
import argparse
import logging
import uvicorn
from py_rs_quant.api.app import app

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("api_server")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Trading System API Server")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="Host to bind the API server")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port to bind the API server")
    return parser.parse_args()

def run_api():
    """Run the API server."""
    args = parse_args()
    logger.info(f"Starting API server at http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    run_api() 