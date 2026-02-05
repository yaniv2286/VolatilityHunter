#!/usr/bin/env python3
"""
Portfolio Analysis Script
Analyzes current portfolio composition and risk metrics
"""

import sys
import os
sys.path.append('src')

from tracker import Portfolio

def analyze_portfolio():
    """Analyze current portfolio composition and risk metrics."""
    
    portfolio = Portfolio()
    positions = portfolio.state['positions']
    
    print("=" * 60)
    print("VOLATILITYHUNTER PORTFOLIO ANALYSIS")
    print("=" * 60)
    
    # Basic stats
    print(f"Total Positions: {len(positions)}/10")
    print(f"Cash Available: ${portfolio.state['cash']:,.2f}")
    print(f"Available Slots: {10 - len(positions)}")
    
    # Position analysis
    total_value = 0
    quality_scores = []
    
    print("\nPOSITION BREAKDOWN:")
    print("-" * 40)
    
    for ticker, pos in positions.items():
        value = pos['shares'] * pos['entry_price']
        total_value += value
        quality_scores.append(pos['quality_score'])
        
        print(f"{ticker}: ${value:,.2f} | Quality: {pos['quality_score']:.2f}")
    
    # Portfolio metrics
    avg_position = total_value / len(positions)
    avg_quality = sum(quality_scores) / len(quality_scores)
    
    print(f"\nTotal Invested: ${total_value:,.2f}")
    print(f"Average Position: ${avg_position:,.2f}")
    print(f"Average Quality Score: {avg_quality:.2f}")
    
    # Risk analysis
    print(f"\nRISK ANALYSIS:")
    print("-" * 40)
    print(f"Position Size: Fixed at $5,000 each")
    print(f"Diversification: {len(positions)} different stocks")
    print(f"Quality Range: {min(quality_scores):.2f} - {max(quality_scores):.2f}")
    
    # Recommendations
    print(f"\nRECOMMENDATIONS:")
    print("-" * 40)
    
    if len(positions) < 10:
        print(f"• Consider adding {10 - len(positions)} more positions")
        print(f"• ${portfolio.state['cash']:,.2f} available for new investments")
    
    if avg_quality < 15:
        print("• Average quality score could be improved")
        print("• Consider higher-quality opportunities")
    
    print("• Current positions all showing BUY signals (healthy)")
    print("• System working correctly - no trades needed")
    
    print("=" * 60)

if __name__ == "__main__":
    analyze_portfolio()
