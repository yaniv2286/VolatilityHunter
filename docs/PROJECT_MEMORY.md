# VolatilityHunter: goals, decisions, and resume checkpoint

Last updated: 2026-10-24 (second update: corrected-backtest foundation built).

Read this at the start of a session, together with the repository protocol.
This is persistent project context, not evidence of future profitability.
Check current code, git status, and recent logs before acting on dated facts.
Update this file when an objective, decision, or checkpoint changes. Do not
mark planned work as completed. New explicit user instructions take precedence.

## User objectives and boundaries

- Research starting capital: USD 100,000.
- Aim: approximately 20% long-term annualized return, not 20% every calendar
  year. Eventually support approximately USD 1,500/month; initially reinvest
  profits without withdrawals for the first few years.
- User accepts approximately 30% drawdown provided the system is working.
  This is a tolerance for evaluation, not a guaranteed loss ceiling or
  permission to accept arbitrary risk. Operational correctness and a
  continuing investment edge must be assessed separately.
- Evaluate returns after modeled trading costs; separately disclose
  data/software expenses. Personal tax treatment is unresolved; label any
  reported tax exclusions rather than claiming after-tax income.
- User wants candid, evidence-based conclusions, including results below
  target. Do not optimize until a historical report happens to show 20%.
- Keep paper-only, long-only, cash-only execution. No short selling, margin,
  leverage, broker migration, or real-money orders in the current scope.
- User has Schwab and IBKR accounts; broker selection is explicitly deferred.
  Account ownership is not authorization for real-money trading.
- Tiingo is the paid data provider. "Trello" was a typo. Do not replace the
  subscription based solely on defects in our simulator. New paid subscriptions
  require explicit approval.

## Strategy baseline and actual execution

- The 32-80 entry range is STOCHASTIC %K, not RSI.
- Preserve `PARAMS['v8.1']` while establishing the corrected baseline:
  stochastic 32-80, SMA200 trend condition, volume surge, annual-return and
  20-day momentum filters, existing ranking, sizing, exits and power-stock logic.
- Strategy decisions belong in `src/strategy_engine.py`. Backtests should
  call shared functions, not clone a subtly different version of the rules.
- The inspected running default is v8.6: v8.1 plus an earnings entry block
  and forced exit. It was promoted and pushed in commit `33ada13`.
  Do not automatically change that default during backtest work.
- The 2026-10-23 log records a v8.6 scan, an IBKR connection on port 7497,
  and a broker-confirmed paper-account fill. This is dated runtime evidence,
  not a claim that a broker is connected in the current session.
- The daily loop aborts if IBKR cannot connect. Earlier descriptions of an
  automatic local-simulation fallback were incorrect.
- Evaluate the earnings overlay separately. Today's Nasdaq calendar cannot
  be substituted for announcements known at historical decision times.

## Corrections that must not be forgotten

Legacy v8.1 headline CAGR around 21.7%, candidate rejection verdicts, and
claims that the strategy is "near-optimal" or "confirmed robust" are NOT
validated investment conclusions.

Confirmed defects:

1. The ranking equity builder can allocate 200% of capital without debiting
   cash. Ten simultaneous positions at 20% allocation, each returning 10%,
   turn $100,000 into $120,000 in that builder; the cash-only maximum is
   $110,000 before costs. This is a reproducible accounting failure.
2. Legacy per-ticker sizing uses the median ATR over the entire series,
   including future observations.
3. Open holdings are not valued daily in the legacy equity builder.
4. Signal-bar closing fills do not reproduce completed-EOD decisions followed
   by later execution.
5. Alphabetical order, fictional ticker-initial sectors, and independent
   per-ticker trade generation differ from portfolio decisions in the engine.
6. Power-stock state and stops differ between legacy backtests and the engine.

All historical strategy comparisons need reevaluation after these problems
are fixed. A passing syntax/health/fixture check is not proof of an edge.
See `docs/V8_3_V8_4_V8_5_RESULTS.md` for audit evidence and acceptance checks;
its older experiment narrative is explicitly superseded by the audit warning.

## Data facts and proposed fixed evaluation contract

Audit completed 2026-10-24 with `scripts/audit_backtest_data.py`, Exit 0:

