"""
Tests for the FastAPI application.
"""
import pytest
from fastapi.testclient import TestClient

from py_rs_quant.api.application import app


@pytest.fixture
def client():
    """Create a test client for the application."""
    return TestClient(app)


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_get_orderbook(client):
    """Test the order book endpoint."""
    response = client.get("/orderbook/BTCUSD")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["symbol"] == "BTCUSD"
    assert "bids" in data
    assert "asks" in data
    assert "timestamp" in data


def test_get_trades(client):
    """Test the trades endpoint."""
    response = client.get("/trades")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "trades" in data 