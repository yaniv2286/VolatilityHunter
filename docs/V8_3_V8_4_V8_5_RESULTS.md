# V8.3 / V8.4 / V8.5 Experiment Results

**Date:** 2026-10-19 | **Status:** All candidates REJECTED — v8.1 remains champion
**Baseline (same backtest run):** v8.1 = 21.79% 26yr CAGR | -31.84% MaxDD | 0.71 Sharpe | 27.48% WR | 43,076 trades | $16.1M final equity

All candidates were added as separate `PARAMS` entries in `src/strategy_engine.py`.
`DEFAULT_VERSION` was **never** changed from `'v8.1'`. All filters are param-gated
(keys absent in v8.1 -> zero behavior change, confirmed by byte-identical
`simulate_monday --date 2026-09-01` candidate list before/after).

## Phase 1 - Indicator infrastructure (kept, inert)

Added to `src/strategy_v7_2.py` `add_indicators_v7_2()`: `ema_3`, `ema_8`,
`sma_20`, `rsi_8` (recursive Wilder/RMA `ewm(adjust=False)` convention),
`adx_14`, `plus_di_14`, `minus_di_14`. Verified by `scripts/verify_indicators_v83.py`.
Simulation output identical to baseline (17 candidates: EGO TDW ERO SSL HP CLMT
KYTX PBF WFRD HLX VIST BP NVS IMCR CTRA CF QSR). Health check Exit 0.

## Phase 2 - v8.3 trend-quality filters: REJECTED

Per-filter rejection audit on v8.1 base entry bars (why it failed):

| Filter | Rejects |
|---|---|
| 20-day breakout (close > max high 20) | 72.7% - contradicts buy-the-dip |
| Stop distance <= 5% (min low/ema8/sma20) | 52.9% - pullback entries leave lagging MAs below |
| ADX >= 20 | 23.9% |
| SMA200 proximity 1.5% | 0.7% |

