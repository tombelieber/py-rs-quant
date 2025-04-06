use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::cmp::Ordering;
use std::collections::{BTreeMap, HashMap, VecDeque};
use std::sync::{Arc, RwLock};

/// Python module Enums
#[pyclass]
#[derive(Clone, Copy)]
pub enum PyOrderType {
    Market,
    Limit,
}

#[pyclass]
#[derive(Clone, Copy)]
pub enum PyOrderSide {
    Buy,
    Sell,
}

#[pyclass]
#[derive(Clone, Copy)]
pub enum PyOrderStatus {
    New,
    PartiallyFilled,
    Filled,
    Cancelled,
    Rejected,
}

/// Order type enum: Market or Limit
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderType {
    Market,
    Limit,
}

/// Order side enum: Buy or Sell
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderSide {
    Buy,
    Sell,
}

/// Order status enum
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderStatus {
    New,
    PartiallyFilled,
    Filled,
    Cancelled,
    Rejected,
}

/// Order struct representing a single order in the order book
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    pub id: u64,
    pub side: OrderSide,
    pub order_type: OrderType,
    pub price: Option<f64>, // None for market orders
    pub quantity: f64,
    pub filled_quantity: f64,
    pub status: OrderStatus,
    pub timestamp: u64,
    pub symbol: Option<String>,
    // Cache remaining quantity for performance
    pub remaining_quantity: f64,
}

impl Order {
    pub fn new(
        id: u64,
        side: OrderSide,
        order_type: OrderType,
        price: Option<f64>,
        quantity: f64,
        timestamp: u64,
        symbol: Option<String>,
    ) -> Self {
        Order {
            id,
            side,
            order_type,
            price,
            quantity,
            filled_quantity: 0.0,
            status: OrderStatus::New,
            timestamp,
            symbol,
            remaining_quantity: quantity,
        }
    }
}

/// Trade struct representing a single trade
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Trade {
    pub id: u64,
    pub buy_order_id: u64,
    pub sell_order_id: u64,
    pub price: f64,
    pub quantity: f64,
    pub timestamp: u64,
    pub symbol: Option<String>,
}

/// PriceLevel struct for aggregating orders at the same price
#[derive(Debug, Clone)]
pub struct PriceLevel {
    pub price: f64,
    pub orders: Vec<Order>,
    pub total_quantity_cache: f64,
    pub is_dirty: bool,
}

impl PriceLevel {
    pub fn new(price: f64) -> Self {
        PriceLevel {
            price,
            orders: Vec::with_capacity(16), // Pre-allocate to avoid frequent reallocations
            total_quantity_cache: 0.0,
            is_dirty: false,
        }
    }

    pub fn add_order(&mut self, order: Order) {
        self.total_quantity_cache += order.remaining_quantity;
        self.orders.push(order);
    }

    pub fn remove_order(&mut self, order_id: u64) -> Option<Order> {
        if let Some(pos) = self.orders.iter().position(|o| o.id == order_id) {
            let order = self.orders.swap_remove(pos); // Use swap_remove for O(1) removal
            self.is_dirty = true;
            Some(order)
        } else {
            None
        }
    }

    pub fn update_quantity_cache(&mut self) {
        if self.is_dirty {
            self.total_quantity_cache = self.orders.iter().map(|o| o.remaining_quantity).sum();
            self.is_dirty = false;
        }
    }

    pub fn total_quantity(&mut self) -> f64 {
        self.update_quantity_cache();
        self.total_quantity_cache
    }

    pub fn is_empty(&self) -> bool {
        self.orders.is_empty()
    }
}

/// Batch of orders to process efficiently
#[derive(Debug, Default, Clone)]
pub struct OrderBatch {
    pub buy_market_orders: Vec<Order>,
    pub sell_market_orders: Vec<Order>,
    pub buy_limit_orders: Vec<Order>,
    pub sell_limit_orders: Vec<Order>,
}

