"""
Analyze hard stop performance and provide optimization recommendations
"""
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path("d:/GitHub/VolatilityHunter")
PORTFOLIO_FILE = ROOT / "data" / "portfolio.json"

def analyze_hard_stops():
    """Analyze all hard stop exits to evaluate performance"""
    
    with open(PORTFOLIO_FILE, 'r') as f:
        portfolio = json.load(f)
    
    trade_history = portfolio.get('trade_history', [])
    
    # Filter hard stop exits
    hard_stops = [
        t for t in trade_history 
        if t.get('type') == 'SELL' and 'Hard stop' in t.get('reason', '')
    ]
    
    if not hard_stops:
        print("No hard stop exits found in trade history")
        return
    
    print("=" * 80)
    print("HARD STOP ANALYSIS - 8% THRESHOLD")
    print("=" * 80)
    print()
    
    # Calculate statistics
    total_stops = len(hard_stops)
    total_loss = sum(t['pnl'] for t in hard_stops)
    avg_loss = total_loss / total_stops if total_stops > 0 else 0
    avg_loss_pct = sum(t['pnl_pct'] for t in hard_stops) / total_stops if total_stops > 0 else 0
    
    print(f"Total Hard Stops: {total_stops}")
    print(f"Total Loss: ${total_loss:,.2f}")
    print(f"Average Loss: ${avg_loss:,.2f}")
    print(f"Average Loss %: {avg_loss_pct:.2f}%")
    print()
    
    # Show individual exits
    print("INDIVIDUAL HARD STOP EXITS:")
    print("-" * 80)
    print(f"{'Ticker':<8} {'Date':<12} {'Loss $':<12} {'Loss %':<10} {'Actual %':<10}")
    print("-" * 80)
    
    for t in hard_stops:
        date = t['timestamp'][:10]
        print(f"{t['ticker']:<8} {date:<12} ${t['pnl']:>10,.2f} {t['pnl_pct']:>8.2f}%  {t['pnl_pct']:>8.2f}%")
    
    print()
    print("=" * 80)
    print("OPTIMIZATION ANALYSIS")
    print("=" * 80)
    print()
    
    # Analyze if stops were too tight
    stops_near_threshold = sum(1 for t in hard_stops if abs(t['pnl_pct']) <= 10.0)
    stops_beyond_threshold = sum(1 for t in hard_stops if abs(t['pnl_pct']) > 10.0)
    
    print(f"Stops at 8-10% (near threshold): {stops_near_threshold} ({stops_near_threshold/total_stops*100:.1f}%)")
    print(f"Stops beyond 10%: {stops_beyond_threshold} ({stops_beyond_threshold/total_stops*100:.1f}%)")
    print()
    
    # Calculate what would have happened with different thresholds
    print("WHAT-IF ANALYSIS:")
    print("-" * 80)
    
    for threshold in [10, 12, 15]:
        would_have_stopped = sum(1 for t in hard_stops if abs(t['pnl_pct']) >= threshold)
        would_have_avoided = total_stops - would_have_stopped
        
        print(f"\nIf threshold was {threshold}%:")
        print(f"  Would still stop: {would_have_stopped}/{total_stops} trades")
        print(f"  Would avoid stop: {would_have_avoided}/{total_stops} trades")
        print(f"  Potential savings: ${would_have_avoided * avg_loss:,.2f}")
    
    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    # Provide recommendations based on data
    if avg_loss_pct > -11:
        print("✅ RECOMMENDATION: WIDEN STOP TO 12%")
        print()
        print("Reasoning:")
        print(f"  • Average loss is {avg_loss_pct:.1f}%, close to 8% threshold")
        print(f"  • {stops_near_threshold}/{total_stops} stops were near threshold (normal volatility)")
        print("  • Wider stop allows for normal pullbacks in volatile stocks")
        print("  • Reduces false exits while still protecting capital")
        print()
        print("Expected Impact:")
        print(f"  • Reduce false exits by ~{stops_near_threshold/total_stops*100:.0f}%")
        print("  • Allow winners more room to develop")
        print("  • Still exit on true breakdowns")
    else:
        print("⚠️ RECOMMENDATION: KEEP AT 8% OR TIGHTEN")
        print()
        print("Reasoning:")
        print(f"  • Average loss is {avg_loss_pct:.1f}%, well beyond threshold")
        print("  • Stops are catching real breakdowns, not false signals")
        print("  • Current threshold is appropriate for risk management")
    
    print()
    print("=" * 80)
    print("ALTERNATIVE: VOLATILITY-BASED STOPS")
    print("=" * 80)
    print()
    print("Instead of fixed 8%, use ATR-based stops:")
    print("  • High volatility stocks: 2.5-3x ATR stop (~12-15%)")
    print("  • Medium volatility: 2x ATR stop (~8-10%)")
    print("  • Low volatility: 1.5x ATR stop (~5-7%)")
    print()
    print("Benefits:")
    print("  ✅ Adapts to each stock's personality")
    print("  ✅ Reduces false exits on volatile stocks")
    print("  ✅ Tighter protection on stable stocks")
    print()
    print("Implementation:")
    print("  • Already supported in v8.1 with VOL_SIZE parameter")
    print("  • Can extend to volatility-based stops")
    print("  • Requires ATR calculation in indicators")
    
    print()

if __name__ == "__main__":
    analyze_hard_stops()
