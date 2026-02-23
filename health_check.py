"""
VolatilityHunter Health Check
Morning Guard - System Health Monitoring
"""

import os
import json
import requests
import socket
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple
from src.notifications import log_info, log_warning, log_error
from src.email_notifier import EmailNotifier
from src.config import TIINGO_KEY, TIINGO_BASE_URL
from src.system_monitor import SystemMonitor

class HealthChecker:
    """System health monitoring for VolatilityHunter"""
    
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self._load_config()
        self.system_monitor = SystemMonitor()
        self.email_notifier = EmailNotifier()
        
        # Health check results
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'status': 'GREEN',  # Default to GREEN, change to RED if critical failures
            'checks': {},
            'system_metrics': {},
            'summary': []
        }
    
    def _load_config(self) -> Dict:
        """Load configuration from config.json, config.ini, or .env"""
        try:
            config = {}
            
            # Try config.json first
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    config.update(json.load(f))
            
            # Try config.ini
            elif os.path.exists('config.ini'):
                import configparser
                ini_config = configparser.ConfigParser()
                ini_config.read('config.ini')
                if 'DEFAULT' in ini_config:
                    config.update(dict(ini_config['DEFAULT']))
            
            # Try .env file
            if os.path.exists('.env'):
                from dotenv import load_dotenv
                load_dotenv()
                
                # Override with .env values
                env_mappings = {
                    'TRADING_MODE': os.getenv('TRADING_MODE'),
                    'DATA_SOURCE': os.getenv('DATA_SOURCE'),
                    'IBKR_HOST': os.getenv('IBKR_HOST', '127.0.0.1'),
                    'IBKR_PORT': int(os.getenv('IBKR_PORT', '7497')),
                    'BROKERAGE_TYPE': os.getenv('BROKERAGE_TYPE', 'ibkr')
                }
                
                for key, value in env_mappings.items():
                    if value is not None:
                        config[key] = value
            
            return config
            
        except Exception as e:
            log_error(f"Error loading config: {e}")
            return {}
    
    def check_internet_connectivity(self) -> Tuple[bool, str]:
        """Check internet connectivity"""
        try:
            response = requests.get('https://httpbin.org/ip', timeout=10)
            if response.status_code == 200:
                ip_info = response.json()
                return True, f"Connected - IP: {ip_info.get('origin', 'Unknown')}"
            else:
                return False, f"HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "Connection timeout"
        except requests.exceptions.ConnectionError:
            return False, "Connection error"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def check_tiingo_api(self) -> Tuple[bool, str]:
        """Check Tiingo API connectivity and key validity"""
        if not TIINGO_KEY:
            return False, "Tiingo API key not configured"
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Token {TIINGO_KEY}'
            }
            
            # Test with a simple API call using daily prices (more reliable)
            url = "https://api.tiingo.com/tiingo/daily/AAPL/prices"
            params = {'startDate': '2026-01-01', 'endDate': '2026-01-02'}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return True, f"API key valid - Sample data: AAPL price ${data[0].get('close', 'N/A')}"
                else:
                    return False, "API returned empty data"
            elif response.status_code == 401:
                return False, "Invalid API key"
            elif response.status_code == 403:
                return False, "API access forbidden"
            else:
                return False, f"API error: HTTP {response.status_code}"
        
        except requests.exceptions.Timeout:
            return False, "API connection timeout"
        except requests.exceptions.ConnectionError:
            return False, "API connection error"
        except Exception as e:
            return False, f"API check failed: {str(e)}"
    
    def check_disk_permissions(self) -> Tuple[bool, str]:
        """Check disk write permissions"""
        try:
            # Test writing to data directory
            test_file = 'data/health_check_test.tmp'
            os.makedirs('data', exist_ok=True)
            
            with open(test_file, 'w') as f:
                f.write(f"Health check test at {datetime.now()}")
            
            # Test reading back
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Clean up
            os.remove(test_file)
            
            return True, "Read/write permissions OK"
        
        except PermissionError:
            return False, "Permission denied - check directory permissions"
        except OSError as e:
            return False, f"Disk I/O error: {str(e)}"
        except Exception as e:
            return False, f"Disk check failed: {str(e)}"
    
    def check_market_hours(self) -> Tuple[bool, str]:
        """Check if current time is within IST trading window (17:30 - 23:00)"""
        try:
            # Get current time in IST
            utc_now = datetime.now(timezone.utc)
            ist_offset = timedelta(hours=3, minutes=30)  # IST = UTC+3:30
            ist_now = utc_now + ist_offset
            
            current_hour = ist_now.hour
            current_minute = ist_now.minute
            current_time = current_hour * 100 + current_minute
            
            # SweetSpot trading window: 17:30 to 23:00 IST (1-hour stabilization after market open)
            window_start = 1730  # 17:30 IST
            window_end = 2300    # 23:00 IST
            
            if window_start <= current_time <= window_end:
                return True, f"SweetSpot window OK - Current time: {ist_now.strftime('%H:%M')} IST"
            else:
                return False, f"Outside SweetSpot window - Current time: {ist_now.strftime('%H:%M')} IST (Window: 17:30-23:00 IST)"
                
        except Exception as e:
            return False, f"Market hours check failed: {str(e)}"
    
    def check_ibkr_connectivity(self) -> Tuple[bool, str]:
        """Check IBKR Gateway/TWS connectivity - MANDATORY in all modes"""
        try:
            # Get IBKR config
            host = self.config.get('IBKR_HOST', '127.0.0.1')
            
            # Determine port based on trading mode
            trading_mode = self.config.get('TRADING_MODE', '').upper()
            if trading_mode == 'LIVE':
                port = self.config.get('IBKR_PORT', 7496)  # Live trading port
            else:
                port = self.config.get('IBKR_PORT', 7497)  # Paper trading port
            
            # Test 1: Basic socket connectivity
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 second timeout
            
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result != 0:
                return False, f"IBKR Gateway/TWS NOT reachable at {host}:{port} ({trading_mode}) - Start TWS/Gateway!"
            
            # Test 2: Try to instantiate IBKR interface
            try:
                from src.brokerage_interface import get_brokerage_interface
                ibkr_interface = get_brokerage_interface({
                    'BROKERAGE_TYPE': 'ibkr',
                    'IBKR_HOST': host,
                    'IBKR_PORT': port,
                    'IBKR_CLIENT_ID': 999
                })
                
                # Test 3: Try to connect
                if ibkr_interface.connect():
                    # Test 4: Try a real trade (buy and immediate sell)
                    try:
                        import time
                        
                        # Get account info first
                        account = ibkr_interface.get_account_info()
                        cash = account.get('cash', 0)
                        
                        if cash >= 1000:  # Only test if we have enough cash
                            # Buy 1 share of a cheap stock (e.g., SIRI)
                            symbol = 'SIRI'  # Usually cheap stock
                            shares = 1
                            
                            # Place buy order
                            buy_result = ibkr_interface.place_market_order(symbol, shares, 'buy')
                            
                            if buy_result.get('success', False):
                                buy_order_id = buy_result.get('order_id')
                                
                                # Wait a moment for order to process
                                time.sleep(2)
                                
                                # Place sell order for the same stock
                                sell_result = ibkr_interface.place_market_order(symbol, shares, 'sell')
                                
                                if sell_result.get('success', False):
                                    sell_order_id = sell_result.get('order_id')
                                    
                                    ibkr_interface.disconnect()
                                    return True, f"IBKR Interface fully functional with trade test at {host}:{port} ({trading_mode}) - Buy ID: {buy_order_id}, Sell ID: {sell_order_id}"
                                else:
                                    ibkr_interface.disconnect()
                                    return False, f"IBKR buy order succeeded but sell failed: {sell_result.get('reason', 'Unknown')}"
                            else:
                                ibkr_interface.disconnect()
                                return False, f"IBKR buy order failed: {buy_result.get('reason', 'Unknown')}"
                        else:
                            ibkr_interface.disconnect()
                            return True, f"IBKR Interface connected but insufficient cash (${cash:,.2f}) for trade test at {host}:{port} ({trading_mode})"
                            
                    except Exception as trade_error:
                        ibkr_interface.disconnect()
                        return False, f"IBKR Interface connected but trade test failed: {trade_error}"
                else:
                    return False, f"IBKR Interface connection failed at {host}:{port} ({trading_mode})"
                    
            except Exception as e:
                return False, f"IBKR Interface instantiation failed: {str(e)}"
                
        except Exception as e:
            return False, f"IBKR connectivity check failed: {str(e)}"
    
    def check_config_validity(self) -> Tuple[bool, str]:
        """Check configuration file validity"""
        try:
            required_fields = ['TRADING_MODE', 'DATA_SOURCE']
            missing_fields = []
            
            for field in required_fields:
                if field not in self.config:
                    missing_fields.append(field)
            
            if missing_fields:
                return False, f"Missing config fields: {', '.join(missing_fields)}"
            
            # Check trading mode validity
            trading_mode = self.config.get('TRADING_MODE', '').upper()
            if trading_mode not in ['PAPER', 'LIVE']:
                return False, f"Invalid TRADING_MODE: {trading_mode}"
            
            # Check data source validity
            data_source = self.config.get('DATA_SOURCE', '').upper()
            if data_source not in ['TIINGO', 'YFINANCE']:
                return False, f"Invalid DATA_SOURCE: {data_source}"
            
            return True, f"Config valid - Mode: {trading_mode}, Source: {data_source}"
        
        except Exception as e:
            return False, f"Config validation failed: {str(e)}"
    
    def check_log_directory(self) -> Tuple[bool, str]:
        """Check log directory and permissions"""
        try:
            log_dir = 'logs'
            os.makedirs(log_dir, exist_ok=True)
            
            # Test log file creation
            today = datetime.now().strftime('%Y-%m-%d')
            test_log = f"{log_dir}/VH_{today}.log"
            
            with open(test_log, 'a') as f:
                f.write(f"\n[HEALTH_CHECK] Test log entry at {datetime.now()}\n")
            
            return True, f"Log directory OK: {log_dir}"
        
        except Exception as e:
            return False, f"Log directory check failed: {str(e)}"
    
    def check_python_environment(self) -> Tuple[bool, str]:
        """Check Python environment and key packages - WARNING ONLY"""
        try:
            import sys
            import pandas
            import numpy
            import requests
            
            python_version = sys.version_info
            
            # Python 3.10+ is stable for v8.0 - always PASS, just warn if older
            if python_version < (3, 10):
                return True, f"Python {python_version.major}.{python_version.minor} - OK (WARNING: upgrade to 3.10+ recommended)"
            elif python_version == (3, 10):
                return True, f"Python {python_version.major}.{python_version.minor}.{python_version.micro} - OK (v8.0 stable)"
            else:
                return True, f"Python {python_version.major}.{python_version.minor}.{python_version.micro} - OK"
        
        except ImportError as e:
            return False, f"Missing required package: {str(e)}"
        except Exception as e:
            return False, f"Python environment check failed: {str(e)}"
    
    def get_system_metrics(self) -> Dict:
        """Get system resource metrics"""
        try:
            return self.system_monitor.get_resource_usage()
        except Exception as e:
            log_error(f"Error getting system metrics: {e}")
            return {'cpu': 'N/A', 'memory': 'N/A', 'disk': 'N/A'}
    
    def run_all_checks(self) -> Dict:
        """Run all health checks"""
        log_info("Starting VolatilityHunter health check...")
        
        # Define all checks to run
        checks = [
            ('Market Hours', self.check_market_hours),
            ('Internet Connectivity', self.check_internet_connectivity),
            ('Tiingo API', self.check_tiingo_api),
            ('IBKR Connectivity', self.check_ibkr_connectivity),
            ('Disk Permissions', self.check_disk_permissions),
            ('Config Validity', self.check_config_validity),
            ('Log Directory', self.check_log_directory),
            ('Python Environment', self.check_python_environment)
        ]
        
        # Run each check
        for check_name, check_func in checks:
            try:
                success, message = check_func()
                self.results['checks'][check_name] = {
                    'status': 'PASS' if success else 'FAIL',
                    'message': message
                }
                
                if not success:
                    self.results['status'] = 'RED'
                    log_error(f"Health check FAILED: {check_name} - {message}")
                else:
                    log_info(f"Health check PASSED: {check_name} - {message}")
                    
            except Exception as e:
                self.results['checks'][check_name] = {
                    'status': 'ERROR',
                    'message': f"Check failed: {str(e)}"
                }
                self.results['status'] = 'RED'
                log_error(f"Health check ERROR: {check_name} - {str(e)}")
        
        # Get system metrics
        self.results['system_metrics'] = self.get_system_metrics()
        
        # Generate summary
        passed_checks = sum(1 for check in self.results['checks'].values() if check['status'] == 'PASS')
        total_checks = len(self.results['checks'])
        
        self.results['summary'] = [
            f"System Status: {self.results['status']}",
            f"Checks Passed: {passed_checks}/{total_checks}",
            f"Timestamp: {self.results['timestamp']}"
        ]
        
        log_info(f"Health check complete: {self.results['status']} ({passed_checks}/{total_checks} checks passed)")
        return self.results
    
    def send_health_report(self) -> bool:
        """Send health report via email"""
        try:
            # Generate email content
            subject = f"VolatilityHunter Health Report: {self.results['status']}"
            
            # Build HTML body
            html_body = f"""
            <html>
            <body>
                <h2>🔍 VolatilityHunter Health Report</h2>
                <p><b>Status:</b> <span style="color: {'green' if self.results['status'] == 'GREEN' else 'red'}">{self.results['status']}</span></p>
                <p><b>Timestamp:</b> {self.results['timestamp']}</p>
                
                <h3>📊 System Metrics</h3>
                <ul>
                    <li>CPU: {self.results['system_metrics'].get('cpu', 'N/A')}</li>
                    <li>Memory: {self.results['system_metrics'].get('memory', 'N/A')}</li>
                    <li>Disk: {self.results['system_metrics'].get('disk', 'N/A')}</li>
                </ul>
                
                <h3>🔧 Health Checks</h3>
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <th style="padding: 8px; background-color: #f0f0f0;">Check</th>
                        <th style="padding: 8px; background-color: #f0f0f0;">Status</th>
                        <th style="padding: 8px; background-color: #f0f0f0;">Details</th>
                    </tr>
            """
            
            for check_name, check_result in self.results['checks'].items():
                status_color = 'green' if check_result['status'] == 'PASS' else 'red'
                html_body += f"""
                    <tr>
                        <td style="padding: 8px;">{check_name}</td>
                        <td style="padding: 8px; color: {status_color}; font-weight: bold;">{check_result['status']}</td>
                        <td style="padding: 8px;">{check_result['message']}</td>
                    </tr>
                """
            
            html_body += """
                </table>
                
                <h3>📝 Summary</h3>
                <ul>
            """
            
            for summary_item in self.results['summary']:
                html_body += f"<li>{summary_item}</li>"
            
            html_body += """
                </ul>
                
                <p><i>This health check runs automatically to ensure system readiness for trading.</i></p>
            </body>
            </html>
            """
            
            # Send email with log attachment
            today = datetime.now().strftime('%Y-%m-%d')
            log_file = f"logs/VH_{today}.log"
            
            success = self.email_notifier.send_email(
                subject=subject,
                body=html_body,
                attachment_path=log_file if os.path.exists(log_file) else None
            )
            
            if success:
                log_info("Health report email sent successfully")
            else:
                log_error("Failed to send health report email")
            
            return success
            
        except Exception as e:
            log_error(f"Error sending health report: {e}")
            return False


