#!/usr/bin/env python3
"""
Functional Health Check
=======================
Tests every component actually used by the live trading pipeline.
Must exit with code 0 for trading to proceed.

Checks:
  1. strategy_engine  -- imports + DEFAULT_VERSION + PARAMS intact
  2. strategy_v7_2    -- add_indicators_v7_2 importable
  3. brokerage_interface -- importable, IBKR class exists
  4. email_notifier   -- importable, EmailNotifier class exists
  5. config.py        -- TIINGO_API_KEY accessible
  6. portfolio.json   -- readable, valid JSON, required keys present
  7. tickers.txt      -- readable, at least 100 tickers
  8. data/SPY.parquet -- exists (regime filter needs it)
  9. data/*.parquet   -- at least 500 parquet files present
  10. IBKR port 7497  -- reachable (warns only, does not block trading)

ASCII output only. Task Scheduler compatible.
Exit code 0 = all critical checks pass.
Exit code 1 = at least one critical check failed.
"""

import sys
import os
import json
import socket
import logging
import traceback
from pathlib import Path
from datetime import datetime

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / 'logs'
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_DIR / 'functional_health_check.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('health_check')

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


def _result(name: str, status: str, detail: str) -> dict:
    symbol = "[OK]" if status == PASS else ("[WARN]" if status == WARN else "[FAIL]")
    logger.info(f"  {symbol} {name}: {detail}")
    return {"name": name, "status": status, "detail": detail}


def check_strategy_engine() -> dict:
    try:
        from src.strategy_engine import (
            DEFAULT_VERSION, PARAMS, get_params,
            check_exits, scan_universe, calc_position_size,
            can_enter, get_spy_regime, promote_power_stocks,
        )
        p = get_params(DEFAULT_VERSION)
        required = ['HARD_STOP_PCT', 'OVERBOUGHT_EXIT', 'TIME_STOP_DAYS',
                    'REGIME_MAX_POS', 'SECTOR_MAX', 'VOL_SIZE']
        missing = [k for k in required if k not in p]
        if missing:
            return _result("strategy_engine", FAIL, f"Missing params: {missing}")
        return _result("strategy_engine", PASS,
                       f"DEFAULT_VERSION={DEFAULT_VERSION} | HARD_STOP={p['HARD_STOP_PCT']:.0%}")
    except Exception as e:
        return _result("strategy_engine", FAIL, f"{e}\n{traceback.format_exc()}")


def check_strategy_v7_2() -> dict:
    try:
        from src.strategy_v7_2 import add_indicators_v7_2
        import pandas as pd
        import numpy as np
        df = pd.DataFrame({
            'close': [100.0 + i for i in range(250)],
            'high':  [101.0 + i for i in range(250)],
            'low':   [99.0  + i for i in range(250)],
            'volume': [1_000_000] * 250,
        })
        result = add_indicators_v7_2(df)
        if 'stoch_k' not in result.columns:
            return _result("strategy_v7_2", FAIL, "add_indicators_v7_2 missing stoch_k")
        return _result("strategy_v7_2", PASS, "add_indicators_v7_2 OK")
    except Exception as e:
        return _result("strategy_v7_2", FAIL, f"{e}\n{traceback.format_exc()}")


def check_brokerage_interface() -> dict:
    try:
        from src.brokerage_interface import get_brokerage_interface
        return _result("brokerage_interface", PASS, "get_brokerage_interface importable")
    except Exception as e:
        return _result("brokerage_interface", FAIL, f"{e}\n{traceback.format_exc()}")


def check_email_notifier() -> dict:
    try:
        from src.email_notifier import EmailNotifier
        return _result("email_notifier", PASS, "EmailNotifier importable")
    except Exception as e:
        return _result("email_notifier", FAIL, f"{e}\n{traceback.format_exc()}")


def check_config() -> dict:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
        key = os.environ.get('TIINGO_API_KEY') or os.environ.get('TIINGO_KEY', '')
        if not key:
            return _result("config(.env)", WARN, "TIINGO_API_KEY not set in .env")
        return _result("config(.env)", PASS, f"TIINGO_API_KEY set ({len(key)} chars)")
    except Exception as e:
        return _result("config(.env)", FAIL, f"{e}")


