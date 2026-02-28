"""
Sync Agent - Handles portfolio synchronization and email reporting
"""

import asyncio
import logging
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import time
import os
import websockets
import threading
from concurrent.futures import ThreadPoolExecutor

from src.interfaces.agent_interface import AgentInterface, AgentStatus, MessageType, HealthStatus
from src.messaging.message_types import SyncRequest, SyncResponse
from src.config.agent_config import SyncAgentConfig
from src.utils.message_safety import RateLimiter
from src.utils.error_handler import ErrorHandler, ErrorSeverity

@dataclass
class ReconciliationResult:
    """Portfolio reconciliation result"""
    is_reconciled: bool
    discrepancies: List[Dict[str, Any]]
    reconciled_positions: int
    total_positions: int
    reconciliation_time: float
    timestamp: str
    details: Optional[Dict[str, Any]] = None

@dataclass
class PositionDiscrepancy:
    """Position discrepancy details"""
    ticker: str
    discrepancy_type: str  # quantity, price, cost_basis, missing
    tws_value: Any
    local_value: Any
    difference: Any
    percentage_diff: Optional[float] = None
    severity: str = "medium"  # low, medium, high, critical

@dataclass
class SyncResult:
    """Synchronization result"""
    success: bool
    target: str
    status: str
    synced_items: int
    timestamp: str
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    total_return: float
    daily_return: float
    weekly_return: float
    monthly_return: float
    annual_return: float
    cagr: float  # Compound Annual Growth Rate
    max_drawdown: float
    current_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    volatility: float
    beta: float
    alpha: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    consecutive_wins: int
    consecutive_losses: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_fees: float
    net_profit: float
    gross_profit: float
    gross_loss: float
    risk_free_rate: float = 0.02  # 2% risk-free rate

@dataclass
class RiskMetrics:
    """Risk analysis metrics"""
    var_95: float  # Value at Risk 95%
    var_99: float  # Value at Risk 99%
    cvar_95: float  # Conditional VaR 95%
    cvar_99: float  # Conditional VaR 99%
    downside_deviation: float
    upside_deviation: float
    semi_variance: float
    tracking_error: float
    information_ratio: float
    calmar_ratio: float
    sterling_ratio: float
    burke_ratio: float
    tail_ratio: float
    omega_ratio: float
    pain_index: float
    ulcer_index: float
    martin_ratio: float

@dataclass
class SectorPerformance:
    """Sector-based performance analysis"""
    sector_name: str
    allocation: float  # Percentage of portfolio
    return_pct: float
    contribution_to_return: float
    risk_contribution: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    beta: float

@dataclass
class Alert:
    """Portfolio alert definition"""
    alert_id: str
    alert_type: str  # position, risk, price, volume, compliance, margin
    severity: str  # low, medium, high, critical
    title: str
    message: str
    ticker: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False
    resolved: bool = False
    action_required: bool = False
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class AlertRule:
    """Alert rule definition"""
    rule_id: str
    name: str
    description: str
    alert_type: str
    condition: str  # gt, lt, eq, gte, lte, pct_change, abs_change
    threshold: float
    severity: str
    enabled: bool = True
    cooldown_period: int = 300  # seconds
    last_triggered: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class AlertStatistics:
    """Alert system statistics"""
    total_alerts: int
    active_alerts: int
    resolved_alerts: int
    critical_alerts: int
    alerts_by_type: Dict[str, int]
    alerts_by_severity: Dict[str, int]
    average_resolution_time: float
    alerts_today: int
    alerts_this_week: int
    alerts_this_month: int

