#!/usr/bin/env python3
"""
Sync TWS Portfolio with Current Live Data
Updates local portfolio with actual TWS positions from screenshot
"""

import json
import os
from datetime import datetime

def sync_with_actual_tws_data():
    """Sync with actual TWS data from user's screenshot"""
    
    # Actual TWS positions from screenshot (current live prices)
    tws_positions = {
        "AMAT": {
            "quantity": 8,
            "avg_price": 377.57,  # From previous sync
            "last_price": 372.64,  # Current price from screenshot
            "value": 2981.12,
            "unrealized_pnl": -39.44
        },
        "CTRE": {
            "quantity": 462,
            "avg_price": 40.60,
            "last_price": 40.78,
            "value": 18838.51,
            "unrealized_pnl": 81.39
        },
        "EXP": {
            "quantity": 118,
            "avg_price": 231.57,
            "last_price": 220.77,
            "value": 26050.92,
            "unrealized_pnl": -1273.98
        },
        "FSLY": {
            "quantity": 146,
            "avg_price": 17.30,
            "last_price": 17.57,
            "value": 2565.66,
            "unrealized_pnl": 39.32
        },
        "LFST": {
            "quantity": 1622,
            "avg_price": 7.085,
            "last_price": 6.91,
            "value": 11201.53,
            "unrealized_pnl": -290.34
        },
        "NGG": {
            "quantity": 104,
            "avg_price": 92.66,
            "last_price": 93.54,
            "value": 9728.18,
            "unrealized_pnl": 91.62
        },
        "NMR": {
            "quantity": 260,
            "avg_price": 9.065,
            "last_price": 9.11,
            "value": 2368.60,
            "unrealized_pnl": 11.70
        },
        "OGE": {
            "quantity": 442,
            "avg_price": 48.20,
            "last_price": 48.46,
            "value": 21419.39,
            "unrealized_pnl": 114.99
        },
        "SYNA": {
            "quantity": 36,
            "avg_price": 82.83,
            "last_price": 80.78,
            "value": 2907.99,
            "unrealized_pnl": -73.91
        },
        "TSLA": {
            "quantity": 1,
            "avg_price": 395.80,
            "last_price": 404.71,
            "value": 404.71,
            "unrealized_pnl": 8.91
        },
        "XEL": {
            "quantity": 350,
            "avg_price": 83.71,
            "last_price": 83.72,
            "value": 29300.91,
            "unrealized_pnl": 3.91
        }
    }
    
    # Calculate totals
    total_position_value = sum(pos["value"] for pos in tws_positions.values())
    total_unrealized_pnl = sum(pos["unrealized_pnl"] for pos in tws_positions.values())
    
    # Estimate cash (TWS shows $50,000+ in your account)
    estimated_cash = 50000.0
    total_portfolio_value = estimated_cash + total_position_value
    
    # Create updated portfolio
    updated_portfolio = {
        "cash": estimated_cash,
        "positions": tws_positions,
        "total_value": total_portfolio_value,
        "last_updated": datetime.now().isoformat(),
        "trades": [],
        "sync_source": "tws_live_screenshot",
        "sync_timestamp": datetime.now().isoformat(),
        "total_position_value": total_position_value,
        "total_unrealized_pnl": total_unrealized_pnl,
        "position_count": len(tws_positions),
        "account_id": "DUP663578",  # From TWS screenshot
        "currency": "USD"
    }
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Write updated portfolio
    portfolio_file = "data/portfolio_sim.json"
    with open(portfolio_file, 'w') as f:
        json.dump(updated_portfolio, f, indent=2)
    
    print("✅ Portfolio synchronized with TWS screenshot data!")
    print(f"📊 Portfolio Summary:")
    print(f"   Account: {updated_portfolio['account_id']}")
    print(f"   Cash: ${estimated_cash:,.2f}")
    print(f"   Positions: {len(tws_positions)}")
    print(f"   Position Value: ${total_position_value:,.2f}")
    print(f"   Total Portfolio: ${total_portfolio_value:,.2f}")
    print(f"   Total P&L: ${total_unrealized_pnl:+,.2f}")
    print(f"   Last Updated: {updated_portfolio['last_updated']}")
    
    print("\n📈 Current TWS Positions (LIVE DATA):")
    print("-" * 80)
    
    # Sort positions by value for better readability
    sorted_positions = sorted(tws_positions.items(), key=lambda x: x[1]['value'], reverse=True)
    
    for ticker, pos in sorted_positions:
        pnl_sign = "+" if pos["unrealized_pnl"] >= 0 else ""
        pnl_color = "🟢" if pos["unrealized_pnl"] >= 0 else "🔴"
        
        print(f"{ticker:4} | {pos['quantity']:4} shares | "
              f"${pos['avg_price']:7.2f} → ${pos['last_price']:7.2f} | "
              f"Value: ${pos['value']:8,.2f} | "
              f"{pnl_color} P&L: {pnl_sign}{pos['unrealized_pnl']:7.2f}")
    
    print("-" * 80)
    print(f"\n🎯 SYNC STATUS: ✅ COMPLETE")
    print(f"   📁 File: {portfolio_file}")
    print(f"   🔄 Source: TWS Live Screenshot")
    print(f"   ⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return True

if __name__ == "__main__":
    sync_with_actual_tws_data()
