from datetime import datetime, timezone, timedelta

# Order placement time from logs (UTC)
order_time_utc = datetime(2026, 3, 17, 11, 23, 43, tzinfo=timezone.utc)

# Convert to ET (UTC-4 during DST, UTC-5 during EST)
et_offset = timedelta(hours=-4)  # March is DST
order_time_et = order_time_utc + et_offset

print("Order Placement Analysis:")
print(f"UTC Time: {order_time_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"ET Time:  {order_time_et.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Day:      {order_time_et.strftime('%A')}")
print()

# Market hours (9:30 AM - 4:00 PM ET on weekdays)
market_open = order_time_et.replace(hour=9, minute=30, second=0, microsecond=0)
market_close = order_time_et.replace(hour=16, minute=0, second=0, microsecond=0)

print("US Market Hours:")
print(f"Open:  {market_open.strftime('%H:%M:%S')}")
print(f"Close: {market_close.strftime('%H:%M:%S')}")
print()

if market_open <= order_time_et <= market_close:
    print("✅ ORDERS PLACED DURING MARKET HOURS")
else:
    print("❌ ORDERS PLACED OUTSIDE MARKET HOURS")
    
if order_time_et.hour < 9 or order_time_et.hour >= 16:
    print("📍 LIKELY CAUSE: Market closed - orders won't fill until next open")
else:
    print("📍 Orders should have filled - check liquidity or IBKR issues")
