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
    def place_market_order(self, symbol: str, quantity: int, side: str, price: float = None) -> Dict:
        """Place a market order (price parameter for limit order fallback in paper trading)"""
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
    
    def place_market_order(self, symbol: str, quantity: int, side: str, price: float = None) -> Dict:
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
        self.port = config.get('IBKR_PORT', 7497)  # TWS Paper port (active connection)
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
                timeout=60,
                readonly=False
            )

            if not self.ib.isConnected():
                log_error("IBKR connect() returned but isConnected() is False")
                return False

            # Suppress Error 10089 by permitting delayed data for paper trading
            self.ib.reqMarketDataType(3)  # 3 = Delayed data
            
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
            # Get account values
            account_values = self.ib.accountValues()
            
            # Multi-currency support: read base currency values
            # BASE currency is the account's base currency (USD, ILS, etc.)
            cash = 0.0
            equity = 0.0
            available_funds = 0.0
            detected_currency = None
            
            for value in account_values:
                # TotalCashValue in base currency (includes all currencies converted)
                if value.tag == 'TotalCashValue' and value.currency != 'BASE':
                    # Use the first non-BASE currency (account's actual currency)
                    if cash == 0.0:
                        cash = float(value.value)
                        detected_currency = value.currency
                
                # NetLiquidation = total account value (cash + positions)
                if value.tag == 'NetLiquidation' and value.currency != 'BASE':
                    if equity == 0.0:
                        equity = float(value.value)
                        if not detected_currency:
                            detected_currency = value.currency
                
                # AvailableFunds = cash available for trading
                if value.tag == 'AvailableFunds' and value.currency != 'BASE':
                    if available_funds == 0.0:
                        available_funds = float(value.value)
                        if not detected_currency:
                            detected_currency = value.currency
            
            # Fallback: if still zero, try BASE currency
            if cash == 0.0 or equity == 0.0:
                for value in account_values:
                    if value.tag == 'CashBalance' and value.currency == 'BASE':
                        cash = float(value.value)
                    if value.tag == 'NetLiquidation' and value.currency == 'BASE':
                        equity = float(value.value)
            
            # CURRENCY CONVERSION: Convert ILS to USD
            # ILS (Israeli Shekel) to USD conversion rate (approximate)
            ILS_TO_USD = 0.27  # 1 ILS ≈ 0.27 USD
            
            if detected_currency == 'ILS':
                log_info(f"Converting ILS to USD: {cash:,.2f} ILS → {cash * ILS_TO_USD:,.2f} USD")
                cash = cash * ILS_TO_USD
                equity = equity * ILS_TO_USD
                available_funds = available_funds * ILS_TO_USD if available_funds > 0 else 0.0
            
            # Calculate portfolio value
            portfolio_value = equity - cash if equity > 0 else 0.0
            
            return {
                'cash': cash,
                'portfolio_value': portfolio_value,
                'buying_power': available_funds if available_funds > 0 else cash,
                'equity': equity,
                'daytrade_count': 0,
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
            # Use portfolio() instead of positions() to get PortfolioItem objects with marketValue
            portfolio_items = self.ib.portfolio()
            return [
                {
                    'symbol': item.contract.symbol,
                    'quantity': item.position,
                    'side': 'long' if item.position > 0 else 'short',
                    'market_value': float(item.marketValue),
                    'cost_basis': float(item.averageCost * abs(item.position)),
                    'unrealized_pl': float(item.unrealizedPNL),
                    'unrealized_plpc': (float(item.unrealizedPNL) / (float(item.averageCost) * abs(item.position)) * 100) if item.averageCost and item.position != 0 else 0,
                    'current_price': float(item.marketPrice) if item.marketPrice else 0,
                    'entry_price': float(item.averageCost) if item.averageCost else 0
                }
                for item in portfolio_items
                if item.contract.secType == 'STK'  # Only stocks
            ]
        except Exception as e:
            log_error(f"Failed to get IBKR positions: {e}")
            return []
    
    def place_market_order(self, symbol: str, quantity: int, side: str, price: float = None) -> Dict:
        """Place a market order (using limit order with aggressive pricing for paper trading)"""
        if not self.is_connected or not self.ib:
            return {'success': False, 'reason': 'Not connected to IBKR'}
        
        validation = self.validate_order(symbol, quantity, side)
        if not validation['valid']:
            return {'success': False, 'reason': validation['reason']}
        
        # ANTI-SHORTING LOGIC: Prevent accidental short positions
        if side.upper() == 'SELL':
            try:
                positions = self.ib.positions()
                current_position = 0
                for pos in positions:
                    if pos.contract.symbol == symbol:
                        current_position = pos.position
                        break
                
                if current_position <= 0:
                    log_error(f"ANTI-SHORTING ABORT: Cannot SELL {symbol} - current position is {current_position}")
                    return {
                        'success': False, 
                        'reason': f'Anti-shorting protection: position={current_position}, cannot sell'
                    }
                
                if quantity > current_position:
                    log_error(f"ANTI-SHORTING ABORT: Cannot SELL {quantity} shares of {symbol} - only have {current_position}")
                    return {
                        'success': False,
                        'reason': f'Anti-shorting protection: trying to sell {quantity} but only have {current_position}'
                    }
            except Exception as e:
                log_error(f"Anti-shorting check failed for {symbol}: {e}")
                return {'success': False, 'reason': f'Anti-shorting check failed: {e}'}
        
        try:
            from ib_insync import Stock, LimitOrder, TagValue
            import pandas as pd
            
            # 1. Force SMART routing and qualify the contract
            contract = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            
            # 2. Get market snapshot for marketable limit price
            limit_price = self._calculate_marketable_limit(symbol, side)
            
            # 3. Create LimitOrder with Adaptive Algo
            order = LimitOrder(side.upper(), quantity, limit_price)
            order.algoStrategy = 'Adaptive'
            order.algoParams = [TagValue('adaptivePriority', 'Normal')]
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            
            log_info(f"Placed Adaptive Limit order: {side.upper()} {quantity} {symbol} @ {limit_price:.2f} (SMART)")
            
            return {
                'success': True,
                'order_id': str(trade.order.orderId),
                'symbol': symbol,
                'quantity': quantity,
                'side': side,
                'type': 'adaptive_limit',
                'status': trade.orderStatus.status
            }
            
        except Exception as e:
            log_error(f"Failed to place Adaptive Limit order: {e}")
            return {'success': False, 'reason': str(e)}
    
    def _calculate_marketable_limit(self, symbol: str, side: str) -> float:
        """Calculate marketable limit price with 1% buffer using live market data"""
        try:
            # Request market snapshot
            from ib_insync import Stock
            ticker = self.ib.reqMktData(Stock(symbol, 'SMART', 'USD'), '', False, False)
            self.ib.sleep(1)  # Allow data to populate
            
            # Get bid/ask prices
            bid = ticker.bid
            ask = ticker.ask
            
            # Cancel market data subscription
            self.ib.cancelMktData(ticker)
            
            # Calculate limit price with 1% buffer
            if side.upper() == 'BUY':
                if ask and ask > 0:
                    limit_price = ask * 1.01  # 1% above ask
                    log_info(f"BUY limit for {symbol}: ask={ask:.2f}, limit={limit_price:.2f}")
                else:
                    raise ValueError("Invalid ask price")
            else:  # SELL
                if bid and bid > 0:
                    limit_price = bid * 0.99  # 1% below bid
                    log_info(f"SELL limit for {symbol}: bid={bid:.2f}, limit={limit_price:.2f}")
                else:
                    raise ValueError("Invalid bid price")
            
            return round(limit_price, 2)
            
        except Exception as e:
            log_warning(f"Market data unavailable for {symbol}, using fallback: {e}")
            return self._fallback_limit_price(symbol, side)
    
    def _fallback_limit_price(self, symbol: str, side: str) -> float:
        """Fallback to last known close price from Parquet data"""
        try:
            import pandas as pd
            import os
            
            # Load latest data from Parquet file
            data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', f'{symbol.lower()}.parquet')
            
            if not os.path.exists(data_file):
                raise ValueError(f"No data file found for {symbol}")
            
            df = pd.read_parquet(data_file)
            if df.empty or 'close' not in df.columns:
                raise ValueError(f"No close price data for {symbol}")
            
            # Get last known close price
            close_price = df['close'].iloc[-1]
            
            # Apply 1% buffer
            if side.upper() == 'BUY':
                limit_price = close_price * 1.01
            else:  # SELL
                limit_price = close_price * 0.99
            
            log_warning(f"Fallback limit for {symbol}: close={close_price:.2f}, limit={limit_price:.2f}")
            return round(limit_price, 2)
            
        except Exception as e:
            log_error(f"Fallback pricing failed for {symbol}: {e}")
            # Last resort - use a reasonable default
            if side.upper() == 'BUY':
                return 100.0  # Default buy limit
            else:
                return 50.0   # Default sell limit
    
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
