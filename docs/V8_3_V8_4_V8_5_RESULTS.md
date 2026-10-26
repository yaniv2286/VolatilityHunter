# V8.3 / V8.4 / V8.5 Experiment Results

> AUDIT CORRECTION (2026-10-24): The strategy verdicts and causal explanations
> below are historical notes, not validated investment conclusions. The legacy
> simulator fails cash-only accounting, does not value open holdings daily, and
> differs from the shared engine. Its per-ticker volatility sizing also uses
> future observations. Do not use these CAGRs, drawdowns, or candidate rejection
> verdicts for promotion or income forecasts until recomputed with a validated
> portfolio simulator. This correction does not change the running paper strategy.
>
> Contrary to the historical statements below, v8.6 was subsequently promoted
> in commit 33ada13. The 2026-10-23 trading log records a v8.6 scan and an IBKR
> paper-account fill. Functional checks prove code paths run, not profitability.

## Backtest integrity audit and replacement requirements (2026-10-24)

Agreed research objectives: $100,000 starting capital, no withdrawals during
the initial compounding period, 20% annualized return target, and approximately
30% acceptable drawdown. Evaluate returns after modeled trading costs and
separately disclose data/software expenses and personal-tax exclusions.
Neither objective is a guaranteed future return or maximum loss.
Keep existing stochastic 32-80, volume, momentum and exit rules as an explicit
v8.1 baseline; evaluate the v8.6 earnings overlay separately. Broker migration
is deferred. Current scope remains paper-only, long-only and cash-only.

### Reproduced failure

Calling `scripts/backtest_v8_1_vs_v8_7.py:build_equity_curve` with ten trades,
all entering on 2020-01-02, exiting on 2020-01-06, earning 10%, and assigned
distinct sectors with `vol_scale=1` produces $120,000 from $100,000.
The cash-only maximum for these simultaneous trades, before costs, is $110,000.
The builder implicitly allocates $200,000 without a cash debit. This proves
that the harness can violate the mandate; it does not quantify the distortion
in every previously reported historical run.

Other confirmed implementation issues:

- `src/strategy_v8_1.py` calculates `median_atr_pct` across the full series;
  later volatility changes therefore affect earlier position sizing.
- Entries use the signal bar's close, although its final indicators are only
  known after the bar completes. This does not reproduce next-session execution.
- Equity curves omit daily unrealized gains and losses in open holdings.
- Legacy sector assignments use ticker initials; same-day baseline ordering
  is alphabetical rather than the shared engine's composite score.
- Per-ticker trades are generated independently of portfolio acceptance, so
  sorting these precomputed records cannot reproduce a portfolio state machine.
- The per-ticker power-stock rules and stop logic differ from the shared engine.

### Required acceptance checks for the replacement

1. Replay an exchange-session event timeline with explicit signal and execution
   timestamps. Data available to decisions must be restricted to that timestamp.
   Changing future prices must not change earlier signals, fills or sizing.
2. Maintain one cash/share ledger, integer shares, settled-funds availability
   under an explicit historical settlement policy, and fill-confirmed position
   state. Reject unaffordable purchases and sales beyond owned shares.
3. Value every open holding daily. Reconcile cash, holdings, dividend
   receivables, corporate actions, fees and total equity against hand-calculated
   fixtures, including an open position suffering a large interim loss.
4. Call shared engine decisions instead of cloning strategy rules. Test
   scanner ranking, exits, power promotion, partial exits and position caps
   against identical inputs/state in the paper path. Record unresolved parity
   differences rather than silently claiming agreement.
5. Model execution costs, gaps, rejected/unfilled orders and missing prices.
   Daily open prices are only an approximation to the intraday paper execution
   schedule; label that limitation and stress it, or obtain suitable intraday
   observations before claiming execution parity.
6. Audit Tiingo coverage, adjustments, symbol changes, delistings and historical
   universe eligibility. Missing historical coverage must block an investment
   conclusion, not silently remove losing stocks. Current sector mappings
   must not be described as historical point-in-time classifications.
7. Use only earnings information known at the simulated date. Today's calendar
   is not valid historical evidence; mark v8.6 performance unevaluable where
   timestamped historical announcements are unavailable.
8. Report accepted portfolio trades, daily equity/drawdown, annual and rolling
   returns, time underwater, turnover, exposure, costs and benchmark results.
   Record code revision, parameters, data fingerprints, exclusions and assumptions
   so the run can be reproduced.
9. Separate chronological research/evaluation periods and document that previously
   inspected history is not untouched. Freeze rules before forward paper
   evaluation. Sensitivity and adverse-cost tests supplement, not replace, it.

