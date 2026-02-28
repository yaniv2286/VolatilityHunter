"""
Portfolio Synchronizer - Syncs local portfolio with IBKR
Ensures TWS portfolio matches email reports exactly
"""

import json
import os
from datetime import datetime
from src.notifications import log_info, log_warning, log_error
from src.brokerage_interface import get_brokerage_interface

class PortfolioSynchronizer:
    """Synchronizes local portfolio with IBKR account"""
    
    def __init__(self, portfolio_file='data/portfolio.json'):
        self.portfolio_file = os.path.abspath(portfolio_file)
        self.ibkr_interface = None
        
    def connect_ibkr(self):
        """Connect to IBKR interface"""
        try:
            self.ibkr_interface = get_brokerage_interface({
                'BROKERAGE_TYPE': 'ibkr',
                'IBKR_HOST': '127.0.0.1',
                'IBKR_PORT': 7497,
                'IBKR_CLIENT_ID': 555
            })
            
            if self.ibkr_interface.connect():
                log_info("PortfolioSynchronizer: Connected to IBKR")
                return True
            else:
                log_error("PortfolioSynchronizer: Failed to connect to IBKR")
                return False
                
        except Exception as e:
            log_error(f"PortfolioSynchronizer: IBKR connection error: {e}")
            return False
    
    def disconnect_ibkr(self):
        """Disconnect from IBKR interface"""
        if self.ibkr_interface:
            self.ibkr_interface.disconnect()
            self.ibkr_interface = None
    
    def load_local_portfolio(self):
        """Load local portfolio state"""
        try:
            with open(self.portfolio_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            log_error(f"PortfolioSynchronizer: Failed to load local portfolio: {e}")
            return None
    
    def get_ibkr_portfolio(self):
        """Get current IBKR portfolio state"""
        if not self.ibkr_interface:
            return None
            
        try:
            # Get account info
            account = self.ibkr_interface.get_account_info()
            
            # Get positions
            positions = self.ibkr_interface.get_positions()
            
            # Convert to local portfolio format
            ibkr_positions = {}
            for pos in positions:
                symbol = pos.get('symbol', '')
                quantity = pos.get('quantity', 0)
                if quantity > 0:
                    ibkr_positions[symbol] = {
                        'shares': abs(quantity),
                        'cost_basis': pos.get('cost_basis', 0),
                        'entry_price': pos.get('entry_price', 0),
                        'last_updated': datetime.now().isoformat()
                    }
            
            return {
                'cash': account.get('cash', 0),
                'positions': ibkr_positions,
                'total_value': account.get('portfolio_value', 0),
                'ibkr_sync_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            log_error(f"PortfolioSynchronizer: Failed to get IBKR portfolio: {e}")
            return None
    
    def sync_portfolio_to_ibkr(self, force_sync=False):
        """
        Sync local portfolio to IBKR
        
        Args:
            force_sync: If True, sync even if portfolios appear similar
            
        Returns:
            dict: Sync results
        """
        log_info("PortfolioSynchronizer: Starting portfolio sync to IBKR")
        
        if not self.connect_ibkr():
            return {'success': False, 'reason': 'Failed to connect to IBKR'}
        
        try:
            # Load local portfolio
            local_portfolio = self.load_local_portfolio()
            if not local_portfolio:
                return {'success': False, 'reason': 'Failed to load local portfolio'}
            
            # Get IBKR portfolio
            ibkr_portfolio = self.get_ibkr_portfolio()
            if not ibkr_portfolio:
                return {'success': False, 'reason': 'Failed to get IBKR portfolio'}
            
            # Compare portfolios
            sync_actions = self._calculate_sync_actions(local_portfolio, ibkr_portfolio)
            
            if not sync_actions and not force_sync:
                log_info("PortfolioSynchronizer: Portfolios already synchronized")
                return {
                    'success': True,
                    'actions': [],
                    'reason': 'Portfolios already synchronized'
                }
            
            # Execute sync actions
            results = self._execute_sync_actions(sync_actions)
            
            log_info(f"PortfolioSynchronizer: Sync completed - {len(results)} actions")
            return {
                'success': True,
                'actions': results,
                'local_portfolio': local_portfolio,
                'ibkr_portfolio': ibkr_portfolio
            }
            
        except Exception as e:
            log_error(f"PortfolioSynchronizer: Sync error: {e}")
            return {'success': False, 'reason': str(e)}
        finally:
            self.disconnect_ibkr()
    
    def _calculate_sync_actions(self, local_portfolio, ibkr_portfolio):
        """Calculate what actions needed to sync portfolios"""
        actions = []
        
        local_positions = local_portfolio.get('positions', {})
        ibkr_positions = ibkr_portfolio.get('positions', {})
        
        # Find positions to add (in local but not in IBKR)
        for symbol, local_pos in local_positions.items():
            if symbol not in ibkr_positions:
                actions.append({
                    'type': 'buy',
                    'symbol': symbol,
                    'shares': local_pos.get('shares', 0),
                    'reason': f'Position {symbol} missing in IBKR'
                })
        
        # Find positions to remove (in IBKR but not in local)
        for symbol, ibkr_pos in ibkr_positions.items():
            if symbol not in local_positions:
                actions.append({
                    'type': 'sell',
                    'symbol': symbol,
                    'shares': ibkr_pos.get('shares', 0),
                    'reason': f'Position {symbol} should not be in IBKR'
                })
        
        # Find position size differences
        for symbol in local_positions:
            if symbol in ibkr_positions:
                local_shares = local_positions[symbol].get('shares', 0)
                ibkr_shares = ibkr_positions[symbol].get('shares', 0)
                
                if local_shares != ibkr_shares:
                    diff = local_shares - ibkr_shares
                    if diff > 0:
                        actions.append({
                            'type': 'buy',
                            'symbol': symbol,
                            'shares': diff,
                            'reason': f'Position size mismatch for {symbol}'
                        })
                    elif diff < 0:
                        actions.append({
                            'type': 'sell',
                            'symbol': symbol,
                            'shares': abs(diff),
                            'reason': f'Position size mismatch for {symbol}'
                        })
        
        return actions
    
    def _execute_sync_actions(self, actions):
        """Execute sync actions"""
        results = []
        
        for action in actions:
            try:
                symbol = action['symbol']
                shares = action['shares']
                action_type = action['type']
                reason = action['reason']
                
                log_info(f"PortfolioSynchronizer: {action_type.upper()} {shares} shares of {symbol} - {reason}")
                
                # Place order
                order_result = self.ibkr_interface.place_market_order(symbol, shares, action_type)
                
                if order_result.get('success', False):
                    order_id = order_result.get('order_id')
                    results.append({
                        'success': True,
                        'action': action,
                        'order_id': order_id,
                        'status': 'placed'
                    })
                    log_info(f"PortfolioSynchronizer: Order placed - ID: {order_id}")
                else:
                    results.append({
                        'success': False,
                        'action': action,
                        'reason': order_result.get('reason', 'Unknown'),
                        'status': 'failed'
                    })
                    log_error(f"PortfolioSynchronizer: Order failed - {order_result.get('reason', 'Unknown')}")
                    
            except Exception as e:
                results.append({
                    'success': False,
                    'action': action,
                    'reason': str(e),
                    'status': 'error'
                })
                log_error(f"PortfolioSynchronizer: Action error - {e}")
        
        return results
    
    def verify_sync(self):
        """Verify that portfolios are synchronized"""
        log_info("PortfolioSynchronizer: Verifying portfolio synchronization")
        
        if not self.connect_ibkr():
            return {'success': False, 'reason': 'Failed to connect to IBKR'}
        
        try:
            # Get both portfolios
            local_portfolio = self.load_local_portfolio()
            ibkr_portfolio = self.get_ibkr_portfolio()
            
            if not local_portfolio or not ibkr_portfolio:
                return {'success': False, 'reason': 'Failed to load portfolios'}
            
            # Compare
            local_positions = set(local_portfolio.get('positions', {}).keys())
            ibkr_positions = set(ibkr_portfolio.get('positions', {}).keys())
            
            missing_in_ibkr = local_positions - ibkr_positions
            extra_in_ibkr = ibkr_positions - local_positions
            
            # Check position sizes
            size_mismatches = []
            for symbol in local_positions & ibkr_positions:
                local_shares = local_portfolio['positions'][symbol].get('shares', 0)
                ibkr_shares = ibkr_portfolio['positions'][symbol].get('shares', 0)
                if local_shares != ibkr_shares:
                    size_mismatches.append({
                        'symbol': symbol,
                        'local_shares': local_shares,
                        'ibkr_shares': ibkr_shares
                    })
            
            is_synced = (len(missing_in_ibkr) == 0 and 
                        len(extra_in_ibkr) == 0 and 
                        len(size_mismatches) == 0)
            
            result = {
                'success': True,
                'is_synchronized': is_synced,
                'missing_in_ibkr': list(missing_in_ibkr),
                'extra_in_ibkr': list(extra_in_ibkr),
                'size_mismatches': size_mismatches,
                'local_cash': local_portfolio.get('cash', 0),
                'ibkr_cash': ibkr_portfolio.get('cash', 0),
                'local_position_count': len(local_positions),
                'ibkr_position_count': len(ibkr_positions)
            }
            
            if is_synced:
                log_info("PortfolioSynchronizer: ✅ Portfolios are synchronized")
            else:
                log_warning("PortfolioSynchronizer: ❌ Portfolios are NOT synchronized")
            
            return result
            
        except Exception as e:
            log_error(f"PortfolioSynchronizer: Verification error: {e}")
            return {'success': False, 'reason': str(e)}
        finally:
            self.disconnect_ibkr()
