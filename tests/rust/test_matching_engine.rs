use matching_engine::{OrderBook, OrderSide, OrderType};

#[test]
fn test_limit_order_addition() {
    let mut book = OrderBook::new();

    // Add a buy order
    let buy_order_id = book.add_order(
        OrderSide::Buy,
        OrderType::Limit,
        Some(100.0),
        10.0,
        123456789,
    );

    // Add a sell order
    let sell_order_id = book.add_order(
        OrderSide::Sell,
        OrderType::Limit,
        Some(110.0),
        5.0,
        123456790,
    );

    // Get order book snapshot
    let (buy_orders, sell_orders) = book.get_order_book_snapshot();

    // Verify buy orders
    assert_eq!(buy_orders.len(), 1);
    assert_eq!(buy_orders[0].0, 100.0); // Price
    assert_eq!(buy_orders[0].1, 10.0); // Quantity

    // Verify sell orders
    assert_eq!(sell_orders.len(), 1);
    assert_eq!(sell_orders[0].0, 110.0); // Price
    assert_eq!(sell_orders[0].1, 5.0); // Quantity
}

#[test]
fn test_matching_limit_orders() {
    let mut book = OrderBook::new();

    // Add a buy order
    let buy_order_id = book.add_order(
        OrderSide::Buy,
        OrderType::Limit,
        Some(100.0),
        10.0,
        123456789,
    );

    // Add a sell order that will match
    let sell_order_id = book.add_order(
        OrderSide::Sell,
        OrderType::Limit,
        Some(100.0),
        5.0,
        123456790,
    );

    // Get order book snapshot
    let (buy_orders, sell_orders) = book.get_order_book_snapshot();

    // Verify buy orders (should have 5 remaining)
    assert_eq!(buy_orders.len(), 1);
    assert_eq!(buy_orders[0].0, 100.0); // Price
    assert_eq!(buy_orders[0].1, 5.0); // Quantity (10.0 - 5.0)

    // Verify sell orders (should be empty)
    assert_eq!(sell_orders.len(), 0);

    // Verify trades
    let trades = book.get_trades();
    assert_eq!(trades.len(), 1);
    assert_eq!(trades[0].buy_order_id, buy_order_id);
    assert_eq!(trades[0].sell_order_id, sell_order_id);
    assert_eq!(trades[0].price, 100.0);
    assert_eq!(trades[0].quantity, 5.0);
}

#[test]
fn test_market_order() {
    let mut book = OrderBook::new();

    // Add a sell limit order
    let sell_order_id = book.add_order(
        OrderSide::Sell,
        OrderType::Limit,
        Some(100.0),
        10.0,
        123456789,
    );

    // Add a buy market order
    let buy_order_id = book.add_order(OrderSide::Buy, OrderType::Market, None, 5.0, 123456790);

    // Get order book snapshot
    let (buy_orders, sell_orders) = book.get_order_book_snapshot();

    // Verify buy orders (should be empty)
    assert_eq!(buy_orders.len(), 0);

    // Verify sell orders (should have 5 remaining)
    assert_eq!(sell_orders.len(), 1);
    assert_eq!(sell_orders[0].0, 100.0); // Price
    assert_eq!(sell_orders[0].1, 5.0); // Quantity (10.0 - 5.0)

    // Verify trades
    let trades = book.get_trades();
    assert_eq!(trades.len(), 1);
    assert_eq!(trades[0].buy_order_id, buy_order_id);
    assert_eq!(trades[0].sell_order_id, sell_order_id);
    assert_eq!(trades[0].price, 100.0);
    assert_eq!(trades[0].quantity, 5.0);
}

#[test]
fn test_cancel_order() {
    let mut book = OrderBook::new();

    // Add a buy order
    let buy_order_id = book.add_order(
        OrderSide::Buy,
        OrderType::Limit,
        Some(100.0),
        10.0,
        123456789,
    );

    // Cancel the order
    let success = book.cancel_order(buy_order_id);
    assert!(success);

    // Get order book snapshot (should be empty)
    let (buy_orders, sell_orders) = book.get_order_book_snapshot();
    assert_eq!(buy_orders.len(), 0);
    assert_eq!(sell_orders.len(), 0);

    // Try to cancel a non-existent order
    let success = book.cancel_order(999);
    assert!(!success);
}