impl OrderBatch {
    pub fn new() -> Self {
        OrderBatch {
            buy_market_orders: Vec::with_capacity(16),
            sell_market_orders: Vec::with_capacity(16),
            buy_limit_orders: Vec::with_capacity(32),
            sell_limit_orders: Vec::with_capacity(32),
        }
    }

    pub fn add_order(&mut self, order: Order) {
        match (order.side, order.order_type) {
            (OrderSide::Buy, OrderType::Market) => self.buy_market_orders.push(order),
            (OrderSide::Sell, OrderType::Market) => self.sell_market_orders.push(order),
            (OrderSide::Buy, OrderType::Limit) => self.buy_limit_orders.push(order),
            (OrderSide::Sell, OrderType::Limit) => self.sell_limit_orders.push(order),
        }
    }

    pub fn sort(&mut self) {
        // Sort market orders by timestamp (FIFO)
        self.buy_market_orders.sort_by_key(|o| o.timestamp);
        self.sell_market_orders.sort_by_key(|o| o.timestamp);

        // Sort limit orders by price (best price first) then timestamp
        self.buy_limit_orders.sort_by(|a, b| {
            let a_price = a.price.unwrap_or(0.0);
            let b_price = b.price.unwrap_or(0.0);
            b_price
                .partial_cmp(&a_price)
                .unwrap_or(Ordering::Equal)
                .then_with(|| a.timestamp.cmp(&b.timestamp))
        });

        self.sell_limit_orders.sort_by(|a, b| {
            let a_price = a.price.unwrap_or(f64::MAX);
            let b_price = b.price.unwrap_or(f64::MAX);
            a_price
                .partial_cmp(&b_price)
                .unwrap_or(Ordering::Equal)
                .then_with(|| a.timestamp.cmp(&b.timestamp))
        });
    }

    pub fn is_empty(&self) -> bool {
        self.buy_market_orders.is_empty()
            && self.sell_market_orders.is_empty()
            && self.buy_limit_orders.is_empty()
            && self.sell_limit_orders.is_empty()
    }

    pub fn len(&self) -> usize {
        self.buy_market_orders.len()
            + self.sell_market_orders.len()
            + self.buy_limit_orders.len()
            + self.sell_limit_orders.len()
    }
}

/// Object pool for reducing allocations
struct ObjectPool<T> {
    items: VecDeque<T>,
    max_size: usize,
}

impl<T> ObjectPool<T> {
    fn new(max_size: usize) -> Self {
        ObjectPool {
            items: VecDeque::with_capacity(max_size / 2),
            max_size,
        }
    }

    fn get(&mut self) -> Option<T> {
        self.items.pop_front()
    }

    fn return_item(&mut self, item: T) {
        if self.items.len() < self.max_size {
            self.items.push_back(item);
        }
    }
}

/// OrderBook struct with optimized implementation
#[derive(Debug)]
pub struct OrderBook {
    // Price levels for improved locality and reduced cloning
    buy_price_levels: BTreeMap<i64, PriceLevel>, // Negative price (int bits) as key for correct sorting
    sell_price_levels: BTreeMap<i64, PriceLevel>, // Price bits as key

    // Fast lookups
    orders_by_id: HashMap<u64, (OrderSide, i64)>, // Map order ID to side and price key

    // Order and trade IDs
    next_order_id: u64,
    next_trade_id: u64,

    // Trades with pre-allocated capacity
    trades: Vec<Trade>,

    // Price level cache (hot price points)
    price_level_cache: RwLock<HashMap<(bool, i64), Arc<RwLock<PriceLevel>>>>,
    cache_hits: usize,
    cache_misses: usize,
    max_cache_size: usize,

    // Reusable vectors for batch operations
    removed_price_levels: Vec<i64>,

    // Statistics
    stats: OrderBookStats,
}

#[derive(Debug, Clone, Default)]
pub struct OrderBookStats {
    pub orders_processed: u64,
    pub trades_executed: u64,
    pub cache_hits: u64,
    pub cache_misses: u64,
}

