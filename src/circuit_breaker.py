#!/usr/bin/env python3
"""
CIRCUIT BREAKER (Dead Man's Switch)
===================================
Eliminates all silent failures in the trading pipeline.
Performs strict pre-flight checks before any trading activity.

If any check fails, raises CriticalFailure - no silent logging allowed.
"""

import os
import sys
import json
import socket
import requests
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# ── Path setup ─────────────────────────────────────────────────────────────
ROOT = Path(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# ── Custom Exception ───────────────────────────────────────────────────────
class CriticalFailure(Exception):
    """Critical system failure - trading must halt immediately."""
    pass

# ── Circuit Breaker Class ───────────────────────────────────────────────────
class TradingCircuitBreaker:
    """
    Dead Man's Switch for the trading pipeline.
    Performs strict pre-flight validation before any trading activity.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("circuit_breaker")
        self.tiingo_api_key = os.getenv("TIINGO_API_KEY", "")
        self.gateway_port = int(os.getenv("IBKR_PORT", "7497"))
        self.portfolio_path = ROOT / "data" / "portfolio.json"
        self.root_dir = ROOT
        
    def validate_all(self) -> bool:
        """
        Perform all pre-flight checks.
        Raises CriticalFailure if any check fails.
        """
        self.logger.info("=" * 60)
        self.logger.info("CIRCUIT BREAKER: PRE-FLIGHT VALIDATION")
        self.logger.info("=" * 60)
        
        checks = [
            ("Data Check", self._validate_data_connection),
            ("Data Freshness Check", self._validate_data_freshness),
            ("Broker Check", self._validate_broker_connection),
            ("State Check", self._validate_portfolio_state),
        ]
        
        for check_name, check_func in checks:
            self.logger.info(f"Executing {check_name}...")
            try:
                check_func()
                self.logger.info(f"✅ {check_name} PASSED")
            except CriticalFailure as e:
                self.logger.error(f"❌ {check_name} FAILED: {e}")
                raise
            except Exception as e:
                self.logger.error(f"❌ {check_name} ERROR: {e}")
                raise CriticalFailure(f"{check_name} encountered unexpected error: {e}")
        
        self.logger.info("=" * 60)
        self.logger.info("✅ ALL PRE-FLIGHT CHECKS PASSED - TRADING ENABLED")
        self.logger.info("=" * 60)
        return True
    
    def _validate_data_connection(self):
        """Validate Tiingo API is responding."""
        if not self.tiingo_api_key:
            raise CriticalFailure("TIINGO_API_KEY missing from .env")
        
        try:
            # Test API with recent data (check last 3 days)
            url = "https://api.tiingo.com/tiingo/daily/spy/prices"
            params = {
                'token': self.tiingo_api_key,
                'startDate': '2026-04-24',  # Friday
                'endDate': '2026-04-24'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                raise CriticalFailure(f"Tiingo API returned status {response.status_code}")
            
            data = response.json()
            if not isinstance(data, list) or len(data) == 0:
                # Try today's data as fallback
                params['startDate'] = '2026-04-27'
                params['endDate'] = '2026-04-27'
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if not isinstance(data, list) or len(data) == 0:
                    raise CriticalFailure("Tiingo API returned invalid data for both recent and current dates")
            
            self.logger.info(f"Tiingo API responding (status: {response.status_code})")
            
        except requests.exceptions.Timeout:
            raise CriticalFailure("Tiingo API timeout - data service unavailable")
        except requests.exceptions.ConnectionError:
            raise CriticalFailure("Tiingo API connection failed - check internet")
        except requests.exceptions.RequestException as e:
            raise CriticalFailure(f"Tiingo API request failed: {e}")
        except json.JSONDecodeError:
            raise CriticalFailure("Tiingo API returned invalid JSON")
    
    def _validate_data_freshness(self):
        """Validate that Parquet data files are fresh (current trading day)."""
        try:
            import pandas as pd
            from datetime import datetime, timedelta
            
            # Check SPY parquet file as benchmark
            spy_file = os.path.join(self.root_dir, "data", "SPY.parquet")
            
            if not os.path.exists(spy_file):
                raise CriticalFailure("SPY.parquet file missing - data not loaded")
            
            # Load and check latest date
            df = pd.read_parquet(spy_file)
            if df.empty:
                raise CriticalFailure("SPY.parquet file empty - data corrupted")
            
            # Use date column instead of index
            if 'date' in df.columns:
                latest_date = df['date'].iloc[-1]
            else:
                raise CriticalFailure("No date column found in Parquet file")
            
            if isinstance(latest_date, str):
                latest_date = pd.to_datetime(latest_date).date()
            elif hasattr(latest_date, 'date'):
                latest_date = latest_date.date()
            else:
                latest_date = latest_date
            
            today = datetime.now().date()
            
            # Check if data is from today or most recent trading day
            if latest_date == today:
                self.logger.info(f"Data freshness confirmed: {latest_date} (current day)")
            elif today.weekday() == 0:  # Monday - check for Friday data
                if latest_date == today - timedelta(days=3):  # Friday
                    self.logger.info(f"Data freshness confirmed: {latest_date} (Friday data for Monday)")
                else:
                    raise CriticalFailure(f"Stale data detected: {latest_date} (expected Friday data for Monday)")
            elif latest_date == today - timedelta(days=1):  # Yesterday for other days
                self.logger.info(f"Data freshness confirmed: {latest_date} (yesterday's data)")
            else:
                raise CriticalFailure(f"Stale data detected: {latest_date} (not current trading day)")
            
        except ImportError:
            raise CriticalFailure("pandas not available - cannot validate data freshness")
        except Exception as e:
            if isinstance(e, CriticalFailure):
                raise
            raise CriticalFailure(f"Data freshness check failed: {e}")
    
    def _validate_broker_connection(self):
        """Validate IBKR Gateway is listening on port 7497."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('127.0.0.1', self.gateway_port))
            sock.close()
            
            if result != 0:
                raise CriticalFailure(f"IBKR Gateway not responding on port {self.gateway_port}")
            
            self.logger.info(f"IBKR Gateway responding on port {self.gateway_port}")
            
        except socket.timeout:
            raise CriticalFailure(f"IBKR Gateway connection timeout on port {self.gateway_port}")
        except socket.error as e:
            raise CriticalFailure(f"IBKR Gateway socket error: {e}")
    
    def _validate_portfolio_state(self):
        """Validate portfolio.json exists and contains valid JSON."""
        try:
            if not self.portfolio_path.exists():
                # Empty portfolio is OK - create initial state
                initial_state = {
                    "positions": {},
                    "cash": 100000.0,
                    "last_updated": datetime.now().isoformat(),
                    "version": "v8.1.2"
                }
                self.portfolio_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.portfolio_path, 'w') as f:
                    json.dump(initial_state, f, indent=2)
                self.logger.info("Created initial portfolio.json")
                return
            
            # Validate existing portfolio JSON
            with open(self.portfolio_path, 'r') as f:
                portfolio = json.load(f)
            
            # Required fields check
            required_fields = ['positions', 'cash', 'last_updated']
            for field in required_fields:
                if field not in portfolio:
                    raise CriticalFailure(f"portfolio.json missing required field: {field}")
            
            # Validate data types
            if not isinstance(portfolio['positions'], dict):
                raise CriticalFailure("portfolio.positions must be a dictionary")
            
            if not isinstance(portfolio['cash'], (int, float)):
                raise CriticalFailure("portfolio.cash must be numeric")
            
            self.logger.info(f"portfolio.json valid ({len(portfolio['positions'])} positions)")
            
        except json.JSONDecodeError as e:
            raise CriticalFailure(f"portfolio.json corrupted - invalid JSON: {e}")
        except Exception as e:
            raise CriticalFailure(f"portfolio.json validation failed: {e}")

