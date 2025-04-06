try:
    import matching_engine
    print("SUCCESS: matching_engine module is available!")
    print(f"Available classes/functions: {dir(matching_engine)}")
    
    # Test creating a PyOrderBook instance
    engine = matching_engine.PyOrderBook()
    print("SUCCESS: Created PyOrderBook instance")
    
    # Check methods available on PyOrderBook
    print(f"PyOrderBook methods/attributes: {dir(engine)}")
    
    # Check method signatures using help
    import inspect
    print("\nInspecting add_limit_order:")
    print(inspect.signature(engine.add_limit_order))
    print("\nInspecting add_market_order:")
    print(inspect.signature(engine.add_market_order))
    print("\nInspecting get_order_book_snapshot:")
    print(inspect.signature(engine.get_order_book_snapshot))
    
    # Test some basic functionality with the correct arguments
    buy_side = matching_engine.PyOrderSide.Buy
    sell_side = matching_engine.PyOrderSide.Sell
    timestamp = 12345678  # An integer timestamp
    
    # Add a buy limit order
    buy_order_id = engine.add_limit_order(buy_side, 100.0, 1.0, timestamp)
    print(f"Added buy limit order with ID: {buy_order_id}")
    
    # Add a sell limit order
    sell_order_id = engine.add_limit_order(sell_side, 101.0, 0.5, timestamp)
    print(f"Added sell limit order with ID: {sell_order_id}")
    
    # Get the order book
    buy_orders, sell_orders = engine.get_order_book_snapshot()
    print(f"Order book: {len(buy_orders)} buy orders, {len(sell_orders)} sell orders")
    print(f"Buy orders: {buy_orders}")
    print(f"Sell orders: {sell_orders}")
    
    # Test market order
    market_order_id = engine.add_market_order(buy_side, 0.5, timestamp)
    print(f"Added market order with ID: {market_order_id}")
    
    # Get trades
    trades = engine.get_trades()
    print(f"Trades: {len(trades)}")
    for trade in trades:
        print(f"  Trade: {trade}")
    
except ImportError as e:
    print(f"ERROR: Could not import matching_engine: {e}")
except Exception as e:
    print(f"ERROR: An error occurred while testing: {e}")
    import traceback
    traceback.print_exc() 