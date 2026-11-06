#!/usr/bin/env python3
"""
Lightweight read-only analysis script for last week's performance.

Constraints:
- Does NOT import or touch src/strategy_engine.py
- Reads directly from data/portfolio.json and logs/
- Completely non-interactive
- Outputs formatted markdown tables to console

Author: VolatilityHunter Analysis Module
Version: 1.0
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import re

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
LOGS_DIR = ROOT / "logs"

def parse_date_from_filename(filename: str) -> datetime:
    """Extract date from manifest filename like run_manifest_2026-05-12.json"""
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d')
    return None

def get_last_week_manifests() -> List[Tuple[datetime, Path]]:
    """Find all run manifests from the past 7 days"""
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    
    manifests = []
    for manifest_file in DATA_DIR.glob("run_manifest_*.json"):
        date = parse_date_from_filename(manifest_file.name)
        if date and date >= week_ago:
            manifests.append((date, manifest_file))
    
    return sorted(manifests, key=lambda x: x[0])

def parse_manifest(manifest_path: Path) -> Dict:
    """Parse a run manifest file"""
    try:
        with open(manifest_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

def parse_health_check_log(date: datetime) -> Dict:
    """Parse health check results from logs for a specific date"""
    log_file = LOGS_DIR / "functional_health_check.log"
    if not log_file.exists():
        return {"status": "LOG_NOT_FOUND"}
    
    date_str = date.strftime('%Y-%m-%d')
    results = {
        "pass_count": 0,
        "warn_count": 0,
        "fail_count": 0,
        "status": "UNKNOWN"
    }
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            in_target_date = False
            for line in f:
                if date_str in line:
                    in_target_date = True
                
                if in_target_date:
                    if "RESULTS:" in line:
                        match = re.search(r'(\d+)\s+PASS\s*\|\s*(\d+)\s+WARN\s*\|\s*(\d+)\s+FAIL', line)
                        if match:
                            results["pass_count"] = int(match.group(1))
                            results["warn_count"] = int(match.group(2))
                            results["fail_count"] = int(match.group(3))
                    
                    if "HEALTH CHECK PASSED" in line:
                        results["status"] = "PASSED"
                        break
                    elif "HEALTH CHECK FAILED" in line:
                        results["status"] = "FAILED"
                        break
    except Exception as e:
        results["error"] = str(e)
    
    return results

def parse_tiingo_errors(date: datetime) -> List[str]:
    """Parse Tiingo batch fetch errors from trading logs"""
    log_file = LOGS_DIR / f"trading_{date.strftime('%Y-%m-%d')}.log"
    errors = []
    
    if not log_file.exists():
        return errors
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if "ERROR" in line and ("Tiingo" in line or "tiingo" in line):
                    errors.append(line.strip())
                elif "WARN" in line and ("Tiingo" in line or "tiingo" in line):
                    errors.append(line.strip())
    except Exception as e:
        errors.append(f"Error reading log: {e}")
    
    return errors

def load_portfolio() -> Dict:
    """Load current portfolio state from portfolio.json"""
    portfolio_file = DATA_DIR / "portfolio.json"
    
    try:
        with open(portfolio_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

def calculate_realized_pnl_from_history(portfolio: Dict) -> float:
    """Calculate realized P&L from trade history in the past 7 days"""
    if "trade_history" not in portfolio:
        return 0.0
    
    week_ago = datetime.now() - timedelta(days=7)
    realized_pnl = 0.0
    
    for trade in portfolio["trade_history"]:
        if trade.get("type") == "SELL":
            try:
                trade_date = datetime.fromisoformat(trade["timestamp"])
                if trade_date >= week_ago:
                    realized_pnl += trade.get("pnl", 0.0)
            except:
                pass
    
    return realized_pnl

def format_currency(value: float) -> str:
    """Format currency with commas and 2 decimal places"""
    return f"${value:,.2f}"

def format_percentage(value: float) -> str:
    """Format percentage with 2 decimal places"""
    return f"{value:.2f}%"

def main():
    print("=" * 80)
    print("[REPORT] LAST WEEK PERFORMANCE ANALYSIS")
    print("=" * 80)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Period: Last 7 days")
    print()
    
    # Get manifests from last week
    manifests = get_last_week_manifests()
    
    if not manifests:
        print("[WARN]  No run manifests found in the past 7 days")
        return
    
    print(f"[FILES] Found {len(manifests)} run(s) in the past 7 days")
    print()
    
    # Parse each manifest
    print("## Daily Run Summary")
    print()
    print("| Date       | Status         | Gateway | Data Update | Health Check | Trading Loop | Duration |")
    print("|------------|----------------|---------|-------------|--------------|--------------|----------|")
    
    run_summary = []
    for date, manifest_path in manifests:
        manifest = parse_manifest(manifest_path)
        
        if "error" in manifest:
            print(f"| {date.strftime('%Y-%m-%d')} | ERROR | - | - | - | - | - |")
            continue
        
        status = manifest.get("status", "UNKNOWN")
        gateway_status = manifest.get("gateway", {}).get("status", "unknown")
        
        # Extract step statuses
        steps = manifest.get("steps", {})
        data_update_exit = steps.get("data_update", {}).get("exit_code", "N/A")
        health_check_exit = steps.get("health_check", {}).get("exit_code", "N/A")
        trading_loop_exit = steps.get("trading_loop", {}).get("exit_code", "N/A")
        
        # Calculate total duration
        started = manifest.get("started_at", "")
        completed = manifest.get("completed_at", "")
        duration = "N/A"
        if started and completed:
            try:
                start_dt = datetime.fromisoformat(started)
                end_dt = datetime.fromisoformat(completed)
                duration_sec = (end_dt - start_dt).total_seconds()
                duration = f"{int(duration_sec // 60)}m {int(duration_sec % 60)}s"
            except:
                pass
        
        # Format status with emoji
        status_emoji = "[OK]" if status == "SUCCESS" else "[FAIL]"
        gateway_emoji = "[OK]" if gateway_status == "online" else "[FAIL]"
        data_emoji = "[OK]" if data_update_exit == 0 else "[FAIL]" if data_update_exit != "N/A" else "-"
        health_emoji = "[OK]" if health_check_exit == 0 else "[FAIL]" if health_check_exit != "N/A" else "-"
        trading_emoji = "[OK]" if trading_loop_exit == 0 else "[FAIL]" if trading_loop_exit != "N/A" else "-"
        
        print(f"| {date.strftime('%Y-%m-%d')} | {status_emoji} {status:12s} | {gateway_emoji:7s} | {data_emoji:11s} | {health_emoji:12s} | {trading_emoji:12s} | {duration:8s} |")
        
        run_summary.append({
            "date": date,
            "status": status,
            "gateway": gateway_status,
            "manifest": manifest
        })
    
    print()
    
    # Health Check Details
    print("## Health Check Results")
    print()
    print("| Date       | Status | PASS | WARN | FAIL |")
    print("|------------|--------|------|------|------|")
    
    for date, _ in manifests:
        health_results = parse_health_check_log(date)
        status = health_results.get("status", "UNKNOWN")
        pass_count = health_results.get("pass_count", 0)
        warn_count = health_results.get("warn_count", 0)
        fail_count = health_results.get("fail_count", 0)
        
        status_emoji = "[OK]" if status == "PASSED" else "[FAIL]" if status == "FAILED" else "[WARN]"
        print(f"| {date.strftime('%Y-%m-%d')} | {status_emoji} {status:6s} | {pass_count:4d} | {warn_count:4d} | {fail_count:4d} |")
    
    print()
    
    # Tiingo Errors
    print("## Tiingo API Issues")
    print()
    
    tiingo_issues_found = False
    for date, _ in manifests:
        errors = parse_tiingo_errors(date)
        if errors:
            tiingo_issues_found = True
            print(f"### {date.strftime('%Y-%m-%d')}")
            for error in errors[:5]:  # Limit to 5 errors per day
                print(f"- {error}")
            if len(errors) > 5:
                print(f"- ... and {len(errors) - 5} more errors")
            print()
    
    if not tiingo_issues_found:
        print("[OK] No Tiingo API errors detected in the past 7 days")
        print()
    
    # Portfolio Analysis
    print("## Current Portfolio State")
    print()
    
    portfolio = load_portfolio()
    
    if "error" in portfolio:
        print(f"[FAIL] Error loading portfolio: {portfolio['error']}")
        return
    
    cash = portfolio.get("cash", 0.0)
    positions = portfolio.get("positions", {})
    total_value = portfolio.get("total_value", 0.0)
    
    print(f"**Cash Balance**: {format_currency(cash)}")
    print(f"**Total Portfolio Value**: {format_currency(total_value)}")
    print(f"**Open Positions**: {len(positions)}")
    print()
    
    if positions:
        print("### Open Positions")
        print()
        print("| Ticker | Shares | Entry Price | Entry Date | Days Held | Stop Loss   |")
        print("|--------|--------|-------------|------------|-----------|-------------|")
        
        for ticker, pos in positions.items():
            shares = pos.get("shares", 0)
            entry_price = pos.get("entry_price", 0.0)
            entry_date = pos.get("entry_date", "N/A")
            stop_loss = pos.get("stop_loss_price", 0.0)
            
            # Calculate days held
            days_held = "N/A"
            if entry_date != "N/A":
                try:
                    entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
                    days_held = (datetime.now() - entry_dt).days
                except:
                    pass
            
            print(f"| {ticker:6s} | {shares:6d} | {format_currency(entry_price):11s} | {entry_date:10s} | {str(days_held):9s} | {format_currency(stop_loss):11s} |")
        
        print()
    
    # Realized P&L from last week
    print("## Weekly Performance")
    print()
    
    realized_pnl = calculate_realized_pnl_from_history(portfolio)
    
    if realized_pnl != 0.0:
        pnl_emoji = "[GAIN]" if realized_pnl > 0 else "[LOSS]"
        print(f"{pnl_emoji} **Realized P&L (Last 7 Days)**: {format_currency(realized_pnl)}")
    else:
        print("[REPORT] **Realized P&L (Last 7 Days)**: No closed positions")
    
    print()
    
    # Weekly trades summary
    trade_history = portfolio.get("trade_history", [])
    week_ago = datetime.now() - timedelta(days=7)
    
    weekly_buys = []
    weekly_sells = []
    
    for trade in trade_history:
        try:
            trade_date = datetime.fromisoformat(trade["timestamp"])
            if trade_date >= week_ago:
                if trade.get("type") == "BUY":
                    weekly_buys.append(trade)
                elif trade.get("type") == "SELL":
                    weekly_sells.append(trade)
        except:
            pass
    
    print(f"**Weekly Trades**: {len(weekly_buys)} BUY | {len(weekly_sells)} SELL")
    
    if weekly_sells:
        print()
        print("### Closed Positions (Last 7 Days)")
        print()
        print("| Date       | Ticker | Shares | Exit Price | P&L        | P&L %   | Reason |")
        print("|------------|--------|--------|------------|------------|---------|--------|")
        
        for trade in weekly_sells:
            trade_date = datetime.fromisoformat(trade["timestamp"]).strftime('%Y-%m-%d')
            ticker = trade.get("ticker", "N/A")
            shares = trade.get("shares", 0)
            price = trade.get("price", 0.0)
            pnl = trade.get("pnl", 0.0)
            pnl_pct = trade.get("pnl_pct", 0.0)
            reason = trade.get("reason", "N/A")[:30]  # Truncate long reasons
            
            pnl_str = format_currency(pnl)
            pnl_pct_str = format_percentage(pnl_pct)
            
            print(f"| {trade_date} | {ticker:6s} | {shares:6d} | {format_currency(price):10s} | {pnl_str:10s} | {pnl_pct_str:7s} | {reason:30s} |")
        
        print()
    
    # Summary statistics
    print("## Summary Statistics")
    print()
    
    successful_runs = sum(1 for r in run_summary if r["status"] == "SUCCESS")
    failed_runs = len(run_summary) - successful_runs
    success_rate = (successful_runs / len(run_summary) * 100) if run_summary else 0
    
    print(f"- **Total Runs**: {len(run_summary)}")
    print(f"- **Successful Runs**: {successful_runs} ({success_rate:.1f}%)")
    print(f"- **Failed Runs**: {failed_runs}")
    print(f"- **Current Cash**: {format_currency(cash)}")
    print(f"- **Portfolio Value**: {format_currency(total_value)}")
    print(f"- **Open Positions**: {len(positions)}")
    print(f"- **Weekly Realized P&L**: {format_currency(realized_pnl)}")
    
    print()
    print("=" * 80)
    print("[OK] Analysis Complete")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FAIL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