- Current universe: 2,135 symbols, 2,134 readable files, 8,932,209 observations.
- AXL missing; 65 files shorter than 300 rows.
- 775 files start 2000-01-03; none has pre-2000 observations.
- 2,065 files end 2026-10-22; 69 end earlier and need investigation.
- All readable files contain adjusted OHLCV, dividend, and split fields.
  Basic date/closing-price checks passed. This is not a complete data audit.
- Read-only authenticated Tiingo requests for SPY, AAPL, and MSFT each
  returned 504 observations covering 1998-1999 with corporate-action fields.
  Full-universe pre-2000 availability has not been established.
- The repair script explicitly requests history starting in 2000. The local
  cutoff alone is not a provider-history limitation.

Proposed dates:

- Acquire daily history from 1998-01-01; 1998-1999 is indicator warmup.
- Measure a fixed 2000-2025 interval, subject to historical-universe and warmup
  validation. Later listings must earn eligibility through sufficient history.
- Report 2026 separately with an explicit cutoff; inspected local data ends
  2026-10-22. Do not label already-inspected 2026 data as untouched.
- New data after freezing a version provides forward paper evidence.
- Do not extend to 1990 merely to increase the headline test length.

The current ticker list is NOT a validated historical universe. Delisted stocks,
symbol identity changes, historical eligibility, missing sessions, corporate
actions and stale endpoints remain unresolved. More history for current
survivors does not fix survivorship bias.

## Coverage findings (2026-10-24 provider audit)

A Tiingo supported-tickers catalog audit exists at
`data/research/coverage_20261024T182831312532Z/` (its generating script
`scripts/audit_tiingo_universe.py` is missing and may need rebuilding):

- Catalog: 109,127 rows; 16,371 USD stocks on US exchanges; 8,150 ended
  before 2026-10-22 => delisted histories ARE available (TWTR verified:
  full history through 2022-10-28 delisting).
- ~16,910 early-ending USD symbols exist OUTSIDE our 2,135 universe:
  survivorship bias in the current universe is real and quantified.
- Only 793 of our 2,135 tickers have provider history before 2000.
- 2,292 duplicate symbol keys in catalog => symbol recycling exists;
  identities resolved via live meta endpoint are not point-in-time.
- Zombie bars confirmed: SPLK continues printing flat-price ~0-volume
  rows after its 2024-03-18 acquisition. Detection rule needed:
  consecutive zero/low-volume flat closes = untradeable.
- Symbol redirects found: AXL -> DCH (Dauch Corp), EQR -> VMRK.
- `no_data` tickers include BBBY (bankrupt 2023) - exactly the kind of
  missing loser that inflates survivor-only results.

## Corrected backtest foundation (built 2026-10-24)

New components, all verification passing:

- `src/portfolio_ledger.py`: cash/settled-cash ledger, integer shares,
  no oversell/shorting, T+1 settlement, fees, dividends, splits with
  cash-in-lieu, daily mark-to-market, fill/reject order log.
- `scripts/verify_ledger.py`: 27 hand-calculated checks, Exit 0 -
  including the $200k-from-$100k regression fixture.
- `src/backtest_engine.py`: daily replay calling SHARED engine functions
  (check_exits, scan_universe, can_enter, calc_position_size,
  promote_power_stocks). Signals on completed bar T fill at T+1 raw open
  with configurable slippage/commission; corporate actions applied at
  ex-date before fills; untradeable positions force-liquidated after 20
  sessions at last price; settled-cash enforced by ledger.
- `scripts/verify_backtest_corrected.py`: future-data isolation
  (truncated vs full data = identical results), determinism, cash
  integrity, next-open fills. Exit 0.
- `scripts/download_research_snapshot.py`: resumable Tiingo snapshot
  fetcher -> data/research/snapshot_1998_20261022/ with progress.jsonl,
  per-ticker sha256, manifest. Redirect resolution via meta endpoint.
- `scripts/backtest_corrected.py`: runner -> reports/backtest_*_{summary
  .json,equity.csv,trades.csv} with CAGR/maxDD/yearly/exposure/benchmark.
