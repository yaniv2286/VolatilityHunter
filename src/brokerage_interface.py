"""
VolatilityHunter Brokerage Interface
Abstract base class for brokerage API integrations
"""

import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging as _logging
_bi_logger = _logging.getLogger('brokerage_interface')
def log_info(msg): _bi_logger.info(msg)
def log_warning(msg): _bi_logger.warning(msg)
def log_error(msg): _bi_logger.error(msg)

class BrokerageInterface(ABC):
    """Abstract base class for brokerage integrations"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.is_connected = False
        
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to brokerage API"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close connection to brokerage API"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict:
        """Get account information including cash balance"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        pass
    
    @abstractmethod
    def place_market_order(self, symbol: str, quantity: int, side: str) -> Dict:
        """Place a market order"""
        pass
    
    @abstractmethod
    def place_limit_order(self, symbol: str, quantity: int, side: str, price: float) -> Dict:
        """Place a limit order"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict:
        """Get order status"""
        pass
    
    def validate_order(self, symbol: str, quantity: int, side: str) -> Dict:
        """Validate order parameters"""
        if quantity <= 0:
            return {'valid': False, 'reason': 'Quantity must be positive'}
        
        if side not in ['buy', 'sell']:
            return {'valid': False, 'reason': 'Side must be buy or sell'}
        
        if not symbol or not isinstance(symbol, str):
            return {'valid': False, 'reason': 'Symbol must be a non-empty string'}
        
        return {'valid': True}


class AlpacaInterface(BrokerageInterface):
    """Alpaca brokerage implementation"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.api_key = config.get('ALPACA_API_KEY')
        self.secret_key = config.get('ALPACA_SECRET_KEY')
        self.base_url = config.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        self.client = None
        
    def connect(self) -> bool:
        """Connect to Alpaca API"""
        try:
            import alpaca_trade_api as tradeapi
            
            if not self.api_key or not self.secret_key:
                log_error("Alpaca API keys not provided")
                return False
            
            self.client = tradeapi.REST(
                key_id=self.api_key,
                secret_key=self.secret_key,
                base_url=self.base_url
            )
            
            # Test connection
            account = self.client.get_account()
            log_info(f"Connected to Alpaca. Account: ${float(account.cash):,.2f} cash")
            self.is_connected = True
            return True
            
        except ImportError:
            log_error("Alpaca trade API not installed. Install with: pip install alpaca-trade-api")
            return False
        except Exception as e:
            log_error(f"Failed to connect to Alpaca: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Alpaca API"""
        self.client = None
        self.is_connected = False
        log_info("Disconnected from Alpaca")
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        if not self.is_connected or not self.client:
            return {}
        
        try:
            account = self.client.get_account()
            return {
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'buying_power': float(account.buying_power),
                'equity': float(account.equity),
                'daytrade_count': account.daytrade_count,
                'pattern_day_trader': account.pattern_day_trader
            }
        except Exception as e:
            log_error(f"Failed to get account info: {e}")
            return {}
    
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        if not self.is_connected or not self.client:
            return []
        
        try:
            positions = self.client.list_positions()
            return [
                {
                    'symbol': pos.symbol,
                    'quantity': int(pos.qty),
                    'side': pos.side,
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                    'current_price': float(pos.current_price),
                    'entry_price': float(pos.avg_entry_price)
                }
                for pos in positions
            ]
        except Exception as e:
            log_error(f"Failed to get positions: {e}")
            return []
    
    def place_market_order(self, symbol: str, quantity: int, side: str) -> Dict:
        """Place a market order"""
        if not self.is_connected or not self.client:
            return {'success': False, 'reason': 'Not connected to brokerage'}
        
        validation = self.validate_order(symbol, quantity, side)
        if not validation['valid']:
            return {'success': False, 'reason': validation['reason']}
        
        try:
            order = self.client.submit_order(
                symbol=symbol,
                qty=quantity,
                side=side,
                type='market',
                time_in_force='day'
            )
            
            log_info(f"Placed market order: {side.upper()} {quantity} {symbol} (ID: {order.id})")
            
            return {
                'success': True,
                'order_id': order.id,
                'symbol': symbol,
                'quantity': quantity,
                'side': side,
                'type': 'market',
                'status': order.status
            }
            
        except Exception as e:
            log_error(f"Failed to place market order: {e}")
            return {'success': False, 'reason': str(e)}
    
    def place_limit_order(self, symbol: str, quantity: int, side: str, price: float) -> Dict:
        """Place a limit order"""
        if not self.is_connected or not self.client:
            return {'success': False, 'reason': 'Not connected to brokerage'}
        
        validation = self.validate_order(symbol, quantity, side)
        if not validation['valid']:
            return {'success': False, 'reason': validation['reason']}
        
        try:
            order = self.client.submit_order(
                symbol=symbol,
                qty=quantity,
                side=side,
                type='limit',
                time_in_force='day',
                limit_price=price
            )
            
            log_info(f"Placed limit order: {side.upper()} {quantity} {symbol} @ ${price:.2f} (ID: {order.id})")
            
            return {
                'success': True,
                'order_id': order.id,
                'symbol': symbol,
                'quantity': quantity,
                'side': side,
                'type': 'limit',
                'price': price,
                'status': order.status
            }
            
        except Exception as e:
            log_error(f"Failed to place limit order: {e}")
            return {'success': False, 'reason': str(e)}
    
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order"""
        if not self.is_connected or not self.client:
            return {'success': False, 'reason': 'Not connected to brokerage'}
        
        try:
            self.client.cancel_order(order_id)
            log_info(f"Cancelled order: {order_id}")
            return {'success': True, 'order_id': order_id}
        except Exception as e:
            log_error(f"Failed to cancel order {order_id}: {e}")
            return {'success': False, 'reason': str(e)}
    
    def get_order_status(self, order_id: str) -> Dict:
        """Get order status"""
        if not self.is_connected or not self.client:
            return {'success': False, 'reason': 'Not connected to brokerage'}
        
        try:
            order = self.client.get_order(order_id)
            return {
                'success': True,
                'order_id': order.id,
                'symbol': order.symbol,
                'quantity': order.qty,
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'filled_qty': order.filled_qty,
                'filled_avg_price': order.filled_avg_price
            }
        except Exception as e:
            log_error(f"Failed to get order status for {order_id}: {e}")
            return {'success': False, 'reason': str(e)}


class IBKRInterface(BrokerageInterface):
    """Interactive Brokers brokerage implementation"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.host = config.get('IBKR_HOST', '127.0.0.1')
        self.port = config.get('IBKR_PORT', 7497)  # Paper trading port
        # Use random client ID to avoid conflicts
        import random
        self.client_id = config.get('IBKR_CLIENT_ID', random.randint(100, 999))
        self.ib = None
        
    def connect(self) -> bool:
        """Connect to IBKR TWS/Gateway - R3 fix: no threading, use ib_insync event loop directly"""
        try:
            from ib_insync import IB, util
            import socket as _socket
            import traceback as _tb

            if not self.host or not self.port:
                log_error("IBKR host and port not provided")
                return False

            # Quick port check before attempting connection
            probe = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
            probe.settimeout(5)
            port_open = probe.connect_ex((self.host, self.port)) == 0
            probe.close()
            if not port_open:
                log_error(f"IBKR port {self.port} not reachable - is IB Gateway running?")
                return False

            self.ib = IB()

            # ib_insync manages its own event loop - connect() is synchronous here
            # timeout parameter prevents hanging forever
            self.ib.connect(
                self.host, self.port,
                clientId=self.client_id,
                timeout=15,
                readonly=False
            )

            if not self.ib.isConnected():
                log_error("IBKR connect() returned but isConnected() is False")
                return False

            log_info(f"Connected to IBKR at {self.host}:{self.port} (clientId={self.client_id})")

            # Get account cash
            try:
                accounts = self.ib.accountValues()
                for value in accounts:
                    if value.tag == 'AvailableFunds' and value.currency == 'USD':
                        log_info(f"Account cash: ${float(value.value):,.2f}")
                        break
            except Exception:
                pass

            self.is_connected = True
            return True

        except ImportError:
            log_error("ib_insync not installed: pip install ib_insync")
            return False
        except Exception as e:
            log_error(f"IBKR connect failed: {e}")
            log_error(_tb.format_exc())
            return False
    
    async def test_connection(self) -> bool:
        """Test IBKR connection"""
        try:
            if not self.ib or not self.ib.isConnected():
                return False
            
            # Test by requesting account summary
            accounts = self.ib.accountSummary()
            return len(accounts) > 0
            
        except Exception as e:
            log_error(f"IBKR connection test failed: {e}")
            return False
    
    def _start_heartbeat(self):
        """Start heartbeat logger for connection monitoring"""
        import threading
        import time
        
        def heartbeat():
            while self.is_connected and self.ib and self.ib.isConnected():
                log_info("[HEARTBEAT] IBKR connection active")
                time.sleep(10)  # Heartbeat every 10 seconds
        
        heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()
        log_info("IBKR heartbeat monitoring started")
    
    def disconnect(self):
        """Disconnect from IBKR"""
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
            log_info("Disconnected from IBKR")
        self.ib = None
        self.is_connected = False
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        if not self.is_connected or not self.ib:
            return {}
        
        try:
            account_values = self.ib.accountValues()
            
            cash = 0.0
            portfolio_value = 0.0
            buying_power = 0.0
            equity = 0.0
            
            for value in account_values:
                if value.tag == 'AvailableFunds' and value.currency == 'USD':
                    cash = float(value.value)
                elif value.tag == 'NetLiquidation' and value.currency == 'USD':
                    equity = float(value.value)
                elif value.tag == 'BuyingPower' and value.currency == 'USD':
                    buying_power = float(value.value)
                elif value.tag == 'GrossPositionValue' and value.currency == 'USD':
                    portfolio_value = float(value.value)
            
            return {
                'cash': cash,
                'portfolio_value': portfolio_value,
                'buying_power': buying_power,
                'equity': equity,
                'daytrade_count': 0,  # IBKR doesn't expose this easily
                'pattern_day_trader': False
            }
        except Exception as e:
            log_error(f"Failed to get IBKR account info: {e}")
            return {}
    
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        if not self.is_connected or not self.ib:
            return []
        
        try:
            positions = self.ib.positions()
            return [
                {
                    'symbol': pos.contract.symbol,
                    'quantity': pos.position,
                    'side': 'long' if pos.position > 0 else 'short',
                    'market_value': float(pos.marketValue),
                    'cost_basis': float(pos.avgCost * abs(pos.position)),
                    'unrealized_pl': float(pos.unrealizedPNL),
                    'unrealized_plpc': (float(pos.unrealizedPNL) / (float(pos.avgCost) * abs(pos.position)) * 100) if pos.avgCost and pos.position != 0 else 0,
                    'current_price': float(pos.marketValue / pos.position) if pos.position != 0 else 0,
                    'entry_price': float(pos.avgCost) if pos.avgCost else 0
                }
                for pos in positions
                if pos.contract.secType == 'STK'  # Only stocks
            ]
        except Exception as e:
            log_error(f"Failed to get IBKR positions: {e}")
            return []
    
    def place_market_order(self, symbol: str, quantity: int, side: str) -> Dict:
        """Place a market order"""
        if not self.is_connected or not self.ib:
            return {'success': False, 'reason': 'Not connected to IBKR'}
        
        validation = self.validate_order(symbol, quantity, side)
        if not validation['valid']:
            return {'success': False, 'reason': validation['reason']}
        
        try:
            from ib_insync import Stock, MarketOrder
            
            # Create contract
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Create order
            order = MarketOrder(side.upper(), quantity)
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            
            log_info(f"Placed IBKR market order: {side.upper()} {quantity} {symbol}")
            
            return {
                'success': True,
                'order_id': str(trade.order.orderId),
                'symbol': symbol,
                'quantity': quantity,
                'side': side,
                'type': 'market',
                'status': trade.orderStatus.status
            }
            
        except Exception as e:
            log_error(f"Failed to place IBKR market order: {e}")
            return {'success': False, 'reason': str(e)}
    
    def place_limit_order(self, symbol: str, quantity: int, side: str, price: float) -> Dict:
        """Place a limit order"""
        if not self.is_connected or not self.ib:
            return {'success': False, 'reason': 'Not connected to IBKR'}
        
        validation = self.validate_order(symbol, quantity, side)
        if not validation['valid']:
            return {'success': False, 'reason': validation['reason']}
        
        try:
            from ib_insync import Stock, LimitOrder
            
            # Create contract
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Create order
            order = LimitOrder(side.upper(), quantity, price)
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            
            log_info(f"Placed IBKR limit order: {side.upper()} {quantity} {symbol} @ ${price:.2f}")
            
            return {
                'success': True,
                'order_id': str(trade.order.orderId),
                'symbol': symbol,
                'quantity': quantity,
                'side': side,
                'type': 'limit',
                'price': price,
                'status': trade.orderStatus.status
            }
            
        except Exception as e:
            log_error(f"Failed to place IBKR limit order: {e}")
            return {'success': False, 'reason': str(e)}
    
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order"""
        if not self.is_connected or not self.ib:
            return {'success': False, 'reason': 'Not connected to IBKR'}
        
        try:
            # Find the order by ID
            for trade in self.ib.openTrades():
                if str(trade.order.orderId) == order_id:
                    self.ib.cancelOrder(trade.order)
                    log_info(f"Cancelled IBKR order: {order_id}")
                    return {'success': True, 'order_id': order_id}
            
            return {'success': False, 'reason': f'Order {order_id} not found'}
            
        except Exception as e:
            log_error(f"Failed to cancel IBKR order {order_id}: {e}")
            return {'success': False, 'reason': str(e)}
    
    def get_order_status(self, order_id: str) -> Dict:
        """Get order status"""
        if not self.is_connected or not self.ib:
            return {'success': False, 'reason': 'Not connected to IBKR'}
        
        try:
            # Find the order by ID
            for trade in self.ib.openTrades():
                if str(trade.order.orderId) == order_id:
                    return {
                        'success': True,
                        'order_id': order_id,
                        'symbol': trade.contract.symbol,
                        'quantity': trade.order.totalQuantity,
                        'side': trade.order.action.lower(),
                        'type': trade.order.orderType.lower(),
                        'status': trade.orderStatus.status,
                        'filled_qty': trade.orderStatus.filled,
                        'filled_avg_price': trade.orderStatus.avgFillPrice if trade.orderStatus.avgFillPrice else 0
                    }
            
            return {'success': False, 'reason': f'Order {order_id} not found'}
            
        except Exception as e:
            log_error(f"Failed to get IBKR order status for {order_id}: {e}")
            return {'success': False, 'reason': str(e)}


def get_brokerage_interface(config: Dict) -> BrokerageInterface:
    """Factory function to get appropriate brokerage interface"""
    brokerage_type = config.get('BROKERAGE_TYPE', 'alpaca').lower()
    
    if brokerage_type == 'alpaca':
        return AlpacaInterface(config)
    elif brokerage_type == 'ibkr' or brokerage_type == 'interactive_brokers':
        return IBKRInterface(config)
    else:
        raise ValueError(f"Unsupported brokerage type: {brokerage_type}")