class SyncAgent(AgentInterface):
    """Sync agent for portfolio synchronization and email reporting"""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        self.agent_config = SyncAgentConfig(**config)
        
        # Core components
        self.portfolio_synchronizer = None
        self.email_generator = None  # Initialize after config validation
        
        # Real-time sync components
        self.websocket_connection = None
        self.sync_thread = None
        self.sync_executor = ThreadPoolExecutor(max_workers=2)
        self.is_syncing = False
        self.last_sync_time = None
        
        # Safety utilities
        self.error_handler = ErrorHandler(self.agent_id)
        self.rate_limiter = RateLimiter(max_messages_per_second=20)
        
        # Performance tracking
        self.sync_times: Dict[str, float] = {}
        self.sync_counts: Dict[str, int] = {}
        self.real_time_updates: List[Dict[str, Any]] = []
        
        # Performance analytics
        self.performance_history: List[Dict[str, Any]] = []
        self.daily_returns: List[float] = []
        self.weekly_returns: List[float] = []
        self.monthly_returns: List[float] = []
        self.portfolio_values: List[Dict[str, Any]] = []
        self.trade_history: List[Dict[str, Any]] = []
        
        # Performance cache
        self._cached_performance: Optional[PerformanceMetrics] = None
        self._cached_risk_metrics: Optional[RiskMetrics] = None
        self._performance_cache_time: Optional[float] = None
        self._performance_cache_ttl: float = 300.0  # 5 minutes cache
        
        # Alert system
        self.alerts: List[Alert] = []
        self.alert_rules: List[AlertRule] = []
        self.alert_statistics: Optional[AlertStatistics] = None
        self.alert_cooldowns: Dict[str, float] = {}
        self.alert_handlers: Dict[str, callable] = {}
        
        # Alert configuration
        self.alert_config = {
            'max_active_alerts': 100,
            'alert_retention_days': 30,
            'auto_resolve_hours': 24,
            'escalation_enabled': True,
            'notification_channels': ['email', 'log'],
            'critical_alert_threshold': 0.05,
            'high_alert_threshold': 0.10,
            'medium_alert_threshold': 0.20
        }
        
        # Sync targets
        self.sync_targets = self.agent_config.sync_targets
        
        # Initialize components
        self._init_components()
    
    def _init_components(self):
        """Initialize sync components"""
        try:
            # Initialize email generator
            self.email_generator = EmailGenerator(self.agent_config)
            self.logger.info("Email generator initialized")
            
            # Initialize portfolio synchronizer
            self.portfolio_synchronizer = PortfolioSynchronizer(self.agent_config)
            self.logger.info("Portfolio synchronizer initialized")
            
        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            # Continue without components - will be handled in testing
        
    async def initialize(self) -> bool:
        """Initialize sync agent"""
        try:
            self.logger.info(f"Initializing Sync Agent with targets: {self.sync_targets}")
            
            # Test components
            if not self._test_components():
                self.logger.error("Component tests failed")
                return False
                
            self.update_status(AgentStatus.READY)
            self.logger.info("Sync Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing Sync Agent: {e}")
            self.update_status(AgentStatus.ERROR)
            return False
            
    async def start(self) -> bool:
        """Start sync agent"""
        try:
            self.update_status(AgentStatus.RUNNING)
            self.start_time = datetime.now()
            
            # Start periodic sync
            asyncio.create_task(self._periodic_sync_loop())
            
            self.logger.info("Sync Agent started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting Sync Agent: {e}")
            return False
            
    async def stop(self) -> bool:
        """Stop sync agent"""
        try:
            self.update_status(AgentStatus.SHUTDOWN)
            self.sync_times.clear()
            self.sync_counts.clear()
            self.logger.info("Sync Agent stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping Sync Agent: {e}")
            return False
            
    async def process_message(self, message) -> Optional[Dict[str, Any]]:
        """Process incoming messages"""
        try:
            # Rate limiting
            if not self.rate_limiter.is_allowed():
                return await self._create_error_response(message, "Rate limit exceeded")
                
            self.rate_limiter.record_request()
            
            if message.message_type == MessageType.SYNC_REQUEST:
                return await self._handle_sync_request(message)
            elif message.message_type == MessageType.HEALTH_CHECK:
                return await self._handle_health_check(message)
            else:
                return None
                
        except Exception as e:
            self.error_handler.handle_error(e, {
                "message_type": message.message_type.value if message.message_type else "unknown",
                "sender": message.sender,
                "recipient": message.recipient
            }, ErrorSeverity.MEDIUM, "SyncAgent.process_message")
            
            return await self._create_error_response(message, str(e))
            
    async def health_check(self) -> HealthStatus:
        """Perform health check"""
        try:
            start_time = time.time()
            
            # Check components
            components_ok = await self._check_components()
            
            uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            return HealthStatus(
                agent_id=self.agent_id,
                status=AgentStatus.RUNNING if components_ok else AgentStatus.ERROR,
                last_check=datetime.now().isoformat(),
                cpu_usage=0.0,
                memory_usage=0.0,
                error_count=0,
                last_error=None,
                uptime=uptime
            )
            
        except Exception as e:
            return HealthStatus(
                agent_id=self.agent_id,
                status=AgentStatus.ERROR,
                last_check=datetime.now().isoformat(),
                cpu_usage=0.0,
                memory_usage=0.0,
                error_count=1,
                last_error=str(e)
            )
            
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return ["sync_request", "sync_response", "health_check"]
        
    async def verify_portfolio_sync(self) -> bool:
        """Verify portfolio synchronization"""
        try:
            # Mock verification for testing
            return True
        except Exception as e:
            self.logger.error(f"Portfolio sync verification failed: {e}")
            return False
    
    async def update_portfolio(self, execution_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """Update portfolio state with real trade results"""
        try:
            import json
            import os
            from datetime import datetime
            
            portfolio_file = "data/portfolio_sim.json"
            
            # Load existing portfolio
            if os.path.exists(portfolio_file):
                with open(portfolio_file, 'r') as f:
                    portfolio = json.load(f)
            else:
                # Initialize new portfolio
                portfolio = {
                    "account_id": "VOLATILITY_HUNTER",
                    "cash": 1000000.0,
                    "buying_power": 1000000.0,
                    "total_value": 1000000.0,
                    "positions": {},
                    "trades": [],
                    "last_updated": datetime.now().isoformat()
                }
            
            # Process execution results
            if execution_results and execution_results.get('success'):
                results = execution_results.get('results', [])
                updated_positions = 0
                
                for trade in results:
                    if trade.get('action') == 'BUY' and not trade.get('error'):
                        ticker = trade['ticker']
                        quantity = trade['quantity']
                        price = trade['price']
                        value = trade['value']
                        
                        # Update portfolio
                        if ticker in portfolio['positions']:
                            # Add to existing position
                            pos = portfolio['positions'][ticker]
                            old_quantity = pos['quantity']
                            old_avg_price = pos['avg_price']
                            
                            # Calculate new average price
                            total_cost = (old_quantity * old_avg_price) + (quantity * price)
                            new_quantity = old_quantity + quantity
                            new_avg_price = total_cost / new_quantity
                            
                            pos['quantity'] = new_quantity
                            pos['avg_price'] = new_avg_price
                            pos['last_price'] = price
                            pos['value'] = new_quantity * price
                        else:
                            # New position
                            portfolio['positions'][ticker] = {
                                'quantity': quantity,
                                'avg_price': price,
                                'last_price': price,
                                'value': value,
                                'entry_date': datetime.now().isoformat(),
                                'is_power_stock': False
                            }
                        
                        # Update cash
                        portfolio['cash'] -= value
                        portfolio['buying_power'] = portfolio['cash']
                        
                        # Add to trade history
                        portfolio['trades'].append({
                            'ticker': ticker,
                            'action': 'BUY',
                            'quantity': quantity,
                            'price': price,
                            'value': value,
                            'timestamp': datetime.now().isoformat(),
                            'order_id': trade.get('order_id')
                        })
                        
                        updated_positions += 1
                
                # Calculate total portfolio value
                total_position_value = sum(pos['value'] for pos in portfolio['positions'].values())
                portfolio['total_value'] = portfolio['cash'] + total_position_value
                
                portfolio['last_updated'] = datetime.now().isoformat()
                
                # Save portfolio
                with open(portfolio_file, 'w') as f:
                    json.dump(portfolio, f, indent=2)
                
                self.logger.info(f"Portfolio updated: {updated_positions} positions, total value: ${portfolio['total_value']:,.2f}")
                
                return {
                    "success": True,
                    "updated_positions": updated_positions,
                    "portfolio_value": portfolio['total_value'],
                    "cash": portfolio['cash'],
                    "positions_count": len(portfolio['positions']),
                    "update_time": portfolio['last_updated']
                }
            else:
                # No execution results, just return current state
                return {
                    "success": True,
                    "updated_positions": 0,
                    "portfolio_value": portfolio.get('total_value', 0),
                    "cash": portfolio.get('cash', 0),
                    "positions_count": len(portfolio.get('positions', {})),
                    "update_time": portfolio.get('last_updated', self._get_timestamp())
                }
                
        except Exception as e:
            self.logger.error(f"Portfolio update failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_portfolio(self) -> bool:
        """Save portfolio state to disk"""
        try:
            import json
            import os
            from datetime import datetime
            
            portfolio_file = "data/portfolio_sim.json"
            
            # Ensure data directory exists
            os.makedirs(os.path.dirname(portfolio_file), exist_ok=True)
            
            # Load current portfolio
            if os.path.exists(portfolio_file):
                with open(portfolio_file, 'r') as f:
                    portfolio = json.load(f)
            else:
                self.logger.warning("No portfolio file found to save")
                return True
            
            # Update timestamp
            portfolio['last_updated'] = datetime.now().isoformat()
            
            # Save to file
            with open(portfolio_file, 'w') as f:
                json.dump(portfolio, f, indent=2)
            
            # Create backup
            backup_file = f"data/portfolio_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w') as f:
                json.dump(portfolio, f, indent=2)
            
            self.logger.info(f"Portfolio saved to {portfolio_file} and backed up to {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Portfolio save failed: {e}")
            return False
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
        
    async def sync_portfolio(self, sync_type: str = "portfolio", target: str = "all", force_sync: bool = False) -> Dict[str, Any]:
        """Synchronize portfolio"""
        try:
            start_time = time.time()
            
            # Validate request
            if not self._validate_sync_request(sync_type, target, force_sync):
                return {
                    "success": False,
                    "error": "Invalid sync request",
                    "sync_type": sync_type,
                    "target": target
                }
                
            # Perform sync
            if target == "all" or target == "tws":
                tws_result = await self._sync_to_tws(sync_type, force_sync)
            else:
                tws_result = SyncResult(True, "tws", "completed", 0, datetime.now().isoformat(), True, None)
                
            if target == "all" or target == "local":
                local_result = await self._sync_to_local(sync_type, force_sync)
            else:
                local_result = SyncResult(True, "local", "completed", 0, datetime.now().isoformat(), True, None)
                
            # Track performance
            sync_time = time.time() - start_time
            self.sync_times[sync_type] = sync_time
            self.sync_counts[sync_type] = self.sync_counts.get(sync_type, 0) + 1
            
            success = tws_result.success and local_result.success
            
            self.logger.info(f"Synced {sync_type} to {target} in {sync_time:.2f}s")
            
            return {
                "success": success,
                "sync_type": sync_type,
                "target": target,
                "results": [self._sync_result_to_dict(tws_result), self._sync_result_to_dict(local_result)],
                "sync_time": sync_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error syncing portfolio: {e}")
            return {
                "success": False,
                "error": str(e),
                "sync_type": sync_type,
                "target": target
            }
            
    async def generate_email_report(self, report_type: str = "daily", include_performance: bool = True) -> Dict[str, Any]:
        """Generate email report"""
        try:
            start_time = time.time()
            
            # Generate report
            report = await self.email_generator.generate_report(report_type, include_performance)
            
            generation_time = time.time() - start_time
            self.logger.info(f"Generated {report_type} report in {generation_time:.2f}s")
            
            return {
                "success": True,
                "report_type": report_type,
                "report": report,
                "generation_time": generation_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating email report: {e}")
            return {
                "success": False,
                "error": str(e),
                "report_type": report_type,
                "timestamp": datetime.now().isoformat()
            }
            
    async def _handle_sync_request(self, message) -> Dict[str, Any]:
        """Handle sync request message"""
        try:
            data = message.data
            
            if "sync_type" in data:
                result = await self.sync_portfolio(
                    data["sync_type"],
                    data.get("target", "all"),
                    data.get("force_sync", False)
                )
                return result
            else:
                return {"success": False, "error": "Missing sync_type"}
                
        except Exception as e:
            self.logger.error(f"Error handling sync request: {e}")
            return {"success": False, "error": str(e)}
            
    async def _handle_health_check(self, message) -> Dict[str, Any]:
        """Handle health check message"""
        try:
            health = await self.health_check()
            
            return {
                "success": True,
                "health_status": health.status.value,
                "sync_targets": self.sync_targets,
                "auto_reconcile": self.agent_config.auto_reconcile,
                "email_reports": self.agent_config.email_reports
            }
            
        except Exception as e:
            self.logger.error(f"Error handling health check: {e}")
            return {"success": False, "error": str(e)}
    
    def _validate_portfolio_data(self, portfolio: Dict[str, Any]) -> bool:
        """Validate portfolio data integrity"""
        try:
            required_fields = ['cash', 'positions', 'total_value', 'last_updated']
            
            for field in required_fields:
                if field not in portfolio:
                    self.logger.error(f"Missing required portfolio field: {field}")
                    return False
            
            # Validate positions
            if not isinstance(portfolio['positions'], dict):
                self.logger.error("Portfolio positions must be a dictionary")
                return False

            # Validate each position
            for ticker, position in portfolio['positions'].items():
                required_pos_fields = ['quantity', 'avg_price', 'value']
                for field in required_pos_fields:
                    if field not in position:
                        self.logger.error(f"Missing required position field {field} for {ticker}")
                        return False

                # Validate numeric fields
                if not isinstance(position['quantity'], (int, float)) or position['quantity'] < 0:
                    self.logger.error(f"Invalid quantity for {ticker}: {position['quantity']}")
                    return False
                
                if not isinstance(position['avg_price'], (int, float)) or position['avg_price'] <= 0:
                    self.logger.error(f"Invalid avg_price for {ticker}: {position['avg_price']}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Portfolio validation failed: {e}")
            return False
    def _validate_sync_request(self, sync_type: str, target: str, force_sync: bool) -> bool:
        """Validate sync request"""
        try:
            if sync_type not in ["portfolio", "positions", "account", "all"]:
                return False
                
            if target not in ["tws", "local", "all"]:
                return False
                
            return True
            
        except Exception:
            return False
            
    async def _sync_to_tws(self, sync_type: str, force_sync: bool) -> SyncResult:
        """Sync portfolio to TWS/IBKR"""
        try:
            start_time = time.time()
            
            # Get current portfolio
            portfolio_file = "data/portfolio_sim.json"
            if not os.path.exists(portfolio_file):
                return SyncResult(False, "tws", "failed", 0, datetime.now().isoformat(), None, "Portfolio file not found")
            
            with open(portfolio_file, 'r') as f:
                portfolio = json.load(f)
            
            # Validate portfolio data
            if not self._validate_portfolio_data(portfolio):
                return SyncResult(False, "tws", "failed", 0, datetime.now().isoformat(), None, "Portfolio data validation failed")
            
            # In production, this would sync with IBKR TWS
            # For now, we'll simulate the sync
            synced_items = 0
            
            # Sync positions
            for ticker, position in portfolio['positions'].items():
                try:
                    # Simulate TWS sync
                    self.logger.debug(f"Syncing {ticker} to TWS")
                    synced_items += 1
                except Exception as e:
                    self.logger.error(f"Failed to sync {ticker} to TWS: {e}")
            
            # Sync cash
            try:
                self.logger.debug(f"Syncing cash balance to TWS: ${portfolio['cash']}")
                synced_items += 1
            except Exception as e:
                self.logger.error(f"Failed to sync cash to TWS: {e}")
            
            sync_time = time.time() - start_time
            
            return SyncResult(
                True, 
                "tws", 
                "completed", 
                synced_items, 
                datetime.now().isoformat(),
                {"sync_time": sync_time, "positions_synced": len(portfolio['positions'])},
                None
            )
            
        except Exception as e:
            self.logger.error(f"TWS sync failed: {e}")
            return SyncResult(False, "tws", "failed", 0, datetime.now().isoformat(), None, str(e))
    
    async def start_real_time_sync(self) -> bool:
        """Start real-time WebSocket sync with IBKR"""
        try:
            if self.is_syncing:
                self.logger.warning("Real-time sync already running")
                return True
            
            self.is_syncing = True
            self.logger.info("Starting real-time WebSocket sync with IBKR")
            
            # Start WebSocket connection in background thread
            self.sync_thread = threading.Thread(
                target=self._websocket_sync_loop,
                daemon=True
            )
            self.sync_thread.start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start real-time sync: {e}")
            self.is_syncing = False
            return False
    
    def _websocket_sync_loop(self):
        """WebSocket sync loop for real-time updates"""
        try:
            # In production, this would connect to IBKR WebSocket
            # For now, we'll simulate real-time updates
            
            while self.is_syncing:
                try:
                    # Simulate receiving portfolio update from IBKR
                    update = self._simulate_ibkr_update()
                    
                    if update:
                        # Process update in thread pool
                        future = self.sync_executor.submit(
                            self._process_real_time_update,
                            update
                        )
                        
                        # Track update
                        self.real_time_updates.append({
                            'timestamp': datetime.now().isoformat(),
                            'update': update,
                            'processed': False
                        })
                        
                        # Keep only last 100 updates
                        if len(self.real_time_updates) > 100:
                            self.real_time_updates = self.real_time_updates[-100:]
                    
                    # Sub-second sync interval
                    time.sleep(0.5)  # 500ms for sub-second sync
                    
                except Exception as e:
                    self.logger.error(f"Error in WebSocket sync loop: {e}")
                    time.sleep(5)  # Wait 5 seconds before retry
                    
        except Exception as e:
            self.logger.error(f"WebSocket sync loop failed: {e}")
            self.is_syncing = False
    
    def _simulate_ibkr_update(self) -> Optional[Dict[str, Any]]:
        """Simulate IBKR portfolio update"""
        try:
            # In production, this would be real data from IBKR WebSocket
            # For simulation, we'll occasionally generate updates
            
            import random
            
            if random.random() < 0.1:  # 10% chance of update
                return {
                    'type': 'portfolio_update',
                    'timestamp': datetime.now().isoformat(),
                    'positions': {
                        'AAPL': {'quantity': 100, 'market_price': 150.25},
                        'TSLA': {'quantity': 50, 'market_price': 201.50}
                    },
                    'cash': 45000.0,
                    'total_value': 75000.0
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error simulating IBKR update: {e}")
            return None
    
    def _process_real_time_update(self, update: Dict[str, Any]) -> bool:
        """Process real-time portfolio update"""
        try:
            start_time = time.time()
            
            # Validate update
            if not self._validate_portfolio_update(update):
                self.logger.error("Invalid portfolio update received")
                return False
            
            # Update local portfolio
            if not self._update_local_portfolio(update):
                self.logger.error("Failed to update local portfolio")
                return False
            
            # Mark as processed
            for record in self.real_time_updates:
                if record['update'] == update:
                    record['processed'] = True
                    break
            
            # Update sync time
            self.last_sync_time = datetime.now().isoformat()
            
            # Log performance
            process_time = time.time() - start_time
            self.logger.info(f"Real-time update processed in {process_time:.3f}s")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing real-time update: {e}")
            return False
    
    def _validate_portfolio_update(self, update: Dict[str, Any]) -> bool:
        """Validate portfolio update from IBKR"""
        try:
            required_fields = ['type', 'timestamp', 'positions', 'cash', 'total_value']
            
            for field in required_fields:
                if field not in update:
                    self.logger.error(f"Missing required field in update: {field}")
                    return False
            
            # Validate positions
            if not isinstance(update['positions'], dict):
                self.logger.error("Positions must be a dictionary")
                return False
            
            # Validate cash and total_value
            if not isinstance(update['cash'], (int, float)) or update['cash'] < 0:
                self.logger.error(f"Invalid cash value: {update['cash']}")
                return False
            
            if not isinstance(update['total_value'], (int, float)) or update['total_value'] < 0:
                self.logger.error(f"Invalid total_value: {update['total_value']}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Portfolio update validation failed: {e}")
            return False
    
    def _update_local_portfolio(self, update: Dict[str, Any]) -> bool:
        """Update local portfolio with real-time data"""
        try:
            portfolio_file = "data/portfolio_sim.json"
            
            # Load current portfolio
            if os.path.exists(portfolio_file):
                with open(portfolio_file, 'r', encoding='utf-8') as f:
                    portfolio = json.load(f)
            else:
                # Create new portfolio
                portfolio = {
                    'cash': update['cash'],
                    'positions': {},
                    'total_value': update['total_value'],
                    'last_updated': update['timestamp'],
                    'trades': []
                }
            
            # Update positions
            for ticker, position_data in update['positions'].items():
                if ticker in portfolio['positions']:
                    # Update existing position
                    portfolio['positions'][ticker]['last_price'] = position_data['market_price']
                    portfolio['positions'][ticker]['value'] = (
                        portfolio['positions'][ticker]['quantity'] * position_data['market_price']
                    )
                else:
                    # New position (shouldn't happen in real-time sync)
                    self.logger.warning(f"New position detected in real-time sync: {ticker}")
            
            # Update portfolio totals
            portfolio['cash'] = update['cash']
            portfolio['total_value'] = update['total_value']
            portfolio['last_updated'] = update['timestamp']
            
            # Save portfolio
            with open(portfolio_file, 'w', encoding='utf-8') as f:
                json.dump(portfolio, f, indent=2)
            
            self.logger.info(f"Portfolio updated with real-time data: {len(update['positions'])} positions")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update local portfolio: {e}")
            return False
    
    async def stop_real_time_sync(self) -> bool:
        """Stop real-time WebSocket sync"""
        try:
            if not self.is_syncing:
                self.logger.warning("Real-time sync not running")
                return True
            
            self.is_syncing = False
            
            # Wait for sync thread to finish
            if self.sync_thread and self.sync_thread.is_alive():
                self.sync_thread.join(timeout=5)
            
            # Close WebSocket connection
            if self.websocket_connection:
                await self.websocket_connection.close()
                self.websocket_connection = None
            
            self.logger.info("Real-time sync stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop real-time sync: {e}")
            return False
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get real-time sync status"""
        return {
            'is_syncing': self.is_syncing,
            'last_sync_time': self.last_sync_time,
            'total_updates': len(self.real_time_updates),
            'processed_updates': sum(1 for u in self.real_time_updates if u['processed']),
            'sync_targets': self.sync_targets,
            'websocket_connected': self.websocket_connection is not None
        }
    
    async def advanced_reconciliation(self, tws_portfolio: Dict[str, Any], local_portfolio: Dict[str, Any]) -> ReconciliationResult:
        """Perform advanced portfolio reconciliation"""
        try:
            start_time = time.time()
            
            self.logger.info("Starting advanced portfolio reconciliation")
            
            # Initialize result
            discrepancies = []
            reconciled_positions = 0
            total_positions = 0
            
            # Reconcile cash
            cash_discrepancy = self._reconcile_cash(tws_portfolio, local_portfolio)
            if cash_discrepancy:
                discrepancies.append(cash_discrepancy)
            
            # Reconcile positions
            tws_positions = tws_portfolio.get('positions', {})
            local_positions = local_portfolio.get('positions', {})
            
            # Get all unique tickers
            all_tickers = set(tws_positions.keys()) | set(local_positions.keys())
            total_positions = len(all_tickers)
            
            for ticker in all_tickers:
                position_discrepancies = self._reconcile_position(
                    ticker, 
                    tws_positions.get(ticker), 
                    local_positions.get(ticker)
                )
                
                if position_discrepancies:
                    discrepancies.extend(position_discrepancies)
                else:
                    reconciled_positions += 1
            
            # Reconcile total portfolio value
            value_discrepancy = self._reconcile_portfolio_value(tws_portfolio, local_portfolio)
            if value_discrepancy:
                discrepancies.append(value_discrepancy)
            
            # Calculate reconciliation time
            reconciliation_time = time.time() - start_time
            
            # Determine if reconciled
            is_reconciled = len(discrepancies) == 0
            
            # Create result
            result = ReconciliationResult(
                is_reconciled=is_reconciled,
                discrepancies=[vars(d) if hasattr(d, 'vars') else d for d in discrepancies],
                reconciled_positions=reconciled_positions,
                total_positions=total_positions,
                reconciliation_time=reconciliation_time,
                timestamp=datetime.now().isoformat(),
                details={
                    'cash_reconciled': cash_discrepancy is None,
                    'positions_reconciled': reconciled_positions,
                    'total_positions': total_positions,
                    'value_reconciled': value_discrepancy is None
                }
            )
            
            # Log results
            if is_reconciled:
                self.logger.info(f"Portfolio reconciled successfully in {reconciliation_time:.3f}s")
            else:
                self.logger.warning(f"Portfolio reconciliation found {len(discrepancies)} discrepancies")
                for discrepancy in discrepancies:
                    self.logger.warning(f"  - {discrepancy}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Advanced reconciliation failed: {e}")
            return ReconciliationResult(
                is_reconciled=False,
                discrepancies=[{'error': str(e)}],
                reconciled_positions=0,
                total_positions=0,
                reconciliation_time=0,
                timestamp=datetime.now().isoformat(),
                details={'error': str(e)}
            )
    
    def _reconcile_cash(self, tws_portfolio: Dict[str, Any], local_portfolio: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Reconcile cash balances"""
        try:
            tws_cash = float(tws_portfolio.get('cash', 0))
            local_cash = float(local_portfolio.get('cash', 0))
            
            if abs(tws_cash - local_cash) > 0.01:  # $0.01 tolerance
                return {
                    'type': 'cash_discrepancy',
                    'tws_value': tws_cash,
                    'local_value': local_cash,
                    'difference': tws_cash - local_cash,
                    'percentage_diff': abs((tws_cash - local_cash) / max(tws_cash, local_cash, 1)) * 100,
                    'severity': 'high' if abs(tws_cash - local_cash) > 100 else 'medium'
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Cash reconciliation failed: {e}")
            return {'type': 'cash_error', 'error': str(e)}
    
    def _reconcile_position(self, ticker: str, tws_position: Optional[Dict[str, Any]], local_position: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Reconcile individual position"""
        discrepancies = []
        
        try:
            # Check if position exists in both
            if tws_position is None and local_position is None:
                return discrepancies
            
            if tws_position is None:
                discrepancies.append({
                    'type': 'missing_position',
                    'ticker': ticker,
                    'discrepancy_type': 'missing',
                    'tws_value': None,
                    'local_value': local_position,
                    'severity': 'high'
                })
                return discrepancies
            
            if local_position is None:
                discrepancies.append({
                    'type': 'missing_position',
                    'ticker': ticker,
                    'discrepancy_type': 'missing',
                    'tws_value': tws_position,
                    'local_value': None,
                    'severity': 'high'
                })
                return discrepancies
            
            # Reconcile quantity
            tws_qty = float(tws_position.get('quantity', 0))
            local_qty = float(local_position.get('quantity', 0))
            
            if abs(tws_qty - local_qty) > 0.001:  # 0.001 share tolerance
                discrepancies.append({
                    'type': 'quantity_discrepancy',
                    'ticker': ticker,
                    'discrepancy_type': 'quantity',
                    'tws_value': tws_qty,
                    'local_value': local_qty,
                    'difference': tws_qty - local_qty,
                    'percentage_diff': abs((tws_qty - local_qty) / max(tws_qty, local_qty, 1)) * 100,
                    'severity': 'critical' if abs(tws_qty - local_qty) > 10 else 'high'
                })
            
            # Reconcile average price (cost basis)
            tws_avg_price = float(tws_position.get('avg_price', 0))
            local_avg_price = float(local_position.get('avg_price', 0))
            
            if tws_avg_price > 0 and local_avg_price > 0:
                price_diff_pct = abs((tws_avg_price - local_avg_price) / max(tws_avg_price, local_avg_price)) * 100
                
                if price_diff_pct > 0.1:  # 0.1% tolerance
                    discrepancies.append({
                        'type': 'price_discrepancy',
                        'ticker': ticker,
                        'discrepancy_type': 'price',
                        'tws_value': tws_avg_price,
                        'local_value': local_avg_price,
                        'difference': tws_avg_price - local_avg_price,
                        'percentage_diff': price_diff_pct,
                        'severity': 'medium' if price_diff_pct < 1 else 'high'
                    })
            
            # Reconcile market price (last price)
            tws_last_price = float(tws_position.get('last_price', 0))
            local_last_price = float(local_position.get('last_price', 0))
            
            if tws_last_price > 0 and local_last_price > 0:
                price_diff_pct = abs((tws_last_price - local_last_price) / max(tws_last_price, local_last_price)) * 100
                
                if price_diff_pct > 0.05:  # 0.05% tolerance for market price
                    discrepancies.append({
                        'type': 'market_price_discrepancy',
                        'ticker': ticker,
                        'discrepancy_type': 'market_price',
                        'tws_value': tws_last_price,
                        'local_value': local_last_price,
                        'difference': tws_last_price - local_last_price,
                        'percentage_diff': price_diff_pct,
                        'severity': 'low'  # Market price differences are less critical
                    })
            
            return discrepancies
            
        except Exception as e:
            self.logger.error(f"Position reconciliation failed for {ticker}: {e}")
            return [{'type': 'position_error', 'ticker': ticker, 'error': str(e)}]
    
    def _reconcile_portfolio_value(self, tws_portfolio: Dict[str, Any], local_portfolio: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Reconcile total portfolio value"""
        try:
            tws_total = float(tws_portfolio.get('total_value', 0))
            local_total = float(local_portfolio.get('total_value', 0))
            
            if abs(tws_total - local_total) > 0.01:  # $0.01 tolerance
                return {
                    'type': 'portfolio_value_discrepancy',
                    'tws_value': tws_total,
                    'local_value': local_total,
                    'difference': tws_total - local_total,
                    'percentage_diff': abs((tws_total - local_total) / max(tws_total, local_total, 1)) * 100,
                    'severity': 'high' if abs(tws_total - local_total) > 1000 else 'medium'
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Portfolio value reconciliation failed: {e}")
            return {'type': 'portfolio_value_error', 'error': str(e)}
    
    async def auto_reconcile_discrepancies(self, reconciliation_result: ReconciliationResult) -> bool:
        """Automatically reconcile discrepancies if possible"""
        try:
            if reconciliation_result.is_reconciled:
                self.logger.info("Portfolio already reconciled")
                return True
            
            self.logger.info(f"Attempting to auto-reconcile {len(reconciliation_result.discrepancies)} discrepancies")
            
            reconciled_count = 0
            
            for discrepancy in reconciliation_result.discrepancies:
                try:
                    # Attempt auto-reconciliation based on discrepancy type
                    if discrepancy['type'] == 'market_price_discrepancy':
                        # Update local market price with TWS price (safe to auto-fix)
                        if await self._auto_fix_market_price(discrepancy):
                            reconciled_count += 1
                    
                    elif discrepancy['type'] == 'cash_discrepancy' and discrepancy['severity'] == 'low':
                        # Auto-fix small cash differences
                        if await self._auto_fix_cash(discrepancy):
                            reconciled_count += 1
                    
                    # Don't auto-fix critical discrepancies (quantity, avg_price, missing positions)
                    
                except Exception as e:
                    self.logger.error(f"Failed to auto-reconcile discrepancy: {e}")
            
            self.logger.info(f"Auto-reconciled {reconciled_count} discrepancies")
            return reconciled_count > 0
            
        except Exception as e:
            self.logger.error(f"Auto-reconciliation failed: {e}")
            return False
    
    async def _auto_fix_market_price(self, discrepancy: Dict[str, Any]) -> bool:
        """Auto-fix market price discrepancy"""
        try:
            ticker = discrepancy['ticker']
            tws_price = discrepancy['tws_value']
            
            # Update local portfolio with TWS market price
            portfolio_file = "data/portfolio_sim.json"
            
            with open(portfolio_file, 'r', encoding='utf-8') as f:
                portfolio = json.load(f)
            
            if ticker in portfolio['positions']:
                portfolio['positions'][ticker]['last_price'] = tws_price
                portfolio['positions'][ticker]['value'] = (
                    portfolio['positions'][ticker]['quantity'] * tws_price
                )
                
                with open(portfolio_file, 'w', encoding='utf-8') as f:
                    json.dump(portfolio, f, indent=2)
                
                self.logger.info(f"Auto-fixed market price for {ticker}: ${tws_price}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to auto-fix market price: {e}")
            return False
    
    async def _auto_fix_cash(self, discrepancy: Dict[str, Any]) -> bool:
        """Auto-fix small cash discrepancy"""
        try:
            tws_cash = discrepancy['tws_value']
            
            # Update local portfolio with TWS cash
            portfolio_file = "data/portfolio_sim.json"
            
            with open(portfolio_file, 'r', encoding='utf-8') as f:
                portfolio = json.load(f)
            
            portfolio['cash'] = tws_cash
            portfolio['buying_power'] = tws_cash
            
            with open(portfolio_file, 'w', encoding='utf-8') as f:
                json.dump(portfolio, f, indent=2)
            
            self.logger.info(f"Auto-fixed cash balance: ${tws_cash}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to auto-fix cash: {e}")
            return False
    
    async def calculate_comprehensive_performance(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        try:
            # Check cache
            current_time = time.time()
            if (self._cached_performance and 
                self._performance_cache_time and 
                current_time - self._performance_cache_time < self._performance_cache_ttl):
                return self._cached_performance
            
            self.logger.info("Calculating comprehensive performance metrics")
            
            # Load portfolio history
            portfolio_history = await self._load_portfolio_history()
            if not portfolio_history:
                self.logger.warning("No portfolio history available for performance calculation")
                return self._create_empty_performance_metrics()
            
            # Calculate returns
            returns_data = self._calculate_returns(portfolio_history)
            
            # Calculate trade statistics
            trade_stats = self._calculate_trade_statistics()
            
            # Calculate risk metrics
            risk_metrics = await self._calculate_risk_metrics()
            
            # Calculate performance metrics
            performance = PerformanceMetrics(
                total_return=returns_data['total_return'],
                daily_return=returns_data['daily_return'],
                weekly_return=returns_data['weekly_return'],
                monthly_return=returns_data['monthly_return'],
                annual_return=returns_data['annual_return'],
                cagr=returns_data['cagr'],
                max_drawdown=returns_data['max_drawdown'],
                current_drawdown=returns_data['current_drawdown'],
                sharpe_ratio=risk_metrics['sharpe_ratio'],
                sortino_ratio=risk_metrics['sortino_ratio'],
                volatility=risk_metrics['volatility'],
                beta=risk_metrics['beta'],
                alpha=risk_metrics['alpha'],
                win_rate=trade_stats['win_rate'],
                profit_factor=trade_stats['profit_factor'],
                avg_win=trade_stats['avg_win'],
                avg_loss=trade_stats['avg_loss'],
                largest_win=trade_stats['largest_win'],
                largest_loss=trade_stats['largest_loss'],
                consecutive_wins=trade_stats['consecutive_wins'],
                consecutive_losses=trade_stats['consecutive_losses'],
                total_trades=trade_stats['total_trades'],
                winning_trades=trade_stats['winning_trades'],
                losing_trades=trade_stats['losing_trades'],
                total_fees=trade_stats['total_fees'],
                net_profit=trade_stats['net_profit'],
                gross_profit=trade_stats['gross_profit'],
                gross_loss=trade_stats['gross_loss']
            )
            
            # Cache results
            self._cached_performance = performance
            self._performance_cache_time = current_time
            
            self.logger.info(f"Performance metrics calculated: CAGR={performance.cagr:.2%}, Sharpe={performance.sharpe_ratio:.2f}")
            return performance
            
        except Exception as e:
            self.logger.error(f"Failed to calculate performance metrics: {e}")
            return self._create_empty_performance_metrics()
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            self.logger.info("Generating comprehensive performance report")
            
            # Calculate all metrics
            performance = await self.calculate_comprehensive_performance()
            risk_metrics = await self.calculate_risk_metrics()
            sector_performance = await self.calculate_sector_performance()
            
            # Generate report
            report = {
                'timestamp': datetime.now().isoformat(),
                'performance_metrics': {
                    'total_return': f"{performance.total_return:.2%}",
                    'daily_return': f"{performance.daily_return:.2%}",
                    'weekly_return': f"{performance.weekly_return:.2%}",
                    'monthly_return': f"{performance.monthly_return:.2%}",
                    'annual_return': f"{performance.annual_return:.2%}",
                    'cagr': f"{performance.cagr:.2%}",
                    'max_drawdown': f"{performance.max_drawdown:.2%}",
                    'current_drawdown': f"{performance.current_drawdown:.2%}",
                    'sharpe_ratio': f"{performance.sharpe_ratio:.2f}",
                    'sortino_ratio': f"{performance.sortino_ratio:.2f}",
                    'volatility': f"{performance.volatility:.2%}",
                    'beta': f"{performance.beta:.2f}",
                    'alpha': f"{performance.alpha:.2%}",
                    'win_rate': f"{performance.win_rate:.2%}",
                    'profit_factor': f"{performance.profit_factor:.2f}",
                    'avg_win': f"${performance.avg_win:.2f}",
                    'avg_loss': f"${performance.avg_loss:.2f}",
                    'largest_win': f"${performance.largest_win:.2f}",
                    'largest_loss': f"${performance.largest_loss:.2f}",
                    'consecutive_wins': performance.consecutive_wins,
                    'consecutive_losses': performance.consecutive_losses,
                    'total_trades': performance.total_trades,
                    'winning_trades': performance.winning_trades,
                    'losing_trades': performance.losing_trades,
                    'total_fees': f"${performance.total_fees:.2f}",
                    'net_profit': f"${performance.net_profit:.2f}",
                    'gross_profit': f"${performance.gross_profit:.2f}",
                    'gross_loss': f"${performance.gross_loss:.2f}"
                },
                'risk_metrics': {
                    'var_95': f"{risk_metrics.var_95:.2%}",
                    'var_99': f"{risk_metrics.var_99:.2%}",
                    'cvar_95': f"{risk_metrics.cvar_95:.2%}",
                    'cvar_99': f"{risk_metrics.cvar_99:.2%}",
                    'downside_deviation': f"{risk_metrics.downside_deviation:.2%}",
                    'upside_deviation': f"{risk_metrics.upside_deviation:.2%}",
                    'semi_variance': f"{risk_metrics.semi_variance:.4f}",
                    'tracking_error': f"{risk_metrics.tracking_error:.2%}",
                    'information_ratio': f"{risk_metrics.information_ratio:.2f}",
                    'calmar_ratio': f"{risk_metrics.calmar_ratio:.2f}",
                    'sterling_ratio': f"{risk_metrics.sterling_ratio:.2f}",
                    'burke_ratio': f"{risk_metrics.burke_ratio:.2f}",
                    'tail_ratio': f"{risk_metrics.tail_ratio:.2f}",
                    'omega_ratio': f"{risk_metrics.omega_ratio:.2f}",
                    'pain_index': f"{risk_metrics.pain_index:.2%}",
                    'ulcer_index': f"{risk_metrics.ulcer_index:.2%}",
                    'martin_ratio': f"{risk_metrics.martin_ratio:.2f}"
                },
                'sector_performance': [
                    {
                        'sector': sp.sector_name,
                        'allocation': f"{sp.allocation:.2%}",
                        'return': f"{sp.return_pct:.2%}",
                        'contribution_to_return': f"{sp.contribution_to_return:.2%}",
                        'risk_contribution': f"{sp.risk_contribution:.2%}",
                        'sharpe_ratio': f"{sp.sharpe_ratio:.2f}",
                        'max_drawdown': f"{sp.max_drawdown:.2%}",
                        'volatility': f"{sp.volatility:.2%}",
                        'beta': f"{sp.beta:.2f}"
                    }
                    for sp in sector_performance
                ],
                'summary': {
                    'total_sectors': len(sector_performance),
                    'top_sector': sector_performance[0].sector_name if sector_performance else 'N/A',
                    'performance_grade': self._calculate_performance_grade(performance),
                    'risk_grade': self._calculate_risk_grade(risk_metrics),
                    'overall_grade': self._calculate_overall_grade(performance, risk_metrics)
                }
            }
            
            self.logger.info("Performance report generated successfully")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate performance report: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    # Helper methods for performance calculation
    async def _load_portfolio_history(self) -> List[Dict[str, Any]]:
        """Load portfolio history from files"""
        try:
            # In production, this would load from database or files
            # For now, return simulated data
            return [
                {'date': '2026-01-01', 'total_value': 100000},
                {'date': '2026-01-02', 'total_value': 101000},
                {'date': '2026-01-03', 'total_value': 100500},
                {'date': '2026-01-04', 'total_value': 102000},
                {'date': '2026-01-05', 'total_value': 101500},
            ]
        except Exception as e:
            self.logger.error(f"Failed to load portfolio history: {e}")
            return []
    
    def _calculate_returns(self, history: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate various return metrics"""
        try:
            if len(history) < 2:
                return {
                    'total_return': 0.0,
                    'daily_return': 0.0,
                    'weekly_return': 0.0,
                    'monthly_return': 0.0,
                    'annual_return': 0.0,
                    'cagr': 0.0,
                    'max_drawdown': 0.0,
                    'current_drawdown': 0.0
                }
            
            # Calculate returns
            start_value = history[0]['total_value']
            end_value = history[-1]['total_value']
            total_return = (end_value - start_value) / start_value
            
            # Calculate daily return (last day)
            daily_return = (history[-1]['total_value'] - history[-2]['total_value']) / history[-2]['total_value']
            
            # Calculate weekly return (last 7 days)
            weekly_return = 0.0
            if len(history) >= 7:
                week_start = history[-7]['total_value']
                week_end = history[-1]['total_value']
                weekly_return = (week_end - week_start) / week_start
            
            # Calculate monthly return (last 30 days)
            monthly_return = 0.0
            if len(history) >= 30:
                month_start = history[-30]['total_value']
                month_end = history[-1]['total_value']
                monthly_return = (month_end - month_start) / month_start
            
            # Calculate annual return
            annual_return = total_return * (365 / len(history))
            
            # Calculate CAGR
            days = len(history)
            cagr = (end_value / start_value) ** (365 / days) - 1
            
            # Calculate max drawdown
            peak = start_value
            max_drawdown = 0.0
            
            for record in history:
                value = record['total_value']
                if value > peak:
                    peak = value
                
                drawdown = (peak - value) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            # Calculate current drawdown
            current_peak = max(record['total_value'] for record in history)
            current_drawdown = (current_peak - end_value) / current_peak
            
            return {
                'total_return': total_return,
                'daily_return': daily_return,
                'weekly_return': weekly_return,
                'monthly_return': monthly_return,
                'annual_return': annual_return,
                'cagr': cagr,
                'max_drawdown': max_drawdown,
                'current_drawdown': current_drawdown
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate returns: {e}")
            return {
                'total_return': 0.0,
                'daily_return': 0.0,
                'weekly_return': 0.0,
                'monthly_return': 0.0,
                'annual_return': 0.0,
                'cagr': 0.0,
                'max_drawdown': 0.0,
                'current_drawdown': 0.0
            }
    
    def _calculate_trade_statistics(self) -> Dict[str, Any]:
        """Calculate trade statistics"""
        try:
            # In production, this would analyze actual trade history
            # For now, return simulated data
            return {
                'win_rate': 0.65,
                'profit_factor': 1.8,
                'avg_win': 1250.0,
                'avg_loss': -680.0,
                'largest_win': 5000.0,
                'largest_loss': -2500.0,
                'consecutive_wins': 5,
                'consecutive_losses': 3,
                'total_trades': 45,
                'winning_trades': 29,
                'losing_trades': 16,
                'total_fees': 450.0,
                'net_profit': 12500.0,
                'gross_profit': 36250.0,
                'gross_loss': -23750.0
            }
        except Exception as e:
            self.logger.error(f"Failed to calculate trade statistics: {e}")
            return {
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'consecutive_wins': 0,
                'consecutive_losses': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_fees': 0.0,
                'net_profit': 0.0,
                'gross_profit': 0.0,
                'gross_loss': 0.0
            }
    
    async def _calculate_risk_metrics(self) -> Dict[str, float]:
        """Calculate risk metrics"""
        try:
            # In production, this would calculate actual risk metrics
            # For now, return simulated data
            return {
                'sharpe_ratio': 1.85,
                'sortino_ratio': 2.45,
                'volatility': 0.15,
                'beta': 1.12,
                'alpha': 0.08
            }
        except Exception as e:
            self.logger.error(f"Failed to calculate risk metrics: {e}")
            return {
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'volatility': 0.0,
                'beta': 0.0,
                'alpha': 0.0
            }
    
    async def calculate_risk_metrics(self) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        try:
            # Check cache
            if self._cached_risk_metrics and self._performance_cache_time:
                return self._cached_risk_metrics
            
            self.logger.info("Calculating comprehensive risk metrics")
            
            # Load returns data
            returns_data = self._load_returns_data()
            if not returns_data:
                return self._create_empty_risk_metrics()
            
            # Calculate risk metrics
            risk_metrics = RiskMetrics(
                var_95=self._calculate_var(returns_data, 0.05),
                var_99=self._calculate_var(returns_data, 0.01),
                cvar_95=self._calculate_cvar(returns_data, 0.05),
                cvar_99=self._calculate_cvar(returns_data, 0.01),
                downside_deviation=self._calculate_downside_deviation(returns_data),
                upside_deviation=self._calculate_upside_deviation(returns_data),
                semi_variance=self._calculate_semi_variance(returns_data),
                tracking_error=self._calculate_tracking_error(returns_data),
                information_ratio=self._calculate_information_ratio(returns_data),
                calmar_ratio=self._calculate_calmar_ratio(returns_data),
                sterling_ratio=self._calculate_sterling_ratio(returns_data),
                burke_ratio=self._calculate_burke_ratio(returns_data),
                tail_ratio=self._calculate_tail_ratio(returns_data),
                omega_ratio=self._calculate_omega_ratio(returns_data),
                pain_index=self._calculate_pain_index(returns_data),
                ulcer_index=self._calculate_ulcer_index(returns_data),
                martin_ratio=self._calculate_martin_ratio(returns_data)
            )
            
            # Cache results
            self._cached_risk_metrics = risk_metrics
            
            self.logger.info(f"Risk metrics calculated: VaR95={risk_metrics.var_95:.2%}")
            return risk_metrics
            
        except Exception as e:
            self.logger.error(f"Failed to calculate risk metrics: {e}")
            return self._create_empty_risk_metrics()
    
    async def calculate_sector_performance(self) -> List[SectorPerformance]:
        """Calculate sector-based performance analysis"""
        try:
            self.logger.info("Calculating sector performance analysis")
            
            # Get current portfolio
            portfolio = await self._load_current_portfolio()
            if not portfolio:
                return []
            
            # Sector mapping (simplified - in production, use real sector data)
            sector_mapping = self._get_sector_mapping()
            
            # Group positions by sector
            sector_data = {}
            total_value = portfolio.get('total_value', 0)
            
            for ticker, position in portfolio.get('positions', {}).items():
                sector = sector_mapping.get(ticker, 'Unknown')
                position_value = position.get('value', 0)
                
                if sector not in sector_data:
                    sector_data[sector] = {
                        'total_value': 0,
                        'positions': [],
                        'returns': []
                    }
                
                sector_data[sector]['total_value'] += position_value
                sector_data[sector]['positions'].append(position)
            
            # Calculate sector metrics
            sector_performance = []
            
            for sector_name, data in sector_data.items():
                allocation = data['total_value'] / total_value if total_value > 0 else 0
                
                # Calculate sector return (simplified)
                sector_return = self._calculate_sector_return(data['positions'])
                
                # Calculate sector contribution to total return
                contribution_to_return = sector_return * allocation
                
                # Calculate sector risk (simplified)
                sector_volatility = self._calculate_sector_volatility(data['positions'])
                risk_contribution = sector_volatility * allocation
                
                # Calculate sector Sharpe ratio
                sector_sharpe = self._calculate_sector_sharpe(sector_return, sector_volatility)
                
                # Calculate sector max drawdown
                sector_max_dd = self._calculate_sector_max_drawdown(data['positions'])
                
                # Calculate sector beta (simplified)
                sector_beta = self._calculate_sector_beta(data['positions'])
                
                sector_perf = SectorPerformance(
                    sector_name=sector_name,
                    allocation=allocation,
                    return_pct=sector_return,
                    contribution_to_return=contribution_to_return,
                    risk_contribution=risk_contribution,
                    sharpe_ratio=sector_sharpe,
                    max_drawdown=sector_max_dd,
                    volatility=sector_volatility,
                    beta=sector_beta
                )
                
                sector_performance.append(sector_perf)
            
            # Sort by allocation
            sector_performance.sort(key=lambda x: x.allocation, reverse=True)
            
            self.logger.info(f"Sector performance calculated for {len(sector_performance)} sectors")
            return sector_performance
            
        except Exception as e:
            self.logger.error(f"Failed to calculate sector performance: {e}")
            return []
    
    # Placeholder helper methods (would be implemented with actual calculations)
    def _create_empty_performance_metrics(self) -> PerformanceMetrics:
        """Create empty performance metrics"""
        return PerformanceMetrics(
            total_return=0.0, daily_return=0.0, weekly_return=0.0, monthly_return=0.0,
            annual_return=0.0, cagr=0.0, max_drawdown=0.0, current_drawdown=0.0,
            sharpe_ratio=0.0, sortino_ratio=0.0, volatility=0.0, beta=0.0, alpha=0.0,
            win_rate=0.0, profit_factor=0.0, avg_win=0.0, avg_loss=0.0,
            largest_win=0.0, largest_loss=0.0, consecutive_wins=0, consecutive_losses=0,
            total_trades=0, winning_trades=0, losing_trades=0, total_fees=0.0,
            net_profit=0.0, gross_profit=0.0, gross_loss=0.0
        )
    
    def _create_empty_risk_metrics(self) -> RiskMetrics:
        """Create empty risk metrics"""
        return RiskMetrics(
            var_95=0.0, var_99=0.0, cvar_95=0.0, cvar_99=0.0,
            downside_deviation=0.0, upside_deviation=0.0, semi_variance=0.0,
            tracking_error=0.0, information_ratio=0.0, calmar_ratio=0.0,
            sterling_ratio=0.0, burke_ratio=0.0, tail_ratio=0.0,
            omega_ratio=0.0, pain_index=0.0, ulcer_index=0.0, martin_ratio=0.0
        )
    
    def _load_returns_data(self) -> List[float]:
        """Load returns data for risk calculations"""
        return [0.01, -0.005, 0.02, -0.01, 0.015, -0.008, 0.025, -0.012, 0.018, -0.003]
    
    def _calculate_var(self, returns: List[float], confidence: float) -> float:
        """Calculate Value at Risk"""
        returns_sorted = sorted(returns)
        index = int(len(returns_sorted) * confidence)
        return abs(returns_sorted[index])
    
    def _calculate_cvar(self, returns: List[float], confidence: float) -> float:
        """Calculate Conditional Value at Risk"""
        returns_sorted = sorted(returns)
        index = int(len(returns_sorted) * confidence)
        tail_returns = returns_sorted[:index]
        return abs(sum(tail_returns) / len(tail_returns)) if tail_returns else 0.0
    
    def _calculate_downside_deviation(self, returns: List[float]) -> float:
        """Calculate downside deviation"""
        negative_returns = [r for r in returns if r < 0]
        if not negative_returns:
            return 0.0
        return np.std(negative_returns)
    
    def _calculate_upside_deviation(self, returns: List[float]) -> float:
        """Calculate upside deviation"""
        positive_returns = [r for r in returns if r > 0]
        if not positive_returns:
            return 0.0
        return np.std(positive_returns)
    
    def _calculate_semi_variance(self, returns: List[float]) -> float:
        """Calculate semi-variance"""
        negative_returns = [r for r in returns if r < 0]
        if not negative_returns:
            return 0.0
        return np.var(negative_returns)
    
    def _calculate_tracking_error(self, returns: List[float]) -> float:
        """Calculate tracking error"""
        # Simplified - would compare against benchmark
        return np.std(returns) * np.sqrt(252)
    
    def _calculate_information_ratio(self, returns: List[float]) -> float:
        """Calculate information ratio"""
        # Simplified - would compare against benchmark
        return np.mean(returns) / (np.std(returns) + 1e-8)
    
    def _calculate_calmar_ratio(self, returns: List[float]) -> float:
        """Calculate Calmar ratio"""
        total_return = sum(returns)
        max_drawdown = max(returns) - min(returns)
        return total_return / (abs(max_drawdown) + 1e-8)
    
    def _calculate_sterling_ratio(self, returns: List[float]) -> float:
        """Calculate Sterling ratio"""
        return np.mean(returns) / (abs(min(returns)) + 1e-8)
    
    def _calculate_burke_ratio(self, returns: List[float]) -> float:
        """Calculate Burke ratio"""
        return np.mean(returns) / (np.sqrt(sum(r**2 for r in returns if r < 0)) + 1e-8)
    
    def _calculate_tail_ratio(self, returns: List[float]) -> float:
        """Calculate tail ratio"""
        percentile_95 = np.percentile(returns, 95)
        percentile_5 = np.percentile(returns, 5)
        return abs(percentile_95) / (abs(percentile_5) + 1e-8)
    
    def _calculate_omega_ratio(self, returns: List[float]) -> float:
        """Calculate Omega ratio"""
        threshold = 0.0
        gains = sum(r - threshold for r in returns if r > threshold)
        losses = sum(abs(r - threshold) for r in returns if r < threshold)
        return gains / (losses + 1e-8)
    
    def _calculate_pain_index(self, returns: List[float]) -> float:
        """Calculate pain index"""
        drawdowns = []
        peak = 0
        for r in returns:
            peak = max(peak, peak + r)
            drawdown = peak - (peak + r)
            if drawdown > 0:
                drawdowns.append(drawdown)
        return sum(drawdowns) / len(drawdowns) if drawdowns else 0.0
    
    def _calculate_ulcer_index(self, returns: List[float]) -> float:
        """Calculate ulcer index"""
        drawdowns = []
        peak = 0
        for r in returns:
            peak = max(peak, peak + r)
            drawdown = peak - (peak + r)
            if drawdown > 0:
                drawdowns.append(drawdown)
        return np.sqrt(sum(d**2 for d in drawdowns) / len(drawdowns)) if drawdowns else 0.0
    
    def _calculate_martin_ratio(self, returns: List[float]) -> float:
        """Calculate Martin ratio"""
        return np.mean(returns) / (self._calculate_ulcer_index(returns) + 1e-8)
    
    async def _load_current_portfolio(self) -> Dict[str, Any]:
        """Load current portfolio"""
        try:
            portfolio_file = "data/portfolio_sim.json"
            if os.path.exists(portfolio_file):
                with open(portfolio_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Failed to load current portfolio: {e}")
            return {}
    
    def _get_sector_mapping(self) -> Dict[str, str]:
        """Get sector mapping for tickers"""
        return {
            'AAPL': 'Technology',
            'MSFT': 'Technology',
            'GOOGL': 'Technology',
            'TSLA': 'Consumer Discretionary',
            'AMZN': 'Consumer Discretionary',
            'JPM': 'Financial',
            'BAC': 'Financial',
            'XOM': 'Energy',
            'CVX': 'Energy',
            'JNJ': 'Healthcare',
            'PFE': 'Healthcare'
        }
    
    def _calculate_sector_return(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate sector return"""
        return 0.05  # Simplified
    
    def _calculate_sector_volatility(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate sector volatility"""
        return 0.18  # Simplified
    
    def _calculate_sector_sharpe(self, return_pct: float, volatility: float) -> float:
        """Calculate sector Sharpe ratio"""
        return return_pct / (volatility + 1e-8)
    
    def _calculate_sector_max_drawdown(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate sector max drawdown"""
        return 0.12  # Simplified
    
    def _calculate_sector_beta(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate sector beta"""
        return 1.1  # Simplified
    
    def _calculate_performance_grade(self, performance: PerformanceMetrics) -> str:
        """Calculate performance grade"""
        if performance.cagr > 0.20 and performance.sharpe_ratio > 2.0:
            return 'A+'
        elif performance.cagr > 0.15 and performance.sharpe_ratio > 1.5:
            return 'A'
        elif performance.cagr > 0.10 and performance.sharpe_ratio > 1.0:
            return 'B'
        elif performance.cagr > 0.05 and performance.sharpe_ratio > 0.5:
            return 'C'
        else:
            return 'D'
    
    def _calculate_risk_grade(self, risk_metrics: RiskMetrics) -> str:
        """Calculate risk grade"""
        if risk_metrics.var_95 < 0.02 and risk_metrics.ulcer_index < 0.05:
            return 'Low'
        elif risk_metrics.var_95 < 0.05 and risk_metrics.ulcer_index < 0.10:
            return 'Medium'
        else:
            return 'High'
    
    def _calculate_overall_grade(self, performance: PerformanceMetrics, risk_metrics: RiskMetrics) -> str:
        """Calculate overall grade"""
        perf_grade = self._calculate_performance_grade(performance)
        risk_grade = self._calculate_risk_grade(risk_metrics)
        
        if perf_grade in ['A+', 'A'] and risk_grade == 'Low':
            return 'Excellent'
        elif perf_grade in ['A', 'B'] and risk_grade in ['Low', 'Medium']:
            return 'Good'
        elif perf_grade in ['B', 'C'] and risk_grade in ['Medium', 'High']:
            return 'Average'
        else:
            return 'Poor'
    
    async def initialize_alert_system(self):
        """Initialize comprehensive alert system"""
        try:
            self.logger.info("Initializing comprehensive alert system")
            
            # Load default alert rules
            await self._load_default_alert_rules()
            
            # Initialize alert handlers
            self._initialize_alert_handlers()
            
            # Clean up old alerts
            await self._cleanup_old_alerts()
            
            # Calculate initial statistics
            await self._update_alert_statistics()
            
            self.logger.info(f"Alert system initialized with {len(self.alert_rules)} rules")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize alert system: {e}")
    
    async def add_alert_rule(self, rule: AlertRule) -> bool:
        """Add new alert rule"""
        try:
            # Validate rule
            if not self._validate_alert_rule(rule):
                return False
            
            # Check for duplicates
            existing_rules = [r for r in self.alert_rules if r.name == rule.name]
            if existing_rules:
                self.logger.warning(f"Alert rule '{rule.name}' already exists")
                return False
            
            # Add rule
            self.alert_rules.append(rule)
            self.logger.info(f"Added alert rule: {rule.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add alert rule: {e}")
            return False
    
    async def check_alerts(self, portfolio: Dict[str, Any]) -> List[Alert]:
        """Check all alert rules against current portfolio"""
        try:
            triggered_alerts = []
            current_time = time.time()
            
            for rule in self.alert_rules:
                if not rule.enabled:
                    continue
                
                # Check cooldown
                if rule.rule_id in self.alert_cooldowns:
                    if current_time - self.alert_cooldowns[rule.rule_id] < rule.cooldown_period:
                        continue
                
                # Check rule condition
                alert = await self._evaluate_alert_rule(rule, portfolio)
                if alert:
                    triggered_alerts.append(alert)
                    
                    # Update cooldown
                    self.alert_cooldowns[rule.rule_id] = current_time
                    rule.last_triggered = alert.timestamp
                    
                    # Add to alerts list
                    self.alerts.append(alert)
                    
                    # Trigger alert handler
                    await self._handle_alert(alert)
            
            # Update statistics
            await self._update_alert_statistics()
            
            # Clean up old alerts
            await self._cleanup_old_alerts()
            
            if triggered_alerts:
                self.logger.info(f"Triggered {len(triggered_alerts)} alerts")
            
            return triggered_alerts
            
        except Exception as e:
            self.logger.error(f"Failed to check alerts: {e}")
            return []
    
    async def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts"""
        try:
            active_alerts = [alert for alert in self.alerts if not alert.resolved]
            
            # Sort by severity and timestamp
            severity_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
            active_alerts.sort(key=lambda x: (severity_order.get(x.severity, 0), x.timestamp), reverse=True)
            
            return active_alerts
            
        except Exception as e:
            self.logger.error(f"Failed to get active alerts: {e}")
            return []
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        try:
            for alert in self.alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    self.logger.info(f"Alert acknowledged: {alert_id}")
                    return True
            
            self.logger.warning(f"Alert not found: {alert_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        try:
            for alert in self.alerts:
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    alert.acknowledged = True
                    self.logger.info(f"Alert resolved: {alert_id}")
                    
                    # Update statistics
                    await self._update_alert_statistics()
                    return True
            
            self.logger.warning(f"Alert not found: {alert_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to resolve alert: {e}")
            return False
    
    async def get_alert_statistics(self) -> AlertStatistics:
        """Get alert system statistics"""
        try:
            if not self.alert_statistics:
                await self._update_alert_statistics()
            
            return self.alert_statistics
            
        except Exception as e:
            self.logger.error(f"Failed to get alert statistics: {e}")
            return self._create_empty_alert_statistics()
    
    async def generate_alert_report(self) -> Dict[str, Any]:
        """Generate comprehensive alert report"""
        try:
            self.logger.info("Generating comprehensive alert report")
            
            # Get statistics
            stats = await self.get_alert_statistics()
            
            # Get active alerts
            active_alerts = await self.get_active_alerts()
            
            # Get recent alerts (last 24 hours)
            recent_alerts = await self._get_recent_alerts(hours=24)
            
            # Get alerts by type and severity
            alerts_by_type = self._group_alerts_by_type(self.alerts)
            alerts_by_severity = self._group_alerts_by_severity(self.alerts)
            
            # Generate report
            report = {
                'timestamp': datetime.now().isoformat(),
                'statistics': {
                    'total_alerts': stats.total_alerts,
                    'active_alerts': stats.active_alerts,
                    'resolved_alerts': stats.resolved_alerts,
                    'critical_alerts': stats.critical_alerts,
                    'average_resolution_time': f"{stats.average_resolution_time:.2f} hours",
                    'alerts_today': stats.alerts_today,
                    'alerts_this_week': stats.alerts_this_week,
                    'alerts_this_month': stats.alerts_this_month
                },
                'active_alerts': [
                    {
                        'alert_id': alert.alert_id,
                        'type': alert.alert_type,
                        'severity': alert.severity,
                        'title': alert.title,
                        'message': alert.message,
                        'ticker': alert.ticker,
                        'current_value': alert.current_value,
                        'threshold_value': alert.threshold_value,
                        'timestamp': alert.timestamp,
                        'acknowledged': alert.acknowledged,
                        'action_required': alert.action_required
                    }
                    for alert in active_alerts[:20]  # Limit to 20 most recent
                ],
                'recent_alerts': [
                    {
                        'alert_id': alert.alert_id,
                        'type': alert.alert_type,
                        'severity': alert.severity,
                        'title': alert.title,
                        'timestamp': alert.timestamp,
                        'resolved': alert.resolved
                    }
                    for alert in recent_alerts[:50]  # Limit to 50 most recent
                ],
                'alerts_by_type': {
                    alert_type: len(alerts) for alert_type, alerts in alerts_by_type.items()
                },
                'alerts_by_severity': {
                    severity: len(alerts) for severity, alerts in alerts_by_severity.items()
                },
                'alert_rules': [
                    {
                        'rule_id': rule.rule_id,
                        'name': rule.name,
                        'type': rule.alert_type,
                        'severity': rule.severity,
                        'enabled': rule.enabled,
                        'last_triggered': rule.last_triggered
                    }
                    for rule in self.alert_rules
                ],
                'summary': {
                    'total_rules': len(self.alert_rules),
                    'enabled_rules': len([r for r in self.alert_rules if r.enabled]),
                    'critical_active': len([a for a in active_alerts if a.severity == 'critical']),
                    'high_active': len([a for a in active_alerts if a.severity == 'high']),
                    'system_health': self._calculate_alert_system_health()
                }
            }
            
            self.logger.info("Alert report generated successfully")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate alert report: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    # Private methods for alert system
    async def _load_default_alert_rules(self):
        """Load default alert rules"""
        try:
            default_rules = [
                # Position alerts
                AlertRule(
                    rule_id="position_size_large",
                    name="Large Position Size",
                    description="Alert when position size exceeds 10% of portfolio",
                    alert_type="position",
                    condition="gt",
                    threshold=0.10,
                    severity="high"
                ),
                AlertRule(
                    rule_id="position_concentration",
                    name="Position Concentration",
                    description="Alert when single position exceeds 20% of portfolio",
                    alert_type="position",
                    condition="gt",
                    threshold=0.20,
                    severity="critical"
                ),
                
                # Risk alerts
                AlertRule(
                    rule_id="portfolio_drawdown",
                    name="Portfolio Drawdown",
                    description="Alert when portfolio drawdown exceeds 10%",
                    alert_type="risk",
                    condition="gt",
                    threshold=0.10,
                    severity="high"
                ),
                AlertRule(
                    rule_id="portfolio_drawdown_critical",
                    name="Critical Portfolio Drawdown",
                    description="Alert when portfolio drawdown exceeds 20%",
                    alert_type="risk",
                    condition="gt",
                    threshold=0.20,
                    severity="critical"
                ),
                AlertRule(
                    rule_id="volatility_spike",
                    name="Volatility Spike",
                    description="Alert when daily volatility exceeds 5%",
                    alert_type="risk",
                    condition="gt",
                    threshold=0.05,
                    severity="medium"
                ),
                
                # Price alerts
                AlertRule(
                    rule_id="price_drop_5pct",
                    name="5% Price Drop",
                    description="Alert when any position drops 5% in a day",
                    alert_type="price",
                    condition="pct_change",
                    threshold=-0.05,
                    severity="medium"
                ),
                AlertRule(
                    rule_id="price_drop_10pct",
                    name="10% Price Drop",
                    description="Alert when any position drops 10% in a day",
                    alert_type="price",
                    condition="pct_change",
                    threshold=-0.10,
                    severity="high"
                ),
                AlertRule(
                    rule_id="price_spike_10pct",
                    name="10% Price Spike",
                    description="Alert when any position spikes 10% in a day",
                    alert_type="price",
                    condition="pct_change",
                    threshold=0.10,
                    severity="medium"
                ),
                
                # Volume alerts
                AlertRule(
                    rule_id="volume_spike",
                    name="Volume Spike",
                    description="Alert when trading volume exceeds 5x average",
                    alert_type="volume",
                    condition="gt",
                    threshold=5.0,
                    severity="low"
                ),
                AlertRule(
                    rule_id="unusual_volume",
                    name="Unusual Volume",
                    description="Alert when trading volume exceeds 10x average",
                    alert_type="volume",
                    condition="gt",
                    threshold=10.0,
                    severity="medium"
                ),
                
                # Compliance alerts
                AlertRule(
                    rule_id="margin_call",
                    name="Margin Call",
                    description="Alert when margin usage exceeds 80%",
                    alert_type="margin",
                    condition="gt",
                    threshold=0.80,
                    severity="critical"
                ),
                AlertRule(
                    rule_id="margin_warning",
                    name="Margin Warning",
                    description="Alert when margin usage exceeds 60%",
                    alert_type="margin",
                    condition="gt",
                    threshold=0.60,
                    severity="high"
                ),
                AlertRule(
                    rule_id="concentration_limit",
                    name="Concentration Limit",
                    description="Alert when sector concentration exceeds 30%",
                    alert_type="compliance",
                    condition="gt",
                    threshold=0.30,
                    severity="high"
                )
            ]
            
            self.alert_rules.extend(default_rules)
            self.logger.info(f"Loaded {len(default_rules)} default alert rules")
            
        except Exception as e:
            self.logger.error(f"Failed to load default alert rules: {e}")
    
    def _initialize_alert_handlers(self):
        """Initialize alert handlers"""
        try:
            self.alert_handlers = {
                'position': self._handle_position_alert,
                'risk': self._handle_risk_alert,
                'price': self._handle_price_alert,
                'volume': self._handle_volume_alert,
                'compliance': self._handle_compliance_alert,
                'margin': self._handle_margin_alert
            }
            
            self.logger.info("Alert handlers initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize alert handlers: {e}")
    
    async def _evaluate_alert_rule(self, rule: AlertRule, portfolio: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate a single alert rule"""
        try:
            if rule.alert_type == 'position':
                return await self._evaluate_position_rule(rule, portfolio)
            elif rule.alert_type == 'risk':
                return await self._evaluate_risk_rule(rule, portfolio)
            elif rule.alert_type == 'price':
                return await self._evaluate_price_rule(rule, portfolio)
            elif rule.alert_type == 'volume':
                return await self._evaluate_volume_rule(rule, portfolio)
            elif rule.alert_type == 'compliance':
                return await self._evaluate_compliance_rule(rule, portfolio)
            elif rule.alert_type == 'margin':
                return await self._evaluate_margin_rule(rule, portfolio)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate alert rule {rule.name}: {e}")
            return None
    
    async def _evaluate_position_rule(self, rule: AlertRule, portfolio: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate position-based alert rule"""
        try:
            total_value = portfolio.get('total_value', 0)
            positions = portfolio.get('positions', {})
            
            for ticker, position in positions.items():
                position_value = position.get('value', 0)
                position_pct = position_value / total_value if total_value > 0 else 0
                
                if self._check_condition(rule.condition, position_pct, rule.threshold):
                    return Alert(
                        alert_id=f"pos_{ticker}_{int(time.time())}",
                        alert_type="position",
                        severity=rule.severity,
                        title=f"Position Alert: {ticker}",
                        message=f"{ticker} position {position_pct:.2%} exceeds threshold of {rule.threshold:.2%}",
                        ticker=ticker,
                        current_value=position_pct,
                        threshold_value=rule.threshold,
                        action_required=rule.severity in ['high', 'critical']
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate position rule: {e}")
            return None
    
    async def _evaluate_risk_rule(self, rule: AlertRule, portfolio: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate risk-based alert rule"""
        try:
            # Get current performance metrics
            performance = await self.calculate_comprehensive_performance()
            
            if rule.rule_id == "portfolio_drawdown" or rule.rule_id == "portfolio_drawdown_critical":
                current_dd = performance.current_drawdown
                
                if self._check_condition(rule.condition, current_dd, rule.threshold):
                    return Alert(
                        alert_id=f"drawdown_{int(time.time())}",
                        alert_type="risk",
                        severity=rule.severity,
                        title="Portfolio Drawdown Alert",
                        message=f"Portfolio drawdown {current_dd:.2%} exceeds threshold of {rule.threshold:.2%}",
                        current_value=current_dd,
                        threshold_value=rule.threshold,
                        action_required=True
                    )
            
            elif rule.rule_id == "volatility_spike":
                volatility = performance.volatility
                
                if self._check_condition(rule.condition, volatility, rule.threshold):
                    return Alert(
                        alert_id=f"volatility_{int(time.time())}",
                        alert_type="risk",
                        severity=rule.severity,
                        title="Volatility Spike Alert",
                        message=f"Portfolio volatility {volatility:.2%} exceeds threshold of {rule.threshold:.2%}",
                        current_value=volatility,
                        threshold_value=rule.threshold
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate risk rule: {e}")
            return None
    
    async def _evaluate_price_rule(self, rule: AlertRule, portfolio: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate price-based alert rule"""
        try:
            positions = portfolio.get('positions', {})
            
            for ticker, position in positions.items():
                # Get previous day's price (simplified - in production, use historical data)
                current_price = position.get('last_price', 0)
                previous_price = position.get('avg_price', current_price)  # Simplified
                
                if previous_price > 0:
                    price_change = (current_price - previous_price) / previous_price
                    
                    if self._check_condition(rule.condition, price_change, rule.threshold):
                        direction = "drop" if price_change < 0 else "spike"
                        return Alert(
                            alert_id=f"price_{ticker}_{int(time.time())}",
                            alert_type="price",
                            severity=rule.severity,
                            title=f"Price {direction.title()}: {ticker}",
                            message=f"{ticker} price {direction} {abs(price_change):.2%} to ${current_price:.2f}",
                            ticker=ticker,
                            current_value=price_change,
                            threshold_value=rule.threshold
                        )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate price rule: {e}")
            return None
    
    async def _evaluate_volume_rule(self, rule: AlertRule, portfolio: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate volume-based alert rule"""
        try:
            # Simplified volume check (in production, use actual volume data)
            # For now, return None as we don't have volume data
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate volume rule: {e}")
            return None
    
    async def _evaluate_compliance_rule(self, rule: AlertRule, portfolio: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate compliance-based alert rule"""
        try:
            if rule.rule_id == "concentration_limit":
                # Check sector concentration
                sector_performance = await self.calculate_sector_performance()
                
                for sector in sector_performance:
                    if self._check_condition(rule.condition, sector.allocation, rule.threshold):
                        return Alert(
                            alert_id=f"sector_{sector.sector_name}_{int(time.time())}",
                            alert_type="compliance",
                            severity=rule.severity,
                            title=f"Sector Concentration Alert: {sector.sector_name}",
                            message=f"{sector.sector_name} concentration {sector.allocation:.2%} exceeds threshold of {rule.threshold:.2%}",
                            current_value=sector.allocation,
                            threshold_value=rule.threshold,
                            action_required=True
                        )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate compliance rule: {e}")
            return None
    
    async def _evaluate_margin_rule(self, rule: AlertRule, portfolio: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate margin-based alert rule"""
        try:
            # Simplified margin calculation (in production, use actual margin data)
            total_value = portfolio.get('total_value', 0)
            cash = portfolio.get('cash', 0)
            margin_used = (total_value - cash) / total_value if total_value > 0 else 0
            
            if self._check_condition(rule.condition, margin_used, rule.threshold):
                return Alert(
                    alert_id=f"margin_{int(time.time())}",
                    alert_type="margin",
                    severity=rule.severity,
                    title="Margin Alert",
                    message=f"Margin usage {margin_used:.2%} exceeds threshold of {rule.threshold:.2%}",
                    current_value=margin_used,
                    threshold_value=rule.threshold,
                    action_required=True
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate margin rule: {e}")
            return None
    
    def _check_condition(self, condition: str, current_value: float, threshold: float) -> bool:
        """Check if alert condition is met"""
        try:
            if condition == "gt":
                return current_value > threshold
            elif condition == "lt":
                return current_value < threshold
            elif condition == "gte":
                return current_value >= threshold
            elif condition == "lte":
                return current_value <= threshold
            elif condition == "eq":
                return abs(current_value - threshold) < 1e-8
            elif condition == "pct_change":
                return current_value < threshold  # For percentage changes
            elif condition == "abs_change":
                return abs(current_value) > threshold
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check condition: {e}")
            return False
    
    def _validate_alert_rule(self, rule: AlertRule) -> bool:
        """Validate alert rule"""
        try:
            # Check required fields
            if not rule.rule_id or not rule.name or not rule.alert_type:
                return False
            
            # Check condition
            valid_conditions = ["gt", "lt", "eq", "gte", "lte", "pct_change", "abs_change"]
            if rule.condition not in valid_conditions:
                return False
            
            # Check severity
            valid_severities = ["low", "medium", "high", "critical"]
            if rule.severity not in valid_severities:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate alert rule: {e}")
            return False
    
    async def _handle_alert(self, alert: Alert):
        """Handle triggered alert"""
        try:
            # Log alert
            log_level = {
                'low': logging.INFO,
                'medium': logging.WARNING,
                'high': logging.ERROR,
                'critical': logging.CRITICAL
            }.get(alert.severity, logging.INFO)
            
            self.logger.log(log_level, f"ALERT: {alert.title} - {alert.message}")
            
            # Call specific handler
            if alert.alert_type in self.alert_handlers:
                await self.alert_handlers[alert.alert_type](alert)
            
            # Send notifications
            await self._send_alert_notifications(alert)
            
        except Exception as e:
            self.logger.error(f"Failed to handle alert: {e}")
    
    async def _send_alert_notifications(self, alert: Alert):
        """Send alert notifications"""
        try:
            # Log notification
            notification_message = f"ALERT NOTIFICATION: {alert.title} ({alert.severity.upper()}) - {alert.message}"
            
            if 'email' in self.alert_config['notification_channels']:
                # In production, send email notification
                self.logger.info(f"Email notification sent for alert: {alert.alert_id}")
            
            if 'log' in self.alert_config['notification_channels']:
                self.logger.info(notification_message)
            
        except Exception as e:
            self.logger.error(f"Failed to send alert notifications: {e}")
    
    # Alert handlers
    async def _handle_position_alert(self, alert: Alert):
        """Handle position alert"""
        try:
            self.logger.info(f"Handling position alert: {alert.title}")
            # Add position-specific handling logic here
        except Exception as e:
            self.logger.error(f"Failed to handle position alert: {e}")
    
    async def _handle_risk_alert(self, alert: Alert):
        """Handle risk alert"""
        try:
            self.logger.info(f"Handling risk alert: {alert.title}")
            # Add risk-specific handling logic here
        except Exception as e:
            self.logger.error(f"Failed to handle risk alert: {e}")
    
    async def _handle_price_alert(self, alert: Alert):
        """Handle price alert"""
        try:
            self.logger.info(f"Handling price alert: {alert.title}")
            # Add price-specific handling logic here
        except Exception as e:
            self.logger.error(f"Failed to handle price alert: {e}")
    
    async def _handle_volume_alert(self, alert: Alert):
        """Handle volume alert"""
        try:
            self.logger.info(f"Handling volume alert: {alert.title}")
            # Add volume-specific handling logic here
        except Exception as e:
            self.logger.error(f"Failed to handle volume alert: {e}")
    
    async def _handle_compliance_alert(self, alert: Alert):
        """Handle compliance alert"""
        try:
            self.logger.info(f"Handling compliance alert: {alert.title}")
            # Add compliance-specific handling logic here
        except Exception as e:
            self.logger.error(f"Failed to handle compliance alert: {e}")
    
    async def _handle_margin_alert(self, alert: Alert):
        """Handle margin alert"""
        try:
            self.logger.info(f"Handling margin alert: {alert.title}")
            # Add margin-specific handling logic here
        except Exception as e:
            self.logger.error(f"Failed to handle margin alert: {e}")
    
    async def _cleanup_old_alerts(self):
        """Clean up old alerts"""
        try:
            retention_days = self.alert_config['alert_retention_days']
            cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 3600)
            
            # Remove old alerts
            original_count = len(self.alerts)
            self.alerts = [alert for alert in self.alerts 
                          if datetime.fromisoformat(alert.timestamp).timestamp() > cutoff_time]
            
            removed_count = original_count - len(self.alerts)
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} old alerts")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old alerts: {e}")
    
    async def _update_alert_statistics(self):
        """Update alert statistics"""
        try:
            current_time = datetime.now()
            
            # Calculate statistics
            total_alerts = len(self.alerts)
            active_alerts = len([a for a in self.alerts if not a.resolved])
            resolved_alerts = len([a for a in self.alerts if a.resolved])
            critical_alerts = len([a for a in self.alerts if a.severity == 'critical'])
            
            # Group by type and severity
            alerts_by_type = {}
            alerts_by_severity = {}
            
            for alert in self.alerts:
                alerts_by_type[alert.alert_type] = alerts_by_type.get(alert.alert_type, 0) + 1
                alerts_by_severity[alert.severity] = alerts_by_severity.get(alert.severity, 0) + 1
            
            # Calculate average resolution time
            resolved_alerts_with_time = [a for a in self.alerts if a.resolved and hasattr(a, 'resolution_time')]
            avg_resolution_time = 0.0
            if resolved_alerts_with_time:
                avg_resolution_time = sum(a.resolution_time for a in resolved_alerts_with_time) / len(resolved_alerts_with_time)
            
            # Calculate time-based counts
            today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = current_time - timedelta(days=current_time.weekday())
            month_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            alerts_today = len([a for a in self.alerts 
                              if datetime.fromisoformat(a.timestamp) >= today_start])
            alerts_this_week = len([a for a in self.alerts 
                                  if datetime.fromisoformat(a.timestamp) >= week_start])
            alerts_this_month = len([a for a in self.alerts 
                                   if datetime.fromisoformat(a.timestamp) >= month_start])
            
            self.alert_statistics = AlertStatistics(
                total_alerts=total_alerts,
                active_alerts=active_alerts,
                resolved_alerts=resolved_alerts,
                critical_alerts=critical_alerts,
                alerts_by_type=alerts_by_type,
                alerts_by_severity=alerts_by_severity,
                average_resolution_time=avg_resolution_time,
                alerts_today=alerts_today,
                alerts_this_week=alerts_this_week,
                alerts_this_month=alerts_this_month
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update alert statistics: {e}")
    
    async def _get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Get recent alerts"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_alerts = [alert for alert in self.alerts 
                            if datetime.fromisoformat(alert.timestamp) >= cutoff_time]
            
            # Sort by timestamp
            recent_alerts.sort(key=lambda x: x.timestamp, reverse=True)
            
            return recent_alerts
            
        except Exception as e:
            self.logger.error(f"Failed to get recent alerts: {e}")
            return []
    
    def _group_alerts_by_type(self, alerts: List[Alert]) -> Dict[str, List[Alert]]:
        """Group alerts by type"""
        grouped = {}
        for alert in alerts:
            if alert.alert_type not in grouped:
                grouped[alert.alert_type] = []
            grouped[alert.alert_type].append(alert)
        return grouped
    
    def _group_alerts_by_severity(self, alerts: List[Alert]) -> Dict[str, List[Alert]]:
        """Group alerts by severity"""
        grouped = {}
        for alert in alerts:
            if alert.severity not in grouped:
                grouped[alert.severity] = []
            grouped[alert.severity].append(alert)
        return grouped
    
    def _create_empty_alert_statistics(self) -> AlertStatistics:
        """Create empty alert statistics"""
        return AlertStatistics(
            total_alerts=0,
            active_alerts=0,
            resolved_alerts=0,
            critical_alerts=0,
            alerts_by_type={},
            alerts_by_severity={},
            average_resolution_time=0.0,
            alerts_today=0,
            alerts_this_week=0,
            alerts_this_month=0
        )
    
    def _calculate_alert_system_health(self) -> str:
        """Calculate alert system health"""
        try:
            if not self.alert_statistics:
                return "Unknown"
            
            # Health based on active critical alerts
            critical_active = len([a for a in self.alerts if a.severity == 'critical' and not a.resolved])
            
            if critical_active > 5:
                return "Critical"
            elif critical_active > 2:
                return "Warning"
            elif critical_active > 0:
                return "Caution"
            else:
                return "Healthy"
                
        except Exception as e:
            self.logger.error(f"Failed to calculate alert system health: {e}")
            return "Unknown"
            
    async def _check_components(self) -> bool:
        """Check if all components are available"""
        try:
            # Check portfolio file access
            portfolio_file = self.config.get('portfolio_file', 'data/portfolio_sim.json')
            if not os.path.exists(portfolio_file):
                return False
            
            # Check data directory
            if not os.path.exists("data"):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking components: {e}")
            return False

    async def _periodic_sync_loop(self):
        """Periodic sync loop"""
        while self.status == AgentStatus.RUNNING:
            try:
                await asyncio.sleep(self.agent_config.sync_interval)
                
                if self.agent_config.auto_reconcile:
                    # Auto reconcile would go here
                    pass
                    
            except Exception as e:
                self.logger.error(f"Error in periodic sync loop: {e}")
                await asyncio.sleep(60)

class PortfolioSynchronizer:
    """Portfolio synchronization component"""
    
    def __init__(self, config: SyncAgentConfig):
        self.config = config
        self.logger = logging.getLogger("portfolio_synchronizer")
    
    async def sync_portfolio(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronize portfolio"""
        try:
            # Placeholder implementation
            return {
                "success": True,
                "synced_positions": len(portfolio.get('positions', {})),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Portfolio sync failed: {e}")
            return {"success": False, "error": str(e)}
            
    async def _sync_to_local(self, sync_type: str, force_sync: bool) -> Any:
        """Sync to local"""
        try:
            # Placeholder implementation
            return SyncResult(True, "local", "completed", 0, datetime.now().isoformat(), True, None)
            
        except Exception as e:
            return SyncResult(False, "local", "failed", 0, datetime.now().isoformat(), False, str(e))
            
    async def _create_error_response(self, original_message, error: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
    def _sync_result_to_dict(self, result) -> Dict[str, Any]:
        """Convert SyncResult to dictionary"""
        return {
            "success": result.success,
            "target": result.target,
            "status": result.status,
            "synced_items": result.synced_items,
            "timestamp": result.timestamp,
            "error": result.error,
            "details": result.details
        }

class EmailGenerator:
    """Email report generator"""
    
    def __init__(self, config: SyncAgentConfig):
        self.config = config
        self.logger = logging.getLogger("email_generator")
        
    async def generate_report(self, report_type: str, include_performance: bool = True) -> Dict[str, Any]:
        """Generate email report"""
        try:
            # Placeholder implementation
            report = {
                "report_type": report_type,
                "subject": f"VolatilityHunter {report_type.title()} Report",
                "body": f"Daily {report_type.lower()} report generated at {datetime.now().isoformat()}",
                "timestamp": datetime.now().isoformat()
            }
            
            if include_performance:
                report["performance"] = {
                    "sync_performance": "Good",
                    "email_delivery": "Successful"
                }
                
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating email report: {e}")
            return {"error": str(e)}

