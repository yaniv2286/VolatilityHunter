"""
Strategy Factory for VolatilityHunter
Provides factory pattern for selecting between v7.2 and Sweet Spot strategies
"""

import json
import os
from typing import Dict, Any, Optional
from src.notifications import log_info, log_warning, log_error

class StrategyFactory:
    """
    Factory for creating and managing trading strategies
    Supports v7.2 Hybrid Strategy and Sweet Spot Enhanced Strategy
    """
    
    def __init__(self, config_file: str = 'config.json'):
        """
        Initialize strategy factory
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.config = self._load_config()
        self.strategy_selection = self.config.get('STRATEGY_SELECTION', 'v7_2')
        self.sweet_spot_config = self.config.get('SWEET_SPOT', {})
        
        log_info(f"[STRATEGY_FACTORY] Initialized with strategy: {self.strategy_selection}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                log_warning(f"[STRATEGY_FACTORY] Config file {self.config_file} not found, using defaults")
                return self._get_default_config()
        except Exception as e:
            log_error(f"[STRATEGY_FACTORY] Error loading config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'STRATEGY_SELECTION': 'v7_2',
            'SWEET_SPOT': {
                'enable_patterns': True,
                'enable_spread_monitoring': True,
                'enable_time_filters': True,
                'pattern_weight': 0.3,
                'min_enhanced_score': 0.6
            }
        }
    
    def create_strategy(self, brokerage_interface=None):
        """
        Create strategy instance based on configuration
        
        Args:
            brokerage_interface: IBKR interface for spread monitoring
            
        Returns:
            Strategy instance
        """
        try:
            if self.strategy_selection == 'sweet_spot':
                log_info("[STRATEGY_FACTORY] Creating Sweet Spot Enhanced Strategy")
                return self._create_sweet_spot_strategy(brokerage_interface)
            elif self.strategy_selection == 'v7_2':
                log_info("[STRATEGY_FACTORY] Creating v7.2 Hybrid Strategy")
                return self._create_v7_2_strategy()
            else:
                log_warning(f"[STRATEGY_FACTORY] Unknown strategy {self.strategy_selection}, falling back to v7_2")
                return self._create_v7_2_strategy()
                
        except Exception as e:
            log_error(f"[STRATEGY_FACTORY] Error creating strategy: {e}")
            log_info("[STRATEGY_FACTORY] Falling back to v7.2 strategy")
            return self._create_v7_2_strategy()
    
    def _create_sweet_spot_strategy(self, brokerage_interface=None):
        """Create Sweet Spot Enhanced Strategy"""
        try:
            from src.sweet_spot_strategy import SweetSpotStrategy
            
            strategy = SweetSpotStrategy(
                config=self.sweet_spot_config,
                brokerage_interface=brokerage_interface
            )
            
            log_info("[STRATEGY_FACTORY] Sweet Spot strategy created successfully")
            return strategy
            
        except ImportError as e:
            log_error(f"[STRATEGY_FACTORY] Sweet Spot strategy not available: {e}")
            log_info("[STRATEGY_FACTORY] Falling back to v7.2 strategy")
            return self._create_v7_2_strategy()
        except Exception as e:
            log_error(f"[STRATEGY_FACTORY] Error creating Sweet Spot strategy: {e}")
            return self._create_v7_2_strategy()
    
    def _create_v7_2_strategy(self):
        """Create v7.2 Hybrid Strategy (wrapper for backward compatibility)"""
        try:
            # Return a wrapper that provides the same interface as SweetSpotStrategy
            # but uses v7.2 functions internally
            return V7_2StrategyWrapper()
            
        except Exception as e:
            log_error(f"[STRATEGY_FACTORY] Error creating v7.2 strategy wrapper: {e}")
            raise
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Get information about current strategy selection
        
        Returns:
            Strategy information dictionary
        """
        return {
            'selected_strategy': self.strategy_selection,
            'sweet_spot_enabled': self.strategy_selection == 'sweet_spot',
            'sweet_spot_config': self.sweet_spot_config,
            'available_strategies': ['v7_2', 'sweet_spot']
        }
    
    def switch_strategy(self, new_strategy: str) -> bool:
        """
        Switch to a different strategy
        
        Args:
            new_strategy: New strategy to switch to ('v7_2' or 'sweet_spot')
            
        Returns:
            True if switch successful, False otherwise
        """
        try:
            if new_strategy in ['v7_2', 'sweet_spot']:
                old_strategy = self.strategy_selection
                self.strategy_selection = new_strategy
                
                # Update config file
                self.config['STRATEGY_SELECTION'] = new_strategy
                self._save_config()
                
                log_info(f"[STRATEGY_FACTORY] Switched from {old_strategy} to {new_strategy}")
                return True
            else:
                log_error(f"[STRATEGY_FACTORY] Invalid strategy: {new_strategy}")
                return False
                
        except Exception as e:
            log_error(f"[STRATEGY_FACTORY] Error switching strategy: {e}")
            return False
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            log_info(f"[STRATEGY_FACTORY] Configuration saved to {self.config_file}")
        except Exception as e:
            log_error(f"[STRATEGY_FACTORY] Error saving config: {e}")