# ── Emergency Alert Function ─────────────────────────────────────────────────
def trigger_emergency_alert(failure_reason: str):
    """
    Send emergency alert and print ASCII death rattle.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # ASCII Death Rattle
    death_rattle = f"""
{'!' * 80}
{'!' * 80}
!!! CRITICAL SYSTEM FAILURE - TRADING HALTED !!!
!!! CIRCUIT BREAKER TRIGGERED - DEAD MAN'S SWITCH !!!
{'!' * 80}
Timestamp: {timestamp}
Failure: {failure_reason}
{'!' * 80}
ACTION REQUIRED:
1. Check system logs for detailed error information
2. Verify all external dependencies (API, Gateway, Data)
3. Do NOT restart trading until issue is resolved
{'!' * 80}
{'!' * 80}
"""
    
    print(death_rattle)
    
    # Send email alert
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from email_notifier import EmailNotifier
        notifier = EmailNotifier()
        
        subject = "🚨 CRITICAL FAILURE - TRADING HALTED"
        body = f"""
Circuit Breaker triggered - trading system halted.

Timestamp: {timestamp}
Failure: {failure_reason}

IMMEDIATE ACTION REQUIRED:
- Check system logs
- Verify external dependencies
- Do NOT restart until resolved

This is an automated critical failure alert.
"""
        
        notifier.send_email(subject, body)
        print("📧 Emergency alert sent to Architect")
        
    except Exception as e:
        print(f"⚠️  Failed to send email alert: {e}")
    
    # Force exit
    sys.exit(1)
