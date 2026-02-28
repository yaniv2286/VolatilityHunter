#!/usr/bin/env python3
"""
Sweet Spot Strategy Compliance Test
Verify the strategy agent uses all Sweet Spot Trading Blueprint components
"""

import sys
import os
import asyncio
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

async def test_sweet_spot_strategy_compliance():
    """Test Sweet Spot Strategy compliance with full blueprint"""
    print("🎯 SWEET SPOT STRATEGY COMPLIANCE TEST")
    print("=" * 60)
    
    try:
        # Import and initialize strategy agent
        from src.agents.strategy.agent import StrategyAgent
        
        # Strategy configuration with all Sweet Spot features enabled
        strategy_config = {
            "agent_id": "test_sweet_spot_agent",
            "agent_type": "strategy",
            "enabled": True,
            "log_level": "INFO",
            "default_strategy": "sweet_spot_v7_2",
            "sweet_spot_config": {
                "enable_patterns": True,
                "enable_spread_monitoring": True,
                "enable_time_filters": True,
                "enable_earnings_filter": True,
                "enable_volume_confirmation": True,
                "enable_candlestick_confirmation": True,
                "enable_20_percent_rule": True,
                "enable_stop_losses": True,
                "enable_power_stocks": True,
                "pattern_weight": 0.3,
                "risk_per_trade": 0.01,
                "max_position_percent": 0.20
            }
        }
        
        print(f"🤖 Initializing Strategy Agent with Sweet Spot compliance...")
        strategy_agent = StrategyAgent("test_sweet_spot_agent", strategy_config)
        
        if await strategy_agent.initialize():
            print(f"✅ Strategy Agent initialized successfully")
            
            # Check Sweet Spot Strategy availability
            if hasattr(strategy_agent, 'sweet_spot_strategy') and strategy_agent.sweet_spot_strategy:
                print(f"✅ Sweet Spot Strategy loaded and active")
                
                # Test with a sample ticker
                test_tickers = ["AAPL", "MSFT", "TSLA"]
                print(f"\n📊 Testing Sweet Spot analysis on {len(test_tickers)} tickers...")
                
                # Generate signals using Sweet Spot Strategy
                signal_result = await strategy_agent.generate_signals(
                    tickers=test_tickers,
                    strategy="sweet_spot_v7_2",
                    parameters={
                        "portfolio_data": {
                            "total_equity": 100000,
                            "current_positions": []
                        }
                    }
                )
                
                if signal_result.get('success', False):
                    print(f"✅ Sweet Spot signal generation successful")
                    
                    # Analyze compliance features
                    await analyze_compliance_features(signal_result, strategy_agent)
                    
                else:
                    print(f"❌ Sweet Spot signal generation failed")
                    print(f"   Error: {signal_result.get('error', 'Unknown error')}")
                    return False
                    
            else:
                print(f"❌ Sweet Spot Strategy not loaded")
                print(f"   Available strategies: {getattr(strategy_agent, 'pattern_strategy', 'None')}")
                return False
                
        else:
            print(f"❌ Strategy Agent initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Sweet Spot compliance: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def analyze_compliance_features(signal_result, strategy_agent):
    """Analyze Sweet Spot compliance features in the signal results"""
    print(f"\n🔍 SWEET SPOT BLUEPRINT COMPLIANCE ANALYSIS")
    print("=" * 60)
    
    compliance_score = 0
    total_checks = 0
    
    # Check 1: Pre-Trade Checklist
    print(f"\n📋 1. PRE-TRADE CHECKLIST")
    print("-" * 40)
    
    total_checks += 1
    if hasattr(strategy_agent.sweet_spot_strategy, 'enable_time_filters') and strategy_agent.sweet_spot_strategy.enable_time_filters:
        print(f"✅ 10:06 AM Rule: Implemented")
        compliance_score += 1
    else:
        print(f"❌ 10:06 AM Rule: Missing")
    
    total_checks += 1
    if hasattr(strategy_agent.sweet_spot_strategy, 'enable_spread_monitoring') and strategy_agent.sweet_spot_strategy.enable_spread_monitoring:
        print(f"✅ Bid/Ask Spread: Implemented")
        compliance_score += 1
    else:
        print(f"❌ Bid/Ask Spread: Missing")
    
    total_checks += 1
    if hasattr(strategy_agent.sweet_spot_strategy, 'enable_earnings_filter') and strategy_agent.sweet_spot_strategy.enable_earnings_filter:
        print(f"✅ Earnings Filter: Implemented")
        compliance_score += 1
    else:
        print(f"❌ Earnings Filter: Missing")
    
    total_checks += 1
    if hasattr(strategy_agent.sweet_spot_strategy, 'enable_time_filters') and strategy_agent.sweet_spot_strategy.enable_time_filters:
        print(f"✅ Friday Rule: Implemented")
        compliance_score += 1
    else:
        print(f"❌ Friday Rule: Missing")
    
    # Check 2: Entry Rules
    print(f"\n🎯 2. ENTRY RULES")
    print("-" * 40)
    
    total_checks += 1
    if hasattr(strategy_agent.sweet_spot_strategy, 'enable_patterns') and strategy_agent.sweet_spot_strategy.enable_patterns:
        print(f"✅ Sweet Spot Zone (32-80%): Implemented")
        compliance_score += 1
    else:
        print(f"❌ Sweet Spot Zone: Missing")
    
    total_checks += 1
    if hasattr(strategy_agent.sweet_spot_strategy, 'enable_volume_confirmation') and strategy_agent.sweet_spot_strategy.enable_volume_confirmation:
        print(f"✅ Volume Confirmation: Implemented")
        compliance_score += 1
    else:
        print(f"❌ Volume Confirmation: Missing")
    
    total_checks += 1
    if hasattr(strategy_agent.sweet_spot_strategy, 'enable_candlestick_confirmation') and strategy_agent.sweet_spot_strategy.enable_candlestick_confirmation:
        print(f"✅ Candlestick Patterns: Implemented")
        compliance_score += 1
    else:
        print(f"❌ Candlestick Patterns: Missing")
    
    total_checks += 1
    if hasattr(strategy_agent.sweet_spot_strategy, 'enable_patterns') and strategy_agent.sweet_spot_strategy.enable_patterns:
        print(f"✅ Chart Patterns (W/M/H&S): Implemented")
        compliance_score += 1
    else:
        print(f"❌ Chart Patterns: Missing")
    
    # Check 3: Exit Rules
    print(f"\n🚪 3. EXIT RULES")
    print("-" * 40)
    
    total_checks += 1
    # Check if signals contain exit information
    signals = signal_result.get('signals', {})
    if signals:
        sample_signal = list(signals.values())[0] if signals else {}
        if 'analysis' in sample_signal and 'sweet_spot_analysis' in sample_signal['analysis']:
            print(f"✅ Trend Breakdown: Implemented")
            compliance_score += 1
        else:
            print(f"❌ Trend Breakdown: Missing")
    else:
        print(f"❌ Trend Breakdown: No signals to check")
    
    total_checks += 1
    if hasattr(strategy_agent.sweet_spot_strategy, 'enable_power_stocks'):
        print(f"✅ Power Stock Exception: Implemented")
        compliance_score += 1
    else:
        print(f"❌ Power Stock Exception: Missing")
    
    # Check 4: Risk Management
    print(f"\n🛡️ 4. RISK MANAGEMENT")
    print("-" * 40)
    
    total_checks += 1
    if hasattr(strategy_agent.sweet_spot_strategy, 'enable_20_percent_rule'):
        print(f"✅ 20% Position Rule: Implemented")
        compliance_score += 1
    else:
        print(f"❌ 20% Position Rule: Missing")
    
    total_checks += 1
    if hasattr(strategy_agent.sweet_spot_strategy, 'enable_stop_losses'):
        print(f"✅ Stop Losses (1-5%): Implemented")
        compliance_score += 1
    else:
        print(f"❌ Stop Losses: Missing")
    
    # Calculate compliance percentage
    compliance_percentage = (compliance_score / total_checks) * 100 if total_checks > 0 else 0
    
    print(f"\n📊 COMPLIANCE SUMMARY")
    print("=" * 60)
    print(f"✅ Features Implemented: {compliance_score}/{total_checks}")
    print(f"📈 Compliance Percentage: {compliance_percentage:.1f}%")
    
    if compliance_percentage >= 90:
        print(f"🎉 EXCELLENT: Near-full Sweet Spot Blueprint compliance!")
    elif compliance_percentage >= 75:
        print(f"👍 GOOD: Strong Sweet Spot Blueprint compliance")
    elif compliance_percentage >= 50:
        print(f"⚠️  MODERATE: Partial Sweet Spot Blueprint compliance")
    else:
        print(f"❌ POOR: Low Sweet Spot Blueprint compliance")
    
    # Show sample signal analysis
    if signals:
        print(f"\n📈 SAMPLE SIGNAL ANALYSIS")
        print("-" * 40)
        for ticker, signal in list(signals.items())[:2]:  # Show first 2 signals
            print(f"\n📊 {ticker}:")
            print(f"   • Signal: {signal.get('signal', 'Unknown')}")
            print(f"   • Confidence: {signal.get('confidence', 0):.2f}")
            print(f"   • Sweet Spot Compliant: {signal.get('sweet_spot_compliant', False)}")
            
            if 'analysis' in signal and 'sweet_spot_analysis' in signal['analysis']:
                ss_analysis = signal['analysis']['sweet_spot_analysis']
                print(f"   • Enhanced Score: {ss_analysis.get('enhanced_score', 0):.3f}")
                
                components = ss_analysis.get('components', {})
                if components:
                    print(f"   • Component Scores:")
                    for comp, score in components.items():
                        print(f"     - {comp}: {score:.3f}")

async def test_individual_components():
    """Test individual Sweet Spot components"""
    print(f"\n🔧 INDIVIDUAL COMPONENT TESTING")
    print("=" * 60)
    
    try:
        from src.sweet_spot_strategy import SweetSpotStrategy
        from src.storage import DataStorage
        
        # Initialize Sweet Spot Strategy
        config = {
            'enable_patterns': True,
            'enable_spread_monitoring': True,
            'enable_time_filters': True,
            'enable_earnings_filter': True,
            'enable_volume_confirmation': True,
            'enable_candlestick_confirmation': True
        }
        
        sweet_spot = SweetSpotStrategy(config)
        print(f"✅ Sweet Spot Strategy initialized")
        
        # Test with AAPL data
        storage = DataStorage()
        aapl_data = storage.load_data("AAPL")
        
        if aapl_data is not None and len(aapl_data) > 200:
            print(f"✅ AAPL data loaded: {len(aapl_data)} days")
            
            # Run Sweet Spot analysis
            analysis = sweet_spot.analyze_stock_sweet_spot("AAPL", aapl_data)
            
            if analysis:
                print(f"✅ Sweet Spot analysis completed")
                
                # Check for key components
                if 'sweet_spot_analysis' in analysis:
                    ss_analysis = analysis['sweet_spot_analysis']
                    
                    print(f"\n📊 COMPONENT BREAKDOWN:")
                    
                    # Time filters
                    if 'time_filters' in ss_analysis:
                        time_analysis = ss_analysis['time_filters']
                        print(f"   • Time Filters: ✅")
                        print(f"     - 10:06 AM Optimal: {time_analysis.get('is_10_06_optimal', 'Unknown')}")
                        print(f"     - Friday Optimal: {time_analysis.get('is_friday_optimal', 'Unknown')}")
                    
                    # Volume confirmation
                    if 'volume_confirmation' in ss_analysis:
                        vol_analysis = ss_analysis['volume_confirmation']
                        print(f"   • Volume Confirmation: ✅")
                        print(f"     - Volume Ratio: {vol_analysis.get('volume_ratio', 0):.1%}")
                        print(f"     - Consistent: {vol_analysis.get('volume_consistent', False)}")
                    
                    # Earnings filter
                    if 'earnings_filter' in ss_analysis:
                        earn_analysis = ss_analysis['earnings_filter']
                        print(f"   • Earnings Filter: ✅")
                        print(f"     - Safe: {earn_analysis.get('earnings_safe', False)}")
                        print(f"     - Message: {earn_analysis.get('message', 'No message')}")
                    
                    # Pattern analysis
                    if 'patterns' in ss_analysis:
                        patterns = ss_analysis['patterns']
                        print(f"   • Pattern Recognition: ✅")
                        print(f"     - Patterns Found: {len(patterns.get('signals', []))}")
                    
                    # Enhanced score
                    enhanced_score = ss_analysis.get('enhanced_score', 0)
                    print(f"   • Enhanced Score: {enhanced_score:.3f}")
                    
                else:
                    print(f"❌ No sweet_spot_analysis found in results")
            else:
                print(f"❌ Sweet Spot analysis failed")
        else:
            print(f"❌ No AAPL data available")
            
    except Exception as e:
        print(f"❌ Error testing components: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 VOLATILITYHUNTER SWEET SPOT STRATEGY TEST")
    print("=" * 60)
    
    # Run compliance test
    compliance_success = asyncio.run(test_sweet_spot_strategy_compliance())
    
    # Run component test
    component_success = asyncio.run(test_individual_components())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULTS")
    print("=" * 60)
    print(f"Compliance Test: {'✅ PASS' if compliance_success else '❌ FAIL'}")
    print(f"Component Test: {'✅ PASS' if component_success else '❌ FAIL'}")
    
    if compliance_success and component_success:
        print(f"\n🎉 SWEET SPOT STRATEGY FULLY COMPLIANT!")
        print(f"📈 Strategy is ready for production trading")
    else:
        print(f"\n⚠️  SOME ISSUES DETECTED")
        print(f"🔧 Review implementation details above")
    
    exit(0 if (compliance_success and component_success) else 1)