- `scripts/verify_prefilter.py`: proves the O(1) numpy candidate
  prefilter == full scan (exact-equivalence speed gate, Exit 0).
  Full 26y baseline: ~52min -> ~17min after prefilter + O(1) pointer
  slicing. Equity curve byte-identical; only dd_window reporting bug
  fixed (peak 2006-05-10 -> trough 2009-11-02). Iteration protocol:
  screen candidates on short windows (~1-3min), full run only for
  finalists; independent runs parallelize across processes.

Backtest timing model vs live: signals use the last completed EOD bar and
fill next session open. Live decides ~09:35 ET on yesterday's bar and
fills intraday ~09:35. Structurally equivalent (signal bar = last
completed bar before fill session) but intraday fills are approximated
by the open. Known remaining differences to disclose: sector map and
earnings calendar are current-date, not point-in-time; entry backfill
after an exit takes one extra session vs live.

## Corrected v8.1 baseline result (2026-10-24, FIRST TRUSTWORTHY RUN)

Snapshot: data/research/snapshot_1998_20261022 (2,124 tickers + SPY/MTUM,
1998-01-01 -> 2026-10-22, per-ticker sha256, git 33ada13).
Window: 2000-01-03 -> 2025-12-31, 6,539 sessions, $100k start,
5bp slippage + $0.005/sh commission ($1 min), T+1 settlement.
Report: reports/backtest_v8.1_2000-01-03_2025-12-31_baseline_summary.json

Headline: CAGR 3.47% (vs SPY 7.78% same window). Final equity $242,423.
Max drawdown -30.34% (peak 2006-05-10 -> trough 2009-11-02, recovered
2013-12-17: 7.6 years underwater). Time underwater 98.6%.
5,102 entries / 5,094 exits, win rate 41.2%, profit factor 1.069.
Fees $28.7k vs dividends $30.2k. Turnover $65.9M. 4 rejected orders.

Concentration: the two largest winners (ARWR +$35k 2014, BE +$33k 2025)
are ~48% of total net profit. Most gains cluster in 2003/2013/2014
post-crash rebounds; 2007-2012 and 2015-2025 are flat-to-negative.

INTERPRETATION: the legacy ~21.7% CAGR was inflated by the cash
accounting defect and lookahead. The honest v8.1 does NOT support the
20% target, and this figure is still an UPPER BOUND (current-universe
survivors only; no delisted losers like BBBY which returned no_data).
The strategy has a marginal positive expectancy that costs mostly
consume. This result needs strategy redesign, not parameter tuning.

## Expanded-universe snapshot + first experiments (2026-10-26)

- Supplement universe built from Tiingo catalog: US-exchange USD stocks
  with >=1y span alive inside 2000-2025, excluding hyphenated/when-issued/
  unit/warrant-style tickers and names already in tickers.txt.
  Source list: temp/ws_delisted_supplement.txt (8,040 rows, 247 duplicate
  catalog rows -> 7,793 unique). 4,244 of them are delisted/ended.
- Snapshot now 9,930 records: 9,886 ok / 43 no_data / 1 error (CON).
  Same frozen snapshot dir; new manifest regenerated.
- `scripts/audit_tiingo_universe.py` REBUILT (script was lost; artifacts
  existed). Reproduces the coverage bundle schema.
- `src/backtest_engine.py` now two-tier: numpy _arr for ALL tickers
  (prefilter, prices, bar dicts) + 800-frame LRU for engine reads.
  ~4GB RAM at 9,886 tickers; day-0 bulk load ~9 min.
- `scripts/backtest_corrected.py --strategy {engine,momentum}` and
  `--capital-ceiling` added.
- `src/momentum_comparator.py`: 12-1 relative-strength momentum, top-10,
  monthly rebalance, same ledger/fills/costs. Benchmark hypothesis only -
  NOT a PARAMS version.

CAPITAL-CEILING DEFECT FOUND: engine get_safe_buying_power caps buying
power at ABSOLUTE_CAPITAL_CEILING=$100k (a live ops guard for the real
account). In a compounding backtest it silently rejects EVERY buy once
equity > ~$500k (alloc=20%*equity > cap). v8.1 full-universe run froze
at $756,032 from 2007 onward. Fixed via --capital-ceiling (process-local
patch, live untouched). WARNING: the same wall exists in LIVE if the
paper/real account ever exceeds ~$500k - flag for future.

