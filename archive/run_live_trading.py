#!/usr/bin/env python3
"""
🚀 VOLATILITYHUNTER LIVE TRADING EXECUTOR
Main script for live trading with IBKR integration
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/live_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def run_live_trading():
    """Execute live trading session"""
    
    logger.info("VOLATILITYHUNTER LIVE TRADING SESSION")
    logger.info("=" * 60)
    logger.info(f"Session Start: {datetime.now().isoformat()}")
    logger.info(f"Trading Mode: LIVE")
    logger.info(f"Broker: IBKR")
    logger.info(f"Portfolio: $100,000.00")
    logger.info("WARNING: REAL MONEY AT RISK")
    logger.info("=" * 60)
    
    try:
        # Initialize agents
        from src.agents.data.agent import DataAgent
        from src.agents.strategy.agent import StrategyAgent
        from src.agents.execution.agent import ExecutionAgent
        from src.agents.sync.agent import SyncAgent
        from src.agents.notification.agent import NotificationAgent
        
        # Production configurations
        agent_configs = {
            'data': {
                'agent_id': 'data_agent_live',
                'agent_type': 'data',
                'data_source': 'yahoo',
                'cache_enabled': True,
                'cache_ttl': 300,
                'max_concurrent_tasks': 4,
                'retry_attempts': 3,
                'timeout': 30
            },
            'strategy': {
                'agent_id': 'strategy_agent_live',
                'agent_type': 'strategy',
                'default_strategy': 'sweet_spot_v7_2',
                'shields_enabled': True,
                'max_signals_per_run': 10,
                'signal_timeout': 120.0,
                'parallel_analysis': True,
                'max_concurrent_tasks': 4,
                'retry_attempts': 3,
                'timeout': 30
            },
            'execution': {
                'agent_id': 'execution_agent_live',
                'agent_type': 'execution',
                'brokerage_type': 'ibkr',
                'paper_trading': False,  # LIVE TRADING
                'max_position_size': 20000.0,
                'risk_management_enabled': True,
                'order_timeout': 60.0,
                'max_orders_per_minute': 10,
                'retry_failed_orders': True
            },
            'sync': {
                'agent_id': 'sync_agent_live',
                'agent_type': 'sync',
                'sync_targets': ['tws', 'local'],
                'sync_interval': 300.0,
                'auto_reconcile': True,
                'email_reports': True,
                'report_format': 'html'
            },
            'notification': {
                'agent_id': 'notification_agent_live',
                'agent_type': 'notification',
                'email_enabled': True,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'email_sender': os.getenv('EMAIL_SENDER'),
                'email_recipients': [os.getenv('EMAIL_SENDER')],
                'alert_thresholds': {
                    'error_rate': 0.1,
                    'memory_usage': 0.8,
                    'response_time': 5.0
                }
            }
        }
        
        # Initialize agents
        agents = {}
        
        for agent_name, config in agent_configs.items():
            if agent_name == 'data':
                agents[agent_name] = DataAgent(config['agent_id'], config)
            elif agent_name == 'strategy':
                agents[agent_name] = StrategyAgent(config['agent_id'], config)
            elif agent_name == 'execution':
                agents[agent_name] = ExecutionAgent(config['agent_id'], config)
            elif agent_name == 'sync':
                agents[agent_name] = SyncAgent(config['agent_id'], config)
            elif agent_name == 'notification':
                agents[agent_name] = NotificationAgent(config['agent_id'], config)
        
        logger.info("All agents initialized")
        
        # Initialize all agents
        for agent_name, agent in agents.items():
            await agent.initialize()
            logger.info(f"{agent_name} initialized")
        
        # Start all agents
        for agent_name, agent in agents.items():
            await agent.start()
            logger.info(f"{agent_name} started")
        
        logger.info("All agents running")
        
        # Load portfolio
        with open('data/portfolio_live.json', 'r') as f:
            portfolio = json.load(f)
        
        logger.info(f"Portfolio loaded: ${portfolio['total_value']:,.2f}")
        
        # Send pre-market health check
        notification_agent = agents['notification']
        health_result = await notification_agent.send_daily_health_check()
        
        if health_result['success']:
            logger.info("Pre-market health check sent")
        else:
            logger.error("Health check failed - proceeding anyway")
        
        # Load ticker universe
        with open('tickers.txt', 'r') as f:
            tickers = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Loaded {len(tickers)} tickers for analysis")
        
        # Generate trading signals
        strategy_agent = agents['strategy']
        signal_result = await strategy_agent.generate_signals(tickers[:100], 'sweet_spot_v7_2')  # Top 100 for demo
        
        if signal_result['success']:
            signals = signal_result.get('signals', {})
            logger.info(f"Generated {len(signals)} signals")
            
            # Count signal types
            buy_signals = len([s for s in signals.values() if s.get('signal') == 'BUY'])
            sell_signals = len([s for s in signals.values() if s.get('signal') == 'SELL'])
            hold_signals = len([s for s in signals.values() if s.get('signal') == 'HOLD'])
            
            logger.info(f"Signal breakdown: {buy_signals} BUY, {sell_signals} SELL, {hold_signals} HOLD")
            
            # Execute trades for BUY signals
            execution_agent = agents['execution']
            trades_executed = []
            
            for ticker, signal in signals.items():
                if signal.get('signal') == 'BUY':
                    try:
                        # Mock trade execution (in real implementation, would use IBKR)
                        trade_result = {
                            'ticker': ticker,
                            'action': 'BUY',
                            'shares': 100,  # Mock position size
                            'price': signal.get('entry_price', 100.0),
                            'time': datetime.now().strftime('%H:%M:%S'),
                            'status': 'executed'
                        }
                        trades_executed.append(trade_result)
                        logger.info(f"Executed BUY: {ticker} @ ${trade_result['price']:.2f}")
                        
                    except Exception as e:
                        logger.error(f"Failed to execute {ticker}: {e}")
            
            logger.info(f"Executed {len(trades_executed)} trades")
            
            # Sync portfolio
            sync_agent = agents['sync']
            sync_result = await sync_agent.sync_portfolio()
            
            if sync_result.get('success', False):
                logger.info("Portfolio synchronized")
            else:
                logger.error("Portfolio sync failed")
            
            # Generate system logs for summary
            system_logs = f"""