impl OrderBook {
    pub fn new() -> Self {
        OrderBook {
            buy_price_levels: BTreeMap::new(),
            sell_price_levels: BTreeMap::new(),
            orders_by_id: HashMap::with_capacity(1024),
            next_order_id: 1,
            next_trade_id: 1,
            trades: Vec::with_capacity(1000),
            price_level_cache: RwLock::new(HashMap::with_capacity(100)),
            cache_hits: 0,
            cache_misses: 0,
            max_cache_size: 100,
            removed_price_levels: Vec::with_capacity(16),
            stats: OrderBookStats::default(),
        }
    }

    // Helper function to convert f64 to i64 bits for stable sorting
    fn price_to_bits(price: f64, is_buy: bool) -> i64 {
        let bits = price.to_bits() as i64;
        if is_buy {
            // For buy orders, negate to get descending order
            -bits
        } else {
            bits
        }
    }

    // Helper function to convert i64 bits back to f64
    fn bits_to_price(bits: i64, is_buy: bool) -> f64 {
        let abs_bits = if is_buy { -bits } else { bits };
        f64::from_bits(abs_bits as u64)
    }

    // Get or create price level with caching
    fn get_or_create_price_level(
        &mut self,
        is_buy: bool,
        price_bits: i64,
        create_new: bool,
    ) -> Option<&mut PriceLevel> {
        let price_map = if is_buy {
            &mut self.buy_price_levels
        } else {
            &mut self.sell_price_levels
        };

        if price_map.contains_key(&price_bits) {
            Some(price_map.get_mut(&price_bits).unwrap())
        } else if create_new {
            let price = Self::bits_to_price(price_bits, is_buy);
            let level = PriceLevel::new(price);
            price_map.insert(price_bits, level);
            Some(price_map.get_mut(&price_bits).unwrap())
        } else {
            None
        }
    }

    pub fn add_order(
        &mut self,
        side: OrderSide,
        order_type: OrderType,
        price: Option<f64>,
        quantity: f64,
        timestamp: u64,
        symbol: Option<String>,
    ) -> u64 {
        let order_id = self.next_order_id;
        self.next_order_id += 1;
        self.stats.orders_processed += 1;

        // Create the order
        let mut order = Order::new(
            order_id, side, order_type, price, quantity, timestamp, symbol,
        );

        // Process the order
        self.process_order(&mut order);

        // Return the order ID
        order_id
    }

    pub fn batch_add_orders(
        &mut self,
        orders: Vec<(OrderSide, OrderType, Option<f64>, f64, u64, Option<String>)>,
    ) -> Vec<u64> {
        if orders.is_empty() {
            return Vec::new();
        }

        let mut order_ids = Vec::with_capacity(orders.len());
        let mut batch = OrderBatch::new();

        // Create all orders first
        for (side, order_type, price, quantity, timestamp, symbol) in orders {
            let order_id = self.next_order_id;
            self.next_order_id += 1;
            order_ids.push(order_id);
            self.stats.orders_processed += 1;

            let order = Order::new(
                order_id, side, order_type, price, quantity, timestamp, symbol,
            );
            batch.add_order(order);
        }

        // Process orders in optimized batches
        self.process_batch(batch);

        order_ids
    }

    fn process_batch(&mut self, mut batch: OrderBatch) {
        // Sort orders within each category for optimal processing
        batch.sort();

        // Process market orders first
        for order in batch.buy_market_orders {
            self.process_market_order(order);
        }

        for order in batch.sell_market_orders {
            self.process_market_order(order);
        }

        // Then process limit orders
        for mut order in batch.buy_limit_orders {
            self.match_limit_order(&mut order);

            // Add to order book if not completely filled
            if order.remaining_quantity > 0.0 {
                let price = order.price.unwrap();
                let price_bits = Self::price_to_bits(price, true);

                let level = self
                    .get_or_create_price_level(true, price_bits, true)
                    .unwrap();
                level.add_order(order.clone());

                self.orders_by_id
                    .insert(order.id, (OrderSide::Buy, price_bits));
            }
        }

        for mut order in batch.sell_limit_orders {
            self.match_limit_order(&mut order);

            // Add to order book if not completely filled
            if order.remaining_quantity > 0.0 {
                let price = order.price.unwrap();
                let price_bits = Self::price_to_bits(price, false);

                let level = self
                    .get_or_create_price_level(false, price_bits, true)
                    .unwrap();
                level.add_order(order.clone());

                self.orders_by_id
                    .insert(order.id, (OrderSide::Sell, price_bits));
            }
        }
    }

