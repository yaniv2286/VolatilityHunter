# Post-Audit Production Fixes

**Date**: 2026-09-02  
**Status**: Functional health check PASS (Exit Code 0)  
**Default Strategy**: `v8.1`  

This document records the fixes applied after the full historical audit of VolatilityHunter.

## 1. Data Pipeline (Tiingo EOD Only)

- `src/smart_data_loader_factory.py` now treats the Tiingo `/iex` endpoint as an **intraday snapshot source only**.
- IEX snapshots are **never persisted** to parquet files.
- Completed end-of-day OHLCV bars are fetched from `https://api.tiingo.com/tiingo/daily/{ticker}/prices` and written to `data/*.parquet`.
- A `_last_completed_eod_date()` helper drops any partial current-day bar when the market has not yet closed, preventing the IEX-snapshot poisoning that corrupted live indicators.
- Yahoo Finance is no longer used on the production path.

## 2. Poisoned Parquet Repair

- `scripts/repair_poisoned_parquets.py` rebuilt all parquets from `2026-04-29` through the most recent completed trading day.
- Result: `2111/2136` tickers repaired; 25 failed (delisted / 404). Volume sanity is now restored.

## 3. Data Freshness & Volume Sanity Health Gate

- `scripts/functional_health_check.py` now includes `check_last_bar_volume_sanity()`.
- It computes a 30-day volume SMA and rejects a run if more than 20% of a sample have last-bar volume below 20% of the SMA (a tell-tale sign of IEX partial-volume poisoning).

## 4. Sector Map

- `scripts/update_sector_map_from_csv.py` downloads the public `adanos/free-ticker-database` CSV and maps US-listed tickers to real GICS-style sectors.
- `scripts/update_sector_map.py` refreshes from Tiingo fundamentals/meta and only overwrites when a real sector is returned.
- Current coverage: ~1,655 real sectors for 2,135 tickers (~77.5%).
- `strategy_engine.py` no longer treats arbitrary first-letter buckets as valid sector mappings.

## 5. Strategy Engine

- Default version reverted from `v8.1.1` to `v8.1`.
- Intraday elapsed-fraction volume loosening removed from `scan_universe`; the live scan now uses the previous completed daily bar.
- ATR stop capped at `HARD_STOP_PCT` (`min(ATR_STOP_MULT * ATR / entry, HARD_STOP_PCT)`) so a wide ATR can no longer produce losses larger than the configured hard stop.

## 6. Position Sizing

- `calc_position_size()` now returns `(shares, cost, atr)`.
- `execute_entries()` records the IBKR fill price and stores the candidate's ATR on the position dict.
- Median ATR calculation fixed: if no open positions exist, the candidate's own ATR% is used as the baseline instead of an arbitrary 0.02 floor.
- Triple cash guard remains in place; no margin or leverage is used.

## 7. Market Calendar & Trading Hours

- `src/market_hours.py` now contains a 2026 NYSE holiday list and early-close map.
- `daily_trading_loop.py` validates market hours before any order placement (both exits and entries) and skips execution on holidays, weekends, pre-market, or post-close.
- Next-open logic skips holidays.

## 8. Order Execution & Ledger

- `daily_trading_loop.py` records IBKR's actual `filled_avg_price` in the portfolio ledger, not the signal/reference price.
- `brokerage_interface.py` already returns confirmed fills; phantom or unfilled entries are no longer added to `portfolio.json`.
- The three phantom `RAPT` BUY records were removed from `data/portfolio.json`.
- Unfilled orders are still cancelled by the existing `OrderMonitor` 5-minute timeout before the loop ends.

## 9. Verification

New standalone verification scripts were added and run successfully:

| Script | Result |
|---|---|
| `python scripts/functional_health_check.py` | Exit 0 |
| `python scripts/verify_data_pipeline.py` | Exit 0 |
| `python scripts/simulate_monday.py --date 2026-09-01` | Exit 0 |
| `python scripts/repair_poisoned_parquets.py` | Exit 0 |

## 10. What Was NOT Changed

- No further strategy tuning was performed. Per the audit findings, strategy parameters will be revisited only after the repaired-data backtest and live path are reconciled.
- No live trades were executed during this fix session; all changes were validated with the health check and simulation.

## 11. Remaining Recommendations

- Run a full repaired-data backtest (`scripts/backtest_v8_vs_v8_1.py`) and compare it to the reconstructed live P/L.
- If the clean backtest still misses the 15% annual target, revisit position sizing, sector concentration, and bear-regime parameters.
- Schedule `scripts/update_data.py` to run after the US market close (so it can append the completed EOD bar) and `scripts/daily_trading_loop.py` to run while the market is open.
- Continue monitoring `logs/` for `ERROR`, `CRITICAL`, and `Traceback` lines.