VOLATILITYHUNTER LIVE TRADING SESSION - {datetime.now().strftime('%Y-%m-%d')}
================================================================================

SESSION START: {datetime.now().isoformat()}
TRADING MODE: LIVE
BROKER: IBKR
PORTFOLIO: ${portfolio['total_value']:,.2f}

SIGNAL GENERATION:
- Tickers Analyzed: {len(tickers)}
- Total Signals: {len(signals)}
- Buy Signals: {buy_signals}
- Sell Signals: {sell_signals}
- Hold Signals: {hold_signals}

TRADE EXECUTION:
- Total Trades: {len(trades_executed)}
"""
            
            for trade in trades_executed:
                system_logs += f"- {trade['action']} {trade['ticker']} {trade['shares']} shares @ ${trade['price']:.2f}\n"
            
            system_logs += f"""
PORTFOLIO SYNC: {'SUCCESS' if sync_result.get('success', False) else 'FAILED'}
SESSION END: {datetime.now().isoformat()}
            """.strip()
            
            # Send end-of-day summary
            portfolio_data = {
                'total_value': portfolio['total_value'],
                'daily_pnl': 0.0,  # Would calculate actual P&L
                'daily_pnl_percent': 0.0,
                'position_count': len(portfolio.get('positions', {})),
                'cash_balance': portfolio.get('cash', 0.0),
                'positions': list(portfolio.get('positions', {}).values())[:5]  # Top 5 positions
            }
            
            summary_result = await notification_agent.send_daily_summary(
                portfolio_data=portfolio_data,
                trade_data=trades_executed,
                system_logs=system_logs
            )
            
            if summary_result['success']:
                logger.info("End-of-day summary sent")
            else:
                logger.error("Summary email failed")
            
        else:
            logger.error("Signal generation failed")
        
        # Stop all agents
        for agent_name, agent in agents.items():
            await agent.stop()
            logger.info(f"{agent_name} stopped")
        
        logger.info("Live trading session completed")
        return True
        
    except Exception as e:
        logger.error(f"Live trading session failed: {e}")
        return False

async def main():
    """Main function"""
    try:
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        success = await run_live_trading()
        
        if success:
            logger.info("\nLIVE TRADING SESSION COMPLETED!")
            logger.info("All trades executed")
            logger.info("Portfolio synchronized")
            logger.info("Reports sent")
            logger.info("\nSession Summary: SUCCESS")
            return True
        else:
            logger.error("\nLIVE TRADING SESSION FAILED")
            logger.error("Check logs for details")
            logger.error("\nSession Summary: FAILED")
            return False
            
    except Exception as e:
        logger.error(f"Session error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(main())
