"""
Scheduler Agent - Monitor and maintain Windows Task Scheduler scripts
"""

import asyncio
import logging
import subprocess
import psutil
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import time

from src.interfaces.agent_interface import AgentInterface, AgentStatus, MessageType, HealthStatus
from src.config.agent_config import AgentConfig
from src.utils.message_safety import RateLimiter
from src.utils.error_handler import ErrorHandler, ErrorSeverity

@dataclass
class TaskStatus:
    """Task status information"""
    task_name: str
    is_running: bool
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    status: str = "unknown"
    exit_code: Optional[int] = None
    process_id: Optional[int] = None
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    uptime: float = 0.0
    last_check: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class ScriptIntegrity:
    """Script integrity check result"""
    script_path: str
    exists: bool
    readable: bool
    executable: bool
    size_bytes: int
    last_modified: str
    checksum: Optional[str] = None
    integrity_status: str = "unknown"
    errors: List[str] = field(default_factory=list)
    last_check: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class SchedulerAlert:
    """Scheduler alert definition"""
    alert_id: str
    alert_type: str  # task_failure, script_integrity, performance, system
    severity: str  # low, medium, high, critical
    title: str
    message: str
    task_name: Optional[str] = None
    script_path: Optional[str] = None
    current_value: Optional[Any] = None
    threshold_value: Optional[Any] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False
    resolved: bool = False
    action_required: bool = False

