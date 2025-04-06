"""
API routes package.
"""
from fastapi import APIRouter

from py_rs_quant.api.routes.health import router as health_router
from py_rs_quant.api.routes.orders import router as orders_router
from py_rs_quant.api.routes.market_data import router as market_data_router


# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(health_router)
router.include_router(orders_router)
router.include_router(market_data_router) 