    fn process_order(&mut self, order: &mut Order) {
        // Handle market orders first
        if order.order_type == OrderType::Market {
            self.process_market_order(order.clone());
            return;
        }

        // Then handle limit orders
        let price = order.price.unwrap(); // Safe unwrap since we know it's a limit order

        // Try to match the order first
        self.match_limit_order(order);

        // If order is not completely filled, add it to the order book
        if order.remaining_quantity > 0.0 {
            match order.side {
                OrderSide::Buy => {
                    // For buy orders, use negative price for descending sort
                    let price_bits = Self::price_to_bits(price, true);
                    let level = self
                        .get_or_create_price_level(true, price_bits, true)
                        .unwrap();
                    level.add_order(order.clone());
                    self.orders_by_id
                        .insert(order.id, (OrderSide::Buy, price_bits));
                }
                OrderSide::Sell => {
                    let price_bits = Self::price_to_bits(price, false);
                    let level = self
                        .get_or_create_price_level(false, price_bits, true)
                        .unwrap();
                    level.add_order(order.clone());
                    self.orders_by_id
                        .insert(order.id, (OrderSide::Sell, price_bits));
                }
            }
        }
    }

    fn process_market_order(&mut self, mut order: Order) {
        match order.side {
            OrderSide::Buy => {
                self.removed_price_levels.clear();
                let mut sell_levels_to_process = Vec::new();

                // Collect levels to process
                for (&price_bits, level) in &self.sell_price_levels {
                    sell_levels_to_process.push((price_bits, level.clone()));
                    if order.remaining_quantity <= 0.0 {
                        break;
                    }
                }

                // Process each level
                for (price_bits, mut level) in sell_levels_to_process {
                    if order.remaining_quantity <= 0.0 {
                        break;
                    }

                    self.match_order_with_level(&mut order, &mut level);

                    // Update the actual level in the book
                    if level.is_empty() {
                        self.sell_price_levels.remove(&price_bits);
                    } else {
                        self.sell_price_levels.insert(price_bits, level);
                    }
                }
            }
            OrderSide::Sell => {
                self.removed_price_levels.clear();
                let mut buy_levels_to_process = Vec::new();

                // Collect levels to process
                for (&price_bits, level) in &self.buy_price_levels {
                    buy_levels_to_process.push((price_bits, level.clone()));
                    if order.remaining_quantity <= 0.0 {
                        break;
                    }
                }

                // Process each level
                for (price_bits, mut level) in buy_levels_to_process {
                    if order.remaining_quantity <= 0.0 {
                        break;
                    }

                    self.match_level_with_order(&mut level, &mut order);

                    // Update the actual level in the book
                    if level.is_empty() {
                        self.buy_price_levels.remove(&price_bits);
                    } else {
                        self.buy_price_levels.insert(price_bits, level);
                    }
                }
            }
        }

        // Update order status
        if order.remaining_quantity <= 0.0 {
            order.status = OrderStatus::Filled;
        } else if order.filled_quantity > 0.0 {
            order.status = OrderStatus::PartiallyFilled;
        } else {
            order.status = OrderStatus::Rejected; // Market orders that can't be filled are rejected
        }
    }

