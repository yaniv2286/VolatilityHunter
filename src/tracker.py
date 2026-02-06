"""
Paper Trading Portfolio Tracker
Simulates trading performance based on signals
"""

import json
import os
from datetime import datetime
from src.notifications import log_info, log_warning, log_error
import yfinance as yf
import pandas as pd
import time

class Portfolio:
    """Manages virtual portfolio for paper trading."""
    
    def __init__(self, portfolio_file='data/portfolio.json'):
        self.portfolio_file = portfolio_file
        self.state = self._load_state()
    
    def _load_state(self):
        """Load portfolio state from JSON file with backup restoration."""
        if os.path.exists(self.portfolio_file):
            try:
                with open(self.portfolio_file, 'r') as f:
                    state = json.load(f)
                    log_info(f"Loaded portfolio: ${state['cash']:.2f} cash, {len(state['positions'])} positions")
                    return state
            except Exception as e:
                log_warning(f"Error loading portfolio: {e}, trying backup...")
                
                # Try to restore from backup
                backup_file = self.portfolio_file.replace('.json', '_backup.json')
                if os.path.exists(backup_file):
                    try:
                        with open(backup_file, 'r') as f:
                            state = json.load(f)
                            log_info(f"Restored portfolio from backup: ${state['cash']:.2f} cash, {len(state['positions'])} positions")
                            # Save the restored state to main file
                            self.state = state
                            self._save_state()
                            return state
                    except Exception as backup_e:
                        log_error(f"Backup restoration failed: {backup_e}")
        
        # Initialize new portfolio
        log_info("Creating new portfolio (no valid backup found)")
        return {
            'cash': 100000.0,
            'positions': {},
            'trade_history': []
        }
    
    def _save_state(self):
        """Save portfolio state to JSON file with backup."""
        try:
            os.makedirs(os.path.dirname(self.portfolio_file), exist_ok=True)
            
            # Create backup before overwriting
            backup_file = self.portfolio_file.replace('.json', '_backup.json')
            if os.path.exists(self.portfolio_file):
                import shutil
                shutil.copy2(self.portfolio_file, backup_file)
                log_info("Portfolio backup created")
            
            # Save main file
            with open(self.portfolio_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            log_info("Portfolio state saved")
        except Exception as e:
            log_warning(f"Error saving portfolio: {e}")
    
    def _check_risk_management_trades(self, current_prices, trades_executed):
        """Check for stop-loss and take-profit opportunities."""
        
        # Risk management parameters
        STOP_LOSS_PCT = -10.0  # Sell if position drops 10%
        TAKE_PROFIT_PCT = 25.0  # Sell if position gains 25%
        
        log_info("Checking risk management (stop-loss/take-profit)...")
        
        positions_to_close = []
        
        for ticker, position in self.state['positions'].items():
            entry_price = position['entry_price']
            shares = position['shares']
            
            # Get current price
            if current_prices and ticker in current_prices:
                current_price = current_prices[ticker]
            else:
                # Skip if no current price available
                continue
            
            # Calculate profit/loss percentage
            profit_loss_pct = ((current_price - entry_price) / entry_price) * 100
            
            # Check stop-loss
            if profit_loss_pct <= STOP_LOSS_PCT:
                log_info(f"[STOP-LOSS] {ticker}: ${current_price:.2f} ({profit_loss_pct:.2f}%) - Triggering stop-loss")
                positions_to_close.append((ticker, current_price, 'STOP-LOSS'))
            
            # Check take-profit
            elif profit_loss_pct >= TAKE_PROFIT_PCT:
                log_info(f"[TAKE-PROFIT] {ticker}: ${current_price:.2f} ({profit_loss_pct:.2f}%) - Triggering take-profit")
                positions_to_close.append((ticker, current_price, 'TAKE-PROFIT'))
        
        # Execute risk management trades
        for ticker, current_price, reason in positions_to_close:
            position = self.state['positions'][ticker]
            entry_price = position['entry_price']
            shares = position['shares']
            
            # Calculate final values
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
                'profit_loss_pct': profit_loss_pct,
                'reason': reason
            }
            
            self.state['trade_history'].append(trade)
            trades_executed['sells'].append(trade)
            
            # Remove position
            del self.state['positions'][ticker]
            
            log_info(f"[RISK] {reason} {ticker}: {shares:.2f} shares @ ${current_price:.2f} | P/L: ${profit_loss:.2f} ({profit_loss_pct:.2f}%)")
            
            # Force save after risk management trade
            self._save_state()
        
        if positions_to_close:
            log_info(f"Risk management: Closed {len(positions_to_close)} positions")
        else:
            log_info("Risk management: No positions triggered stop-loss/take-profit")
    
    def process_signals(self, buy_signals, sell_signals, current_prices=None):
        """
        Process buy and sell signals with immediate execution and forced save.
        
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
        
        log_info(f"Processing {len(buy_signals)} BUY signals and {len(sell_signals)} SELL signals")
        log_info(f"Current positions: {len(self.state['positions'])}/10")
        log_info(f"Available cash: ${self.state['cash']:,.2f}")
        
        # Step 1: Risk Management - Check for stop-loss and take-profit opportunities
        self._check_risk_management_trades(current_prices, trades_executed)
        
        # Step 2: Process SELL signals from strategy
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
                
                # Execute sell immediately
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
                
                # Force save after each sell
                self._save_state()
        
        # Process BUY signals
        max_positions = 10
        position_size = 5000.0  # $5,000 per trade
        
        current_positions = len(self.state['positions'])
        available_slots = max_positions - current_positions
        
        log_info(f"Available slots: {available_slots}")
        log_info(f"Position size: ${position_size:,.2f}")
        
        if available_slots > 0 and self.state['cash'] >= position_size:
            # Buy signals are already sorted by quality_score (highest first)
            for signal in buy_signals[:available_slots]:
                ticker = signal['ticker']
                
                # Skip if already holding
                if ticker in self.state['positions']:
                    log_info(f"Skipping {ticker} - already holding")
                    continue
                
                # Check sector diversification
                from src.strategy import check_sector_diversification
                if not check_sector_diversification(self.state['positions'], ticker):
                    sector = check_sector_diversification.__globals__.get('SECTOR_MAPPING', {}).get(ticker, 'Unknown')
                    log_info(f"Skipping {ticker} - sector limit reached ({sector})")
                    continue
                
                # Check if we have enough cash
                if self.state['cash'] < position_size:
                    log_info(f"Skipping {ticker} - insufficient cash (${self.state['cash']:.2f} < ${position_size:.2f})")
                    break
                
                current_price = signal['indicators']['price']
                shares = position_size / current_price
                cost = shares * current_price
                
                # Execute buy immediately
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
                
                # Force save after each buy
                self._save_state()
        else:
            if available_slots <= 0:
                log_info("No available slots for new positions")
            if self.state['cash'] < position_size:
                log_info(f"Insufficient cash for new positions (${self.state['cash']:.2f} < ${position_size:.2f})")
        
        # Final save to ensure all trades are recorded
        self._save_state()
        
        log_info(f"Trade execution complete: {len(trades_executed['buys'])} buys, {len(trades_executed['sells'])} sells")
        log_info(f"Portfolio now has {len(self.state['positions'])}/10 positions")
        log_info(f"Cash remaining: ${self.state['cash']:,.2f}")
        
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
    
    def fetch_current_prices(self, tickers=None):
        """
        Fetch current market prices using bulk download for live valuation.
        
        Args:
            tickers: List of ticker symbols (optional, defaults to all positions)
            
        Returns:
            Dict of {ticker: current_price}
        """
        if tickers is None:
            tickers = list(self.state['positions'].keys())
        
        if not tickers:
            log_info("No positions to fetch prices for")
            return {}
        
        current_prices = {}
        retry_count = 0
        max_retries = 1
        
        while retry_count <= max_retries:
            try:
                log_info(f"Fetching live prices for {len(tickers)} positions: {', '.join(tickers)}")
                
                # Use bulk download for all tickers at once
                data = yf.download(
                    tickers, 
                    period='5d',  # Use 5 days to ensure we get recent data
                    progress=False
                )
                
                if data.empty:
                    log_warning(f"Bulk download returned empty data (attempt {retry_count + 1}/{max_retries + 1})")
                    if retry_count < max_retries:
                        log_info("Waiting 10 seconds before retry...")
                        time.sleep(10)
                        retry_count += 1
                        continue
                    else:
                        log_error("CRITICAL: Live valuation failed, check internet/headers.")
                        print("CRITICAL: Live valuation failed, check internet/headers.")
                        return current_prices
                
                # Extract prices from bulk download
                live_prices_obtained = 0
                if isinstance(data.columns, pd.MultiIndex):
                    # Multiple tickers - get the last close price for each
                    for ticker in tickers:
                        try:
                            if ('Close', ticker) in data.columns:
                                close_prices = data['Close'][ticker].dropna()
                                if len(close_prices) > 0:
                                    current_price = close_prices.iloc[-1]
                                    current_prices[ticker] = float(current_price)
                                    live_prices_obtained += 1
                                    log_info(f"[VALUATION] Successfully fetched live price for {ticker}: ${current_price:.2f}")
                                else:
                                    log_warning(f"No price data available for {ticker}")
                            else:
                                log_warning(f"Ticker {ticker} not found in downloaded data")
                        except Exception as e:
                            log_error(f"Error processing {ticker}: {e}")
                else:
                    # Single ticker
                    if len(data) > 0:
                        current_price = data['Close'].iloc[-1]
                        current_prices[tickers[0]] = float(current_price)
                        live_prices_obtained += 1
                        log_info(f"[VALUATION] Successfully fetched live price for {tickers[0]}: ${current_price:.2f}")
                    else:
                        log_warning(f"No price data available for {tickers[0]}")
                
                log_info(f"[VALUATION] Successfully fetched live price for {live_prices_obtained} positions")
                
                # Critical check: if we couldn't get any live prices for held positions
                if live_prices_obtained == 0:
                    log_error("CRITICAL: Live valuation failed, check internet/headers.")
                    print("CRITICAL: Live valuation failed, check internet/headers.")
                
                return current_prices
                
            except Exception as e:
                log_error(f"Error in bulk price fetching (attempt {retry_count + 1}/{max_retries + 1}): {e}")
                if retry_count < max_retries:
                    log_info("Waiting 10 seconds before retry...")
                    time.sleep(10)
                    retry_count += 1
                else:
                    log_error("Max retries reached for live price fetching")
                    print("CRITICAL: Live valuation failed, check internet/headers.")
                    break
        
        # Fallback: Use last known price from local data
        log_info("Falling back to local data for price estimation...")
        from src.data_loader import get_stock_data
        
        for ticker in tickers:
            try:
                df = get_stock_data(ticker)
                if df is not None and len(df) > 0:
                    last_price = df.iloc[-1]['Close']
                    current_prices[ticker] = float(last_price)
                    log_info(f"[FALLBACK] {ticker}: ${current_prices[ticker]:.2f} (from local data)")
                else:
                    log_warning(f"No local data available for {ticker}")
            except Exception as fallback_error:
                log_error(f"Error getting local data for {ticker}: {fallback_error}")
        
        return current_prices
    
    def update_portfolio_valuation(self):
        """
        Update portfolio valuation with current market prices and force sync.
        Ensures Total Value = (Current_Price * Shares) + Cash.
        
        Returns:
            Dict with updated portfolio summary
        """
        log_info("Updating portfolio valuation with current market prices...")
        
        # Fetch current prices for all positions
        current_prices = self.fetch_current_prices()
        
        if not current_prices:
            log_warning("No current prices available, using entry prices")
            current_prices = None
        
        # Get updated summary
        summary = self.get_summary(current_prices)
        
        # Force recalculation using current market prices
        log_info("Recalculating portfolio value with current market prices...")
        total_value = self.state['cash']
        
        for ticker, position in self.state['positions'].items():
            shares = position['shares']
            if current_prices and ticker in current_prices:
                current_price = current_prices[ticker]
                position_value = shares * current_price
                total_value += position_value
                log_info(f"[MARKET VALUE] {ticker}: {shares:.2f} shares @ ${current_price:.2f} = ${position_value:.2f}")
            else:
                # Fallback to entry price if current price not available
                entry_price = position['entry_price']
                position_value = shares * entry_price
                total_value += position_value
                log_info(f"[ENTRY VALUE] {ticker}: {shares:.2f} shares @ ${entry_price:.2f} = ${position_value:.2f}")
        
        # Calculate returns based on $100,000 starting capital
        initial_capital = 100000.0
        total_return_dollars = total_value - initial_capital
        total_return_pct = (total_return_dollars / initial_capital) * 100
        
        # Update summary with forced calculation
        summary['total_value'] = total_value
        summary['total_return_dollars'] = total_return_dollars
        summary['total_return_pct'] = total_return_pct
        
        # Log portfolio updates
        log_info(f"[PORTFOLIO] Valuation Updated:")
        log_info(f"   Total Value: ${summary['total_value']:,.2f}")
        log_info(f"   Cash: ${summary['cash']:,.2f}")
        log_info(f"   Positions Value: ${summary['positions_value']:,.2f}")
        log_info(f"   Total Return: ${summary['total_return_dollars']:,.2f} ({summary['total_return_pct']:+.2f}%)")
        log_info(f"   Positions: {summary['num_positions']}")
        
        # Log individual position updates
        for pos in summary['positions_detail']:
            log_info(f"   {pos['ticker']}: {pos['shares']:.2f} shares @ ${pos['current_price']:.2f} | "
                    f"P/L: ${pos['unrealized_pl']:.2f} ({pos['unrealized_pl_pct']:+.2f}%)")
        
        # Force save portfolio state after valuation
        self._save_state()
        log_info("Portfolio state synchronized and saved")
        
        return summary