class SchedulerAgent(AgentInterface):
    """Scheduler agent for monitoring Windows Task Scheduler scripts"""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        
        # Extract scheduler-specific config
        scheduler_config = {
            'check_interval': config.get('check_interval', 60),
            'task_timeout': config.get('task_timeout', 300),
            'max_cpu_usage': config.get('max_cpu_usage', 80.0),
            'max_memory_usage': config.get('max_memory_usage', 80.0),
            'alert_cooldown': config.get('alert_cooldown', 300),
            'auto_restart_enabled': config.get('auto_restart_enabled', True),
            'integrity_check_interval': config.get('integrity_check_interval', 3600)
        }
        
        # Task monitoring
        self.monitored_tasks: Dict[str, TaskStatus] = {}
        self.task_scripts: Dict[str, str] = {}  # task_name -> script_path
        
        # Script integrity
        self.script_integrity: Dict[str, ScriptIntegrity] = {}
        
        # Alerts
        self.scheduler_alerts: List[SchedulerAlert] = []
        self.alert_handlers: Dict[str, callable] = {}
        
        # Performance tracking
        self.task_performance: Dict[str, Dict[str, float]] = {}
        self.system_metrics: Dict[str, float] = {}
        
        # Safety utilities
        self.error_handler = ErrorHandler(self.agent_id)
        self.rate_limiter = RateLimiter(max_messages_per_second=5)
        
        # Initialize monitored tasks
        self._initialize_monitored_tasks()
        
        # Initialize running state
        self.running = False
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get scheduler agent capabilities"""
        return {
            'task_monitoring': True,
            'script_integrity': True,
            'performance_monitoring': True,
            'alert_system': True,
            'auto_restart': self.scheduler_config['auto_restart_enabled'],
            'monitored_tasks': list(self.monitored_tasks.keys()),
            'task_scripts': self.task_scripts.copy()
        }
    
    async def health_check(self) -> HealthStatus:
        """Perform health check"""
        try:
            # Check system metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_usage = psutil.virtual_memory().percent
            
            # Check monitored tasks
            running_tasks = len([s for s in self.monitored_tasks.values() if s.is_running])
            total_tasks = len(self.monitored_tasks)
            
            # Check script integrity
            valid_scripts = len([s for s in self.script_integrity.values() if s.integrity_status == "valid"])
            total_scripts = len(self.script_integrity)
            
            # Calculate health score
            health_score = 100.0
            
            # Deduct for system resource usage
            if cpu_usage > 90:
                health_score -= 20
            elif cpu_usage > 80:
                health_score -= 10
            
            if memory_usage > 90:
                health_score -= 20
            elif memory_usage > 80:
                health_score -= 10
            
            # Deduct for task issues
            if running_tasks < total_tasks:
                health_score -= 20 * (1 - running_tasks / total_tasks)
            
            # Deduct for script issues
            if valid_scripts < total_scripts:
                health_score -= 20 * (1 - valid_scripts / total_scripts)
            
            # Determine status
            if health_score >= 90:
                status = HealthStatus.HEALTHY
            elif health_score >= 70:
                status = HealthStatus.WARNING
            elif health_score >= 50:
                status = HealthStatus.CRITICAL
            else:
                status = HealthStatus.FAILED
            
            return HealthStatus(
                status=status,
                message=f"Health score: {health_score:.1f}%"
            )
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return HealthStatus.FAILED
    
    async def initialize(self) -> bool:
        """Initialize scheduler agent"""
        try:
            self.logger.info("Initializing Scheduler Agent...")
            
            # Perform initial checks
            await self._perform_initial_checks()
            
            self.logger.info("Scheduler Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Scheduler Agent: {e}")
            return False
    
    async def process_message(self, message: Any) -> Any:
        """Process incoming message"""
        try:
            # Handle different message types
            if hasattr(message, 'message_type'):
                if message.message_type == MessageType.HEALTH_CHECK:
                    return await self.health_check()
                elif message.message_type == MessageType.GET_STATUS:
                    return await self.get_status()
                elif message.message_type == MessageType.GET_CAPABILITIES:
                    return await self.get_capabilities()
            
            # Default response
            return {"status": "processed", "timestamp": datetime.now().isoformat()}
            
        except Exception as e:
            self.logger.error(f"Failed to process message: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
        
    def _initialize_monitored_tasks(self):
        """Initialize the tasks we need to monitor"""
        try:
            # TWS Manager (24/7)
            self.monitored_tasks["Auto_TWS_Manager"] = TaskStatus(
                task_name="Auto_TWS_Manager",
                is_running=False,
                status="unknown"
            )
            self.task_scripts["Auto_TWS_Manager"] = "scripts/DAILY_ROUTINE/run_auto_tws_manager.bat"
            
            # Trading System (Daily 17:30)
            self.monitored_tasks["Auto_Trading_System"] = TaskStatus(
                task_name="Auto_Trading_System",
                is_running=False,
                status="unknown"
            )
            self.task_scripts["Auto_Trading_System"] = "scripts/DAILY_ROUTINE/run_trading.bat"
            
            self.logger.info(f"Initialized monitoring for {len(self.monitored_tasks)} tasks")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitored tasks: {e}")
    
    async def start(self) -> bool:
        """Start the scheduler agent"""
        try:
            self.logger.info("Starting Scheduler Agent...")
            self.start_time = datetime.now()
            
            # Start monitoring loops
            asyncio.create_task(self._task_monitoring_loop())
            asyncio.create_task(self._script_integrity_loop())
            asyncio.create_task(self._performance_monitoring_loop())
            
            # Initialize alert handlers
            self._initialize_alert_handlers()
            
            # Perform initial checks
            await self._perform_initial_checks()
            
            self.logger.info("Scheduler Agent started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Scheduler Agent: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the scheduler agent"""
        try:
            self.logger.info("Stopping Scheduler Agent...")
            self.running = False
            
            # Generate final report
            await self._generate_final_report()
            
            self.logger.info("Scheduler Agent stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop Scheduler Agent: {e}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get scheduler agent status"""
        try:
            return {
                'agent_id': self.agent_id,
                'status': self.status.value,
                'uptime': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                'monitored_tasks': len(self.monitored_tasks),
                'active_alerts': len([a for a in self.scheduler_alerts if not a.resolved]),
                'last_check': datetime.now().isoformat(),
                'task_status': {
                    name: {
                        'is_running': status.is_running,
                        'status': status.status,
                        'last_check': status.last_check
                    }
                    for name, status in self.monitored_tasks.items()
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            return {'error': str(e)}
    
    async def _task_monitoring_loop(self):
        """Main task monitoring loop"""
        while self.running:
            try:
                self.logger.debug("Checking task statuses...")
                
                # Check each monitored task
                for task_name in self.monitored_tasks:
                    await self._check_task_status(task_name)
                
                # Check for alerts
                await self._check_for_alerts()
                
                # Wait for next check
                await asyncio.sleep(self.scheduler_config['check_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in task monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait before retry
    
    async def _check_task_status(self, task_name: str):
        """Check status of a specific task"""
        try:
            # Update last check time
            self.monitored_tasks[task_name].last_check = datetime.now().isoformat()
            
            # Check if task process is running
            is_running = await self._is_task_running(task_name)
            self.monitored_tasks[task_name].is_running = is_running
            
            # Get process details if running
            if is_running:
                process_info = await self._get_process_info(task_name)
                self.monitored_tasks[task_name].process_id = process_info.get('pid')
                self.monitored_tasks[task_name].cpu_usage = process_info.get('cpu_percent', 0.0)
                self.monitored_tasks[task_name].memory_usage = process_info.get('memory_percent', 0.0)
                self.monitored_tasks[task_name].status = "running"
            else:
                self.monitored_tasks[task_name].process_id = None
                self.monitored_tasks[task_name].cpu_usage = 0.0
                self.monitored_tasks[task_name].memory_usage = 0.0
                self.monitored_tasks[task_name].status = "stopped"
            
            # Get task scheduler information
            scheduler_info = await self._get_task_scheduler_info(task_name)
            if scheduler_info:
                self.monitored_tasks[task_name].last_run = scheduler_info.get('last_run')
                self.monitored_tasks[task_name].next_run = scheduler_info.get('next_run')
                self.monitored_tasks[task_name].exit_code = scheduler_info.get('last_result')
            
            self.logger.debug(f"Task {task_name}: {self.monitored_tasks[task_name].status}")
            
        except Exception as e:
            self.logger.error(f"Failed to check task status for {task_name}: {e}")
    
    async def _is_task_running(self, task_name: str) -> bool:
        """Check if a task process is currently running"""
        try:
            script_path = self.task_scripts.get(task_name)
            if not script_path:
                return False
            
            # Check for processes running the script
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any(script_path in cmd for cmd in cmdline):
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check if task {task_name} is running: {e}")
            return False
    
    async def _get_process_info(self, task_name: str) -> Dict[str, Any]:
        """Get detailed process information for a task"""
        try:
            script_path = self.task_scripts.get(task_name)
            if not script_path:
                return {}
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any(script_path in cmd for cmd in cmdline):
                        return {
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cpu_percent': proc.info['cpu_percent'],
                            'memory_percent': proc.info['memory_percent'],
                            'create_time': proc.create_time()
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to get process info for {task_name}: {e}")
            return {}
    
    async def _get_task_scheduler_info(self, task_name: str) -> Dict[str, Any]:
        """Get Windows Task Scheduler information for a task"""
        try:
            # Use schtasks command to get task information
            cmd = f'schtasks /query /tn "{task_name}" /fo list /v'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse the output
                lines = result.stdout.strip().split('\n')
                info = {}
                
                for line in lines:
                    if 'Last Run Time:' in line:
                        info['last_run'] = line.split('Last Run Time:')[-1].strip()
                    elif 'Next Run Time:' in line:
                        info['next_run'] = line.split('Next Run Time:')[-1].strip()
                    elif 'Last Result:' in line:
                        info['last_result'] = line.split('Last Result:')[-1].strip()
                
                return info
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to get task scheduler info for {task_name}: {e}")
            return {}
    
    async def _script_integrity_loop(self):
        """Script integrity checking loop"""
        while self.running:
            try:
                self.logger.debug("Checking script integrity...")
                
                # Check all monitored scripts
                for task_name, script_path in self.task_scripts.items():
                    await self._check_script_integrity(task_name, script_path)
                
                # Wait for next check
                await asyncio.sleep(self.scheduler_config['integrity_check_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in script integrity loop: {e}")
                await asyncio.sleep(300)  # Wait before retry
    
    async def _check_script_integrity(self, task_name: str, script_path: str):
        """Check integrity of a script file"""
        try:
            full_path = os.path.join(os.getcwd(), script_path)
            
            integrity = ScriptIntegrity(
                script_path=script_path,
                exists=os.path.exists(full_path),
                readable=False,
                executable=False,
                size_bytes=0,
                last_modified="",
                integrity_status="unknown"
            )
            
            if integrity.exists:
                # Check if readable
                try:
                    with open(full_path, 'r') as f:
                        f.read(1)  # Try to read first byte
                    integrity.readable = True
                except Exception:
                    integrity.errors.append("File not readable")
                
                # Check if executable
                integrity.executable = os.access(full_path, os.X_OK)
                if not integrity.executable:
                    integrity.errors.append("File not executable")
                
                # Get file stats
                stat = os.stat(full_path)
                integrity.size_bytes = stat.st_size
                integrity.last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
                
                # Calculate simple checksum
                try:
                    with open(full_path, 'rb') as f:
                        content = f.read()
                        integrity.checksum = hash(content)
                    integrity.integrity_status = "valid"
                except Exception as e:
                    integrity.errors.append(f"Checksum failed: {e}")
                    integrity.integrity_status = "corrupted"
            else:
                integrity.errors.append("File does not exist")
                integrity.integrity_status = "missing"
            
            self.script_integrity[task_name] = integrity
            
            # Log status
            if integrity.integrity_status != "valid":
                self.logger.warning(f"Script integrity issue for {task_name}: {integrity.integrity_status}")
            
        except Exception as e:
            self.logger.error(f"Failed to check script integrity for {task_name}: {e}")
    
    async def _performance_monitoring_loop(self):
        """Performance monitoring loop"""
        while self.running:
            try:
                # Get system metrics
                self.system_metrics = {
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Check for performance alerts
                await self._check_performance_alerts()
                
                # Wait for next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in performance monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_performance_alerts(self):
        """Check for performance-related alerts"""
        try:
            # Check CPU usage
            if self.system_metrics['cpu_percent'] > self.scheduler_config['max_cpu_usage']:
                await self._create_alert(
                    alert_type="performance",
                    severity="high",
                    title="High CPU Usage",
                    message=f"System CPU usage is {self.system_metrics['cpu_percent']:.1f}%",
                    current_value=self.system_metrics['cpu_percent'],
                    threshold_value=self.scheduler_config['max_cpu_usage']
                )
            
            # Check memory usage
            if self.system_metrics['memory_percent'] > self.scheduler_config['max_memory_usage']:
                await self._create_alert(
                    alert_type="performance",
                    severity="high",
                    title="High Memory Usage",
                    message=f"System memory usage is {self.system_metrics['memory_percent']:.1f}%",
                    current_value=self.system_metrics['memory_percent'],
                    threshold_value=self.scheduler_config['max_memory_usage']
                )
            
        except Exception as e:
            self.logger.error(f"Failed to check performance alerts: {e}")
    
    async def _check_for_alerts(self):
        """Check for any alert conditions"""
        try:
            # Check task failures
            for task_name, status in self.monitored_tasks.items():
                # Check if task should be running but isn't
                if not status.is_running and self._should_task_be_running(task_name):
                    await self._create_alert(
                        alert_type="task_failure",
                        severity="critical",
                        title=f"Task Not Running: {task_name}",
                        message=f"Task {task_name} should be running but is not",
                        task_name=task_name,
                        action_required=True
                    )
                
                # Check for high resource usage
                if status.is_running:
                    if status.cpu_usage > 90:
                        await self._create_alert(
                            alert_type="performance",
                            severity="medium",
                            title=f"High CPU Usage: {task_name}",
                            message=f"Task {task_name} CPU usage is {status.cpu_usage:.1f}%",
                            task_name=task_name,
                            current_value=status.cpu_usage,
                            threshold_value=90
                        )
                    
                    if status.memory_usage > 90:
                        await self._create_alert(
                            alert_type="performance",
                            severity="medium",
                            title=f"High Memory Usage: {task_name}",
                            message=f"Task {task_name} memory usage is {status.memory_usage:.1f}%",
                            task_name=task_name,
                            current_value=status.memory_usage,
                            threshold_value=90
                        )
            
            # Check script integrity
            for task_name, integrity in self.script_integrity.items():
                if integrity.integrity_status != "valid":
                    await self._create_alert(
                        alert_type="script_integrity",
                        severity="high",
                        title=f"Script Integrity Issue: {task_name}",
                        message=f"Script {integrity.script_path} has integrity issues: {integrity.integrity_status}",
                        task_name=task_name,
                        script_path=integrity.script_path,
                        action_required=True
                    )
            
        except Exception as e:
            self.logger.error(f"Failed to check for alerts: {e}")
    
    def _should_task_be_running(self, task_name: str) -> bool:
        """Determine if a task should be running based on schedule"""
        try:
            current_time = datetime.now()
            
            if task_name == "Auto_TWS_Manager":
                # TWS Manager should always be running (24/7)
                return True
            elif task_name == "Auto_Trading_System":
                # Trading System runs daily at 17:30
                # Check if we're within a reasonable window (17:30-18:30)
                target_time = current_time.replace(hour=17, minute=30, second=0, microsecond=0)
                end_time = current_time.replace(hour=18, minute=30, second=0, microsecond=0)
                
                # Handle overnight wraparound
                if current_time.time() >= target_time.time() or current_time.time() <= end_time.time():
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to determine if task {task_name} should be running: {e}")
            return False
    
    async def _create_alert(self, alert_type: str, severity: str, title: str, message: str, 
                           task_name: str = None, script_path: str = None, 
                           current_value: Any = None, threshold_value: Any = None,
                           action_required: bool = False):
        """Create a scheduler alert"""
        try:
            alert = SchedulerAlert(
                alert_id=f"scheduler_{int(time.time())}_{alert_type}",
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                task_name=task_name,
                script_path=script_path,
                current_value=current_value,
                threshold_value=threshold_value,
                action_required=action_required
            )
            
            self.scheduler_alerts.append(alert)
            
            # Log alert
            log_level = {
                'low': logging.INFO,
                'medium': logging.WARNING,
                'high': logging.ERROR,
                'critical': logging.CRITICAL
            }.get(severity, logging.INFO)
            
            self.logger.log(log_level, f"SCHEDULER ALERT: {title} - {message}")
            
            # Handle alert
            if alert_type in self.alert_handlers:
                await self.alert_handlers[alert_type](alert)
            
        except Exception as e:
            self.logger.error(f"Failed to create alert: {e}")
    
    def _initialize_alert_handlers(self):
        """Initialize alert handlers"""
        try:
            self.alert_handlers = {
                'task_failure': self._handle_task_failure_alert,
                'script_integrity': self._handle_script_integrity_alert,
                'performance': self._handle_performance_alert,
                'system': self._handle_system_alert
            }
            
            self.logger.info("Alert handlers initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize alert handlers: {e}")
    
    async def _handle_task_failure_alert(self, alert: SchedulerAlert):
        """Handle task failure alert"""
        try:
            self.logger.info(f"Handling task failure alert: {alert.title}")
            
            # Auto-restart if enabled
            if self.scheduler_config['auto_restart_enabled']:
                await self._attempt_task_restart(alert.task_name)
            
        except Exception as e:
            self.logger.error(f"Failed to handle task failure alert: {e}")
    
    async def _handle_script_integrity_alert(self, alert: SchedulerAlert):
        """Handle script integrity alert"""
        try:
            self.logger.info(f"Handling script integrity alert: {alert.title}")
            # Script integrity issues require manual intervention
            
        except Exception as e:
            self.logger.error(f"Failed to handle script integrity alert: {e}")
    
    async def _handle_performance_alert(self, alert: SchedulerAlert):
        """Handle performance alert"""
        try:
            self.logger.info(f"Handling performance alert: {alert.title}")
            # Performance alerts are informational
            
        except Exception as e:
            self.logger.error(f"Failed to handle performance alert: {e}")
    
    async def _handle_system_alert(self, alert: SchedulerAlert):
        """Handle system alert"""
        try:
            self.logger.info(f"Handling system alert: {alert.title}")
            # System alerts require attention
            
        except Exception as e:
            self.logger.error(f"Failed to handle system alert: {e}")
    
    async def _attempt_task_restart(self, task_name: str):
        """Attempt to restart a failed task"""
        try:
            self.logger.info(f"Attempting to restart task: {task_name}")
            
            # Use schtasks to run the task
            cmd = f'schtasks /run /tn "{task_name}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Successfully triggered restart for task: {task_name}")
                return True
            else:
                self.logger.error(f"Failed to restart task {task_name}: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to restart task {task_name}: {e}")
            return False
    
    async def _perform_initial_checks(self):
        """Perform initial system checks"""
        try:
            self.logger.info("Performing initial system checks...")
            
            # Check all tasks
            for task_name in self.monitored_tasks:
                await self._check_task_status(task_name)
            
            # Check all scripts
            for task_name, script_path in self.task_scripts.items():
                await self._check_script_integrity(task_name, script_path)
            
            # Get system metrics
            self.system_metrics = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info("Initial checks completed")
            
        except Exception as e:
            self.logger.error(f"Failed to perform initial checks: {e}")
    
    async def _generate_final_report(self):
        """Generate final status report"""
        try:
            self.logger.info("Generating final scheduler report...")
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'agent_id': self.agent_id,
                'uptime': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                'monitored_tasks': len(self.monitored_tasks),
                'task_status': {
                    name: {
                        'is_running': status.is_running,
                        'status': status.status,
                        'last_check': status.last_check,
                        'cpu_usage': status.cpu_usage,
                        'memory_usage': status.memory_usage
                    }
                    for name, status in self.monitored_tasks.items()
                },
                'script_integrity': {
                    name: {
                        'exists': integrity.exists,
                        'status': integrity.integrity_status,
                        'last_modified': integrity.last_modified,
                        'errors': integrity.errors
                    }
                    for name, integrity in self.script_integrity.items()
                },
                'system_metrics': self.system_metrics,
                'total_alerts': len(self.scheduler_alerts),
                'active_alerts': len([a for a in self.scheduler_alerts if not a.resolved]),
                'alerts_by_type': {
                    alert_type: len([a for a in self.scheduler_alerts if a.alert_type == alert_type])
                    for alert_type in set(a.alert_type for a in self.scheduler_alerts)
                }
            }
            
            # Save report to file
            report_file = f"logs/scheduler_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"Final report saved to: {report_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate final report: {e}")
    
    async def get_scheduler_report(self) -> Dict[str, Any]:
        """Get comprehensive scheduler report"""
        try:
            return {
                'timestamp': datetime.now().isoformat(),
                'agent_status': await self.get_status(),
                'monitored_tasks': {
                    name: {
                        'is_running': status.is_running,
                        'status': status.status,
                        'last_run': status.last_run,
                        'next_run': status.next_run,
                        'exit_code': status.exit_code,
                        'process_id': status.process_id,
                        'cpu_usage': status.cpu_usage,
                        'memory_usage': status.memory_usage,
                        'last_check': status.last_check
                    }
                    for name, status in self.monitored_tasks.items()
                },
                'script_integrity': {
                    name: {
                        'script_path': integrity.script_path,
                        'exists': integrity.exists,
                        'readable': integrity.readable,
                        'executable': integrity.executable,
                        'size_bytes': integrity.size_bytes,
                        'last_modified': integrity.last_modified,
                        'integrity_status': integrity.integrity_status,
                        'errors': integrity.errors
                    }
                    for name, integrity in self.script_integrity.items()
                },
                'system_metrics': self.system_metrics,
                'alerts': [
                    {
                        'alert_id': alert.alert_id,
                        'type': alert.alert_type,
                        'severity': alert.severity,
                        'title': alert.title,
                        'message': alert.message,
                        'task_name': alert.task_name,
                        'script_path': alert.script_path,
                        'current_value': alert.current_value,
                        'threshold_value': alert.threshold_value,
                        'timestamp': alert.timestamp,
                        'acknowledged': alert.acknowledged,
                        'resolved': alert.resolved,
                        'action_required': alert.action_required
                    }
                    for alert in self.scheduler_alerts
                ],
                'summary': {
                    'total_tasks': len(self.monitored_tasks),
                    'running_tasks': len([s for s in self.monitored_tasks.values() if s.is_running]),
                    'valid_scripts': len([s for s in self.script_integrity.values() if s.integrity_status == "valid"]),
                    'total_alerts': len(self.scheduler_alerts),
                    'active_alerts': len([a for a in self.scheduler_alerts if not a.resolved]),
                    'critical_alerts': len([a for a in self.scheduler_alerts if a.severity == "critical"]),
                    'system_health': self._calculate_system_health()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get scheduler report: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def _calculate_system_health(self) -> str:
        """Calculate overall system health"""
        try:
            # Check task health
            running_tasks = len([s for s in self.monitored_tasks.values() if s.is_running])
            total_tasks = len(self.monitored_tasks)
            task_health = running_tasks / total_tasks if total_tasks > 0 else 0
            
            # Check script integrity
            valid_scripts = len([s for s in self.script_integrity.values() if s.integrity_status == "valid"])
            total_scripts = len(self.script_integrity)
            script_health = valid_scripts / total_scripts if total_scripts > 0 else 0
            
            # Check alerts
            critical_alerts = len([a for a in self.scheduler_alerts if a.severity == "critical" and not a.resolved])
            
            # Calculate overall health
            if critical_alerts > 0:
                return "Critical"
            elif task_health < 0.5 or script_health < 0.5:
                return "Warning"
            elif task_health == 1.0 and script_health == 1.0:
                return "Healthy"
            else:
                return "Fair"
                
        except Exception as e:
            self.logger.error(f"Failed to calculate system health: {e}")
            return "Unknown"
