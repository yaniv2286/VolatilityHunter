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
        self.portfolio_file = os.path.abspath(portfolio_file)
        self.state = self._load_state()
    
    def _load_state(self):
        """Load portfolio state from JSON file with robust error handling."""
        log_info(f"Loading portfolio from: {self.portfolio_file}")
        
        if not os.path.exists(self.portfolio_file):
            log_info(f"No portfolio found at {self.portfolio_file}, starting fresh.")
            return {
                'cash': 100000.0,
                'positions': {},
                'trade_history': []
            }
        
        try:
            with open(self.portfolio_file, 'r') as f:
                data = json.load(f)
            
            # Use .get() to prevent crashes if keys are missing
            cash = float(data.get("cash", 100000.0))
            positions = data.get("positions", {})
            trade_history = data.get("trade_history", [])
            
            state = {
                'cash': cash,
                'positions': positions,
                'trade_history': trade_history
            }
            
            log_info(f"✅ Successfully loaded portfolio from {self.portfolio_file}")
            log_info(f"   💰 Cash: ${cash:,.2f}")
            log_info(f"   📈 Positions: {len(positions)}")
            log_info(f"   📊 Trade History: {len(trade_history)} trades")
            
            return state
            
        except json.JSONDecodeError as e:
            log_error(f"❌ JSON decode error in portfolio file: {e}")
            # Try backup restoration
            return self._try_backup_restore()
        except Exception as e:
            log_error(f"❌ Error loading portfolio: {e}")
            # Try backup restoration
            return self._try_backup_restore()
    
    def _try_backup_restore(self):
        """Try to restore portfolio from backup file."""
        backup_file = self.portfolio_file.replace('.json', '_backup.json')
        
        if not os.path.exists(backup_file):
            log_warning("No backup file found, starting with fresh portfolio")
            return {
                'cash': 100000.0,
                'positions': {},
                'trade_history': []
            }
        
        try:
            with open(backup_file, 'r') as f:
                data = json.load(f)
            
            # Use .get() to prevent crashes if keys are missing
            cash = float(data.get("cash", 100000.0))
            positions = data.get("positions", {})
            trade_history = data.get("trade_history", [])
            
            state = {
                'cash': cash,
                'positions': positions,
                'trade_history': trade_history
            }
            
            log_info(f"✅ Restored portfolio from backup: {backup_file}")
            log_info(f"   💰 Cash: ${cash:,.2f}")
            log_info(f"   📈 Positions: {len(positions)}")
            
            # Save the restored state to main file
            self.state = state
            self._save_state()
            
            return state
            
        except Exception as backup_e:
            log_error(f"❌ Backup restoration failed: {backup_e}")
            log_warning("Starting with fresh portfolio as last resort")
            return {
                'cash': 100000.0,
                'positions': {},
                'trade_history': []
            }
    
    def _save_state(self):
        """Save portfolio state to JSON file with backup."""
        try:
            directory = os.path.dirname(self.portfolio_file)
            if directory:  # Only try to create if directory string is not empty
                os.makedirs(directory, exist_ok=True)
            
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
    
    def update_trailing_stops(self, current_prices, atr_data=None):
        """
        Update trailing stops for all open positions (A+ Wealth Builder).
        
        Args:
            current_prices: Dict of {ticker: current_price}
            atr_data: Dict of {ticker: current_atr} for ATR-based stops
        
        Returns:
            List of positions that hit their stop loss
        """
        positions_to_close = []
        
        for ticker, position in self.state['positions'].items():
            current_price = current_prices.get(ticker)
            if current_price is None:
                continue
            
            # Update highest price seen
            old_highest = position.get('highest_price', position['entry_price'])
            new_highest = max(old_highest, current_price)
            position['highest_price'] = new_highest
            
            # Calculate new trailing stop
            if atr_data and ticker in atr_data:
                # ATR-based stop: Highest Price - (3.0 * ATR)
                current_atr = atr_data[ticker]
                new_stop = new_highest - (3.0 * current_atr)
            else:
                # Fallback to 10% fixed stop
                new_stop = new_highest * 0.90
            
            # Only move stop up, never down
            old_stop = position.get('stop_price', position['entry_price'] * 0.90)
            if new_stop > old_stop:
                position['stop_price'] = new_stop
                log_info(f"Updated Stop for {ticker}: ${old_stop:.2f} -> ${new_stop:.2f}")
            
            # Check if stop loss triggered
            if current_price < position['stop_price']:
                positions_to_close.append((ticker, current_price, 'TRAILING_STOP'))
        
        return positions_to_close
    
    def check_exit_conditions(self, current_prices, atr_data=None, sma_data=None, sma_25_data=None):
        """
        Check all exit conditions for open positions (A+ Wealth Builder with Power Stock Shield).
        
        Args:
            current_prices: Dict of {ticker: current_price}
            atr_data: Dict of {ticker: current_atr}
            sma_data: Dict of {ticker: sma_200}
            sma_25_data: Dict of {ticker: sma_25} for Power Stock Shield
        
        Returns:
            List of (ticker, exit_price, reason) tuples for positions to close
        """
        positions_to_close = []
        
        # First update trailing stops
        stop_hits = self.update_trailing_stops(current_prices, atr_data)
        positions_to_close.extend(stop_hits)
        
        # Check exit conditions with Power Stock Shield
        if sma_data:
            for ticker, position in self.state['positions'].items():
                if ticker in [pos[0] for pos in positions_to_close]:  # Skip if already closing
                    continue
                
                current_price = current_prices.get(ticker)
                sma_200 = sma_data.get(ticker)
                sma_25 = sma_25_data.get(ticker) if sma_25_data else None
                
                if current_price is None or sma_200 is None:
                    continue
                
                # Check if this is a Power Stock position
                is_power_stock = position.get('is_power_stock', False)
                
                if is_power_stock:
                    # POWER STOCK SHIELD: Enhanced exit rules
                    # Only exit if Price < SMA 25 (fast trend line) OR trailing stop hit
                    if sma_25 is not None and current_price < sma_25:
                        positions_to_close.append((ticker, current_price, 'POWER_STOCK_SMA_25_BREAK'))
                        log_info(f"[POWER STOCK EXIT] {ticker}: SMA 25 break - Power Stock shield breached")
                    # Trailing stop already handled above
                    
                else:
                    # STANDARD EXIT RULES: SMA 200 break
                    if current_price < sma_200:
                        positions_to_close.append((ticker, current_price, 'SMA_200_BREAK'))
        
        return positions_to_close
    
    def execute_exit_trades(self, positions_to_close):
        """
        Execute exit trades for positions that triggered exit conditions.
        
        Args:
            positions_to_close: List of (ticker, exit_price, reason) tuples
        
        Returns:
            List of executed trade dicts
        """
        executed_trades = []
        
        for ticker, exit_price, reason in positions_to_close:
            if ticker not in self.state['positions']:
                continue
            
            position = self.state['positions'][ticker]
            entry_price = position['entry_price']
            shares = position['shares']
            
            # Calculate P&L
            entry_value = entry_price * shares
            exit_value = exit_price * shares
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
                'exit_price': exit_price,
                'exit_date': datetime.now().strftime('%Y-%m-%d'),
                'profit_loss': profit_loss,
                'profit_loss_pct': profit_loss_pct,
                'reason': reason,
                'stop_price': position.get('stop_price'),
                'highest_price': position.get('highest_price')
            }
            
            self.state['trade_history'].append(trade)
            executed_trades.append(trade)
            
            # Remove position
            del self.state['positions'][ticker]
            
            log_info(f"[EXIT] {reason} {ticker}: {shares:.2f} shares @ ${exit_price:.2f} | P/L: ${profit_loss:.2f} ({profit_loss_pct:.2f}%)")
            
            # Force save after exit
            self._save_state()
        
        return executed_trades
    
    def _check_risk_management_trades(self, current_prices, trades_executed):
        """Check for stop-loss, take-profit, and technical exit opportunities."""
        from src.config_manager import get_config
        from src.strategy import analyze_stock
        from src.storage import DataStorage
        
        config = get_config()
        STOP_LOSS_PCT = config.config.stop_loss_pct
        TAKE_PROFIT_PCT = config.config.take_profit_pct
        
        positions_to_close = []
        
        for ticker, position in self.state['positions'].items():
            entry_price = position['entry_price']
            current_price = current_prices.get(ticker, entry_price) if current_prices else entry_price
            
            if current_price <= 0:
                continue
            
            # Calculate profit/loss percentage
            profit_loss_pct = ((current_price - entry_price) / entry_price) * 100
            
            # Check stop-loss
            if profit_loss_pct <= -STOP_LOSS_PCT:
                log_info(f"[STOP-LOSS] {ticker}: ${current_price:.2f} ({profit_loss_pct:.2f}%) - Triggering stop-loss")
                positions_to_close.append((ticker, current_price, 'STOP-LOSS'))
            
            # Check take-profit
            elif profit_loss_pct >= TAKE_PROFIT_PCT:
                log_info(f"[TAKE-PROFIT] {ticker}: ${current_price:.2f} ({profit_loss_pct:.2f}%) - Triggering take-profit")
                positions_to_close.append((ticker, current_price, 'TAKE-PROFIT'))
            
            # Check technical exit signals (stochastic crossover)
            else:
                try:
                    storage = DataStorage()
                    df = storage.load_data(ticker)
                    if df is not None and len(df) > 0:
                        analysis = analyze_stock(df, ticker)
                        indicators = analysis.get('indicators', {})
                        
                        # Check for stochastic crossover (Stochastic K crossing below D)
                        stoch_k = indicators.get('stochastic_k')
                        stoch_d = indicators.get('stochastic_d')
                        
                        if stoch_k is not None and stoch_d is not None:
                            # Get previous day's values for crossover detection
                            if len(df) >= 2:
                                prev_data = df.iloc[-2]
                                curr_data = df.iloc[-1]
                                
                                prev_k = prev_data.get('Stochastic_K')
                                curr_k = curr_data.get('Stochastic_K')
                                prev_d = prev_data.get('Stochastic_D')
                                curr_d = curr_data.get('Stochastic_D')
                                
                                # Bearish crossover: K was above D, now below D
                                if (prev_k is not None and curr_k is not None and 
                                    prev_d is not None and curr_d is not None):
                                    if prev_k > prev_d and curr_k < curr_d:
                                        log_info(f"[TECHNICAL EXIT] {ticker}: Stochastic bearish crossover (K:{curr_k:.2f} < D:{curr_d:.2f})")
                                        positions_to_close.append((ticker, current_price, 'STOCH_CROSS'))
                        
                        # Check if price falls below key moving averages
                        sma_25 = indicators.get('sma_25')
                        sma_50 = indicators.get('sma_50')
                        sma_100 = indicators.get('sma_100')
                        
                        if current_price < sma_25 and profit_loss_pct > 2.0:  # Only if profitable
                            log_info(f"[TECHNICAL EXIT] {ticker}: Below SMA 25 (${sma_25:.2f}) with profit")
                            positions_to_close.append((ticker, current_price, 'BELOW_SMA_25'))
                        elif current_price < sma_50 and profit_loss_pct > 5.0:  # Only if good profit
                            log_info(f"[TECHNICAL EXIT] {ticker}: Below SMA 50 (${sma_50:.2f}) with good profit")
                            positions_to_close.append((ticker, current_price, 'BELOW_SMA_50'))
                        
                except Exception as e:
                    log_info(f"Technical analysis failed for {ticker}: {e}")
                    continue
        
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
                
                # Add position with ATR-based trailing stop data (A+ Wealth Builder)
                # Check if this is a Power Stock
                is_power_stock = signal.get('indicators', {}).get('is_power_stock', False)
                
                self.state['positions'][ticker] = {
                    'shares': shares,
                    'entry_price': current_price,
                    'entry_date': datetime.now().strftime('%Y-%m-%d'),
                    'quality_score': signal.get('quality_score', 0),
                    'atr_at_entry': signal.get('atr_at_entry', 0.0),  # ATR value at entry
                    'stop_price': signal.get('initial_stop', current_price * 0.90),  # Initial trailing stop
                    'highest_price': current_price,  # Track highest price for trailing stop
                    'is_power_stock': is_power_stock  # Power Stock status for enhanced exit rules
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
    
    def update_portfolio_valuation(self, current_prices=None):
        """
        Update portfolio valuation with current market prices and force sync.
        Ensures Total Value = (Current_Price * Shares) + Cash.
        
        Args:
            current_prices: Optional dict of ticker->price for backtesting mode
                           If None, will fetch current prices for live mode
        
        Returns:
            Dict with updated portfolio summary
        """
        log_info("Updating portfolio valuation with current market prices...")
        
        # Use provided prices or fetch current prices for live mode
        if current_prices is None:
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
