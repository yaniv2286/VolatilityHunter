"""
VolatilityHunter Execution Layer
Abstract trading execution with Paper and Live implementations
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional
from src.notifications import log_info, log_warning, log_error
# from src.strategy import check_sector_diversification  # Disabled - using v7.2 strategy
from src.strategy_v7_2 import analyze_stock_v7_2, check_exit_conditions_v7_2, calculate_position_size_v7_2, add_indicators_v7_2

class Executor(ABC):
    """Abstract base class for trading execution"""
    
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self._load_config()
        self.execution_mode = self.config.get('TRADING_MODE', 'PAPER')
        
    def _load_config(self) -> Dict:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                log_warning(f"Config file {self.config_file} not found, using defaults")
                return {}
        except Exception as e:
            log_error(f"Error loading config: {e}")
            return {}
    
    @abstractmethod
    def execute_buy(self, signal: Dict, available_cash: float) -> Dict:
        """Execute a buy order"""
        pass
    
    @abstractmethod
    def execute_sell(self, signal: Dict, position: Dict) -> Dict:
        """Execute a sell order"""
        pass
    
    @abstractmethod
    def get_portfolio_summary(self, current_prices: Optional[Dict] = None) -> Dict:
        """Get current portfolio summary"""
        pass
    
    @abstractmethod
    def process_signals(self, buy_signals: List[Dict], sell_signals: List[Dict], 
                       current_prices: Optional[Dict] = None) -> Dict:
        """Process trading signals"""
        pass
    
    def check_position_limits(self, current_positions: Dict, new_ticker: str) -> bool:
        """Check if adding position would violate limits"""
        max_positions = 10
        max_per_sector = 3
        
        # Check position count limit
        if len(current_positions) >= max_positions:
            return False
        
        # Check sector diversification
        # Note: Sector check temporarily disabled due to old strategy dependency
        # if not check_sector_diversification(current_positions, new_ticker, max_per_sector):
        #     return False
        
        return True
    
    def calculate_position_size(self, signal: Dict, available_cash: float) -> float:
        """Calculate position size using v7.2 1% risk rule"""
        entry_price = signal['indicators']['price']
        
        # Calculate stop loss price (SMA 200 for standard trades)
        stop_loss_price = signal['indicators'].get('sma_200', entry_price * 0.95)
        
        # Use v7.2 position sizing (1% risk rule)
        shares = calculate_position_size_v7_2(available_cash, entry_price, stop_loss_price)
        
        return shares * entry_price  # Return position value


class PaperExecutor(Executor):
    """Paper trading executor for simulation"""
    
    def __init__(self, portfolio_file='data/portfolio.json', config_file='config.json'):
        super().__init__(config_file)
        self.portfolio_file = os.path.abspath(portfolio_file)
        self.state = self._load_portfolio_state()
        
    def _load_portfolio_state(self) -> Dict:
        """Load portfolio state from file with robust error handling."""
        log_info(f"Loading paper portfolio from: {self.portfolio_file}")
        
        if not os.path.exists(self.portfolio_file):
            log_info(f"No portfolio found at {self.portfolio_file}, starting fresh.")
            return {
                'cash': 100000.0,
                'positions': {},
                'trade_history': [],
                'execution_mode': 'PAPER'
            }
        
        try:
            with open(self.portfolio_file, 'r') as f:
                data = json.load(f)
            
            # Use .get() to prevent crashes if keys are missing
            cash = float(data.get("cash", 100000.0))
            positions = data.get("positions", {})
            trade_history = data.get("trade_history", [])
            execution_mode = data.get("execution_mode", "PAPER")
            
            state = {
                'cash': cash,
                'positions': positions,
                'trade_history': trade_history,
                'execution_mode': execution_mode
            }
            
            log_info(f"✅ Successfully loaded paper portfolio from {self.portfolio_file}")
            log_info(f"   💰 Cash: ${cash:,.2f}")
            log_info(f"   📈 Positions: {len(positions)}")
            log_info(f"   📊 Trade History: {len(trade_history)} trades")
            log_info(f"   🎯 Execution Mode: {execution_mode}")
            
            return state
            
        except json.JSONDecodeError as e:
            log_error(f"❌ JSON decode error in portfolio file: {e}")
            # Start with fresh portfolio
            return self._create_fresh_portfolio()
        except Exception as e:
            log_error(f"❌ Error loading portfolio: {e}")
            # Start with fresh portfolio
            return self._create_fresh_portfolio()
    
    def _create_fresh_portfolio(self) -> Dict:
        """Create a fresh portfolio state."""
        log_warning("Creating fresh paper portfolio")
        return {
            'cash': 100000.0,
            'positions': {},
            'trade_history': [],
            'execution_mode': 'PAPER'
        }
    
    def _save_portfolio_state(self):
        """Save portfolio state to file"""
        try:
            directory = os.path.dirname(self.portfolio_file)
            if directory:  # Only try to create if directory string is not empty
                os.makedirs(directory, exist_ok=True)
            
            # Create backup
            backup_file = self.portfolio_file.replace('.json', '_backup.json')
            if os.path.exists(self.portfolio_file):
                import shutil
                shutil.copy2(self.portfolio_file, backup_file)
            
            # Save main file
            with open(self.portfolio_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            log_info("Portfolio state saved")
        except Exception as e:
            log_error(f"Error saving portfolio: {e}")
    
    def execute_buy(self, signal: Dict, available_cash: float) -> Dict:
        """Execute a paper buy order using v7.2 hybrid strategy"""
        ticker = signal['ticker']
        current_price = signal['indicators']['price']
        
        # v7.2: Penny Stock Filter - Minimum price $1.00
        if current_price < 1.00:
            return {
                'success': False,
                'reason': f'Penny stock filter: Price ${current_price:.2f} below $1.00 minimum',
                'trade': None
            }
        
        # Calculate position size using v7.2 1% risk rule
        position_size = self.calculate_position_size(signal, available_cash)
        
        if position_size > available_cash:
            return {
                'success': False,
                'reason': f'Insufficient cash: need ${position_size:.2f}, have ${available_cash:.2f}',
                'trade': None
            }
        
        entry_price = current_price
        stop_loss_price = signal['indicators'].get('sma_200', entry_price * 0.95)
        shares = calculate_position_size_v7_2(available_cash, entry_price, stop_loss_price)
        cost = shares * entry_price
        
        # Update portfolio state with v7.2 features
        self.state['cash'] -= cost
        self.state['positions'][ticker] = {
            'shares': shares,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'entry_date': datetime.now().strftime('%Y-%m-%d'),
            'quality_score': signal.get('quality_score', 0),
            'execution_mode': 'PAPER',
            'is_power_stock': signal.get('is_power_stock', False),  # v7.2: Power Stock status
            'highest_price': entry_price,  # v7.2: Track highest price for trailing stop
            'ticker': ticker  # v7.2: Add ticker for exit logic
        }
        
        # Record trade
        trade = {
            'type': 'BUY',
            'ticker': ticker,
            'shares': shares,
            'price': current_price,
            'cost': cost,
            'timestamp': datetime.now().isoformat(),
            'execution_mode': 'PAPER',
            'quality_score': signal.get('quality_score', 0),
            'reason': signal.get('reason', ''),
            'is_power_stock': signal.get('is_power_stock', False),  # v7.2: Track Power Stock status
            'stop_loss_price': stop_loss_price  # v7.2: Track stop loss
        }
        
        self.state['trade_history'].append(trade)
        self._save_portfolio_state()
        
        # v7.2: Enhanced logging
        power_status = "POWER STOCK" if signal.get('is_power_stock', False) else "Standard"
        log_info(f"[PAPER BUY] {ticker}: {shares:.0f} shares @ ${entry_price:.2f} | Cost: ${cost:.2f} | {power_status}")
        
        return {
            'success': True,
            'reason': f'Paper buy executed for {ticker}',
            'trade': trade
        }
    
    def execute_sell(self, signal: Dict, position: Dict) -> Dict:
        """Execute a paper sell order using v7.2 hybrid strategy"""
        ticker = signal['ticker']
        current_price = signal['indicators']['price']
        
        shares = position['shares']
        entry_price = position['entry_price']
        is_power_stock = position.get('is_power_stock', False)  # v7.2: Check Power Stock status
        
        # Calculate P&L
        entry_value = entry_price * shares
        exit_value = current_price * shares
        profit_loss = exit_value - entry_value
        profit_loss_pct = (profit_loss / entry_value) * 100
        
        # Update portfolio state
        self.state['cash'] += exit_value
        del self.state['positions'][ticker]
        
        # Record trade with v7.2 features
        trade = {
            'type': 'SELL',
            'ticker': ticker,
            'shares': shares,
            'entry_price': entry_price,
            'exit_price': current_price,
            'profit_loss': profit_loss,
            'profit_loss_pct': profit_loss_pct,
            'timestamp': datetime.now().isoformat(),
            'execution_mode': 'PAPER',
            'reason': signal.get('reason', ''),
            'is_power_stock': is_power_stock,  # v7.2: Track if it was a Power Stock
            'highest_price': position.get('highest_price', entry_price)  # v7.2: Track highest price reached
        }
        
        self.state['trade_history'].append(trade)
        self._save_portfolio_state()
        
        # v7.2: Enhanced logging with Power Stock status
        power_status = "POWER STOCK" if is_power_stock else "Standard"
        log_info(f"[PAPER SELL] {ticker}: {shares:.0f} shares @ ${current_price:.2f} | P/L: ${profit_loss:.2f} ({profit_loss_pct:.2f}%) | {power_status}")
        
        return {
            'success': True,
            'reason': f'Paper sell executed for {ticker}',
            'trade': trade
        }
    
    def get_portfolio_summary(self, current_prices: Optional[Dict] = None) -> Dict:
        """Get current portfolio summary"""
        cash = self.state['cash']
        positions_value = 0.0
        positions_detail = []
        
        # Calculate positions value
        for ticker, position in self.state['positions'].items():
            shares = position['shares']
            entry_price = position['entry_price']
            
            # Use current price if provided, otherwise use entry price
            if current_prices and ticker in current_prices:
                current_price = current_prices[ticker]
            else:
                current_price = entry_price
            
            position_value = shares * current_price
            positions_value += position_value
            
            unrealized_pl = (current_price - entry_price) * shares
            unrealized_pl_pct = ((current_price - entry_price) / entry_price) * 100
            
            positions_detail.append({
                'ticker': ticker,
                'shares': shares,
                'entry_price': entry_price,
                'current_price': current_price,
                'value': position_value,
                'unrealized_pl': unrealized_pl,
                'unrealized_pl_pct': unrealized_pl_pct,
                'entry_date': position['entry_date']
            })
        
        total_value = cash + positions_value
        initial_value = 100000.0
        total_return = ((total_value - initial_value) / initial_value) * 100
        
        # Calculate realized P/L from trade history
        realized_pl = sum(
            trade.get('profit_loss', 0) 
            for trade in self.state['trade_history'] 
            if trade['type'] == 'SELL'
        )
        
        return {
            'execution_mode': 'PAPER',
            'cash': cash,
            'positions_value': positions_value,
            'total_value': total_value,
            'total_return_pct': total_return,
            'total_return_dollars': total_value - initial_value,
            'num_positions': len(self.state['positions']),
            'positions_detail': positions_detail,
            'realized_pl': realized_pl,
            'total_trades': len(self.state['trade_history'])
        }
    
    def process_signals(self, buy_signals: List[Dict], sell_signals: List[Dict], 
                       current_prices: Optional[Dict] = None) -> Dict:
        """Process trading signals"""
        trades_executed = {
            'buys': [],
            'sells': [],
            'errors': []
        }
        
        # Detailed trade log for email reporting
        detailed_trade_log = []
        
        log_info(f"Processing {len(buy_signals)} BUY signals and {len(sell_signals)} SELL signals")
        log_info(f"Current positions: {len(self.state['positions'])}/10")
        log_info(f"Available cash: ${self.state['cash']:,.2f}")
        
        # Process SELL signals first
        for signal in sell_signals:
            ticker = signal['ticker']
            if ticker in self.state['positions']:
                try:
                    result = self.execute_sell(signal, self.state['positions'][ticker])
                    if result['success']:
                        trades_executed['sells'].append(result['trade'])
                        # Add to detailed trade log
                        trade = result['trade']
                        detailed_trade_log.append({
                            'time': datetime.fromisoformat(trade['timestamp']).strftime('%H:%M'),
                            'ticker': trade['ticker'],
                            'action': 'SELL',
                            'price': trade['exit_price'],
                            'shares': trade['shares'],
                            'value': trade['exit_price'] * trade['shares'],
                            'reason': trade.get('reason', 'Profit taking')
                        })
                    else:
                        trades_executed['errors'].append({
                            'ticker': ticker,
                            'type': 'SELL',
                            'reason': result['reason']
                        })
                except Exception as e:
                    log_error(f"Error executing sell for {ticker}: {e}")
                    trades_executed['errors'].append({
                        'ticker': ticker,
                        'type': 'SELL',
                        'reason': str(e)
                    })
        
        # Process BUY signals
        available_slots = 10 - len(self.state['positions'])
        available_cash = self.state['cash']
        
        # Sort by quality score (highest first)
        sorted_buy_signals = sorted(buy_signals, key=lambda x: x.get('quality_score', 0), reverse=True)
        
        for signal in sorted_buy_signals[:available_slots]:
            ticker = signal['ticker']
            
            # Skip if already holding
            if ticker in self.state['positions']:
                log_info(f"Skipping {ticker} - already holding")
                continue
            
            # Check position limits
            if not self.check_position_limits(self.state['positions'], ticker):
                log_info(f"Skipping {ticker} - position limits exceeded")
                continue
            
            try:
                result = self.execute_buy(signal, available_cash)
                if result['success']:
                    trades_executed['buys'].append(result['trade'])
                    available_cash -= result['trade']['cost']
                    # Add to detailed trade log
                    trade = result['trade']
                    detailed_trade_log.append({
                        'time': datetime.fromisoformat(trade['timestamp']).strftime('%H:%M'),
                        'ticker': trade['ticker'],
                        'action': 'BUY',
                        'price': trade['price'],
                        'shares': trade['shares'],
                        'value': trade['cost'],
                        'reason': f"Score: {trade.get('quality_score', 0):.1f}"
                    })
                else:
                    trades_executed['errors'].append({
                        'ticker': ticker,
                        'type': 'BUY',
                        'reason': result['reason']
                    })
            except Exception as e:
                log_error(f"Error executing buy for {ticker}: {e}")
                trades_executed['errors'].append({
                    'ticker': ticker,
                    'type': 'BUY',
                    'reason': str(e)
                })
        
        log_info(f"Trade execution complete: {len(trades_executed['buys'])} buys, {len(trades_executed['sells'])} sells")
        
        # Return both executed trades and detailed trade log
        return {
            'buys': trades_executed['buys'],
            'sells': trades_executed['sells'], 
            'errors': trades_executed['errors'],
            'detailed_trade_log': detailed_trade_log
        }

    def check_v7_2_exit_conditions(self, ticker: str, df_data: Dict) -> Optional[Dict]:
        """
        v7.2: Check if position should be sold using hybrid exit logic
        Returns sell signal if exit conditions are met
        """
        if ticker not in self.state['positions']:
            return None
        
        position = self.state['positions'][ticker]
        
        # Add indicators to the data
        df_with_indicators = add_indicators_v7_2(df_data[ticker])
        
        # Check v7.2 exit conditions
        should_exit, exit_reason = check_exit_conditions_v7_2(df_with_indicators, position)
        
        if should_exit:
            # Create sell signal
            latest = df_with_indicators.iloc[-1]
            current_price = latest['adjClose'] if 'adjClose' in latest else latest['Close'] if 'Close' in latest else latest['close']
            
            # Update position state before creating signal
            self.state['positions'][ticker].update(position)
            
            return {
                'ticker': ticker,
                'signal': 'SELL',
                'reason': f'v7.2 Exit: {exit_reason}',
                'indicators': {
                    'price': current_price,
                    'is_power_stock': position.get('is_power_stock', False)
                }
            }
        
        return None


class LiveExecutor(Executor):
    """Live trading executor for real brokerage integration"""
    
    def __init__(self, config_file='config.json'):
        super().__init__(config_file)
        self.execution_mode = 'LIVE'
        log_warning("LiveExecutor is placeholder - not implemented for real trading")
        
        # TODO: Initialize brokerage API connection
        # self.brokerage = BrokerageAPI(config)
    
    def execute_buy(self, signal: Dict, available_cash: float) -> Dict:
        """Execute a live buy order"""
        # TODO: Implement real brokerage buy order
        log_error("Live trading not implemented - placeholder only")
        return {
            'success': False,
            'reason': 'Live trading not implemented',
            'trade': None
        }
    
    def execute_sell(self, signal: Dict, position: Dict) -> Dict:
        """Execute a live sell order"""
        # TODO: Implement real brokerage sell order
        log_error("Live trading not implemented - placeholder only")
        return {
            'success': False,
            'reason': 'Live trading not implemented',
            'trade': None
        }
    
    def get_portfolio_summary(self, current_prices: Optional[Dict] = None) -> Dict:
        """Get current portfolio summary from brokerage"""
        # TODO: Get real portfolio from brokerage
        log_error("Live trading not implemented - placeholder only")
        return {
            'execution_mode': 'LIVE',
            'cash': 0.0,
            'positions_value': 0.0,
            'total_value': 0.0,
            'total_return_pct': 0.0,
            'total_return_dollars': 0.0,
            'num_positions': 0,
            'positions_detail': [],
            'realized_pl': 0.0,
            'total_trades': 0
        }
    
    def process_signals(self, buy_signals: List[Dict], sell_signals: List[Dict], 
                       current_prices: Optional[Dict] = None) -> Dict:
        """Process trading signals with live execution"""
        # TODO: Implement real signal processing
        log_error("Live trading not implemented - placeholder only")
        return {
            'buys': [],
            'sells': [],
            'errors': [{'reason': 'Live trading not implemented'}],
            'detailed_trade_log': []
        }


def get_executor(config_file='config.json', portfolio_file=None) -> Executor:
    """Factory function to get appropriate executor based on config"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        trading_mode = config.get('TRADING_MODE', 'PAPER').upper()
        
        # Default portfolio file if not provided
        if portfolio_file is None:
            portfolio_file = 'data/portfolio.json'
        
        if trading_mode == 'LIVE':
            log_warning("Live trading mode selected - using placeholder implementation")
            return LiveExecutor(config_file)
        else:
            log_info(f"Paper trading mode selected")
            return PaperExecutor(portfolio_file, config_file)
    
    except Exception as e:
        log_error(f"Error determining executor: {e}, defaulting to paper")
        # Default portfolio file if not provided
        if portfolio_file is None:
            portfolio_file = 'data/portfolio.json'
        return PaperExecutor(portfolio_file, config_file)
