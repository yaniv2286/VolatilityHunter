"""
Agent Configuration - Configuration management for agents
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class AgentConfig:
    """Base agent configuration"""
    agent_id: str
    agent_type: str
    enabled: bool = True
    log_level: str = "INFO"
    retry_attempts: int = 3
    timeout: float = 30.0
    max_concurrent_tasks: int = 5
    health_check_interval: float = 60.0

@dataclass
class DataAgentConfig(AgentConfig):
    """Data agent specific configuration"""
    data_source: str = "tiingo"
    cache_enabled: bool = True
    cache_ttl: int = 3600
    max_cache_size: int = 1000
    data_validation_enabled: bool = True
    parallel_loading: bool = True
    batch_size: int = 50

@dataclass
class StrategyAgentConfig(AgentConfig):
    """Strategy agent specific configuration"""
    default_strategy: str = "sweet_spot_v7_2"
    shields_enabled: bool = True
    max_signals_per_run: int = 100
    signal_timeout: float = 120.0
    parallel_analysis: bool = True
    technical_indicators: list = None
    
    def __post_init__(self):
        if self.technical_indicators is None:
            self.technical_indicators = ["sma", "rsi", "macd", "bollinger"]

@dataclass
class ExecutionAgentConfig(AgentConfig):
    """Execution agent specific configuration"""
    brokerage_type: str = "ibkr"
    paper_trading: bool = False
    max_position_size: float = 10000.0
    risk_management_enabled: bool = True
    order_timeout: float = 60.0
    max_orders_per_minute: int = 10
    retry_failed_orders: bool = True

@dataclass
class SyncAgentConfig(AgentConfig):
    """Sync agent specific configuration"""
    sync_targets: list = None
    sync_interval: float = 300.0
    auto_reconcile: bool = True
    email_reports: bool = True
    report_format: str = "html"
    
    def __post_init__(self):
        if self.sync_targets is None:
            self.sync_targets = ["tws", "local"]

@dataclass
class NotificationAgentConfig(AgentConfig):
    """Notification agent specific configuration"""
    email_enabled: bool = True
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    email_sender: str = ""
    email_recipients: list = None
    alert_thresholds: dict = None
    
    def __post_init__(self):
        if self.email_recipients is None:
            self.email_recipients = []
        if self.alert_thresholds is None:
            self.alert_thresholds = {"error_rate": 0.1, "response_time": 5.0, "memory_usage": 0.8}

@dataclass
class TestingAgentConfig(AgentConfig):
    """Testing agent specific configuration"""
    backtest_enabled: bool = True
    dry_run_enabled: bool = True
    integration_tests_enabled: bool = True
    performance_benchmarks_enabled: bool = True
    test_data_path: str = "data/test/"
    backtest_lookback_days: int = 252
    dry_run_initial_capital: float = 100000
    benchmark_strategies: list = None
    
    def __post_init__(self):
        if self.benchmark_strategies is None:
            self.benchmark_strategies = ["sweet_spot_v7_2"]

class ConfigManager:
    """Configuration manager implementation"""
    
    def __init__(self, config_dir: str = "config"):
        self.logger = logging.getLogger("config_manager")
        self.config_dir = config_dir
        self.configs: Dict[str, Dict[str, Any]] = {}
        
    def load_config(self, config_path: str = None) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if config_path is None:
                config_path = os.path.join(self.config_dir, "agents.json")
                
            if not os.path.exists(config_path):
                self.logger.warning(f"Config file not found: {config_path}")
                return {}
                
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            self.configs.update(config)
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return {}
            
    def get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """Get agent configuration"""
        return self.configs.get(agent_id, {})
        
    def validate_config(self) -> bool:
        """Validate configuration"""
        try:
            # Basic validation
            if not self.configs:
                return False
                
            return True
            
        except Exception:
            return False
            
    def create_directories(self) -> bool:
        """Create required directories"""
        try:
            directories = [
                "data",
                "data/test",
                "logs",
                "temp"
            ]
            
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating directories: {e}")
            return False
