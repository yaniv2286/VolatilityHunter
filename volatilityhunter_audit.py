#!/usr/bin/env python3
"""
VolatilityHunter Full Deep Dive Audit
Comprehensive system analysis and reporting tool
"""

import os
import sys
import time
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import subprocess
import gc
import platform

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config_manager import get_config
from src.storage import DataStorage
from src.tracker import Portfolio
from src.strategy import analyze_stock
from src.data_loader_factory import get_data_loader
from src.smart_data_loader_factory import get_smart_data_loader
from src.email_notifier import EmailNotifier
from src.log_collector import LogCollector
from src.notifications import log_info, log_error, log_warning
from src.ticker_manager import TickerManager

class VolatilityHunterAuditor:
    """Comprehensive system auditor for VolatilityHunter"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.config = get_config()
        self.storage = DataStorage()
        self.portfolio = Portfolio()
        self.results = {
            'audit_start': self.start_time.isoformat(),
            'system_info': {},
            'configuration_audit': {},
            'data_audit': {},
            'portfolio_audit': {},
            'strategy_audit': {},
            'performance_audit': {},
            'security_audit': {},
            'integration_audit': {},
            'risk_audit': {},
            'email_audit': {},
            'log_audit': {},
            'recommendations': [],
            'critical_issues': [],
            'warnings': [],
            'summary': {}
        }
    
    def run_full_audit(self) -> Dict[str, Any]:
        """Execute comprehensive system audit"""
        print("[AUDIT] VOLATILITYHUNTER FULL DEEP DIVE AUDIT")
        print("=" * 60)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        try:
            # System Information
            self._audit_system_info()
            
            # Configuration Audit
            self._audit_configuration()
            
            # Data Audit
            self._audit_data_systems()
            
            # Portfolio Audit
            self._audit_portfolio()
            
            # Strategy Audit
            self._audit_strategy_system()
            
            # Performance Audit
            self._audit_performance()
            
            # Security Audit
            self._audit_security()
            
            # Integration Audit
            self._audit_integrations()
            
            # Risk Management Audit
            self._audit_risk_management()
            
            # Email System Audit
            self._audit_email_system()
            
            # Log Analysis
            self._audit_logs()
            
            # Generate Summary
            self._generate_summary()
            
            # Save Results
            self._save_audit_results()
            
            return self.results
            
        except Exception as e:
            log_error(f"Audit failed: {e}")
            self.results['critical_issues'].append(f"Audit execution failed: {e}")
            return self.results
    
    def _audit_system_info(self):
        """Audit system information and resources"""
        print("[SYSTEM] AUDITING SYSTEM INFORMATION...")
        
        system_info = {
            'python_version': sys.version,
            'platform': sys.platform,
            'cpu_count': os.cpu_count(),
            'memory_total': 'N/A (requires psutil)',
            'memory_available': 'N/A (requires psutil)',
            'disk_usage': 'N/A (requires psutil)',
            'process_count': 'N/A (requires psutil)',
            'uptime': 'N/A (requires psutil)',
            'system': platform.system(),
            'machine': platform.machine(),
            'processor': platform.processor()
        }
        
        self.results['system_info'] = system_info
        
        # Note: Advanced system monitoring requires psutil
        if 'N/A' in str(system_info['memory_total']):
            self.results['warnings'].append("Install psutil for advanced system monitoring")
        
        # Basic checks without psutil
        try:
            import shutil
            disk_usage = shutil.disk_usage('.')
            if disk_usage.percent > 90:
                self.results['critical_issues'].append("High disk usage detected")
        except Exception:
            pass
        
        print(f"  [OK] Python: {system_info['python_version'].split()[0]}")
        print(f"  [OK] CPU: {system_info['cpu_count']} cores")
        print(f"  [OK] Memory: {system_info['memory_total']}")
        print(f"  [OK] System: {system_info['system']}")
        print(f"  [OK] Machine: {system_info['machine']}")
        print()
    
    def _audit_configuration(self):
        """Audit configuration settings"""
        print("[CONFIG] AUDITING CONFIGURATION...")
        
        config_audit = {
            'mode': self.config.config.mode.value,
            'data_source': self.config.config.data_source.value,
            'initial_capital': self.config.config.initial_capital,
            'max_positions': self.config.config.max_positions,
            'position_size': self.config.config.position_size,
            'stop_loss_pct': self.config.config.stop_loss_pct,
            'take_profit_pct': self.config.config.take_profit_pct,
            'email_enabled': self.config.config.email_enabled,
            'backtest_enabled': self.config.config.backtest_enabled,
            'checklist_config': self.config.get_pre_trade_checklist_config()
        }
        
        self.results['configuration_audit'] = config_audit
        
        # Validate configuration
        if config_audit['position_size'] > config_audit['initial_capital']:
            self.results['critical_issues'].append("Position size exceeds initial capital")
        
        if config_audit['max_positions'] * config_audit['position_size'] > config_audit['initial_capital'] * 2:
            self.results['warnings'].append("Maximum exposure exceeds 200% of capital")
        
        print(f"  [OK] Mode: {config_audit['mode']}")
        print(f"  [OK] Data Source: {config_audit['data_source']}")
        print(f"  [OK] Capital: ${config_audit['initial_capital']:,.2f}")
        print(f"  [OK] Max Positions: {config_audit['max_positions']}")
        print(f"  [OK] Position Size: ${config_audit['position_size']:,.2f}")
        print(f"  [OK] Stop Loss: {config_audit['stop_loss_pct']*100:.1f}%")
        print(f"  [OK] Take Profit: {config_audit['take_profit_pct']*100:.1f}%")
        print(f"  [OK] Email: {'Enabled' if config_audit['email_enabled'] else 'Disabled'}")
        print()
    
    def _audit_data_systems(self):
        """Audit data storage and loading systems"""
        print("[DATA] AUDITING DATA SYSTEMS...")
        
        data_audit = {
            'storage_path': self.storage.local_dir,
            'storage_exists': os.path.exists(self.storage.local_dir),
            'available_tickers': [],
            'ticker_count': 0,
            'data_quality': {},
            'data_loader_status': 'unknown',
            'data_source_info': {}
        }
        
        # Check storage
        if data_audit['storage_exists']:
            try:
                tickers = self.storage.list_available_tickers()
                data_audit['available_tickers'] = tickers[:20]  # First 20 for audit
                data_audit['ticker_count'] = len(tickers)
                
                # Sample data quality check
                sample_tickers = tickers[:5] if len(tickers) >= 5 else tickers
                for ticker in sample_tickers:
                    try:
                        df = self.storage.load_data(ticker)
                        if df is not None and len(df) > 0:
                            data_audit['data_quality'][ticker] = {
                                'rows': len(df),
                                'columns': list(df.columns),
                                'date_range': f"{df.index[0]} to {df.index[-1]}" if len(df) > 0 else 'No data',
                                'null_count': df.isnull().sum().sum(),
                                'duplicate_count': df.index.duplicated().sum()
                            }
                        else:
                            data_audit['data_quality'][ticker] = {'status': 'No data'}
                    except Exception as e:
                        data_audit['data_quality'][ticker] = {'status': f'Error: {e}'}
                
            except Exception as e:
                data_audit['storage_status'] = f'Error: {e}'
                self.results['warnings'].append(f"Storage audit error: {e}")
        else:
            self.results['critical_issues'].append("Data storage directory not found")
        
        # Check data loader
        try:
            smart_loader = get_smart_data_loader()
            data_audit['data_source_info'] = smart_loader.get_data_source_info()
            data_audit['data_loader_status'] = 'working'
        except Exception as e:
            data_audit['data_loader_status'] = f'Error: {e}'
            self.results['warnings'].append(f"Data loader error: {e}")
        
        self.results['data_audit'] = data_audit
        
        print(f"  [OK] Storage: {'Found' if data_audit['storage_exists'] else 'Not found'}")
        print(f"  [OK] Tickers: {data_audit['ticker_count']} available")
        print(f"  [OK] Data Loader: {data_audit['data_loader_status']}")
        print(f"  [OK] Data Source: {data_audit['data_source_info'].get('source', 'Unknown')}")
        print()
    
    def _audit_portfolio(self):
        """Audit portfolio state and management"""
        print("[PORTFOLIO] AUDITING PORTFOLIO...")
        
        portfolio_audit = {
            'cash': self.portfolio.state['cash'],
            'positions_count': len(self.portfolio.state['positions']),
            'total_value': 0,
            'positions_detail': {},
            'risk_exposure': 0,
            'diversification': {},
            'performance_metrics': {}
        }
        
        try:
            # Calculate total portfolio value
            total_value = self.portfolio.state['cash']
            for ticker, position in self.portfolio.state['positions'].items():
                position_value = position['shares'] * position['entry_price']
                total_value += position_value
                portfolio_audit['positions_detail'][ticker] = {
                    'shares': position['shares'],
                    'entry_price': position['entry_price'],
                    'position_value': position_value,
                    'entry_date': position.get('entry_date', 'Unknown')
                }
            
            portfolio_audit['total_value'] = total_value
            portfolio_audit['risk_exposure'] = (total_value - self.portfolio.state['cash']) / total_value * 100
            
            # Diversification check
            if portfolio_audit['positions_count'] > 0:
                max_position = max(portfolio_audit['positions_detail'].values(), key=lambda x: x['position_value'])
                portfolio_audit['diversification'] = {
                    'max_position_pct': max_position['position_value'] / total_value * 100,
                    'avg_position_size': (total_value - self.portfolio.state['cash']) / portfolio_audit['positions_count']
                }
                
                if portfolio_audit['diversification']['max_position_pct'] > 30:
                    self.results['warnings'].append("High concentration in single position")
            
        except Exception as e:
            portfolio_audit['status'] = f'Error: {e}'
            self.results['warnings'].append(f"Portfolio audit error: {e}")
        
        self.results['portfolio_audit'] = portfolio_audit
        
        print(f"  [OK] Cash: ${portfolio_audit['cash']:,.2f}")
        print(f"  [OK] Positions: {portfolio_audit['positions_count']}")
        print(f"  [OK] Total Value: ${portfolio_audit['total_value']:,.2f}")
        print(f"  [OK] Risk Exposure: {portfolio_audit['risk_exposure']:.1f}%")
        print()
    
    def _audit_strategy_system(self):
        """Audit strategy and signal generation"""
        print("[STRATEGY] AUDITING STRATEGY SYSTEM...")
        
        strategy_audit = {
            'test_results': {},
            'indicator_calculation': 'unknown',
            'signal_generation': 'unknown',
            'checklist_compliance': 'unknown'
        }
        
        try:
            # Test strategy on sample data
            sample_ticker = 'AAPL'
            df = self.storage.load_data(sample_ticker)
            
            if df is not None and len(df) > 0:
                analysis = analyze_stock(df, sample_ticker)
                strategy_audit['test_results'] = {
                    'ticker': sample_ticker,
                    'signal': analysis.get('signal', 'UNKNOWN'),
                    'reason': analysis.get('reason', 'No reason'),
                    'indicators_count': len(analysis.get('indicators', {})),
                    'data_points': len(df)
                }
                strategy_audit['indicator_calculation'] = 'working'
                strategy_audit['signal_generation'] = 'working'
            else:
                strategy_audit['test_results'] = {'status': 'No sample data available'}
                self.results['warnings'].append("No sample data for strategy testing")
            
        except Exception as e:
            strategy_audit['test_results'] = {'status': f'Error: {e}'}
            self.results['warnings'].append(f"Strategy audit error: {e}")
        
        self.results['strategy_audit'] = strategy_audit
        
        print(f"  [OK] Strategy Test: {strategy_audit['test_results'].get('status', 'Working')}")
        if 'signal' in strategy_audit['test_results']:
            print(f"  [OK] Sample Signal: {strategy_audit['test_results']['signal']}")
        print()
    
    def _audit_performance(self):
        """Audit system performance metrics"""
        print("[PERFORMANCE] AUDITING PERFORMANCE...")
        
        performance_audit = {
            'data_loading_speed': {},
            'signal_generation_speed': {},
            'portfolio_processing_speed': {},
            'memory_usage': {},
            'disk_usage': {}
        }
        
        try:
            # Test data loading speed
            start_time = time.time()
            sample_tickers = ['AAPL', 'MSFT', 'GOOGL']
            for ticker in sample_tickers:
                self.storage.load_data(ticker)
            data_load_time = time.time() - start_time
            performance_audit['data_loading_speed'] = {
                'sample_size': len(sample_tickers),
                'time_seconds': data_load_time,
                'avg_per_ticker': data_load_time / len(sample_tickers)
            }
            
            # Memory usage (basic)
            performance_audit['memory_usage'] = {
                'status': 'Basic monitoring only (install psutil for detailed metrics)',
                'recommendation': 'Install psutil for advanced memory monitoring'
            }
            
            # Disk usage (basic)
            try:
                import shutil
                disk_usage = shutil.disk_usage(self.storage.local_dir)
                performance_audit['disk_usage'] = {
                    'total': disk_usage.total,
                    'used': disk_usage.used,
                    'free': disk_usage.free,
                    'percent': disk_usage.percent
                }
            except Exception:
                performance_audit['disk_usage'] = {
                    'status': 'Unable to get disk usage',
                    'recommendation': 'Install psutil for detailed disk monitoring'
                }
            
        except Exception as e:
            performance_audit['status'] = f'Error: {e}'
            self.results['warnings'].append(f"Performance audit error: {e}")
        
        self.results['performance_audit'] = performance_audit
        
        print(f"  [OK] Data Loading: {performance_audit.get('data_loading_speed', {}).get('avg_per_ticker', 0):.3f}s per ticker")
        print(f"  [OK] Memory Usage: {performance_audit.get('memory_usage', {}).get('status', 'Unknown')}")
        print(f"  [OK] Disk Usage: {performance_audit.get('disk_usage', {}).get('percent', 0):.1f}%")
        print()
    
    def _audit_security(self):
        """Audit security configurations"""
        print("[SECURITY] AUDITING SECURITY...")
        
        security_audit = {
            'api_keys_present': {},
            'file_permissions': {},
            'sensitive_data_exposure': {},
            'logging_security': {}
        }
        
        try:
            # Check for API keys in environment
            api_keys = {
                'TIINGO_KEY': bool(os.getenv('TIINGO_KEY')),
                'SMTP_PASSWORD': bool(os.getenv('SENDER_PASSWORD'))
            }
            security_audit['api_keys_present'] = api_keys
            
            # Check file permissions (basic check)
            config_files = ['.env', 'src/config.py']
            for file_path in config_files:
                if os.path.exists(file_path):
                    security_audit['file_permissions'][file_path] = os.access(file_path, os.R_OK)
            
            # Check for sensitive data in logs
            log_collector = LogCollector()
            recent_logs = log_collector.get_recent_logs(1)
            sensitive_patterns = ['password', 'key', 'secret', 'token']
            
            sensitive_found = []
            for log in recent_logs:
                log_lower = log.lower()
                for pattern in sensitive_patterns:
                    if pattern in log_lower:
                        sensitive_found.append(log)
                        break
            
            security_audit['sensitive_data_exposure'] = {
                'patterns_found': len(sensitive_found),
                'sample_logs': sensitive_found[:2] if sensitive_found else []
            }
            
            if sensitive_found:
                self.results['warnings'].append("Sensitive data patterns found in logs")
            
        except Exception as e:
            security_audit['status'] = f'Error: {e}'
            self.results['warnings'].append(f"Security audit error: {e}")
        
        self.results['security_audit'] = security_audit
        
        print(f"  [OK] API Keys: {sum(security_audit['api_keys_present'].values())} configured")
        print(f"  [OK] File Permissions: {len(security_audit['file_permissions'])} files checked")
        print(f"  [OK] Sensitive Data: {security_audit['sensitive_data_exposure']['patterns_found']} patterns found")
        print()
    
    def _audit_integrations(self):
        """Audit external integrations"""
        print("[INTEGRATION] AUDITING INTEGRATIONS...")
        
        integration_audit = {
            'data_sources': {},
            'email_system': {},
            'scheduler': {},
            'external_apis': {}
        }
        
        try:
            # Test data sources
            smart_loader = get_smart_data_loader()
            integration_audit['data_sources'] = smart_loader.get_data_source_info()
            
            # Test email system
            email_notifier = EmailNotifier()
            integration_audit['email_system'] = {
                'configured': email_notifier._validate_config(),
                'sender': email_notifier.sender_email,
                'recipient': email_notifier.recipient_email
            }
            
            # Test ticker manager
            ticker_manager = TickerManager()
            integration_audit['external_apis'] = {
                'ticker_manager': 'working',
                'sp500_available': len(ticker_manager.get_sp500_tickers()) > 0
            }
            
        except Exception as e:
            integration_audit['status'] = f'Error: {e}'
            self.results['warnings'].append(f"Integration audit error: {e}")
        
        self.results['integration_audit'] = integration_audit
        
        print(f"  [OK] Data Sources: {integration_audit['data_sources'].get('source', 'Unknown')}")
        print(f"  [OK] Email System: {'Configured' if integration_audit['email_system'].get('configured') else 'Not configured'}")
        print(f"  [OK] Ticker Manager: {integration_audit['external_apis'].get('ticker_manager', 'Unknown')}")
        print()
    
    def _audit_risk_management(self):
        """Audit risk management systems"""
        print("[RISK] AUDITING RISK MANAGEMENT...")
        
        risk_audit = {
            'stop_loss_configured': self.config.config.stop_loss_pct > 0,
            'take_profit_configured': self.config.config.take_profit_pct > 0,
            'position_sizing': self.config.config.position_size,
            'max_positions': self.config.config.max_positions,
            'checklist_enabled': self.config.get_pre_trade_checklist_config(),
            'portfolio_risk': {}
        }
        
        try:
            # Calculate portfolio risk metrics
            total_value = self.results['portfolio_audit'].get('total_value', 0)
            if total_value > 0:
                cash = self.results['portfolio_audit'].get('cash', 0)
                risk_exposure = (total_value - cash) / total_value * 100
                
                risk_audit['portfolio_risk'] = {
                    'risk_exposure_pct': risk_exposure,
                    'cash_buffer_pct': cash / total_value * 100,
                    'position_count': self.results['portfolio_audit'].get('positions_count', 0)
                }
                
                # Risk checks
                if risk_exposure > 80:
                    self.results['warnings'].append("High portfolio risk exposure")
                if cash / total_value < 10:
                    self.results['warnings'].append("Low cash buffer")
            
        except Exception as e:
            risk_audit['status'] = f'Error: {e}'
            self.results['warnings'].append(f"Risk audit error: {e}")
        
        self.results['risk_audit'] = risk_audit
        
        print(f"  [OK] Stop Loss: {'Configured' if risk_audit['stop_loss_configured'] else 'Not configured'}")
        print(f"  [OK] Take Profit: {'Configured' if risk_audit['take_profit_configured'] else 'Not configured'}")
        print(f"  [OK] Max Positions: {risk_audit['max_positions']}")
        print(f"  [OK] Position Size: ${risk_audit.get('position_sizing', 0):,.2f}")
        print()
    
    def _audit_email_system(self):
        """Audit email notification system"""
        print("[EMAIL] AUDITING EMAIL SYSTEM...")
        
        email_audit = {
            'configuration': {},
            'connectivity': 'unknown',
            'formatting': 'unknown',
            'log_attachment': 'unknown'
        }
        
        try:
            email_notifier = EmailNotifier()
            email_audit['configuration'] = {
                'sender_configured': bool(email_notifier.sender_email),
                'recipient_configured': bool(email_notifier.recipient_email),
                'smtp_configured': bool(email_notifier.smtp_server and email_notifier.smtp_port),
                'authentication': bool(email_notifier.sender_email and email_notifier.sender_password)
            }
            
            # Test email formatting (without sending)
            test_results = {
                'scan_results': {'BUY': [], 'SELL': [], 'HOLD': []},
                'summary': 'Test audit email',
                'portfolio_summary': None,
                'executed_trades': None
            }
            
            # Test formatting
            try:
                body = email_notifier._format_comprehensive_email(test_results)
                email_audit['formatting'] = 'working'
                email_audit['body_length'] = len(body)
            except Exception as e:
                email_audit['formatting'] = f'Error: {e}'
            
            # Test log collection
            log_collector = LogCollector()
            try:
                logs = log_collector.format_logs_for_email(hours=1, max_lines=10)
                email_audit['log_attachment'] = 'working'
                email_audit['log_sample'] = len(logs) > 0
            except Exception as e:
                email_audit['log_attachment'] = f'Error: {e}'
            
        except Exception as e:
            email_audit['status'] = f'Error: {e}'
            self.results['warnings'].append(f"Email audit error: {e}")
        
        self.results['email_audit'] = email_audit
        
        print(f"  [OK] Configuration: {len([k for k, v in email_audit['configuration'].items() if v])}/4 items configured")
        print(f"  [OK] Formatting: {email_audit['formatting']}")
        print(f"  [OK] Log Attachment: {email_audit['log_attachment']}")
        print()
    
    def _audit_logs(self):
        """Audit logging system"""
        print("[LOGS] AUDITING LOGS...")
        
        log_audit = {
            'log_file_exists': False,
            'log_file_size': 0,
            'recent_entries': 0,
            'error_count': 0,
            'warning_count': 0,
            'log_patterns': {}
        }
        
        try:
            log_collector = LogCollector()
            log_audit['log_file_exists'] = os.path.exists(log_collector.log_file)
            
            if log_audit['log_file_exists']:
                log_audit['log_file_size'] = os.path.getsize(log_collector.log_file)
                
                # Analyze recent logs
                recent_logs = log_collector.get_recent_logs(24)  # Last 24 hours
                log_audit['recent_entries'] = len(recent_logs)
                
                # Count errors and warnings
                for log in recent_logs:
                    if ' - ERROR - ' in log:
                        log_audit['error_count'] += 1
                    elif ' - WARNING - ' in log:
                        log_audit['warning_count'] += 1
                
                # Check for patterns
                patterns = ['SIGNAL', 'BOUGHT', 'SOLD', 'PORTFOLIO', 'RISK']
                for pattern in patterns:
                    count = sum(1 for log in recent_logs if pattern in log)
                    log_audit['log_patterns'][pattern] = count
                
                # Check for critical issues
                if log_audit['error_count'] > 10:
                    self.results['warnings'].append("High error count in recent logs")
                
                if log_audit['log_file_size'] > 100 * 1024 * 1024:  # > 100MB
                    self.results['warnings'].append("Large log file size")
            
        except Exception as e:
            log_audit['status'] = f'Error: {e}'
            self.results['warnings'].append(f"Log audit error: {e}")
        
        self.results['log_audit'] = log_audit
        
        print(f"  [OK] Log File: {'Found' if log_audit['log_file_exists'] else 'Not found'}")
        print(f"  [OK] File Size: {log_audit['log_file_size'] / (1024*1024):.1f}MB")
        print(f"  [OK] Recent Entries: {log_audit['recent_entries']}")
        print(f"  [OK] Errors: {log_audit['error_count']}")
        print(f"  [OK] Warnings: {log_audit['warning_count']}")
        print()
    
    def _generate_summary(self):
        """Generate audit summary and recommendations"""
        print("[SUMMARY] GENERATING AUDIT SUMMARY...")
        
        # Calculate overall health score
        health_score = 100
        health_score -= len(self.results['critical_issues']) * 20
        health_score -= len(self.results['warnings']) * 5
        health_score = max(0, health_score)
        
        # Generate recommendations
        recommendations = []
        
        if self.results['portfolio_audit'].get('risk_exposure', 0) > 80:
            recommendations.append("Consider reducing position sizes to lower risk exposure")
        
        if self.results['data_audit'].get('ticker_count', 0) < 10:
            recommendations.append("Expand data coverage with more tickers")
        
        if not self.results['email_audit'].get('configuration', {}).get('smtp_configured'):
            recommendations.append("Configure email settings for notifications")
        
        if self.results['performance_audit'].get('memory_usage', {}).get('percent', 0) > 80:
            recommendations.append("Monitor memory usage - consider optimization")
        
        self.results['recommendations'] = recommendations
        self.results['summary'] = {
            'health_score': health_score,
            'critical_issues_count': len(self.results['critical_issues']),
            'warnings_count': len(self.results['warnings']),
            'recommendations_count': len(recommendations),
            'audit_duration': (datetime.now() - self.start_time).total_seconds(),
            'overall_status': 'HEALTHY' if health_score > 80 else 'NEEDS_ATTENTION' if health_score > 60 else 'CRITICAL'
        }
        
        print(f"  [OK] Health Score: {health_score}/100")
        print(f"  [OK] Critical Issues: {len(self.results['critical_issues'])}")
        print(f"  [OK] Warnings: {len(self.results['warnings'])}")
        print(f"  [OK] Recommendations: {len(recommendations)}")
        print(f"  [OK] Status: {self.results['summary']['overall_status']}")
        print()
    
    def _save_audit_results(self):
        """Save audit results to file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            audit_file = f"audit_results_{timestamp}.json"
            
            with open(audit_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            
            print(f"📄 Audit results saved to: {audit_file}")
            
            # Generate text report
            self._generate_text_report(timestamp)
            
        except Exception as e:
            log_error(f"Failed to save audit results: {e}")
    
    def _generate_text_report(self, timestamp):
        """Generate human-readable text report"""
        report_file = f"audit_report_{timestamp}.txt"
        
        try:
            with open(report_file, 'w') as f:
                f.write("VOLATILITYHUNTER FULL DEEP DIVE AUDIT REPORT\n")
                f.write("=" * 60 + "\n")
                f.write(f"Audit Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Duration: {self.results['summary']['audit_duration']:.2f} seconds\n")
                f.write(f"Health Score: {self.results['summary']['health_score']}/100\n")
                f.write(f"Status: {self.results['summary']['overall_status']}\n\n")
                
                f.write("CRITICAL ISSUES:\n")
                f.write("-" * 20 + "\n")
                for issue in self.results['critical_issues']:
                    f.write(f"• {issue}\n")
                f.write("\n")
                
                f.write("WARNINGS:\n")
                f.write("-" * 20 + "\n")
                for warning in self.results['warnings']:
                    f.write(f"• {warning}\n")
                f.write("\n")
                
                f.write("RECOMMENDATIONS:\n")
                f.write("-" * 20 + "\n")
                for rec in self.results['recommendations']:
                    f.write(f"• {rec}\n")
                f.write("\n")
                
                f.write("DETAILED RESULTS:\n")
                f.write("-" * 20 + "\n")
                f.write(json.dumps(self.results, indent=2, default=str))
            
            print(f"📄 Text report saved to: {report_file}")
            
        except Exception as e:
            log_error(f"Failed to generate text report: {e}")
    
    def print_summary(self):
        """Print audit summary to console"""
        print("\n" + "=" * 60)
        print("AUDIT SUMMARY")
        print("=" * 60)
        
        summary = self.results.get('summary', {})
        print(f"Health Score: {summary.get('health_score', 'N/A')}")
        print(f"Status: {summary.get('overall_status', 'UNKNOWN')}")
        print(f"Critical Issues: {len(self.results['critical_issues'])}")
        print(f"Warnings: {len(self.results['warnings'])}")
        print(f"Recommendations: {len(self.results['recommendations'])}")
        print(f"Duration: {summary.get('audit_duration', 0):.2f} seconds")
        
        if self.results['critical_issues']:
            print("\nCRITICAL ISSUES:")
            for issue in self.results['critical_issues']:
                print(f"  [ERROR] {issue}")
        
        if self.results['warnings']:
            print("\nWARNINGS:")
            for warning in self.results['warnings'][:5]:  # Show first 5
                print(f"  [WARN] {warning}")
            if len(self.results['warnings']) > 5:
                print(f"  ... and {len(self.results['warnings']) - 5} more")
        
        if self.results['recommendations']:
            print("\nRECOMMENDATIONS:")
            for rec in self.results['recommendations'][:5]:  # Show first 5
                print(f"  [INFO] {rec}")
            if len(self.results['recommendations']) > 5:
                print(f"  ... and {len(self.results['recommendations']) - 5} more")
        
        print("\n" + "=" * 60)

def main():
    """Main audit execution"""
    auditor = VolatilityHunterAuditor()
    results = auditor.run_full_audit()
    auditor.print_summary()
    
    return results

if __name__ == "__main__":
    main()
