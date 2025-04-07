"""
Analytics module for processing trade data and generating performance statistics.
"""
import logging
import statistics
import time
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


from py_rs_quant.core.engine import Order, OrderStatus, Trade

logger = logging.getLogger(__name__)


class PerformanceMetric(Enum):
    """Performance metrics that can be calculated."""
    FILL_RATIO = "fill_ratio"
    TRADE_VOLUME = "trade_volume"
    MARKET_IMPACT = "market_impact"
    PRICE_CHANGE = "price_change"
    PRICE_VOLATILITY = "price_volatility"
    ORDER_BOOK_DEPTH = "order_book_depth"
    SPREAD = "spread"
    LATENCY = "latency"


class TimeFrame(Enum):
    """Time frames for aggregating data."""
    SECOND = "1s"
    MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    HOUR = "1h"
    DAY = "1d"


class PerformanceAnalyzer:
    """
    Performance analyzer for calculating trading system metrics.
    """
    
    def __init__(self):
        """Initialize the performance analyzer."""
        # Store trades and orders
        self.trades: List[Trade] = []
        self.orders: Dict[int, Order] = {}
        
        # Store order book snapshots
        self.order_book_snapshots = []
        
        # Store metrics
        self.metrics = {}
        
        # Store price history
        self.price_history: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
        
        # Store latency measurements
        self.latency_measurements = []
    
    def add_trade(self, trade: Trade) -> None:
        """
        Add a trade to the analyzer.
        
        Args:
            trade: The trade to add
        """
        self.trades.append(trade)
        
        # Update the corresponding orders if they exist
        if trade.buy_order_id in self.orders:
            buy_order = self.orders[trade.buy_order_id]
            buy_order.filled_quantity += trade.quantity
            if buy_order.filled_quantity >= buy_order.quantity:
                buy_order.status = OrderStatus.FILLED
            else:
                buy_order.status = OrderStatus.PARTIALLY_FILLED
                
        if trade.sell_order_id in self.orders:
            sell_order = self.orders[trade.sell_order_id]
            sell_order.filled_quantity += trade.quantity
            if sell_order.filled_quantity >= sell_order.quantity:
                sell_order.status = OrderStatus.FILLED
            else:
                sell_order.status = OrderStatus.PARTIALLY_FILLED
    
    def add_order(self, order: Order) -> None:
        """
        Add an order to the analyzer.
        
        Args:
            order: The order to add
        """
        self.orders[order.id] = order
    
    def add_order_book_snapshot(self, 
                               timestamp: int, 
                               symbol: str, 
                               bids: List[Tuple[float, float]], 
                               asks: List[Tuple[float, float]]) -> None:
        """
        Add an order book snapshot to the analyzer.
        
        Args:
            timestamp: Timestamp of the snapshot
            symbol: The trading symbol
            bids: List of (price, quantity) tuples for buy orders
            asks: List of (price, quantity) tuples for sell orders
        """
        self.order_book_snapshots.append({
            "timestamp": timestamp,
            "symbol": symbol,
            "bids": bids,
            "asks": asks
        })
    
    def add_price(self, symbol: str, timestamp: int, price: float) -> None:
        """
        Add a price point to the price history.
        
        Args:
            symbol: The trading symbol
            timestamp: Timestamp of the price
            price: The price
        """
        self.price_history[symbol].append((timestamp, price))
    
    def add_latency_measurement(self, operation: str, latency_ms: float) -> None:
        """
        Add a latency measurement to the analyzer.
        
        Args:
            operation: The operation being measured (e.g., "order_submission", "matching")
            latency_ms: The latency in milliseconds
        """
        self.latency_measurements.append({
            "timestamp": int(time.time() * 1000),
            "operation": operation,
            "latency_ms": latency_ms
        })
    
    def calculate_fill_ratio(self, 
                            symbol: Optional[str] = None, 
                            time_range: Optional[Tuple[int, int]] = None) -> float:
        """
        Calculate the fill ratio (filled orders / total orders).
        
        Args:
            symbol: Optional symbol to filter by
            time_range: Optional (start_time, end_time) tuple to filter by
            
        Returns:
            The fill ratio as a float between 0 and 1
        """
        # Filter orders
        filtered_orders = self._filter_orders(symbol, time_range)
        
        if not filtered_orders:
            return 0.0
        
        # Count filled or partially filled orders
        filled_orders = [
            order for order in filtered_orders
            if order.filled_quantity > 0
        ]
        
        return len(filled_orders) / len(filtered_orders)
    
    def calculate_trade_volume(self,
                              symbol: Optional[str] = None,
                              time_range: Optional[Tuple[int, int]] = None,
                              by_side: bool = False) -> Union[float, Dict[str, float]]:
        """
        Calculate the total trade volume.
        
        Args:
            symbol: Optional symbol to filter by
            time_range: Optional (start_time, end_time) tuple to filter by
            by_side: Whether to break down volume by side
            
        Returns:
            The total volume as a float, or a dict of {side: volume} if by_side is True
        """
        # Filter trades
        filtered_trades = self._filter_trades(symbol, time_range)
        
        if not filtered_trades:
            return 0.0 if not by_side else {"buy": 0.0, "sell": 0.0}
        
        if by_side:
            # Calculate volume by side
            buy_volume = sum(trade.quantity for trade in filtered_trades)
            return {"buy": buy_volume, "sell": buy_volume}  # Same value for both sides
        else:
            # Calculate total volume
            return sum(trade.quantity for trade in filtered_trades)
    
    def calculate_price_statistics(self,
                                 symbol: str,
                                 time_range: Optional[Tuple[int, int]] = None) -> Dict[str, float]:
        """
        Calculate price statistics.
        
        Args:
            symbol: The trading symbol
            time_range: Optional (start_time, end_time) tuple to filter by
            
        Returns:
            Dict of price statistics including min, max, mean, median, volatility
        """
        if symbol not in self.price_history:
            return {
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0,
                "std_dev": 0.0,
                "start": 0.0,
                "end": 0.0,
                "change": 0.0,
                "pct_change": 0.0
            }
        
        # Filter price history by time range
        prices = self.price_history[symbol]
        
        if time_range:
            start_time, end_time = time_range
            prices = [(ts, price) for ts, price in prices if start_time <= ts <= end_time]
        
        if not prices:
            return {
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0,
                "std_dev": 0.0,
                "start": 0.0,
                "end": 0.0,
                "change": 0.0,
                "pct_change": 0.0
            }
        
        # Extract price values
        price_values = [price for _, price in prices]
        
        # Calculate statistics
        min_price = min(price_values)
        max_price = max(price_values)
        mean_price = statistics.mean(price_values)
        median_price = statistics.median(price_values)
        
        # Calculate standard deviation (volatility)
        std_dev = statistics.stdev(price_values) if len(price_values) > 1 else 0.0
        
        # Calculate price change
        start_price = prices[0][1]
        end_price = prices[-1][1]
        price_change = end_price - start_price
        pct_change = price_change / start_price if start_price > 0 else 0.0
        
        return {
            "min": min_price,
            "max": max_price,
            "mean": mean_price,
            "median": median_price,
            "std_dev": std_dev,
            "start": start_price,
            "end": end_price,
            "change": price_change,
            "pct_change": pct_change
        }
    
    def calculate_order_book_metrics(self,
                                   symbol: str,
                                   time_range: Optional[Tuple[int, int]] = None) -> Dict[str, Any]:
        """
        Calculate order book metrics.
        
        Args:
            symbol: The trading symbol
            time_range: Optional (start_time, end_time) tuple to filter by
            
        Returns:
            Dict of order book metrics including spread, depth
        """
        # Filter order book snapshots
        snapshots = [
            snapshot for snapshot in self.order_book_snapshots
            if snapshot["symbol"] == symbol and
            (time_range is None or 
             (time_range[0] <= snapshot["timestamp"] <= time_range[1]))
        ]
        
        if not snapshots:
            return {
                "avg_spread": 0.0,
                "avg_depth": 0.0,
                "avg_bid_depth": 0.0,
                "avg_ask_depth": 0.0
            }
        
        # Calculate spreads
        spreads = []
        depths = []
        bid_depths = []
        ask_depths = []
        
        for snapshot in snapshots:
            bids = snapshot["bids"]
            asks = snapshot["asks"]
            
            if bids and asks:
                # Calculate spread
                best_bid = max(bids, key=lambda x: x[0])[0] if bids else 0
                best_ask = min(asks, key=lambda x: x[0])[0] if asks else float('inf')
                
                if best_bid > 0 and best_ask < float('inf'):
                    spread = best_ask - best_bid
                    spreads.append(spread)
                
                # Calculate depth
                bid_depth = sum(qty for _, qty in bids)
                ask_depth = sum(qty for _, qty in asks)
                
                bid_depths.append(bid_depth)
                ask_depths.append(ask_depth)
                depths.append(bid_depth + ask_depth)
        
        # Calculate averages
        avg_spread = statistics.mean(spreads) if spreads else 0.0
        avg_depth = statistics.mean(depths) if depths else 0.0
        avg_bid_depth = statistics.mean(bid_depths) if bid_depths else 0.0
        avg_ask_depth = statistics.mean(ask_depths) if ask_depths else 0.0
        
        return {
            "avg_spread": avg_spread,
            "avg_depth": avg_depth,
            "avg_bid_depth": avg_bid_depth,
            "avg_ask_depth": avg_ask_depth
        }
    
    def calculate_latency_statistics(self,
                                   operation: Optional[str] = None,
                                   time_range: Optional[Tuple[int, int]] = None) -> Dict[str, float]:
        """
        Calculate latency statistics.
        
        Args:
            operation: Optional operation to filter by
            time_range: Optional (start_time, end_time) tuple to filter by
            
        Returns:
            Dict of latency statistics including min, max, mean, median, p95, p99
        """
        # Filter latency measurements
        measurements = self.latency_measurements
        
        if operation:
            measurements = [m for m in measurements if m["operation"] == operation]
        
        if time_range:
            start_time, end_time = time_range
            measurements = [
                m for m in measurements 
                if start_time <= m["timestamp"] <= end_time
            ]
        
        if not measurements:
            return {
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0,
                "p95": 0.0,
                "p99": 0.0
            }
        
        # Extract latency values
        latencies = [m["latency_ms"] for m in measurements]
        
        # Calculate statistics
        min_latency = min(latencies)
        max_latency = max(latencies)
        mean_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        
        # Calculate percentiles
        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p99_index = int(len(latencies) * 0.99)
        
        p95 = latencies[p95_index] if p95_index < len(latencies) else max_latency
        p99 = latencies[p99_index] if p99_index < len(latencies) else max_latency
        
        return {
            "min": min_latency,
            "max": max_latency,
            "mean": mean_latency,
            "median": median_latency,
            "p95": p95,
            "p99": p99
        }
    
    def compare_python_vs_rust(self, latency_samples: int = 100) -> Dict[str, Any]:
        """
        Get Python performance statistics.
        This method is maintained for backward compatibility but no longer compares
        Python vs Rust since the Rust implementation has been removed.
        
        Args:
            latency_samples: Number of latency samples to use
            
        Returns:
            Dict of Python performance statistics
        """
        # Filter latency measurements for Python
        python_latencies = [
            m["latency_ms"] for m in self.latency_measurements
            if m["operation"].startswith("python_")
        ]
        
        # Limit to the specified number of samples
        python_latencies = python_latencies[-latency_samples:] if python_latencies else []
        
        if not python_latencies:
            return {
                "python_mean": 0.0,
                "python_median": 0.0,
                "python_min": 0.0,
                "python_max": 0.0,
                "python_p95": 0.0,
                "python_p99": 0.0
            }
        
        # Calculate statistics
        python_mean = statistics.mean(python_latencies)
        python_median = statistics.median(python_latencies)
        python_min = min(python_latencies)
        python_max = max(python_latencies)
        
        # Calculate percentiles
        python_latencies.sort()
        p95_idx = int(len(python_latencies) * 0.95)
        p99_idx = int(len(python_latencies) * 0.99)
        python_p95 = python_latencies[p95_idx] if p95_idx < len(python_latencies) else python_max
        python_p99 = python_latencies[p99_idx] if p99_idx < len(python_latencies) else python_max
        
        return {
            "python_mean": python_mean,
            "python_median": python_median,
            "python_min": python_min,
            "python_max": python_max,
            "python_p95": python_p95,
            "python_p99": python_p99
        }
    
    def generate_time_series(self,
                           symbol: str,
                           metric: str,
                           timeframe: TimeFrame,
                           time_range: Optional[Tuple[int, int]] = None) -> List[Dict[str, Any]]:
        """
        Generate a time series of a specific metric.
        
        Args:
            symbol: The trading symbol
            metric: The metric to generate (price, volume, etc.)
            timeframe: The timeframe to aggregate by
            time_range: Optional (start_time, end_time) tuple to filter by
            
        Returns:
            List of time series points with timestamp and value
        """
        if not time_range:
            if not self.price_history.get(symbol):
                return []
            
            # Use full available time range
            timestamps = [ts for ts, _ in self.price_history[symbol]]
            time_range = (min(timestamps), max(timestamps))
        
        start_time, end_time = time_range
        
        # Determine interval in milliseconds
        interval_ms = self._timeframe_to_ms(timeframe)
        
        # Generate time buckets
        buckets = []
        current_time = start_time
        
        while current_time <= end_time:
            bucket_end = current_time + interval_ms
            buckets.append((current_time, bucket_end))
            current_time = bucket_end
        
        # Generate time series
        time_series = []
        
        for bucket_start, bucket_end in buckets:
            bucket_range = (bucket_start, bucket_end)
            
            if metric == "price":
                # Filter price history
                prices = [
                    price for ts, price in self.price_history.get(symbol, [])
                    if bucket_start <= ts < bucket_end
                ]
                
                if prices:
                    value = prices[-1]  # Use last price in bucket
                else:
                    continue  # Skip buckets with no data
            
            elif metric == "volume":
                # Calculate volume in bucket
                value = self.calculate_trade_volume(symbol, bucket_range)
                
                if value == 0:
                    continue  # Skip buckets with no trades
            
            elif metric == "depth":
                # Calculate average order book depth in bucket
                metrics = self.calculate_order_book_metrics(symbol, bucket_range)
                value = metrics["avg_depth"]
                
                if value == 0:
                    continue  # Skip buckets with no order book data
            
            elif metric == "spread":
                # Calculate average spread in bucket
                metrics = self.calculate_order_book_metrics(symbol, bucket_range)
                value = metrics["avg_spread"]
                
                if value == 0:
                    continue  # Skip buckets with no order book data
            
            else:
                logger.warning(f"Unsupported metric: {metric}")
                continue
            
            time_series.append({
                "timestamp": bucket_start,
                "value": value
            })
        
        return time_series
    
    def get_summary_statistics(self, symbol: str) -> Dict[str, Any]:
        """
        Get a comprehensive summary of performance statistics.
        
        Args:
            symbol: The trading symbol
            
        Returns:
            Dict of performance statistics
        """
        # Calculate various statistics
        fill_ratio = self.calculate_fill_ratio(symbol)
        volume = self.calculate_trade_volume(symbol)
        volume_by_side = self.calculate_trade_volume(symbol, by_side=True)
        price_stats = self.calculate_price_statistics(symbol)
        order_book_metrics = self.calculate_order_book_metrics(symbol)
        latency_stats = self.calculate_latency_statistics()
        python_stats = self.compare_python_vs_rust()
        
        # Calculate total orders and trades
        total_orders = len([
            order for order_id, order in self.orders.items()
            if order.symbol == symbol
        ])
        
        # Only count trades for the specified symbol
        total_trades = len([
            trade for trade in self.trades
            if trade.symbol == symbol
        ])
        
        return {
            "symbol": symbol,
            "total_orders": total_orders,
            "total_trades": total_trades,
            "fill_ratio": fill_ratio,
            "volume": volume,
            "volume_by_side": volume_by_side,
            "price_stats": price_stats,
            "order_book": order_book_metrics,
            "latency": latency_stats,
            "performance": python_stats  # Renamed from optimization
        }
    
    def export_metrics_to_dict(self, symbol: str) -> Dict[str, Dict[str, Any]]:
        """
        Export all metrics to a dictionary, typically for serialization to JSON.
        
        Args:
            symbol: The trading symbol
            
        Returns:
            Dict of all metrics
        """
        # Get summary statistics
        summary = self.get_summary_statistics(symbol)
        
        # Get time series data
        price_series = self.generate_time_series(
            symbol, "price", TimeFrame.MINUTE
        )
        
        volume_series = self.generate_time_series(
            symbol, "volume", TimeFrame.MINUTE
        )
        
        depth_series = self.generate_time_series(
            symbol, "depth", TimeFrame.MINUTE
        )
        
        spread_series = self.generate_time_series(
            symbol, "spread", TimeFrame.MINUTE
        )
        
        return {
            "summary": summary,
            "time_series": {
                "price": price_series,
                "volume": volume_series,
                "depth": depth_series,
                "spread": spread_series
            }
        }
    
    def _filter_orders(self,
                      symbol: Optional[str] = None,
                      time_range: Optional[Tuple[int, int]] = None) -> List[Order]:
        """
        Filter orders by symbol and time range.
        
        Args:
            symbol: Optional symbol to filter by
            time_range: Optional (start_time, end_time) tuple to filter by
            
        Returns:
            Filtered list of orders
        """
        filtered_orders = list(self.orders.values())
        
        # Filter by symbol
        if symbol:
            filtered_orders = [order for order in filtered_orders if order.symbol == symbol]
        
        # Filter by time range
        if time_range:
            start_time, end_time = time_range
            filtered_orders = [
                order for order in filtered_orders
                if start_time <= order.timestamp <= end_time
            ]
        
        return filtered_orders
    
    def _filter_trades(self,
                      symbol: Optional[str] = None,
                      time_range: Optional[Tuple[int, int]] = None) -> List[Trade]:
        """
        Filter trades by symbol and time range.
        
        Args:
            symbol: Optional symbol to filter by
            time_range: Optional (start_time, end_time) tuple to filter by
            
        Returns:
            Filtered list of trades
        """
        filtered_trades = self.trades
        
        # Filter by symbol
        if symbol:
            filtered_trades = [
                trade for trade in filtered_trades
                if trade.symbol == symbol
            ]
        
        # Filter by time range
        if time_range:
            start_time, end_time = time_range
            filtered_trades = [
                trade for trade in filtered_trades
                if start_time <= trade.timestamp <= end_time
            ]
        
        return filtered_trades
    
    def _timeframe_to_ms(self, timeframe: TimeFrame) -> int:
        """
        Convert a timeframe to milliseconds.
        
        Args:
            timeframe: The timeframe
            
        Returns:
            The timeframe in milliseconds
        """
        if timeframe == TimeFrame.SECOND:
            return 1000
        elif timeframe == TimeFrame.MINUTE:
            return 60 * 1000
        elif timeframe == TimeFrame.FIVE_MINUTES:
            return 5 * 60 * 1000
        elif timeframe == TimeFrame.FIFTEEN_MINUTES:
            return 15 * 60 * 1000
        elif timeframe == TimeFrame.HOUR:
            return 60 * 60 * 1000
        elif timeframe == TimeFrame.DAY:
            return 24 * 60 * 60 * 1000
        else:
            logger.warning(f"Unknown timeframe: {timeframe}")
            return 60 * 1000  # Default to 1 minute 