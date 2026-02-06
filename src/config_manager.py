"""
VolatilityHunter Configuration System
Centralized configuration for simulation and production modes
"""

import os
from enum import Enum
from typing import Dict, Any
from dataclasses import dataclass

class TradingMode(Enum):
    SIMULATION = "simulation"
    PRODUCTION = "production"

class DataSourceType(Enum):
    TIINGO = "tiingo"
    YAHOO = "yahoo"

@dataclass
class TradingConfig:
    """Main trading configuration"""
    mode: TradingMode = TradingMode.SIMULATION
    data_source: DataSourceType = DataSourceType.TIINGO
    initial_capital: float = 100000.0
    max_positions: int = 10
    position_size: float = 5000.0
    stop_loss_pct: float = 0.10
    take_profit_pct: float = 0.20
    
    # Pre-trade checklist settings
    earnings_check_enabled: bool = True
    volume_check_enabled: bool = True
    pattern_check_enabled: bool = True
    friday_rule_enabled: bool = True
    
    # Email settings
    email_enabled: bool = True
    email_recipient: str = "lugassy.ai@gmail.com"
    
    # Backtesting settings
    backtest_enabled: bool = False
    backtest_start_date: str = None
    backtest_end_date: str = None

class ConfigurationManager:
    """Central configuration management"""
    
    def __init__(self):
        self.config = TradingConfig()
        self._load_environment_variables()
        self._validate_configuration()
    
    def _load_environment_variables(self):
        """Load configuration from environment variables"""
        # Trading mode
        mode = os.getenv('VH_MODE', 'simulation').lower()
        if mode in ['production', 'prod']:
            self.config.mode = TradingMode.PRODUCTION
        else:
            self.config.mode = TradingMode.SIMULATION
        
        # Data source
        data_source = os.getenv('VH_DATA_SOURCE', 'tiingo').lower()
        if data_source in ['yahoo', 'yfinance']:
            self.config.data_source = DataSourceType.YAHOO
        else:
            self.config.data_source = DataSourceType.TIINGO
        
        # Portfolio settings
        self.config.initial_capital = float(os.getenv('VH_INITIAL_CAPITAL', '100000'))
        self.config.max_positions = int(os.getenv('VH_MAX_POSITIONS', '10'))
        self.config.position_size = float(os.getenv('VH_POSITION_SIZE', '5000'))
        self.config.stop_loss_pct = float(os.getenv('VH_STOP_LOSS_PCT', '0.10'))
        self.config.take_profit_pct = float(os.getenv('VH_TAKE_PROFIT_PCT', '0.20'))
        
        # Checklist settings
        self.config.earnings_check_enabled = os.getenv('VH_EARNINGS_CHECK', 'true').lower() == 'true'
        self.config.volume_check_enabled = os.getenv('VH_VOLUME_CHECK', 'true').lower() == 'true'
        self.config.pattern_check_enabled = os.getenv('VH_PATTERN_CHECK', 'true').lower() == 'true'
        self.config.friday_rule_enabled = os.getenv('VH_FRIDAY_RULE', 'true').lower() == 'true'
        
        # Email settings
        self.config.email_enabled = os.getenv('VH_EMAIL_ENABLED', 'true').lower() == 'true'
        self.config.email_recipient = os.getenv('VH_EMAIL_RECIPIENT', 'lugassy.ai@gmail.com')
        
        # Backtesting settings
        self.config.backtest_enabled = os.getenv('VH_BACKTEST', 'false').lower() == 'true'
        self.config.backtest_start_date = os.getenv('VH_BACKTEST_START', None)
        self.config.backtest_end_date = os.getenv('VH_BACKTEST_END', None)
    
    def _validate_configuration(self):
        """Validate configuration settings"""
        if self.config.position_size > self.config.initial_capital:
            raise ValueError("Position size cannot exceed initial capital")
        
        if self.config.max_positions < 1 or self.config.max_positions > 20:
            raise ValueError("Max positions must be between 1 and 20")
        
        if self.config.stop_loss_pct < 0 or self.config.stop_loss_pct > 0.5:
            raise ValueError("Stop loss percentage must be between 0 and 50%")
        
        if self.config.take_profit_pct < 0 or self.config.take_profit_pct > 1.0:
            raise ValueError("Take profit percentage must be between 0 and 100%")
    
    def is_simulation_mode(self) -> bool:
        """Check if running in simulation mode"""
        return self.config.mode == TradingMode.SIMULATION
    
    def is_production_mode(self) -> bool:
        """Check if running in production mode"""
        return self.config.mode == TradingMode.PRODUCTION
    
    def get_pre_trade_checklist_config(self) -> Dict[str, bool]:
        """Get pre-trade checklist configuration"""
        return {
            'earnings_check': self.config.earnings_check_enabled if self.is_production_mode() else True,
            'volume_check': self.config.volume_check_enabled,
            'pattern_check': self.config.pattern_check_enabled,
            'friday_rule': self.config.friday_rule_enabled
        }
    
    def get_strategy_config(self) -> Dict[str, Any]:
        """Get strategy configuration"""
        return {
            'mode': self.config.mode.value,
            'data_source': self.config.data_source.value,
            'checklist': self.get_pre_trade_checklist_config(),
            'portfolio': {
                'initial_capital': self.config.initial_capital,
                'max_positions': self.config.max_positions,
                'position_size': self.config.position_size,
                'stop_loss_pct': self.config.stop_loss_pct,
                'take_profit_pct': self.config.take_profit_pct
            }
        }
    
    def print_configuration(self):
        """Print current configuration"""
        print("=" * 60)
        print("VOLATILITYHUNTER CONFIGURATION")
        print("=" * 60)
        print(f"Mode: {self.config.mode.value.upper()}")
        print(f"Data Source: {self.config.data_source.value.upper()}")
        
        # Show smart data source info
        try:
            from src.smart_data_loader_factory import get_smart_data_loader
            smart_loader = get_smart_data_loader()
            source_info = smart_loader.get_data_source_info()
            print(f"Active Source: {source_info['source']}")
            print(f"Reason: {source_info['reason']}")
            print(f"Tiingo Key Available: {'✅ YES' if source_info['key_available'] else '❌ NO'}")
        except Exception as e:
            print(f"Data Source Info: Unable to load ({e})")
        
        print(f"Initial Capital: ${self.config.initial_capital:,.2f}")
        print(f"Max Positions: {self.config.max_positions}")
        print(f"Position Size: ${self.config.position_size:,.2f}")
        print(f"Stop Loss: {self.config.stop_loss_pct*100:.1f}%")
        print(f"Take Profit: {self.config.take_profit_pct*100:.1f}%")
        print("")
        print("PRE-TRADE CHECKLIST:")
        checklist = self.get_pre_trade_checklist_config()
        for item, enabled in checklist.items():
            status = "✅ ENABLED" if enabled else "❌ DISABLED"
            print(f"  {item.replace('_', ' ').title()}: {status}")
        print("")
        print(f"Email Notifications: {'✅ ENABLED' if self.config.email_enabled else '❌ DISABLED'}")
        print(f"Backtesting: {'✅ ENABLED' if self.config.backtest_enabled else '❌ DISABLED'}")
        print("=" * 60)

# Global configuration instance
config_manager = ConfigurationManager()

def get_config() -> ConfigurationManager:
    """Get global configuration manager"""
    return config_manager

def is_simulation() -> bool:
    """Check if running in simulation mode"""
    return config_manager.is_simulation_mode()

def is_production() -> bool:
    """Check if running in production mode"""
    return config_manager.is_production_mode()
