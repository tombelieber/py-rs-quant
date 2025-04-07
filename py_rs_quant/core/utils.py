"""
Utility functions for the matching engine.
"""
import numpy as np
from numba import jit


@jit(nopython=True)
def calculate_price_stats(prices, quantities):
    """Calculate price statistics efficiently."""
    if len(prices) == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    
    # Calculate weighted price
    total_qty = np.sum(quantities)
    if total_qty <= 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    
    weighted_price = np.sum(prices * quantities) / total_qty
    
    # Calculate other stats
    min_price = np.min(prices)
    max_price = np.max(prices)
    mean_price = np.mean(prices)
    
    # Calculate weighted standard deviation
    if len(prices) > 1:
        variance = np.sum(quantities * (prices - weighted_price) ** 2) / total_qty
        std_dev = np.sqrt(variance)
    else:
        std_dev = 0.0
    
    return min_price, max_price, mean_price, weighted_price, std_dev 