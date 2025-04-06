use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use serde::{Deserialize, Serialize};
use std::cmp::Ordering;
use std::collections::{BTreeMap, HashMap};

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
}

impl Order {
    pub fn new(
        id: u64,
        side: OrderSide,
        order_type: OrderType,
        price: Option<f64>,
        quantity: f64,
        timestamp: u64,
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
}

/// OrderBook struct to manage the buy and sell orders
#[derive(Debug, Clone, Default)]
pub struct OrderBook {
    buy_orders: BTreeMap<(f64, u64), Order>, // Ordered by price (desc) and timestamp
    sell_orders: BTreeMap<(f64, u64), Order>, // Ordered by price (asc) and timestamp
    orders_by_id: HashMap<u64, (OrderSide, f64, u64)>, // For quick lookup
    next_order_id: u64,
    next_trade_id: u64,
    trades: Vec<Trade>,
}

impl OrderBook {
    pub fn new() -> Self {
        OrderBook {
            buy_orders: BTreeMap::new(),
            sell_orders: BTreeMap::new(),
            orders_by_id: HashMap::new(),
            next_order_id: 1,
            next_trade_id: 1,
            trades: Vec::new(),
        }
    }

    pub fn add_order(
        &mut self,
        side: OrderSide,
        order_type: OrderType,
        price: Option<f64>,
        quantity: f64,
        timestamp: u64,
    ) -> u64 {
        let order_id = self.next_order_id;
        self.next_order_id += 1;

        // Create the order
        let mut order = Order::new(order_id, side, order_type, price, quantity, timestamp);

        // Process the order
        self.process_order(&mut order);

        // Return the order ID
        order_id
    }

    fn process_order(&mut self, order: &mut Order) {
        // Handle market orders first
        if order.order_type == OrderType::Market {
            self.match_market_order(order);
            return;
        }

        // Then handle limit orders
        let price = order.price.unwrap(); // Safe unwrap since we know it's a limit order

        // Try to match the order first
        self.match_limit_order(order);

        // If order is not completely filled, add it to the order book
        if order.filled_quantity < order.quantity {
            match order.side {
                OrderSide::Buy => {
                    // For buy orders, use negative price for descending sort
                    self.buy_orders
                        .insert((-price, order.timestamp), order.clone());
                    self.orders_by_id
                        .insert(order.id, (OrderSide::Buy, -price, order.timestamp));
                }
                OrderSide::Sell => {
                    self.sell_orders
                        .insert((price, order.timestamp), order.clone());
                    self.orders_by_id
                        .insert(order.id, (OrderSide::Sell, price, order.timestamp));
                }
            }
        }
    }

    fn match_market_order(&mut self, order: &mut Order) {
        match order.side {
            OrderSide::Buy => {
                // Match against sell orders (ascending price)
                for ((price, _), sell_order) in &mut self.sell_orders.clone() {
                    if order.filled_quantity >= order.quantity {
                        break; // Order fully filled
                    }

                    // Calculate how much can be filled
                    let remaining_to_fill = order.quantity - order.filled_quantity;
                    let available_to_fill = sell_order.quantity - sell_order.filled_quantity;
                    let fill_quantity = remaining_to_fill.min(available_to_fill);

                    // Execute the trade
                    if fill_quantity > 0.0 {
                        self.execute_trade(order, sell_order, *price, fill_quantity);
                    }
                }
            }
            OrderSide::Sell => {
                // Match against buy orders (descending price)
                for ((neg_price, _), buy_order) in &mut self.buy_orders.clone() {
                    if order.filled_quantity >= order.quantity {
                        break; // Order fully filled
                    }

                    // Calculate actual price from negative stored price (for sorting)
                    let price = -neg_price;

                    // Calculate how much can be filled
                    let remaining_to_fill = order.quantity - order.filled_quantity;
                    let available_to_fill = buy_order.quantity - buy_order.filled_quantity;
                    let fill_quantity = remaining_to_fill.min(available_to_fill);

                    // Execute the trade
                    if fill_quantity > 0.0 {
                        self.execute_trade(buy_order, order, price, fill_quantity);
                    }
                }
            }
        }

        // Update order status
        if order.filled_quantity >= order.quantity {
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
                // Match against sell orders with price <= buy price (ascending price)
                for ((sell_price, _), sell_order) in &mut self.sell_orders.clone() {
                    // Stop if sell price is higher than buy price
                    if *sell_price > price || order.filled_quantity >= order.quantity {
                        break;
                    }

                    // Calculate how much can be filled
                    let remaining_to_fill = order.quantity - order.filled_quantity;
                    let available_to_fill = sell_order.quantity - sell_order.filled_quantity;
                    let fill_quantity = remaining_to_fill.min(available_to_fill);

                    // Execute the trade
                    if fill_quantity > 0.0 {
                        self.execute_trade(order, sell_order, *sell_price, fill_quantity);
                    }
                }
            }
            OrderSide::Sell => {
                // Match against buy orders with price >= sell price (descending price)
                for ((neg_buy_price, _), buy_order) in &mut self.buy_orders.clone() {
                    // Calculate actual buy price from negative stored price (for sorting)
                    let buy_price = -neg_buy_price;

                    // Stop if buy price is lower than sell price
                    if buy_price < price || order.filled_quantity >= order.quantity {
                        break;
                    }

                    // Calculate how much can be filled
                    let remaining_to_fill = order.quantity - order.filled_quantity;
                    let available_to_fill = buy_order.quantity - buy_order.filled_quantity;
                    let fill_quantity = remaining_to_fill.min(available_to_fill);

                    // Execute the trade
                    if fill_quantity > 0.0 {
                        self.execute_trade(buy_order, order, buy_price, fill_quantity);
                    }
                }
            }
        }