class V7_2StrategyWrapper:
    """
    Wrapper for v7.2 strategy to provide consistent interface with SweetSpotStrategy
    """
    
    def __init__(self):
        """Initialize v7.2 strategy wrapper"""
        self.config = {}
        log_info("[V7_2_WRAPPER] v7.2 Hybrid Strategy wrapper initialized")
    
    def analyze_stock(self, ticker: str, df, portfolio_data: Dict = None) -> Dict[str, Any]:
        """
        Analyze stock using v7.2 strategy
        
        Args:
            ticker: Stock symbol
            df: DataFrame with OHLCV data
            portfolio_data: Current portfolio state
            
        Returns:
            Analysis results
        """
        try:
            from src.strategy_v7_2 import analyze_stock_v7_2
            return analyze_stock_v7_2(ticker, df, portfolio_data)
        except Exception as e:
            log_error(f"[V7_2_WRAPPER] Error in stock analysis: {e}")
            return {'should_enter': False, 'score': 0.0, 'error': str(e)}
    
    def check_exit_conditions(self, ticker: str, df, position: Dict) -> Dict[str, Any]:
        """
        Check exit conditions using v7.2 strategy
        
        Args:
            ticker: Stock symbol
            df: DataFrame with OHLCV data
            position: Current position data
            
        Returns:
            Exit analysis results
        """
        try:
            from src.strategy_v7_2 import check_exit_conditions_v7_2
            return check_exit_conditions_v7_2(ticker, df, position)
        except Exception as e:
            log_error(f"[V7_2_WRAPPER] Error in exit analysis: {e}")
            return {'should_exit': False, 'error': str(e)}

# Global factory instance
_strategy_factory = None

def get_strategy_factory(config_file: str = 'config.json') -> StrategyFactory:
    """
    Get global strategy factory instance
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        StrategyFactory instance
    """
    global _strategy_factory
    if _strategy_factory is None:
        _strategy_factory = StrategyFactory(config_file)
    return _strategy_factory

def create_trading_strategy(brokerage_interface=None, config_file: str = 'config.json'):
    """
    Convenience function to create trading strategy
    
    Args:
        brokerage_interface: IBKR interface for spread monitoring
        config_file: Path to configuration file
        
    Returns:
        Strategy instance
    """
    factory = get_strategy_factory(config_file)
    return factory.create_strategy(brokerage_interface)

def get_current_strategy_info() -> Dict[str, Any]:
    """
    Get information about current strategy selection
    
    Returns:
        Strategy information dictionary
    """
    factory = get_strategy_factory()
    return factory.get_strategy_info()