def main():
    """Main health check execution"""
    print("="*60)
    print("VolatilityHunter Health Check")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Initialize health checker
        checker = HealthChecker()
        
        # Run all checks
        results = checker.run_all_checks()
        
        # Display results
        print(f"\n[STATUS] System Status: {results['status']}")
        print(f"[SUMMARY] {results['summary'][1]}")
        
        print("\n[DETAILED RESULTS]")
        for check_name, check_result in results['checks'].items():
            status_symbol = "✅" if check_result['status'] == 'PASS' else "❌"
            print(f"  {status_symbol} {check_name}: {check_result['message']}")
        
        print(f"\n[SYSTEM METRICS]")
        metrics = results['system_metrics']
        print(f"  CPU: {metrics.get('cpu', 'N/A')}")
        print(f"  Memory: {metrics.get('memory', 'N/A')}")
        print(f"  Disk: {metrics.get('disk', 'N/A')}")
        
        # Send email report
        print("\n[EMAIL] Sending health report...")
        email_sent = checker.send_health_report()
        print(f"[EMAIL] {'Sent successfully' if email_sent else 'Failed to send'}")
        
        print("="*60)
        
        # Exit with appropriate code
        exit_code = 0 if results['status'] == 'GREEN' else 1
        exit(exit_code)
        
    except Exception as e:
        print(f"\n[ERROR] Health check failed: {e}")
        print("="*60)
        exit(1)


if __name__ == '__main__':
    main()