| Variant | Config | Retention | CAGR delta | DD delta | Verdict |
|---|---|---|---|---|---|
| v8.3 | all four filters | 5.9% | n/a | n/a | FAIL (worse than v8.2's -78%) |
| v8.3b | ADX>=20 + prox only | 75.6% | -1.94% | +2.04 | FAIL (DD <3pt needed) |
| v8.3c | ADX>=15 + prox only | 91.4% | -2.31% | +0.98 | FAIL |

Root cause: v8.1 is a buy-the-dip strategy (stoch 32-80 = pullbacks in uptrends).
Requiring breakouts/ADX trend-strength filters fights the entry philosophy and
removes the bars where the edge lives.

## Phase 3 - v8.4 candle-quality trigger: REJECTED (weakly positive variant exists)

Spec'd triggers audited before backtest - dead on arrival:

| Filter | Rejects |
|---|---|
| Juicy body >= 1.5x ATR | 89.1% |
| RSI-8 cross 50 (event) | 89.4% |
| Green candle | 39.8% |
| Close > ema_8 | 20.3% |
| All combined | 96.6% |

Only `rsi_8 >= 50` (level, not cross) retained 90.9% -> tested as v8.4:

| Metric | v8.1 | v8.4 | Delta |
|---|---|---|---|
| Retention | - | 94.6% | PASS |
| 26yr CAGR | 21.79% | 21.26% | -0.53% |
| MaxDD | -31.84% | -29.73% | +2.11 |
| Sharpe | 0.71 | 0.78 | +0.07 |
| Win rate | 27.48% | 27.74% | +0.26 |

Directionally positive (Sharpe +10% relative, DD improvement) but does not meet
the >=3pt DD gate and gives up raw CAGR. Kept as dormant `v8.4` params - could be
revisited combined with a stronger exit-side change. Not promoted.

## Phase 4 - v8.5 partial exit + breakeven: REJECTED

Implemented in engine (`check_exits` fraction field), executor
(`daily_trading_loop.execute_exits`), and `src/strategy_v8_5.py` backtest twin.
`scripts/verify_partial_exits.py`: ALL 9 checks PASS. `portfolio.json` schema
extended safely via `.get()` (`partial_taken`, `breakeven_stop`).

Backtest verdict - catastrophic:

| Metric | v8.1 | v8.5 | Delta |
|---|---|---|---|
| 26yr CAGR | 21.79% | 0.68% | -21.11% |
| MaxDD | -31.84% | -39.78% | -7.94 (worse) |
| Sharpe | 0.71 | 0.12 | -0.59 |
| Avg win | 17.16% | 8.91% | -8.25% |
| Win rate | 27.48% | 40.23% | +12.75 (mechanical) |
| Exit records | 43,076 | 85,374 | doubled |

Exit breakdown: 38,140 partial legs (avg +2.21% - fires immediately via
ema_3<ema_8), 17,472 breakeven stops (~46% of partial'd positions round-trip to
~0%), 54,412 close<ema_8 finals.

Root cause: v8.1's edge is a fat right tail (27% WR, 17% avg winners). Selling
half at +2% and trailing the runner at ema_8/breakeven amputates exactly that
tail. Win-rate inflation is mechanical (half-size +2% legs); per-position
expectancy collapses. This is the same reason OVERBOUGHT_EXIT=78 exists instead
of tight EMA trails.

## Phase 5a - Earnings guard (v8.6): IMPLEMENTED, dormant

User override: free data source acceptable. Implemented via Nasdaq's keyless
bulk earnings calendar (`https://api.nasdaq.com/api/calendar/earnings?date=`),
one request per day covers the whole market. yfinance was tested but is
rate-limited and unsuitable for a 2,135-ticker universe.

- `src/earnings_calendar.py`: ~30 requests/day refresh, cached to
  `data/earnings_cache.json`, fail-open (missing date never blocks).
  Live coverage: 4,078 tickers in 30d window, 1,704/2,135 of our universe.
- `PARAMS['v8.6']` = v8.1 + `EARNINGS_BLOCK_DAYS=14` +
  `EARNINGS_FORCE_EXIT_DAYS=1`. `DEFAULT_VERSION` stays `'v8.1'`.
- `scripts/verify_earnings_guard.py`: 16/16 checks PASS (mocked maps, no network).
- Health check Exit 0. v8.1 confirmed unaffected by all checks.

**Backtest caveat (documented per plan):** no free point-in-time 26-year
earnings history exists. v8.6 is a live/sim-only overlay - its effect cannot be
measured in the historical backtest without lookahead bias. Expected behavior:
fewer entries during earnings season, occasional forced exits 1 day before
reports. This is a tail-risk guard, not a CAGR improvement.

**Phase 5b (VIX):** still not started - low value vs existing SPY regime filter.

## v8.7 - Candidate ranking experiment: REJECTED

Cash cap means ~5 usable slots, so when >10 tickers qualify on a day (1,172 such
days, 21,769 excess signals), the score function picks which get filled.
Tested by re-sorting same-day v8.1 trade records before the slot-filling
equity builder (`scripts/backtest_v8_1_vs_v8_7.py`):

| Ordering | 26yr CAGR | MaxDD | Sharpe |
|---|---|---|---|
| arrival (harness artifact, alphabetical) | 21.73% | -31.84% | 0.71 |
| volume surge | 14.90% | -30.48% | 0.74 |
| reverse live-score (worst first) | 14.18% | -28.52% | 0.79 |
| live composite (0.6*annual + 0.4*stoch) | 13.63% | -31.66% | 0.71 |
| combo (mom+vol pct ranks) | 12.67% | -30.80% | 0.68 |
| rsi_8 | 10.85% | -30.14% | 0.61 |
| momentum 20d | 10.89% | -30.82% | 0.59 |
| random seeds 1/2/3 | 9.8-10.7% | ~-29.4% | ~0.63 |

Verdict: no systematic ranking beats the incidental baseline. Random orderings
are the worst of all - the live composite score is actually mid-pack, not
harmful. Picking a lucky permutation would be pure overfitting.

**Robustness caveat learned:** realized CAGR has a wide band (~10pts) depending
on intra-day fill order when slots bind. The documented ~21.7% baseline is
partially ordering-luck; treat single-run backtest CAGRs as noisy.

`RANK_BY` machinery stays param-gated in `scan_universe` (verified by
`scripts/verify_v87_ranking.py`, 6/6 PASS) - dormant, no PARAMS entry uses it.

## Phase 6 - Rejected items (recorded per plan)

22:15 ET near-close run (partial-bar poisoning), VIX>=16 scalp / 100% sizing
(breaks position cap + no-margin), 70/30 long-short (margin/borrow), price-tier
sizing (ATR sizing strictly better), SQLite (portfolio.json + .get() suffices),
Alpaca migration (IBKR adapter works).

## Bottom line

Three independent hypotheses (trend-quality filters, entry momentum confirmation,
partial exits/breakeven) all failed acceptance gates against repaired-data v8.1.
The strategy's edge is robust to these overlay classes. v8.1 stays default;
all candidate code remains param-gated and dormant for future reference.

Artifacts: `logs/backtest_v8_1_vs_v8_4_20261019_1557.json`,
`logs/backtest_v8_1_vs_v8_5_20261019_1605.json`, plus v8.3x JSONs in `logs/`.
