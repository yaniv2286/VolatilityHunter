"""
Default Workflows - Default workflow definitions for VolatilityHunter
"""

from .workflow_manager import Workflow, WorkflowStep
from ..interfaces.agent_interface import MessageType

def get_default_workflows() -> dict:
    """Get default workflow definitions"""
    
    workflows = {}
    
    # Daily Trading Workflow
    daily_trading = Workflow(
        name="daily_trading",
        description="Execute complete daily trading workflow",
        steps=[
            WorkflowStep(
                name="functional_health_check",
                agent_id="testing_agent",
                message_type=MessageType.TEST_REQUEST,
                data={
                    "test_type": "functional_health_check",
                    "verify_trading_flow": True,
                    "check_portfolio_sync": True,
                    "execute_real_trade": True
                },
                timeout=300.0  # 5 minutes for complete health check
            ),
            WorkflowStep(
                name="load_market_data",
                agent_id="data_agent",
                message_type=MessageType.DATA_REQUEST,
                data={
                    "tickers": "universe",
                    "date_range": "latest",
                    "data_type": "price"
                },
                timeout=60.0
            ),
            WorkflowStep(
                name="validate_data_quality",
                agent_id="data_agent",
                message_type=MessageType.HEALTH_CHECK,
                data={
                    "check_type": "data_quality",
                    "components": ["data_validation", "cache_status"]
                },
                timeout=30.0
            ),
            WorkflowStep(
                name="generate_trading_signals",
                agent_id="strategy_agent",
                message_type=MessageType.SIGNAL_REQUEST,
                data={
                    "strategy": "sweet_spot_v7_2",
                    "parameters": {
                        "scan_universe": True,
                        "apply_shields": True,
                        "max_signals": 50
                    }
                },
                timeout=120.0
            ),
            WorkflowStep(
                name="execute_trades",
                agent_id="execution_agent",
                message_type=MessageType.EXECUTION_REQUEST,
                data={
                    "execution_mode": "live",
                    "risk_management": True,
                    "position_sizing": "auto"
                },
                timeout=180.0
            ),
            WorkflowStep(
                name="sync_portfolio",
                agent_id="sync_agent",
                message_type=MessageType.SYNC_REQUEST,
                data={
                    "sync_type": "portfolio",
                    "target": "tws",
                    "force_sync": True
                },
                timeout=60.0
            ),
            WorkflowStep(
                name="generate_report",
                agent_id="notification_agent",
                message_type=MessageType.NOTIFICATION_REQUEST,
                data={
                    "notification_type": "email",
                    "report_type": "daily",
                    "include_performance": True
                },
                timeout=30.0
            )
        ],
        parallel=False,
        timeout=600.0
    )
    
    workflows["daily_trading"] = daily_trading
    
    # Backtesting Workflow
    backtesting = Workflow(
        name="backtesting",
        description="Execute comprehensive backtesting workflow",
        steps=[
            WorkflowStep(
                name="load_historical_data",
                agent_id="data_agent",
                message_type=MessageType.DATA_REQUEST,
                data={
                    "tickers": "universe",
                    "date_range": "historical",
                    "data_type": "price",
                    "lookback_days": 9500,  # 26+ years of data
                    "use_vector_db": True,   # Enable ChromaDB acceleration
                    "vector_acceleration": True
                },
                timeout=300.0
            ),
            WorkflowStep(
                name="run_backtest",
                agent_id="testing_agent",
                message_type=MessageType.TEST_REQUEST,
                data={
                    "test_type": "backtest",
                    "strategy": "sweet_spot_v7_2",
                    "parameters": {
                        "initial_capital": 100000,
                        "max_positions": 10,
                        "rebalance_frequency": "daily",
                        "use_vector_db": True,
                        "comprehensive_mode": True,
                        "enable_performance_tracking": True,
                        "risk_management": True,
                        "benchmark_comparison": True
                    }
                },
                timeout=1800.0  # 30 minutes for comprehensive backtest
            ),
            WorkflowStep(
                name="analyze_results",
                agent_id="testing_agent",
                message_type=MessageType.TEST_REQUEST,
                data={
                    "test_type": "performance_analysis",
                    "metrics": ["sharpe_ratio", "max_drawdown", "win_rate", "profit_factor"]
                },
                timeout=60.0
            ),
            WorkflowStep(
                name="generate_backtest_report",
                agent_id="notification_agent",
                message_type=MessageType.NOTIFICATION_REQUEST,
                data={
                    "notification_type": "email",
                    "report_type": "backtest",
                    "include_charts": True
                },
                timeout=30.0
            )
        ],
        parallel=False,
        timeout=600.0
    )
    
    workflows["backtesting"] = backtesting
    
    # System Health Check Workflow
    health_check = Workflow(
        name="health_check",
        description="Comprehensive system health check",
        steps=[
            WorkflowStep(
                name="check_data_agent",
                agent_id="data_agent",
                message_type=MessageType.HEALTH_CHECK,
                data={
                    "check_type": "full",
                    "components": ["data_sources", "cache", "validation"]
                },
                timeout=30.0
            ),
            WorkflowStep(
                name="check_strategy_agent",
                agent_id="strategy_agent",
                message_type=MessageType.HEALTH_CHECK,
                data={
                    "check_type": "full",
                    "components": ["strategy_logic", "signal_generation", "shields"]
                },
                timeout=30.0
            ),
            WorkflowStep(
                name="check_execution_agent",
                agent_id="execution_agent",
                message_type=MessageType.HEALTH_CHECK,
                data={
                    "check_type": "full",
                    "components": ["ibkr_connection", "order_management", "risk_management"]
                },
                timeout=30.0
            ),
            WorkflowStep(
                name="check_sync_agent",
                agent_id="sync_agent",
                message_type=MessageType.HEALTH_CHECK,
                data={
                    "check_type": "full",
                    "components": ["tws_connection", "portfolio_sync", "reconciliation"]
                },
                timeout=30.0
            ),
            WorkflowStep(
                name="check_notification_agent",
                agent_id="notification_agent",
                message_type=MessageType.HEALTH_CHECK,
                data={
                    "check_type": "full",
                    "components": ["email_system", "alerts", "logging"]
                },
                timeout=30.0
            ),
            WorkflowStep(
                name="check_testing_agent",
                agent_id="testing_agent",
                message_type=MessageType.HEALTH_CHECK,
                data={
                    "check_type": "full",
                    "components": ["test_framework", "backtest_engine", "simulation"]
                },
                timeout=30.0
            )
        ],
        parallel=True,
        timeout=120.0
    )
    
    workflows["health_check"] = health_check
    
    # Integration Testing Workflow
    integration_test = Workflow(
        name="integration_test",
        description="Comprehensive integration testing",
        steps=[
            WorkflowStep(
                name="test_data_flow",
                agent_id="testing_agent",
                message_type=MessageType.TEST_REQUEST,
                data={
                    "test_type": "integration",
                    "component": "data_flow",
                    "test_scenarios": ["data_loading", "data_validation", "cache_performance"]
                },
                timeout=120.0
            ),
            WorkflowStep(
                name="test_strategy_execution",
                agent_id="testing_agent",
                message_type=MessageType.TEST_REQUEST,
                data={
                    "test_type": "integration",
                    "component": "strategy_execution",
                    "test_scenarios": ["signal_generation", "shield_validation", "performance"]
                },
                timeout=120.0
            ),
            WorkflowStep(
                name="test_trade_execution",
                agent_id="testing_agent",
                message_type=MessageType.TEST_REQUEST,
                data={
                    "test_type": "integration",
                    "component": "trade_execution",
                    "test_scenarios": ["order_placement", "execution_tracking", "risk_management"]
                },
                timeout=120.0
            ),
            WorkflowStep(
                name="test_portfolio_sync",
                agent_id="testing_agent",
                message_type=MessageType.TEST_REQUEST,
                data={
                    "test_type": "integration",
                    "component": "portfolio_sync",
                    "test_scenarios": ["tws_sync", "reconciliation", "report_generation"]
                },
                timeout=120.0
            ),
            WorkflowStep(
                name="test_notifications",
                agent_id="testing_agent",
                message_type=MessageType.TEST_REQUEST,
                data={
                    "test_type": "integration",
                    "component": "notifications",
                    "test_scenarios": ["email_delivery", "alert_system", "log_monitoring"]
                },
                timeout=60.0
            )
        ],
        parallel=False,
        timeout=600.0
    )
    
    workflows["integration_test"] = integration_test
    
    # Dry Run Simulation Workflow
    dry_run = Workflow(
        name="dry_run",
        description="Execute dry run simulation without real trades",
        steps=[
            WorkflowStep(
                name="load_simulation_data",
                agent_id="data_agent",
                message_type=MessageType.DATA_REQUEST,
                data={
                    "tickers": "universe",
                    "date_range": "latest",
                    "data_type": "price"
                },
                timeout=60.0
            ),
            WorkflowStep(
                name="simulate_signals",
                agent_id="strategy_agent",
                message_type=MessageType.SIGNAL_REQUEST,
                data={
                    "strategy": "sweet_spot_v7_2",
                    "simulation_mode": True,
                    "parameters": {
                        "dry_run": True,
                        "paper_trading": True
                    }
                },
                timeout=120.0
            ),
            WorkflowStep(
                name="simulate_execution",
                agent_id="testing_agent",
                message_type=MessageType.TEST_REQUEST,
                data={
                    "test_type": "dry_run",
                    "simulation_type": "trade_execution",
                    "parameters": {
                        "paper_trading": True,
                        "real_time_simulation": True
                    }
                },
                timeout=180.0
            ),
            WorkflowStep(
                name="generate_simulation_report",
                agent_id="notification_agent",
                message_type=MessageType.NOTIFICATION_REQUEST,
                data={
                    "notification_type": "email",
                    "report_type": "dry_run",
                    "include_simulation_results": True
                },
                timeout=30.0
            )
        ],
        parallel=False,
        timeout=480.0
    )
    
    workflows["dry_run"] = dry_run
    
    return workflows