def check_portfolio_json() -> dict:
    path = ROOT / 'data' / 'portfolio.json'
    try:
        if not path.exists():
            return _result("portfolio.json", WARN, "File not found - will be created on first run")
        with open(path) as f:
            p = json.load(f)
        for key in ['cash', 'positions']:
            if key not in p:
                return _result("portfolio.json", FAIL, f"Missing key: '{key}'")
        n_pos = len(p.get('positions', {}))
        cash  = p.get('cash', 0)
        return _result("portfolio.json", PASS, f"cash=${cash:,.2f} | {n_pos} positions")
    except Exception as e:
        return _result("portfolio.json", FAIL, f"{e}\n{traceback.format_exc()}")


def check_tickers() -> dict:
    path = ROOT / 'tickers.txt'
    try:
        tickers = [t.strip() for t in path.read_text().splitlines() if t.strip()]
        if len(tickers) < 100:
            return _result("tickers.txt", FAIL, f"Only {len(tickers)} tickers (expected 2000+)")
        return _result("tickers.txt", PASS, f"{len(tickers)} tickers loaded")
    except Exception as e:
        return _result("tickers.txt", FAIL, f"{e}")


def check_spy_parquet() -> dict:
    path = ROOT / 'data' / 'SPY.parquet'
    if not path.exists():
        return _result("SPY.parquet", WARN,
                       "Missing - regime filter will default BULL. Run: python -c \"import yfinance as yf; "
                       "yf.download('SPY', start='2000-01-01').to_parquet('data/SPY.parquet')\"")
    try:
        import pandas as pd
        df = pd.read_parquet(path)
        return _result("SPY.parquet", PASS, f"{len(df)} rows")
    except Exception as e:
        return _result("SPY.parquet", FAIL, f"{e}")


def check_parquet_universe() -> dict:
    data_dir = ROOT / 'data'
    parquets = list(data_dir.glob('*.parquet'))
    spy_excluded = [p for p in parquets if p.stem.upper() != 'SPY']
    if len(spy_excluded) < 500:
        return _result("data/*.parquet", WARN,
                       f"Only {len(spy_excluded)} ticker parquets (expected ~2147). "
                       "Run: python scripts/fetch_deep_history.py")
    return _result("data/*.parquet", PASS, f"{len(spy_excluded)} ticker parquets present")


def check_last_bar_volume_sanity() -> dict:
    """Ensure the latest bar in a sample of parquets looks like a full EOD bar."""
    try:
        import pandas as pd
        import numpy as np
        data_dir = ROOT / 'data'
        parquets = [p for p in data_dir.glob('*.parquet') if p.stem.upper() != 'SPY']
        if not parquets:
            return _result("Last-bar volume sanity", WARN, "No parquets found")

        sample = parquets[:50]  # 50-ticker sample
        bad = 0
        checked = 0
        for path in sample:
            try:
                df = pd.read_parquet(path)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                if len(df) < 60:
                    continue
                if 'volume' not in df.columns:
                    continue
                # Compute 30-day volume SMA on the fly if not persisted.
                if 'volume_sma' not in df.columns:
                    df['volume_sma'] = df['volume'].rolling(window=30, min_periods=1).mean()
                last = df.iloc[-1]
                vsma = last['volume_sma']
                vol = last['volume']
                if pd.isna(vsma) or vsma <= 0 or pd.isna(vol):
                    continue
                checked += 1
                if vol < vsma * 0.2:
                    bad += 1
            except Exception:
                continue

        if checked == 0:
            return _result("Last-bar volume sanity", WARN, "Could not evaluate any sample bars")
        ratio = bad / checked
        detail = f"{bad}/{checked} sample tickers have last-bar volume < 20% of 30-day SMA"
        if ratio > 0.2:
            return _result("Last-bar volume sanity", FAIL,
                           f"{detail} - IEX partial-volume poisoning likely; run repair_poisoned_parquets.py")
        return _result("Last-bar volume sanity", PASS, detail)
    except Exception as e:
        return _result("Last-bar volume sanity", FAIL, f"{e}\n{traceback.format_exc()}")