These are requirements for a replacement, not a claim that it is implemented.
No backtest can guarantee future profitability or make a 30% drawdown a hard cap.

### Tiingo coverage check and proposed fixed dates (2026-10-24)

Read-only audit: `python scripts/audit_backtest_data.py`, Exit 0.
The audit covers the current `tickers.txt`, not a historical listing universe:

- 2,135 requested tickers; 2,134 readable files; 8,932,209 rows.
- AXL has no local file. 65 files have fewer than 300 observations.
- 775 files begin on 2000-01-03; none contains pre-2000 observations.
- 2,065 files end on 2026-10-22. The other 69 end earlier and require
  investigation; an older end date alone does not establish a data error.
- All 2,134 files contain adjusted OHLCV, dividend and split columns.
- Basic checks found no duplicate/unsorted/null dates and no missing or
  nonpositive close/adjusted-close values. These checks do not establish
  exchange-session completeness, correct adjustments or historical coverage.

Three authenticated, read-only Tiingo requests for SPY, AAPL and MSFT each
returned 504 daily observations from 1998-01-02 through 1999-12-31, including
raw/adjusted OHLCV, divCash and splitFactor. The provider supports the proposed
warmup period for these samples. Full-universe pre-2000 coverage remains
unverified. `scripts/repair_broken_parquets.py` explicitly sets
`FULL_START = '2000-01-01'`; the local cutoff is not proof of a provider limit.

Proposed research contract:

- Request daily data beginning 1998-01-01 for historically eligible securities.
  1998-1999 is warmup only, not reported investment performance. Later listings
  become eligible only after satisfying the shared engine's history requirements.
- Target the fixed performance interval 2000-01-01 through 2025-12-31, using
  actual exchange sessions. This supersedes the provisional 2001 start if
  warmup and historical-universe coverage pass validation. Do not claim a
  validated full-2000 result before that gate passes.
- Report 2026 separately with an explicit cutoff; the currently inspected
  local endpoint is 2026-10-22. This is already-observed data, not untouched
  forward evidence.
- Acquire and fingerprint a separate research snapshot, including provider
  retrieval dates, historical eligibility and exclusions. Do not overwrite
  the active paper portfolio or silently splice adjusted data from different
  corporate-action revisions.
- Investigate the missing/stale files and historical delistings before accepting
  investment conclusions. More years of today's survivors do not resolve this.
- Freeze data, dates, costs and baseline parameters for each experiment batch.
  A data repair creates a new snapshot and requires rerunning all comparators.

No full-history bulk download, strategy change or broker change was performed
as part of this coverage audit.

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

---

## 2026-10-26 corrected-engine baselines (supersedes all verdicts above)

All numbers: frozen snapshot `data/research/snapshot_1998_20261022`,
2000-01-03 -> 2025-12-31, $100k, T+1, 5bp slippage + $0.005/sh ($1 min),
shared engine decisions, daily mark-to-market.

| Run | Universe | CAGR | Max DD | Final equity | Notes |
|---|---|---:|---:|---:|---|
| v8.1 net | 2,124 survivors | 3.47% | -30.3% | $242k | understates (see below) |
| v8.1 zero-cost | 2,124 survivors | 5.39% | -32.7% | $390k | costs ~1.9pp/yr |
| Momentum 12-1 | 2,124 survivors | 13.34% | -74.3% | $2.58M | untradeable DD |
| Momentum 12-1 | 9,886 honest | **2.39%** | **-99.6%** | $184k | REJECTED |
| **v8.1 net** | **9,886 honest** | **8.54%** | **-31.9%** | **$839k** | reference baseline |

Key findings:
- Survivorship cuts BOTH ways: adding delisted/acquired names RAISED v8.1
  (it catches future takeout winners) but DESTROYED naive momentum.
- v8.1 beats SPY (8.54% vs 7.78%) on the honest universe, within the
  ~30% drawdown tolerance (-31.9%) but underwater 97% of the time and
  5.3 years in the worst window (2015-06 -> 2020-09).
- Alpha is concentrated in 2000-2006 (+46.6/+55.5/+35.8/+77.0% years);
  2014-2025 is essentially flat. The edge decayed, not the machinery.
- Capital-ceiling defect: engine's $100k buying-power ops cap silently
  blocks ALL buys once equity > ~$500k. Lifted for research via
  --capital-ceiling (process-local). Same wall exists in live if the
  account ever exceeds ~$500k - must be revisited before deployment.
- CON ticker needed a Windows-reserved-name filename guard
  (price_filename() in backtest_engine, mirrored in the downloader).

Verdict: v8.1 = 8.54% CAGR reference line. Still short of the 20% goal;
the gap is in the post-2014 flat regime, not in costs or accounting.
