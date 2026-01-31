"""
Paper Trading Portfolio Tracker
Simulates trading performance based on signals
"""

import json
import os
from datetime import datetime
from src.notifications import log_info, log_warning

class Portfolio:
    """Manages virtual portfolio for paper trading."""
    
    def __init__(self, portfolio_file='data/portfolio.json'):
        self.portfolio_file = portfolio_file
        self.state = self._load_state()
    
    def _load_state(self):
        """Load portfolio state from JSON file."""
        if os.path.exists(self.portfolio_file):
            try:
                with open(self.portfolio_file, 'r') as f:
                    state = json.load(f)
                    log_info(f"Loaded portfolio: ${state['cash']:.2f} cash, {len(state['positions'])} positions")
                    return state
            except Exception as e:
                log_warning(f"Error loading portfolio: {e}, creating new")
        
        # Initialize new portfolio
        return {
            'cash': 100000.0,
            'positions': {},
            'trade_history': []
        }
    
    def _save_state(self):
        """Save portfolio state to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.portfolio_file), exist_ok=True)
            with open(self.portfolio_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            log_info("Portfolio state saved")
        except Exception as e:
            log_warning(f"Error saving portfolio: {e}")
    
    def process_signals(self, buy_signals, sell_signals):
        """
        Process buy and sell signals.
        
        Args:
            buy_signals: List of buy signal dicts (sorted by quality_score)
            sell_signals: List of sell signal dicts
        
        Returns:
            Dict with trade summary
        """
        trades_executed = {
            'sells': [],
            'buys': []
        }
        
        # Process SELL signals first
        for signal in sell_signals:
            ticker = signal['ticker']
            if ticker in self.state['positions']:
                position = self.state['positions'][ticker]
                current_price = signal['indicators']['price']
                
                # Calculate profit/loss
                entry_price = position['entry_price']
                shares = position['shares']
                entry_value = entry_price * shares
                exit_value = current_price * shares
                profit_loss = exit_value - entry_value
                profit_loss_pct = (profit_loss / entry_value) * 100
                
                # Execute sell
                self.state['cash'] += exit_value
                
                # Log trade
                trade = {
                    'type': 'SELL',
                    'ticker': ticker,
                    'shares': shares,
                    'entry_price': entry_price,
                    'entry_date': position['entry_date'],
                    'exit_price': current_price,
                    'exit_date': datetime.now().strftime('%Y-%m-%d'),
                    'profit_loss': profit_loss,
                    'profit_loss_pct': profit_loss_pct
                }
                
                self.state['trade_history'].append(trade)
                trades_executed['sells'].append(trade)
                
                # Remove position
                del self.state['positions'][ticker]
                
                log_info(f"SOLD {ticker}: {shares} shares @ ${current_price:.2f} | P/L: ${profit_loss:.2f} ({profit_loss_pct:.2f}%)")
        
        # Process BUY signals
        max_positions = 10
        position_size = 5000.0  # $5,000 per trade
        
        current_positions = len(self.state['positions'])
        available_slots = max_positions - current_positions
        
        if available_slots > 0 and self.state['cash'] >= position_size:
            # Buy signals are already sorted by quality_score (highest first)
            for signal in buy_signals[:available_slots]:
                ticker = signal['ticker']
                
                # Skip if already holding
                if ticker in self.state['positions']:
                    continue
                
                # Check if we have enough cash
                if self.state['cash'] < position_size:
                    break
                
                current_price = signal['indicators']['price']
                shares = position_size / current_price
                cost = shares * current_price
                
                # Execute buy
                self.state['cash'] -= cost
                
                # Add position
                self.state['positions'][ticker] = {
                    'shares': shares,
                    'entry_price': current_price,
                    'entry_date': datetime.now().strftime('%Y-%m-%d'),
                    'quality_score': signal.get('quality_score', 0)
                }
                
                # Log trade
                trade = {
                    'type': 'BUY',
                    'ticker': ticker,
                    'shares': shares,
                    'entry_price': current_price,
                    'entry_date': datetime.now().strftime('%Y-%m-%d'),
                    'cost': cost,
                    'quality_score': signal.get('quality_score', 0)
                }
                
                self.state['trade_history'].append(trade)
                trades_executed['buys'].append(trade)
                
                log_info(f"BOUGHT {ticker}: {shares:.2f} shares @ ${current_price:.2f} | Cost: ${cost:.2f}")
        
        # Save state
        self._save_state()
        
        return trades_executed
    
    def get_summary(self, current_prices=None):
        """
        Get portfolio summary.
        
        Args:
            current_prices: Dict of {ticker: current_price} for positions
        
        Returns:
            Dict with portfolio metrics
        """
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
    
    def get_current_positions(self):
        """Get list of currently held tickers."""
        return list(self.state['positions'].keys())