    fn match_limit_order(&mut self, order: &mut Order) {
        let price = order.price.unwrap(); // Safe unwrap since we know it's a limit order

        match order.side {
            OrderSide::Buy => {
                self.removed_price_levels.clear();
                let mut sell_levels_to_process = Vec::new();

                // Collect levels to process
                for (&price_bits, level) in &self.sell_price_levels {
                    let level_price = Self::bits_to_price(price_bits, false);

                    // Stop if sell price is higher than buy price
                    if level_price > price || order.remaining_quantity <= 0.0 {
                        break;
                    }

                    sell_levels_to_process.push((price_bits, level.clone()));
                }

                // Process each level
                for (price_bits, mut level) in sell_levels_to_process {
                    if order.remaining_quantity <= 0.0 {
                        break;
                    }

                    self.match_order_with_level(order, &mut level);

                    // Update the actual level in the book
                    if level.is_empty() {
                        self.sell_price_levels.remove(&price_bits);
                    } else {
                        self.sell_price_levels.insert(price_bits, level);
                    }
                }
            }
            OrderSide::Sell => {
                self.removed_price_levels.clear();
                let mut buy_levels_to_process = Vec::new();

                // Collect levels to process
                for (&price_bits, level) in &self.buy_price_levels {
                    let level_price = Self::bits_to_price(price_bits, true);

                    // Stop if buy price is lower than sell price
                    if level_price < price || order.remaining_quantity <= 0.0 {
                        break;
                    }

                    buy_levels_to_process.push((price_bits, level.clone()));
                }

                // Process each level
                for (price_bits, mut level) in buy_levels_to_process {
                    if order.remaining_quantity <= 0.0 {
                        break;
                    }

                    self.match_level_with_order(&mut level, order);

                    // Update the actual level in the book
                    if level.is_empty() {
                        self.buy_price_levels.remove(&price_bits);
                    } else {
                        self.buy_price_levels.insert(price_bits, level);
                    }
                }
            }
        }

        // Update order status
        if order.remaining_quantity <= 0.0 {
            order.status = OrderStatus::Filled;
        } else if order.filled_quantity > 0.0 {
            order.status = OrderStatus::PartiallyFilled;
        }
    }

    fn match_order_with_level(&mut self, buy_order: &mut Order, sell_level: &mut PriceLevel) {
        let mut orders_to_remove = Vec::new();

        // Match orders in time priority (FIFO)
        for (i, sell_order) in sell_level.orders.iter_mut().enumerate() {
            if buy_order.remaining_quantity <= 0.0 {
                break;
            }

            // Calculate trade quantity
            let trade_qty = buy_order
                .remaining_quantity
                .min(sell_order.remaining_quantity);

            if trade_qty > 0.0 {
                // Execute the trade
                self.execute_trade(buy_order, sell_order, sell_level.price, trade_qty);

                // Mark filled orders for removal
                if sell_order.status == OrderStatus::Filled {
                    orders_to_remove.push(i);
                }
            }
        }

        // Remove filled orders in reverse order to maintain correct indices
        for &i in orders_to_remove.iter().rev() {
            let order = sell_level.orders.swap_remove(i);
            self.orders_by_id.remove(&order.id);
        }

        // Mark level as dirty if orders were removed
        if !orders_to_remove.is_empty() {
            sell_level.is_dirty = true;
        }
    }

    fn match_level_with_order(&mut self, buy_level: &mut PriceLevel, sell_order: &mut Order) {
        let mut orders_to_remove = Vec::new();

        // Match orders in time priority (FIFO)
        for (i, buy_order) in buy_level.orders.iter_mut().enumerate() {
            if sell_order.remaining_quantity <= 0.0 {
                break;
            }

            // Calculate trade quantity
            let trade_qty = buy_order
                .remaining_quantity
                .min(sell_order.remaining_quantity);

            if trade_qty > 0.0 {
                // Execute the trade
                self.execute_trade(buy_order, sell_order, buy_level.price, trade_qty);

                // Mark filled orders for removal
                if buy_order.status == OrderStatus::Filled {
                    orders_to_remove.push(i);
                }
            }
        }

        // Remove filled orders in reverse order to maintain correct indices
        for &i in orders_to_remove.iter().rev() {
            let order = buy_level.orders.swap_remove(i);
            self.orders_by_id.remove(&order.id);
        }

        // Mark level as dirty if orders were removed
        if !orders_to_remove.is_empty() {
            buy_level.is_dirty = true;
        }
    }

