"""
System Configuration - System-wide configuration management
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class SystemConfig:
    """System-wide configuration"""
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    data_dir: str = "data"
    config_dir: str = "config"
    log_dir: str = "logs"
    temp_dir: str = "temp"
    
@dataclass
class OrchestratorConfig:
    """Orchestrator configuration"""
    health_check_interval: float = 60.0
    max_concurrent_workflows: int = 5
    workflow_timeout: float = 600.0
    agent_timeout: float = 30.0
    retry_attempts: int = 3
    shutdown_timeout: float = 30.0
    
@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    console_enabled: bool = True
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    rotation_when: str = "midnight"
    
@dataclass
class SecurityConfig:
    """Security configuration"""
    api_key_encryption: bool = True
    data_encryption: bool = False
    audit_logging: bool = True
    session_timeout: float = 3600.0  # 1 hour
    
@dataclass
class PerformanceConfig:
    """Performance configuration"""
    max_memory_usage: float = 0.8  # 80% of available memory
    max_cpu_usage: float = 0.9     # 90% of available CPU
    cache_size_limit: int = 1000   # MB
    connection_pool_size: int = 10
    async_task_timeout: float = 300.0

class SystemConfigManager:
    """System configuration manager"""
    
    def __init__(self):
        self.logger = logging.getLogger("system_config_manager")
        self.config: Dict[str, Any] = {}
        
    def load_system_config(self, config_path: str = None) -> Dict[str, Any]:
        """Load system configuration"""
        try:
            if config_path is None:
                config_path = "config/system.json"
                
            # Load base configuration
            base_config = asdict(SystemConfig())
            
            # Load environment-specific overrides
            env_config = self._load_environment_config()
            
            # Load file-based configuration
            file_config = self._load_file_config(config_path)
            
            # Merge configurations
            self.config = self._merge_configs(base_config, env_config, file_config)
            
            self.logger.info("System configuration loaded successfully")
            return self.config
            
        except Exception as e:
            self.logger.error(f"Error loading system config: {e}")
            return asdict(SystemConfig())
            
    def save_system_config(self, config: Dict[str, Any], config_path: str = None) -> bool:
        """Save system configuration"""
        try:
            if config_path is None:
                config_path = "config/system.json"
                
            import json
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            self.config = config
            self.logger.info(f"System configuration saved to {config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving system config: {e}")
            return False
            
    def get_orchestrator_config(self) -> OrchestratorConfig:
        """Get orchestrator configuration"""
        try:
            config_data = self.config.get("orchestrator", {})
            return OrchestratorConfig(**config_data)
        except Exception as e:
            self.logger.error(f"Error getting orchestrator config: {e}")
            return OrchestratorConfig()
            
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration"""
        try:
            config_data = self.config.get("logging", {})
            return LoggingConfig(**config_data)
        except Exception as e:
            self.logger.error(f"Error getting logging config: {e}")
            return LoggingConfig()
            
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration"""
        try:
            config_data = self.config.get("security", {})
            return SecurityConfig(**config_data)
        except Exception as e:
            self.logger.error(f"Error getting security config: {e}")
            return SecurityConfig()
            
    def get_performance_config(self) -> PerformanceConfig:
        """Get performance configuration"""
        try:
            config_data = self.config.get("performance", {})
            return PerformanceConfig(**config_data)
        except Exception as e:
            self.logger.error(f"Error getting performance config: {e}")
            return PerformanceConfig()
            
    def _load_environment_config(self) -> Dict[str, Any]:
        """Load environment-specific configuration"""
        try:
            env_config = {
                "environment": os.getenv("VH_ENVIRONMENT", "development"),
                "debug": os.getenv("VH_DEBUG", "false").lower() == "true",
                "log_level": os.getenv("VH_LOG_LEVEL", "INFO"),
                "data_dir": os.getenv("VH_DATA_DIR", "data"),
                "config_dir": os.getenv("VH_CONFIG_DIR", "config"),
                "log_dir": os.getenv("VH_LOG_DIR", "logs"),
                "temp_dir": os.getenv("VH_TEMP_DIR", "temp")
            }
            
            return env_config
            
        except Exception as e:
            self.logger.error(f"Error loading environment config: {e}")
            return {}
            
    def _load_file_config(self, config_path: str) -> Dict[str, Any]:
        """Load file-based configuration"""
        try:
            import json
            
            if not os.path.exists(config_path):
                return {}
                
            with open(config_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Error loading file config from {config_path}: {e}")
            return {}
            
    def _merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configuration dictionaries"""
        try:
            merged = {}
            
            for config in configs:
                if config:
                    merged.update(config)
                    
            return merged
            
        except Exception as e:
            self.logger.error(f"Error merging configs: {e}")
            return {}
            
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        try:
            keys = key.split('.')
            current = self.config
            
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return default
                    
            return current
            
        except Exception as e:
            self.logger.error(f"Error getting config value {key}: {e}")
            return default
            
    def set_config_value(self, key: str, value: Any) -> bool:
        """Set configuration value by key"""
        try:
            keys = key.split('.')
            current = self.config
            
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
                
            current[keys[-1]] = value
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting config value {key}: {e}")
            return False
            
    def validate_config(self) -> bool:
        """Validate system configuration"""
        try:
            # Validate required directories
            required_dirs = ["data_dir", "config_dir", "log_dir", "temp_dir"]
            for dir_key in required_dirs:
                dir_path = self.config.get(dir_key)
                if not dir_path:
                    self.logger.error(f"Missing required directory config: {dir_key}")
                    return False
                    
            # Validate log level
            log_level = self.config.get("log_level", "INFO")
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if log_level not in valid_levels:
                self.logger.error(f"Invalid log level: {log_level}")
                return False
                
            # Validate environment
            environment = self.config.get("environment", "development")
            valid_envs = ["development", "testing", "staging", "production"]
            if environment not in valid_envs:
                self.logger.error(f"Invalid environment: {environment}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating config: {e}")
            return False
            
    def create_directories(self) -> bool:
        """Create required directories"""
        try:
            directories = [
                self.config.get("data_dir", "data"),
                self.config.get("config_dir", "config"),
                self.config.get("log_dir", "logs"),
                self.config.get("temp_dir", "temp")
            ]
            
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
                self.logger.debug(f"Created directory: {directory}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating directories: {e}")
            return False