RESULTS on survivor universe (2,124): zero-cost v8.1 = 5.39% CAGR vs
3.47% net (costs eat ~1.9pp/yr; gross edge is the real limitation).
Momentum comparator = 13.34% CAGR but -74.3% maxDD - untradeable risk.

RESULTS on honest universe (9,886): momentum 2.39% CAGR, maxDD -99.55%
(final $184k). Survivorship-bias demonstration: 13.34% -> 2.39%. Pure
unfiltered momentum systematically buys winners that then die.

v8.1 honest-universe FINAL (tag full_v2, ceiling lifted):
CAGR 8.54% vs SPY 7.78% - the survivor-universe 3.47% UNDERSTATED the
strategy; the added universe contains delisted/acquired winners it
actually catches. Final equity $838,999 (+739%), maxDD -31.86%
(2015-06-18 -> 2020-09-24: 5.3yr underwater), time underwater 97.2%.
3,909 entries, win rate 40.7%, profit factor 1.139, fees $77.5k.
Yearly: 2000-2006 supplied nearly all alpha (+46.6/+55.5/+35.8/+77.0%);
2014-2025 is essentially flat (best +14.3% 2024, several -3..-11%
years). Edge decay is the core problem to solve next.
Report: reports/backtest_v8.1_2000-01-03_2025-12-31_full_v2_summary.json
Caveat: CON ticker downloaded after run start (1 of ~10k, immaterial).
Delisting exits = last traded price (optimistic for bankruptcies).
Universe still not perfectly point-in-time, but survivorship direction
is now captured rather than assumed.

## Next work, in execution order

1. [DONE] Corrected v8.1 baseline on survivor universe (3.47%).
2. [DONE] Delisted supplement download: 9,887 ok tickers snapshot.
3. [DONE] Momentum comparator: REJECTED on honest data (2.39%, -99.6%).
4. [DONE] v8.1 honest-universe baseline: 8.54% CAGR, -31.9% DD.
   This is THE reference line for all future experiments.
5. Next hypothesis (define gates BEFORE running). Evidence says:
   v8.1's edge lives in 2000-2006 small-cap momentum rebounds and has
   decayed since ~2014. Candidates: (a) earnings-guard on/off effect on
   honest universe, (b) turnover reduction (costs = $77.5k + slippage),
   (c) a trend/momentum overlay to exit the 2015-2025 flat regime.
6. Health gate PASSED (13 OK / 1 WARN: IBKR offline). Docs updated.
   -> Ask Architect about commit.

## Experiment and session discipline

- Separate simulator defects from investment hypotheses. A losing trade is
  not automatically a defect; an accurate lower return is progress.
- Report annual/rolling returns, drawdown and time underwater, exposure,
  turnover, actual accepted portfolio trades, costs and benchmark comparisons.
- Use chronological evaluation, parameter/cost sensitivity, and new forward
  observations. Previously inspected history is not an untouched holdout.
- Keep experiment counts bounded; do not promise monotonic improvement.
- Follow `.windsurfrules`: docs first, Python 3.10, standalone verification,
  health gate after core changes, full traceback logging, safe state handling.
- Keep temporary work in `temp/ws_*`; do not touch archived code or commit
  secrets, market data, or portfolio state. Preserve unrelated dirty files.
- Past commit/push approval was for the previous campaign, not blanket approval
  to trade real funds, subscribe to data, or deploy future changes.
- At handoff, update this checkpoint with files changed, commands/results,
  unresolved risks, and the exact next action. Never claim automatic monitoring
  or cross-session recall without an actual configured mechanism.

## Resume entry points

- `docs/V8_3_V8_4_V8_5_RESULTS.md`: corrected audit and required acceptance checks.
- `scripts/audit_backtest_data.py`: read-only local coverage inventory.
- `src/strategy_engine.py`: strategy parameters and shared decisions.
- `src/strategy_v7_2.py`: shared indicators.
- `src/smart_data_loader_factory.py`: Tiingo data loading.
- `scripts/daily_trading_loop.py`: actual paper execution path.
- `scripts/backtest_v8_1_vs_v8_7.py`: legacy defective portfolio builder for
  regression evidence, not a source of investment conclusions.

Do not execute the daily loop or notification-sending simulations merely to
resume context. Inspect logs and use isolated fixtures first.