    fn execute_trade(
        &mut self,
        buy_order: &mut Order,
        sell_order: &mut Order,
        price: f64,
        quantity: f64,
    ) {
        // Update filled quantities
        buy_order.filled_quantity += quantity;
        buy_order.remaining_quantity -= quantity;
        sell_order.filled_quantity += quantity;
        sell_order.remaining_quantity -= quantity;

        // Update order statuses
        if buy_order.filled_quantity >= buy_order.quantity {
            buy_order.status = OrderStatus::Filled;
            // Will be removed from price level when processing is complete
        } else if buy_order.filled_quantity > 0.0 {
            buy_order.status = OrderStatus::PartiallyFilled;
        }

        if sell_order.filled_quantity >= sell_order.quantity {
            sell_order.status = OrderStatus::Filled;
            // Will be removed from price level when processing is complete
        } else if sell_order.filled_quantity > 0.0 {
            sell_order.status = OrderStatus::PartiallyFilled;
        }

        // Record the trade
        let symbol = buy_order
            .symbol
            .clone()
            .or_else(|| sell_order.symbol.clone());
        let trade = Trade {
            id: self.next_trade_id,
            buy_order_id: buy_order.id,
            sell_order_id: sell_order.id,
            price,
            quantity,
            timestamp: std::cmp::max(buy_order.timestamp, sell_order.timestamp),
            symbol,
        };
        self.next_trade_id += 1;
        self.trades.push(trade);
        self.stats.trades_executed += 1;
    }

    pub fn cancel_order(&mut self, order_id: u64) -> bool {
        if let Some((side, price_bits)) = self.orders_by_id.remove(&order_id) {
            let price_levels = match side {
                OrderSide::Buy => &mut self.buy_price_levels,
                OrderSide::Sell => &mut self.sell_price_levels,
            };

            if let Some(level) = price_levels.get_mut(&price_bits) {
                if let Some(_order) = level.remove_order(order_id) {
                    // Handle empty price level
                    if level.is_empty() {
                        price_levels.remove(&price_bits);
                    }
                    return true;
                }
            }
        }
        false
    }

    pub fn get_order_book_snapshot(&self) -> (Vec<(f64, f64)>, Vec<(f64, f64)>) {
        // Get buy side: price level and total quantity
        let mut buy_snapshot = Vec::with_capacity(self.buy_price_levels.len());
        for (&price_bits, level) in &self.buy_price_levels {
            let price = Self::bits_to_price(price_bits, true);
            // Calculate total quantity directly without mutating
            let total_qty = level.orders.iter().map(|o| o.remaining_quantity).sum();
            buy_snapshot.push((price, total_qty));
        }

        // Get sell side: price level and total quantity
        let mut sell_snapshot = Vec::with_capacity(self.sell_price_levels.len());
        for (&price_bits, level) in &self.sell_price_levels {
            let price = Self::bits_to_price(price_bits, false);
            // Calculate total quantity directly without mutating
            let total_qty = level.orders.iter().map(|o| o.remaining_quantity).sum();
            sell_snapshot.push((price, total_qty));
        }

        // Sort by price (unnecessary but consistent with original)
        buy_snapshot.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(Ordering::Equal));
        sell_snapshot.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(Ordering::Equal));

        (buy_snapshot, sell_snapshot)
    }

    pub fn get_trades(&self) -> Vec<Trade> {
        self.trades.clone()
    }

    pub fn get_statistics(&self) -> OrderBookStats {
        self.stats.clone()
    }
}

