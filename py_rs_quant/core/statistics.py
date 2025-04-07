"""
Price statistics calculation for the matching engine.
"""
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import time

from py_rs_quant.core.utils import calculate_price_stats
from py_rs_quant.core.order_book import OrderBook


class PriceStatisticsCalculator:
    """
    Calculate price statistics from order book data.
    """
    
    def __init__(self, order_book: OrderBook):
        """
        Initialize the price statistics calculator.
        
        Args:
            order_book: The order book to calculate statistics for
        """
        self.order_book = order_book
    
    def calculate_price_statistics(self) -> Dict[str, Any]:
        """
        Calculate price statistics from the current order book.
        
        Returns:
            Dictionary of price statistics
        """
        # Get price levels from order book
        buy_levels, sell_levels = self.order_book.get_order_book_snapshot()
        
        # Use the static method to calculate statistics
        stats = self.calculate_from_price_levels(buy_levels, sell_levels)
        stats["timestamp"] = int(time.time() * 1000)
        
        return stats
    
    @staticmethod
    def calculate_from_price_levels(buy_levels: List[Tuple[float, float]], sell_levels: List[Tuple[float, float]]) -> Dict[str, Any]:
        """
        Calculate price statistics from buy and sell price levels.
        
        Args:
            buy_levels: List of (price, quantity) tuples for buy orders
            sell_levels: List of (price, quantity) tuples for sell orders
            
        Returns:
            Dictionary of price statistics
        """
        # Extract prices and quantities
        buy_prices = [price for price, _ in buy_levels]
        buy_quantities = [qty for _, qty in buy_levels]
            
        sell_prices = [price for price, _ in sell_levels]
        sell_quantities = [qty for _, qty in sell_levels]
            
        # Use numpy for calculations if we have enough data
        if len(buy_prices) > 0 or len(sell_prices) > 0:
            # Convert to numpy arrays
            if buy_prices:
                buy_prices_np = np.array(buy_prices)
                buy_quantities_np = np.array(buy_quantities)
                buy_min, buy_max, buy_mean, buy_weighted, buy_std = calculate_price_stats(buy_prices_np, buy_quantities_np)
            else:
                buy_min = buy_max = buy_mean = buy_weighted = buy_std = 0.0
                
            if sell_prices:
                sell_prices_np = np.array(sell_prices)
                sell_quantities_np = np.array(sell_quantities)
                sell_min, sell_max, sell_mean, sell_weighted, sell_std = calculate_price_stats(sell_prices_np, sell_quantities_np)
            else:
                sell_min = sell_max = sell_mean = sell_weighted = sell_std = 0.0
                
            # Calculate midpoint if both sides have orders
            if buy_prices and sell_prices:
                best_bid = max(buy_prices)
                best_ask = min(sell_prices)
                midpoint = (best_bid + best_ask) / 2
                spread = best_ask - best_bid
            else:
                midpoint = 0.0
                spread = 0.0
                
            return {
                "buy_side": {
                    "min": buy_min,
                    "max": buy_max,
                    "mean": buy_mean,
                    "weighted_mean": buy_weighted,
                    "std_dev": buy_std,
                    "depth": len(buy_prices),
                    "total_quantity": sum(buy_quantities)
                },
                "sell_side": {
                    "min": sell_min,
                    "max": sell_max,
                    "mean": sell_mean,
                    "weighted_mean": sell_weighted,
                    "std_dev": sell_std,
                    "depth": len(sell_prices),
                    "total_quantity": sum(sell_quantities)
                },
                "midpoint": midpoint,
                "spread": spread
            }
        else:
            # Return default values if no prices
            return {
                "buy_side": {"min": 0.0, "max": 0.0, "mean": 0.0, "weighted_mean": 0.0, "std_dev": 0.0, "depth": 0, "total_quantity": 0.0},
                "sell_side": {"min": 0.0, "max": 0.0, "mean": 0.0, "weighted_mean": 0.0, "std_dev": 0.0, "depth": 0, "total_quantity": 0.0},
                "midpoint": 0.0,
                "spread": 0.0
            }
    
    @staticmethod
    def calculate_vwap(trades: List[Tuple[float, float]]) -> float:
        """
        Calculate Volume Weighted Average Price from trades.
        
        Args:
            trades: List of (price, quantity) tuples
            
        Returns:
            VWAP or 0.0 if no trades
        """
        if not trades:
            return 0.0
            
        total_value = sum(price * qty for price, qty in trades)
        total_volume = sum(qty for _, qty in trades)
        
        if total_volume <= 0:
            return 0.0
            
        return total_value / total_volume 