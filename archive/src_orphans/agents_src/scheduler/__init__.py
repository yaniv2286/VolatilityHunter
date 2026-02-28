"""
Scheduler Agent Configuration
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class SchedulerAgentConfig:
    """Configuration for Scheduler Agent"""
    
    # Basic agent configuration
    agent_id: str
    agent_type: str = "scheduler"
    enabled: bool = True
    log_level: str = "INFO"
    retry_attempts: int = 3
    timeout: int = 30
    max_concurrent_tasks: int = 5
    health_check_interval: int = 60
    
    # Scheduler-specific configuration
    check_interval: int = 60  # seconds between task checks
    task_timeout: int = 300   # 5 minutes before considering task failed
    max_cpu_usage: float = 80.0  # CPU usage threshold for alerts
    max_memory_usage: float = 80.0  # Memory usage threshold for alerts
    alert_cooldown: int = 300   # seconds between similar alerts
    auto_restart_enabled: bool = True  # Auto-restart failed tasks
    integrity_check_interval: int = 3600  # 1 hour between integrity checks
    
    # Monitored tasks configuration
    monitored_tasks: List[str] = None
    task_scripts: Dict[str, str] = None
    
    # Alert configuration
    alert_enabled: bool = True
    alert_channels: List[str] = None  # ['log', 'email']
    alert_recipients: List[str] = None
    
    # Performance configuration
    performance_tracking: bool = True
    performance_retention_days: int = 7
    
    def __post_init__(self):
        """Initialize default values"""
        if self.monitored_tasks is None:
            self.monitored_tasks = ["Auto_TWS_Manager", "Auto_Trading_System"]
        
        if self.task_scripts is None:
            self.task_scripts = {
                "Auto_TWS_Manager": "scripts/DAILY_ROUTINE/run_auto_tws_manager.bat",
                "Auto_Trading_System": "scripts/DAILY_ROUTINE/run_trading.bat"
            }
        
        if self.alert_channels is None:
            self.alert_channels = ["log"]
        
        if self.alert_recipients is None:
            self.alert_recipients = []

# For backward compatibility
AgentConfig = SchedulerAgentConfig
