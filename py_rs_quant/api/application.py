"""
Main FastAPI application module.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from py_rs_quant.api.dependencies.engines import initialize_engines
from py_rs_quant.api.routes import router


logger = logging.getLogger("api")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: The configured FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title="Trading System API",
        description="API for the high-performance trading system",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify the actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include main router
    app.include_router(router)
    
    # Add startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize the API on startup."""
        logger.info("Initializing Trading API")
        initialize_engines(use_rust=True)
        logger.info("Trading API initialized successfully")
    
    return app


# Create application instance
app = create_application() 