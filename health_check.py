"""
VolatilityHunter Health Check
Morning Guard - System Health Monitoring
"""

import os
import json
import requests
from datetime import datetime
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
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                return {}
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
        """Check Python environment and key packages"""
        try:
            import sys
            import pandas
            import numpy
            import requests
            
            python_version = sys.version_info
            if python_version < (3, 11):
                return False, f"Python {python_version.major}.{python_version.minor} - upgrade to 3.11+ recommended"
            
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
            ('Internet Connectivity', self.check_internet_connectivity),
            ('Tiingo API', self.check_tiingo_api),
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
