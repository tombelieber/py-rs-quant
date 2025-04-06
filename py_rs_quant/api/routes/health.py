"""
Health check endpoints for the API.
"""
from fastapi import APIRouter, status
from pydantic import BaseModel


# Create router
router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        HealthResponse: The health status of the API
    """
    return HealthResponse(
        status="healthy",
        version="0.1.0"
    ) 