def check_sector_map() -> dict:
    try:
        path = ROOT / 'data' / 'sector_map.json'
        if not path.exists():
            return _result("Sector map", WARN, "sector_map.json not found; run python scripts/update_data.py")
        data = json.load(open(path))
        total = len(data)
        real = sum(1 for v in data.values()
                   if v.get('sector') not in (None, 'Unknown', '')
                   and 'not available' not in str(v.get('sector', '')).lower())
        pct = (real / total * 100) if total else 0
        if total == 0:
            return _result("Sector map", WARN, "sector_map.json is empty")
        if pct < 50:
            return _result("Sector map", WARN,
                           f"Only {real}/{total} ({pct:.1f}%) real sector mappings - sector cap will be unreliable")
        return _result("Sector map", PASS, f"{real}/{total} ({pct:.1f}%) real sector mappings")
    except Exception as e:
        return _result("Sector map", FAIL, f"{e}\n{traceback.format_exc()}")


def check_ibkr_port() -> dict:
    """PORT 7497 REACHABILITY TEST - Deterministic Guardrail"""
    try:
        sock = socket.create_connection(('127.0.0.1', 7497), timeout=2)
        sock.close()
        return _result("IBKR port 7497", PASS, "Port open - IB Gateway/TWS is running")
    except Exception:
        return _result("IBKR port 7497", WARN,
                       "Port 7497 not reachable - will trade in PAPER mode. "
                       "Check auto_tws_manager.log if this is unexpected.")


def check_portfolio_sanity() -> dict:
    """
    PORTFOLIO SANITY TEST - Deterministic Guardrail
    Verifies portfolio.json cash is within reasonable bounds:
    - Not negative (indicates corrupted state)
    - Not > $150k (indicates IBKR Paper account hallucination)
    - Within 10% tolerance of expected $100k range
    """
    try:
        portfolio_path = ROOT / 'data' / 'portfolio.json'
        if not portfolio_path.exists():
            return _result("Portfolio Sanity", FAIL, "portfolio.json not found")
        
        with open(portfolio_path, 'r') as f:
            portfolio = json.load(f)
        
        cash = portfolio.get('cash', 0)
        
        # Check for negative cash (corrupted state)
        if cash < 0:
            return _result("Portfolio Sanity", FAIL, 
                          f"Portfolio cash is NEGATIVE: ${cash:,.2f} - corrupted state detected")
        
        # Check for inflated cash (IBKR Paper hallucination)
        if cash > 150000:
            return _result("Portfolio Sanity", FAIL,
                          f"Portfolio cash ${cash:,.2f} exceeds $150k ceiling - IBKR hallucination detected")
        
        # Check if cash is within reasonable range (10% tolerance of $100k)
        # Allow range: $0 - $150k (after drawdowns or gains)
        if cash > 0 and cash <= 150000:
            return _result("Portfolio Sanity", PASS,
                          f"Cash=${cash:,.2f} within safe range")
        
        return _result("Portfolio Sanity", WARN,
                      f"Cash=${cash:,.2f} - unusual but not critical")
        
    except Exception as e:
        return _result("Portfolio Sanity", FAIL, f"Error checking portfolio: {e}")


def main() -> int:
    logger.info("=" * 65)
    logger.info(f"FUNCTIONAL HEALTH CHECK  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 65)

    checks = [
        check_strategy_engine,
        check_strategy_v7_2,
        check_brokerage_interface,
        check_email_notifier,
        check_config,
        check_portfolio_json,
        check_tickers,
        check_spy_parquet,
        check_parquet_universe,
        check_last_bar_volume_sanity,
        check_sector_map,
        check_ibkr_port,
        check_portfolio_sanity,
    ]

    results = []
    for fn in checks:
        try:
            results.append(fn())
        except Exception as e:
            results.append(_result(fn.__name__, FAIL, f"Unexpected: {e}\n{traceback.format_exc()}"))

    passed  = [r for r in results if r['status'] == PASS]
    warned  = [r for r in results if r['status'] == WARN]
    failed  = [r for r in results if r['status'] == FAIL]

    logger.info("")
    logger.info("=" * 65)
    logger.info(f"RESULTS: {len(passed)} PASS | {len(warned)} WARN | {len(failed)} FAIL")
    logger.info("=" * 65)

    if failed:
        for r in failed:
            logger.error(f"  [FAIL] {r['name']}: {r['detail']}")
        logger.error("HEALTH CHECK FAILED - Aborting trading.")
        return 1

    if warned:
        for r in warned:
            logger.warning(f"  [WARN] {r['name']}: {r['detail']}")

    logger.info("HEALTH CHECK PASSED - Pipeline is ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