        // Update order status
        if order.filled_quantity >= order.quantity {
            order.status = OrderStatus::Filled;
        } else if order.filled_quantity > 0.0 {
            order.status = OrderStatus::PartiallyFilled;
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
        sell_order.filled_quantity += quantity;

        // Update order statuses
        if buy_order.filled_quantity >= buy_order.quantity {
            buy_order.status = OrderStatus::Filled;
            // Remove from order book if completely filled
            if let Some((side, price, timestamp)) = self.orders_by_id.remove(&buy_order.id) {
                match side {
                    OrderSide::Buy => {
                        self.buy_orders.remove(&(price, timestamp));
                    }
                    OrderSide::Sell => {
                        self.sell_orders.remove(&(price, timestamp));
                    }
                }
            }
        } else if buy_order.filled_quantity > 0.0 {
            buy_order.status = OrderStatus::PartiallyFilled;
        }

        if sell_order.filled_quantity >= sell_order.quantity {
            sell_order.status = OrderStatus::Filled;
            // Remove from order book if completely filled
            if let Some((side, price, timestamp)) = self.orders_by_id.remove(&sell_order.id) {
                match side {
                    OrderSide::Buy => {
                        self.buy_orders.remove(&(price, timestamp));
                    }
                    OrderSide::Sell => {
                        self.sell_orders.remove(&(price, timestamp));
                    }
                }
            }
        } else if sell_order.filled_quantity > 0.0 {
            sell_order.status = OrderStatus::PartiallyFilled;
        }

        // Record the trade
        let trade = Trade {
            id: self.next_trade_id,
            buy_order_id: buy_order.id,
            sell_order_id: sell_order.id,
            price,
            quantity,
            timestamp: std::cmp::max(buy_order.timestamp, sell_order.timestamp),
        };
        self.next_trade_id += 1;
        self.trades.push(trade);
    }

    pub fn cancel_order(&mut self, order_id: u64) -> bool {
        if let Some((side, price, timestamp)) = self.orders_by_id.remove(&order_id) {
            match side {
                OrderSide::Buy => {
                    if let Some(mut order) = self.buy_orders.remove(&(price, timestamp)) {
                        order.status = OrderStatus::Cancelled;
                        return true;
                    }
                }
                OrderSide::Sell => {
                    if let Some(mut order) = self.sell_orders.remove(&(price, timestamp)) {
                        order.status = OrderStatus::Cancelled;
                        return true;
                    }
                }
            }
        }
        false
    }

    pub fn get_order_book_snapshot(&self) -> (Vec<(f64, f64)>, Vec<(f64, f64)>) {
        // Get buy side: price level and total quantity
        let mut buy_levels: HashMap<f64, f64> = HashMap::new();
        for ((neg_price, _), order) in &self.buy_orders {
            let price = -neg_price;
            let remaining = order.quantity - order.filled_quantity;
            *buy_levels.entry(price).or_insert(0.0) += remaining;
        }

        // Get sell side: price level and total quantity
        let mut sell_levels: HashMap<f64, f64> = HashMap::new();
        for ((price, _), order) in &self.sell_orders {
            let remaining = order.quantity - order.filled_quantity;
            *sell_levels.entry(*price).or_insert(0.0) += remaining;
        }

        // Convert to sorted vectors
        let mut buy_snapshot: Vec<(f64, f64)> = buy_levels.into_iter().collect();
        buy_snapshot.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(Ordering::Equal));

        let mut sell_snapshot: Vec<(f64, f64)> = sell_levels.into_iter().collect();
        sell_snapshot.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(Ordering::Equal));

        (buy_snapshot, sell_snapshot)
    }

    pub fn get_trades(&self) -> Vec<Trade> {
        self.trades.clone()
    }
}

// Python module
#[pymodule]
fn matching_engine(_py: Python, m: &PyModule) -> PyResult<()> {
    // Register order type enum
    #[pyclass]
    #[derive(Clone, Copy)]
    enum PyOrderType {
        Market,
        Limit,
    }

    // Register order side enum
    #[pyclass]
    #[derive(Clone, Copy)]
    enum PyOrderSide {
        Buy,
        Sell,
    }

    // Register order status enum
    #[pyclass]
    #[derive(Clone, Copy)]
    enum PyOrderStatus {
        New,
        PartiallyFilled,
        Filled,
        Cancelled,
        Rejected,
    }

    // Register order class
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
    }

    // Register trade class
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
    }

    // Register order book class
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

            Ok(self
                .order_book
                .add_order(side, OrderType::Limit, Some(price), quantity, timestamp))
        }

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
                .add_order(side, OrderType::Market, None, quantity, timestamp))
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
                })
                .collect();

            Ok(py_trades)
        }
    }

    // Register the classes and enums with Python
    m.add_class::<PyOrderType>()?;
    m.add_class::<PyOrderSide>()?;
    m.add_class::<PyOrderStatus>()?;
    m.add_class::<PyOrder>()?;
    m.add_class::<PyTrade>()?;
    m.add_class::<PyOrderBook>()?;

    Ok(())
}