impl Clone for OrderBook {
    fn clone(&self) -> Self {
        OrderBook {
            buy_price_levels: self.buy_price_levels.clone(),
            sell_price_levels: self.sell_price_levels.clone(),
            orders_by_id: self.orders_by_id.clone(),
            next_order_id: self.next_order_id,
            next_trade_id: self.next_trade_id,
            trades: self.trades.clone(),
            price_level_cache: RwLock::new(HashMap::new()), // Create new empty cache
            cache_hits: self.cache_hits,
            cache_misses: self.cache_misses,
            max_cache_size: self.max_cache_size,
            removed_price_levels: Vec::with_capacity(16),
            stats: self.stats.clone(),
        }
    }
}

/// Python order class
#[pyclass]
#[derive(Clone)]
struct PyOrder {
    #[pyo3(get)]
    id: u64,
    #[pyo3(get)]
    side: PyOrderSide,
    #[pyo3(get)]
    order_type: PyOrderType,
    #[pyo3(get)]
    price: Option<f64>,
    #[pyo3(get)]
    quantity: f64,
    #[pyo3(get)]
    filled_quantity: f64,
    #[pyo3(get)]
    status: PyOrderStatus,
    #[pyo3(get)]
    timestamp: u64,
    #[pyo3(get)]
    symbol: Option<String>,
}

/// Python trade class
#[pyclass]
#[derive(Clone)]
struct PyTrade {
    #[pyo3(get)]
    id: u64,
    #[pyo3(get)]
    buy_order_id: u64,
    #[pyo3(get)]
    sell_order_id: u64,
    #[pyo3(get)]
    price: f64,
    #[pyo3(get)]
    quantity: f64,
    #[pyo3(get)]
    timestamp: u64,
    #[pyo3(get)]
    symbol: Option<String>,
}

/// Python order book class
#[pyclass]
struct PyOrderBook {
    order_book: OrderBook,
}

#[pymethods]
impl PyOrderBook {
    #[new]
    fn new() -> Self {
        PyOrderBook {
            order_book: OrderBook::new(),
        }
    }

    #[pyo3(signature = (side, price, quantity, timestamp))]
    fn add_limit_order(
        &mut self,
        side: PyOrderSide,
        price: f64,
        quantity: f64,
        timestamp: u64,
    ) -> PyResult<u64> {
        let side = match side {
            PyOrderSide::Buy => OrderSide::Buy,
            PyOrderSide::Sell => OrderSide::Sell,
        };

        Ok(self.order_book.add_order(
            side,
            OrderType::Limit,
            Some(price),
            quantity,
            timestamp,
            None,
        ))
    }

    #[pyo3(signature = (side, quantity, timestamp))]
    fn add_market_order(
        &mut self,
        side: PyOrderSide,
        quantity: f64,
        timestamp: u64,
    ) -> PyResult<u64> {
        let side = match side {
            PyOrderSide::Buy => OrderSide::Buy,
            PyOrderSide::Sell => OrderSide::Sell,
        };

        Ok(self
            .order_book
            .add_order(side, OrderType::Market, None, quantity, timestamp, None))
    }

    fn cancel_order(&mut self, order_id: u64) -> PyResult<bool> {
        Ok(self.order_book.cancel_order(order_id))
    }

    fn get_order_book_snapshot(&self) -> PyResult<(Vec<(f64, f64)>, Vec<(f64, f64)>)> {
        Ok(self.order_book.get_order_book_snapshot())
    }

    fn get_trades(&self) -> PyResult<Vec<PyTrade>> {
        let trades = self.order_book.get_trades();
        let py_trades = trades
            .into_iter()
            .map(|t| PyTrade {
                id: t.id,
                buy_order_id: t.buy_order_id,
                sell_order_id: t.sell_order_id,
                price: t.price,
                quantity: t.quantity,
                timestamp: t.timestamp,
                symbol: t.symbol,
            })
            .collect();

        Ok(py_trades)
    }
}

#[pymodule]
fn matching_engine(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyOrderType>()?;
    m.add_class::<PyOrderSide>()?;
    m.add_class::<PyOrderStatus>()?;
    m.add_class::<PyOrder>()?;
    m.add_class::<PyTrade>()?;
    m.add_class::<PyOrderBook>()?;

    Ok(())
}
