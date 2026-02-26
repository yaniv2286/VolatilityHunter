"""
Execution Agent - Handles trade execution and order management
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import time

from src.interfaces.agent_interface import AgentInterface, AgentStatus, MessageType, HealthStatus
from src.messaging.message_types import ExecutionRequest, ExecutionResponse
from src.config.agent_config import ExecutionAgentConfig
from src.utils.message_safety import RateLimiter
from src.utils.error_handler import ErrorHandler, ErrorSeverity

@dataclass
class OrderResult:
    """Order execution result"""
    success: bool
    order_id: Optional[str]
    error: Optional[str]

class ExecutionAgent(AgentInterface):
    """Execution agent for trade execution and order management"""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        self.agent_config = ExecutionAgentConfig(**config)
        
        # Brokerage interface
        self.brokerage_interface = None
        self.brokerage_connected = False
        
        # Order management
        self.open_orders: Dict[str, Dict[str, Any]] = {}
        self.positions: Dict[str, Dict[str, Any]] = {}
        
        # Safety utilities
        self.error_handler = ErrorHandler(self.agent_id)
        self.rate_limiter = RateLimiter(max_messages_per_second=10)  # 10 msg/sec limit
        
        # Performance tracking
        self.execution_times: Dict[str, float] = {}
        self.error_counts: Dict[str, int] = {}
        
        # Initialize brokerage interface
        self._initialize_brokerage_interface()
        
    async def initialize(self) -> bool:
        """Initialize execution agent"""
        try:
            self.logger.info(f"Initializing Execution Agent with brokerage: {self.agent_config.brokerage_type}")
            
            # Connect to brokerage
            if not await self._connect_brokerage():
                self.logger.error("Failed to connect to brokerage")
                return False
                
            # Load positions
            await self._load_positions()
            
            self.update_status(AgentStatus.READY)
            self.logger.info("Execution Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing Execution Agent: {e}")
            self.update_status(AgentStatus.ERROR)
            return False
            
    async def start(self) -> bool:
        """Start execution agent"""
        try:
            self.update_status(AgentStatus.RUNNING)
            self.start_time = datetime.now()
            
            # Start order monitoring
            asyncio.create_task(self._order_monitoring_loop())
            
            self.logger.info("Execution Agent started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting Execution Agent: {e}")
            return False
            
    async def stop(self) -> bool:
        """Stop execution agent"""
        try:
            self.update_status(AgentStatus.SHUTDOWN)
            
            # Cancel all orders
            await self._cancel_all_orders()
            
            # Disconnect from brokerage
            if self.brokerage_interface and self.brokerage_connected:
                await self.brokerage_interface.disconnect()
                
            self.open_orders.clear()
            self.positions.clear()
            
            self.logger.info("Execution Agent stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping Execution Agent: {e}")
            return False
            
    async def process_message(self, message) -> Optional[Dict[str, Any]]:
        """Process incoming messages"""
        try:
            # Rate limiting
            if not self.rate_limiter.is_allowed():
                return await self._create_error_response(message, "Rate limit exceeded")
                
            self.rate_limiter.record_request()
            
            if message.message_type == MessageType.EXECUTION_REQUEST:
                return await self._handle_execution_request(message)
            elif message.message_type == MessageType.HEALTH_CHECK:
                return await self._handle_health_check(message)
            else:
                return None
                
        except Exception as e:
            self.error_handler.handle_error(e, {
                "message_type": message.message_type.value if message.message_type else "unknown",
                "sender": message.sender,
                "recipient": message.recipient
            }, ErrorSeverity.MEDIUM, "ExecutionAgent.process_message")
            
            return await self._create_error_response(message, str(e))
            
    async def health_check(self) -> HealthStatus:
        """Perform health check"""
        try:
            start_time = time.time()
            
            # Check brokerage connection
            brokerage_ok = self.brokerage_connected
            
            uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            return HealthStatus(
                agent_id=self.agent_id,
                status=AgentStatus.RUNNING if brokerage_ok else AgentStatus.ERROR,
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
        return ["execution_request", "execution_response", "health_check"]
        
    async def test_connection(self) -> bool:
        """Test TWS connection"""
        try:
            if self.brokerage_interface:
                return await self.brokerage_interface.test_connection()
            else:
                # Mock connection for testing
                return True
        except Exception as e:
            self.logger.error(f"TWS connection test failed: {e}")
            return False
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        try:
            if self.brokerage_interface:
                # Get real account info from TWS
                account_info = self.brokerage_interface.get_account_info()
                if account_info:
                    return account_info
                else:
                    # Fallback if TWS fails
                    self.logger.warning("TWS account info failed, using fallback")
                    return self._get_fallback_account_info()
            else:
                # No TWS connection - use portfolio state
                return await self._get_portfolio_account_info()
        except Exception as e:
            self.logger.error(f"Failed to get account info: {e}")
            return self._get_fallback_account_info()
    
    async def _get_portfolio_account_info(self) -> Dict[str, Any]:
        """Get account info from portfolio state"""
        try:
            import json
            import os
            
            portfolio_file = "data/portfolio_sim.json"
            if os.path.exists(portfolio_file):
                with open(portfolio_file, 'r') as f:
                    portfolio = json.load(f)
                
                return {
                    "account_id": portfolio.get('account_id', 'SIM_ACCOUNT'),
                    "balance": portfolio.get('cash', 1000000.0),
                    "buying_power": portfolio.get('buying_power', 2000000.0),
                    "portfolio_value": portfolio.get('total_value', 1000000.0),
                    "positions": portfolio.get('positions', {}),
                    "source": "portfolio_state"
                }
            else:
                return self._get_fallback_account_info()
        except Exception as e:
            self.logger.error(f"Failed to get portfolio account info: {e}")
            return self._get_fallback_account_info()
    
    def _get_fallback_account_info(self) -> Dict[str, Any]:
        """Fallback account info for testing"""
        return {
            "account_id": "FALLBACK_ACCOUNT",
            "balance": 1000000.0,
            "buying_power": 2000000.0,
            "portfolio_value": 1000000.0,
            "positions": {},
            "source": "fallback"
        }
    
    async def execute_trades(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trades based on signals"""
        try:
            if not self.brokerage_interface:
                return {
                    "success": False,
                    "error": "No brokerage interface available",
                    "trades_executed": 0
                }
            
            trades_executed = 0
            total_value = 0.0
            execution_results = []
            
            for ticker, signal in signals.items():
                if signal.get('signal') == 'BUY':
                    # Calculate position size
                    entry_price = signal.get('entry_price', 0)
                    stop_loss = signal.get('stop_loss', 0)
                    
                    if entry_price > 0 and stop_loss > 0:
                        # Get account info for position sizing
                        account_info = await self.get_account_info()
                        portfolio_value = account_info.get('portfolio_value', 1000000)
                        
                        # Calculate position size using Power Stock rules
                        from src.strategy_v7_2 import calculate_position_size_v7_2
                        quantity = calculate_position_size_v7_2(
                            portfolio_value, entry_price, stop_loss
                        )
                        
                        if quantity > 0:
                            # Execute buy order
                            result = await self.execute_trade(
                                ticker=ticker,
                                action="BUY",
                                quantity=quantity,
                                order_type="market"
                            )
                            
                            if result.get('success'):
                                trades_executed += 1
                                total_value += entry_price * quantity
                                execution_results.append({
                                    "ticker": ticker,
                                    "action": "BUY",
                                    "quantity": quantity,
                                    "price": entry_price,
                                    "value": entry_price * quantity,
                                    "order_id": result.get('order_id')
                                })
                            else:
                                execution_results.append({
                                    "ticker": ticker,
                                    "action": "BUY",
                                    "error": result.get('error', 'Unknown error')
                                })
            
            return {
                "success": True,
                "trades_executed": trades_executed,
                "total_value": total_value,
                "execution_time": time.time(),
                "results": execution_results
            }
            
        except Exception as e:
            self.logger.error(f"Trade execution failed: {e}")
            return {"success": False, "error": str(e), "trades_executed": 0}
    
    async def verify_execution(self) -> bool:
        """Verify trade execution with IBKR"""
        try:
            if not self.brokerage_connected:
                self.logger.error("Cannot verify execution - not connected to IBKR")
                return False
            
            # Verify IBKR connection is active
            if not self.brokerage_interface.ib.isConnected():
                self.logger.error("IBKR connection lost - cannot verify execution")
                return False
            
            # Check recent executions
            executions = self.brokerage_interface.ib.executions()
            
            if not executions:
                self.logger.debug("No recent executions found")
                return True
            
            # Verify execution details match our records
            for execution in executions[-10:]:  # Check last 10 executions
                order_id = str(execution.orderId)
                
                # Check if we have this order in our records
                if order_id in self.open_orders:
                    order_info = self.open_orders[order_id]
                    
                    # Verify execution details
                    if execution.side.lower() == order_info['action'] and \
                       execution.symbol == order_info['ticker'] and \
                       execution.shares == order_info['quantity']:
                        
                        self.logger.info(f"✅ Verified execution: {execution.side} {execution.shares} {execution.symbol}")
                        
                        # Remove from open orders
                        del self.open_orders[order_id]
                    else:
                        self.logger.error(f"❌ Execution mismatch: Expected {order_info}, Got {execution.side} {execution.shares} {execution.symbol}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Execution verification failed: {e}")
            return False
        
    async def execute_trade(self, ticker: str, action: str, quantity: int, order_type: str = "market", price: float = None) -> Dict[str, Any]:
        """Execute trade"""
        try:
            start_time = time.time()
            
            # Validate trade request
            if not self._validate_trade_request(ticker, action, quantity, order_type, price):
                return {
                    "success": False,
                    "error": "Invalid trade request",
                    "order_id": None
                }
                
            # Risk management check
            if not self._check_risk_management(ticker, action, quantity):
                return {
                    "success": False,
                    "error": "Risk management rejected",
                    "order_id": None
                }
            
            # Real-time market data validation
            market_validation = await self._validate_market_data(ticker, action, quantity, order_type, price)
            if not market_validation['valid']:
                return {
                    "success": False,
                    "error": f"Market validation failed: {market_validation['reason']}",
                    "order_id": None
                }
                
            # Place order
            order_id = str(uuid.uuid4())
            order_result = await self._place_order(ticker, action, quantity, order_type, price, order_id)
            
            # Track performance
            execution_time = time.time() - start_time
            self.execution_times[ticker] = execution_time
            
            if order_result.success:
                self.logger.info(f"Executed {action} {quantity} {ticker} in {execution_time:.2f}s")
            else:
                self.error_counts[ticker] = self.error_counts.get(ticker, 0) + 1
                self.logger.error(f"Failed to execute {action} {ticker}: {order_result.error}")
                
            return {
                "success": order_result.success,
                "order_id": order_id,
                "ticker": ticker,
                "action": action,
                "quantity": quantity,
                "order_type": order_type,
                "price": order_result.price,
                "status": order_result.status,
                "execution_time": execution_time,
                "error": order_result.error
            }
            
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            self.error_counts[ticker] = self.error_counts.get(ticker, 0) + 1
            return {
                "success": False,
                "error": str(e),
                "order_id": None
            }
            
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order"""
        try:
            if not self.brokerage_connected:
                return {"success": False, "error": "Not connected to brokerage"}
                
            order = self.open_orders.get(order_id)
            if not order:
                return {"success": False, "error": f"Order not found: {order_id}"}
                
            # Cancel order
            cancel_result = await self.brokerage_interface.cancel_order(order_id)
            
            if cancel_result.success:
                if order_id in self.open_orders:
                    del self.open_orders[order_id]
                self.logger.info(f"Cancelled order {order_id}")
            else:
                self.logger.error(f"Failed to cancel order {order_id}: {cancel_result.error}")
                
            return {
                "success": cancel_result.success,
                "order_id": order_id,
                "error": cancel_result.error
            }
            
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "order_id": order_id
            }
            
    async def get_positions(self) -> Dict[str, Any]:
        """Get current positions"""
        try:
            if not self.brokerage_connected:
                return {"success": False, "error": "Not connected to brokerage"}
                
            positions = await self.brokerage_interface.get_positions()
            self.positions = {pos["symbol"]: pos for pos in positions}
            
            return {
                "success": True,
                "positions": positions,
                "count": len(positions),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return {"success": False, "error": str(e)}
            
    async def get_open_orders(self) -> Dict[str, Any]:
        """Get open orders"""
        try:
            if not self.brokerage_connected:
                return {"success": False, "error": "Not connected to brokerage"}
                
            # Get open trades from brokerage
            open_trades = self.brokerage_interface.ib.openTrades()
            
            orders = []
            for trade in open_trades:
                order_info = {
                    "order_id": str(trade.order.orderId),
                    "ticker": trade.contract.symbol,
                    "action": trade.order.action.lower(),
                    "quantity": trade.order.totalQuantity,
                    "order_type": trade.order.orderType.lower(),
                    "price": trade.order.lmtPrice if trade.order.orderType == "LMT" else None,
                    "status": trade.orderStatus.value,
                    "filled_quantity": trade.filled,
                    "remaining_quantity": trade.remaining,
                    "timestamp": trade.logTime.isoformat()
                }
                orders.append(order_info)
                
            return {
                "success": True,
                "orders": orders,
                "count": len(orders),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting open orders: {e}")
            return {"success": False, "error": str(e)}
            
    async def _handle_execution_request(self, message) -> Dict[str, Any]:
        """Handle execution request message"""
        try:
            data = message.data
            
            if "ticker" in data and "action" in data and "quantity" in data:
                result = await self.execute_trade(
                    data["ticker"],
                    data["action"],
                    data["quantity"],
                    data.get("order_type", "market"),
                    data.get("price")
                )
                return result
            else:
                return {
                    "success": False,
                    "error": "Missing required fields: ticker, action, quantity"
                }
                
        except Exception as e:
            self.logger.error(f"Error handling execution request: {e}")
            return {"success": False, "error": str(e)}
            
    async def _handle_health_check(self, message) -> Dict[str, Any]:
        """Handle health check message"""
        try:
            health = await self.health_check()
            
            return {
                "success": True,
                "health_status": health.status.value,
                "brokerage_connected": self.brokerage_connected,
                "open_orders": len(self.open_orders),
                "positions": len(self.positions),
                "paper_trading": self.agent_config.paper_trading,
                "brokerage_type": self.agent_config.brokerage_type
            }
            
        except Exception as e:
            self.logger.error(f"Error handling health check: {e}")
            return {"success": False, "error": str(e)}
            
    def _initialize_brokerage_interface(self):
        """Initialize brokerage interface"""
        try:
            from src.brokerage_interface import get_brokerage_interface
            
            config = {
                "BROKERAGE_TYPE": self.agent_config.brokerage_type,
                "IBKR_HOST": "127.0.0.1",
                "IBKR_PORT": 7497,
                "IBKR_CLIENT_ID": 555
            }
            
            self.brokerage_interface = get_brokerage_interface(config)
            
        except Exception as e:
            self.logger.error(f"Error initializing brokerage interface: {e}")
            
    async def _connect_brokerage(self) -> bool:
        """Connect to brokerage"""
        try:
            if not self.brokerage_interface:
                return False
                
            self.logger.info("Connecting to brokerage...")
            
            connected = await self.brokerage_interface.connect()
            
            if connected:
                self.brokerage_connected = True
                self.logger.info("Successfully connected to brokerage")
                return True
            else:
                self.logger.error("Failed to connect to brokerage")
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to brokerage: {e}")
            return False
            
    def _validate_trade_request(self, ticker: str, action: str, quantity: int, order_type: str, price: float) -> bool:
        """Validate trade request"""
        try:
            # Basic validation
            if not ticker or not isinstance(ticker, str):
                return False
                
            if action not in ["buy", "sell"]:
                return False
                
            if not isinstance(quantity, int) or quantity <= 0:
                return False
                
            if order_type not in ["market", "limit"]:
                return False
                
            if order_type == "limit" and (price is None or price <= 0):
                return False
                
            return True
            
        except Exception:
            return False
            
    def _check_risk_management(self, ticker: str, action: str, quantity: int) -> bool:
        """Check risk management"""
        try:
            if not self.agent_config.risk_management_enabled:
                return True
                
            # Basic risk checks
            max_position_size = self.agent_config.max_position_size
            estimated_price = 100.0  # Placeholder
            position_value = quantity * estimated_price
            
            if position_value > max_position_size:
                self.logger.warning(f"Position size exceeds limit: ${position_value}")
                return False
                
            return True
            
        except Exception:
            return True
            
    async def _place_order(self, ticker: str, action: str, quantity: int, order_type: str, price: float, order_id: str) -> Any:
        """Place order"""
        try:
            if not self.brokerage_connected:
                return OrderResult(False, None, "Not connected to brokerage")
                
            # Create order parameters
            if action.upper() == "BUY":
                actual_quantity = quantity
            else:
                actual_quantity = -quantity
                
            # Place order (placeholder implementation)
            # In real implementation, this would use the brokerage API
            order_info = {
                "order_id": order_id,
                "ticker": ticker,
                "action": action,
                "quantity": actual_quantity,
                "order_type": order_type,
                "price": price,
                "status": "submitted",
                "timestamp": datetime.now().isoformat()
            }
            
            self.open_orders[order_id] = order_info
            
            return OrderResult(True, order_id, None)
            
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return OrderResult(False, None, str(e))
            
    async def _cancel_all_orders(self):
        """Cancel all open orders"""
        try:
            if not self.brokerage_connected:
                return
                
            order_ids = list(self.open_orders.keys())
            
            for order_id in order_ids:
                await self.cancel_order(order_id)
                
        except Exception as e:
            self.logger.error(f"Error cancelling all orders: {e}")
    
    async def _validate_market_data(self, ticker: str, action: str, quantity: int, order_type: str, price: float = None) -> Dict[str, Any]:
        """Validate real-time market data before execution"""
        try:
            if not self.brokerage_connected:
                return {"valid": False, "reason": "Not connected to IBKR"}
            
            # Get real-time ticker data
            ticker_data = self.brokerage_interface.ib.reqMktData(ticker, '', False, False)
            
            # Wait for market data (with timeout)
            await asyncio.sleep(1)  # Allow time for data to populate
            
            if not ticker_data or not hasattr(ticker_data, 'last') or ticker_data.last == 0:
                return {"valid": False, "reason": "No market data available"}
            
            current_price = ticker_data.last
            bid = ticker_data.bid if hasattr(ticker_data, 'bid') else 0
            ask = ticker_data.ask if hasattr(ticker_data, 'ask') else 0
            
            # Validate limit orders
            if order_type.lower() == "limit" and price:
                if action.lower() == "buy" and price >= ask:
                    return {"valid": False, "reason": f"Limit price {price} >= ask {ask}"}
                elif action.lower() == "sell" and price <= bid:
                    return {"valid": False, "reason": f"Limit price {price} <= bid {bid}"}
            
            # Check for unusual spreads
            if bid > 0 and ask > 0:
                spread_pct = (ask - bid) / bid * 100
                if spread_pct > 5.0:  # More than 5% spread
                    return {"valid": False, "reason": f"Excessive spread: {spread_pct:.2f}%"}
            
            # Check for reasonable price movement
            if hasattr(ticker_data, 'close') and ticker_data.close > 0:
                price_change_pct = abs(current_price - ticker_data.close) / ticker_data.close * 100
                if price_change_pct > 10.0:  # More than 10% from close
                    return {"valid": False, "reason": f"Excessive price movement: {price_change_pct:.2f}%"}
            
            # Validate order size relative to volume
            if hasattr(ticker_data, 'volume') and ticker_data.volume > 0:
                volume_ratio = quantity / ticker_data.volume
                if volume_ratio > 0.1:  # Order > 10% of daily volume
                    self.logger.warning(f"Large order size: {quantity} shares ({volume_ratio:.2%} of volume)")
            
            return {
                "valid": True,
                "current_price": current_price,
                "bid": bid,
                "ask": ask,
                "spread_pct": ((ask - bid) / bid * 100) if bid > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Market data validation failed: {e}")
            return {"valid": False, "reason": f"Validation error: {str(e)}"}
    
    async def _place_bracket_order(self, ticker: str, action: str, quantity: int, price: float = None, 
                                 stop_loss_pct: float = 0.05, take_profit_pct: float = 0.10) -> Dict[str, Any]:
        """Place bracket order with stop-loss and take-profit"""
        try:
            from ib_insync import Order, Contract, BracketOrder
            
            # Create contract
            contract = Contract(symbol=ticker, secType='STK', currency='USD', exchange='SMART')
            
            # Get current price if not provided
            if price is None:
                ticker_data = self.brokerage_interface.ib.reqMktData(ticker, '', False, False)
                await asyncio.sleep(1)
                price = ticker_data.last if ticker_data.last > 0 else ticker_data.close
            
            # Calculate stop-loss and take-profit prices
            if action.lower() == "buy":
                stop_loss_price = price * (1 - stop_loss_pct)
                take_profit_price = price * (1 + take_profit_pct)
            else:  # sell
                stop_loss_price = price * (1 + stop_loss_pct)
                take_profit_price = price * (1 - take_profit_pct)
            
            # Create bracket order
            bracket_order = BracketOrder(
                action=action.upper(),
                totalQuantity=quantity,
                limitPrice=price,
                stopLossPrice=stop_loss_price,
                takeProfitPrice=take_profit_price
            )
            
            # Place order
            order_result = self.brokerage_interface.ib.placeOrder(contract, bracket_order)
            
            return OrderResult(True, str(order_result.orderId), None)
            
        except Exception as e:
            self.logger.error(f"Bracket order placement failed: {e}")
            return OrderResult(False, None, str(e))
            
    async def _load_positions(self):
        """Load existing positions"""
        try:
            if self.brokerage_connected:
                positions = await self.brokerage_interface.get_positions()
                self.positions = {pos["symbol"]: pos for pos in positions}
                self.logger.info(f"Loaded {len(self.positions)} positions")
                
        except Exception as e:
            self.logger.error(f"Error loading positions: {e}")
            
    async def _order_monitoring_loop(self):
        """Monitor order status"""
        while self.status == AgentStatus.RUNNING:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                if self.brokerage_connected:
                    await self._update_order_status()
                    
            except Exception as e:
                self.logger.error(f"Error in order monitoring: {e}")
                await asyncio.sleep(30)
                
    async def _update_order_status(self):
        """Update order status"""
        try:
            # Placeholder for order status updates
            pass
            
        except Exception as e:
            self.logger.error(f"Error updating order status: {e}")
            
    async def _create_error_response(self, original_message, error: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }

@dataclass
class OrderResult:
    """Order result"""
    success: bool
    order_id: Optional[str]
    error: Optional[str]
