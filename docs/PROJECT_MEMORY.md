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

## Integrity correction and combination-search checkpoint (2026-10-29)

User requested individual Freedom rules, shared-concept parameter alternatives,
and concurrent combination search to target ~20% CAGR / ~30% drawdown. This
campaign is NOT complete and no optimal configuration has been established.

Before launching search, confirmed stale holdings invalidate prior comparative
verdicts: FT finished holding HSH (last bar 2014), CPGX/RAX (2016), NLSN
(2022), occupying all four slots. v8.1 full_v2 also retained BRL (2008), CRV
(2015), BIOP (2017), PRVB/TRHC (2023). Missing bars did not automatically
queue exits; forced liquidation only handled ALREADY pending orders. Therefore
post-2014 flat performance is not established evidence of edge decay. Prior
statements that Mo's edge must be discretionary are unsupported and withdrawn.
FT's 0.50% and v8.1's 8.54% remain historical outputs, NOT validated ranking
or promotion evidence pending corrected reruns.

Additional FT defects: ascending allocation sorting prioritized low conviction;
FT stop/target state was not split-adjusted. Fixed these plus missing-bar exit
queueing in src/backtest_engine.py and the comparator. Existing 20-session
retry / last-observed-price liquidation remains optimistic, not actual
delisting proceeds. All affected historical runs need rerunning with identical
assumptions. scripts/verify_freedom_integrity.py reproduces missing-bar and
split-state failures and checks shared queue deduplication.

v8.9 prior output: 8.12% CAGR, -30.35% maxDD, PF 1.151, $757,434.80 final.
Fails its CAGR gate versus prior reference; also requires integrity rerun.
Research manifest reports universe_count=1 despite 9,887 loaded tickers;
runner benchmark uses full warmup history instead of slicing the measured
window. Audit/fix provenance and benchmark dates before new comparisons.

Measured environment: Python 3.10.9, 6 logical CPUs, 16GB RAM, only ~3.4GB
available before research jobs. No full-universe research process was active.
Do NOT launch several ~4GB workers. Next: finish integrity verification,
implement reusable read-only feature/cache preparation with exact-equivalence
and no-lookahead tests, measure peak memory, then resource-capped workers.
Search must register finite rule/parameter domains, baseline and individual
ablations first, then pairwise/interactions (including rules weak alone),
record all trials and select return/drawdown Pareto candidates rather than
one lucky full-history maximum. Historical chronological validation is already
inspected data, not an untouched holdout; forward paper evidence is required.
No production default, v8.1 parameters, snapshot, or portfolio changed.
Verification after fixes: verify_freedom_integrity.py (3 tests), verify_ledger.py,
verify_backtest_corrected.py, verify_prefilter.py all Exit 0. Functional health
check Exit 0: 13 PASS / 1 WARN (IBKR offline) / 0 FAIL. git diff --check Exit 0
with line-ending warnings only. These fixture checks do not replace corrected
full-universe reruns. No combination campaign or corrected full run launched.

## Integrity-fixed rerun results (2026-10-29, in progress)

- v8.1 engine, honest 9,887-ticker universe, identical costs/window:
  reports/backtest_v8.1_2000-01-03_2025-12-31_integrity_fix_summary.json
  CAGR 10.76% (was 8.54% pre-fix), final $1,417,188, maxDD -33.6%
  (2015-06-18 -> 2020-05-28), PF 1.135, win rate 40.5%, 4,740 entries,
  fees $123.3k, SPY same window 8.05%. THIS is the new reference line.
- FT on Mo's 15-name watchlist + SPY (corrected): CAGR 1.58%, maxDD -7.94%,
  PF 1.416, win rate 55.3%, avg 0.58 positions - still far below the
  Gemini document's claimed 16.92% CAGR.
- Report filenames now include strategy prefix (backtest_freedom_*) to
  avoid overwriting engine reports; --tickers added (SPY always kept for
  calendar/benchmark); --ft-disable ablation toggles added to
  FreedomTraderComparator (13 registered elements, see
  reports/FT_ABLATION_REGISTER.md pre-registration).
- FT gate vectorized: per-ticker cached float32 (k1, vol_sma30) arrays
  replace per-day slice loops; verified numerically identical vs old math.
- FT honest-universe rerun: in progress at checkpoint time.

## Active research execution checkpoint (2026-10-29)

User authorized continuing unattended research and specifically chose to LET
existing PID 25148 (tag integrity_fix) finish rather than terminate it. It
subsequently finished; an existing Freedom integrity_fix process PID 11660
also finished. Their older runner versions did not fingerprint sources at
startup, so do not substitute them for the newly frozen-code comparisons.

Additional dimensional-integrity fix: engine previously compared raw prices
and entry values against adjusted SMAs/ATR (AAPL 2000-01-03 raw $111.94,
adjusted ATR $0.039). BacktestData.decision_frame now scales dimensional
adjusted fields to the current raw-price basis, preserving return ratios.
Shared engine receives that consistent research view; fills/ledger stay raw.
v8.1 PARAMS and production default/path are unchanged. Production parity for
this loader correction is unresolved and explicitly disclosed in reports.
Freedom feature generation now uses continuous adjusted OHLC for indicators
and rescales price-dimensional outputs to each bar's raw basis; its cheap
stochastic gate uses the same adjusted OHLC arrays.

Speed/memory changes: numpy arrays own only needed columns instead of keeping
entire pandas blocks alive; optional content-hashed indicator parquet cache
outside the immutable snapshot; bounded 64-frame runner cache; vectorized
candidate schedules; numeric nanosecond comparisons in daily pointer loops.
The old scalar prefilter remains as an equivalence oracle. Cache key includes
source price bytes and indicator source hash. FT cache includes comparator
source. Cache writes use process-unique temporary files and atomic replace.

Verification after these changes: health Exit 0 (13 PASS, 1 IBKR-offline WARN),
verify_freedom_integrity.py 4 tests, verify_research_cache.py 5 tests,
verify_ledger.py, verify_backtest_corrected.py, verify_prefilter.py all Exit 0.
New verify_research_baselines.py: 2 tests Exit 0. Tests cover adjusted-scale
invariance, truncated completed-week features, cached/uncached replay equality,
all-session scalar/scheduled prefilter equality on the fixture, and forced
liquidation with settlement. These do not establish strategy profitability.

RUNNING: shell 834557, scripts/run_research_baselines.py campaign
frozen_integrity_20261029 (after integrity_smoke_v2_20261029 completed all 3
smoke jobs with Exit 0). Full v8.1 started PID 23832 at 15:43:30; Freedom
and v8.9 are queued, maximum 2 workers, 1.5GB free-RAM reserve plus measured
worker budget, wait for first worker day-0 before considering another launch.
Single BLAS threads and BELOW_NORMAL Windows priority. Supervisor checks logs
for tracebacks/ERROR/CRITICAL, records peaks/status atomically in
reports/research_baselines_frozen_integrity_20261029.json, logs per job under
logs/research_frozen_integrity_20261029_{v81,freedom,v89}.log.
Expected result tags: frozen_integrity_20261029_v81, _freedom, _v89.

FREEZE CORE SOURCE while these jobs run: runner hashes research source before
replay and rejects a run if hashes change before completion. New unrelated
verification scripts/docs may be edited, but not the six hashed sources.
Runner now fixes SPY measured dates using adjusted-close total returns,
discloses benchmark costs absent, and records actual loaded ticker count,
manifest/ticker hashes, source hashes and exact strategy params. Original
manifest's universe_count=1 is preserved as a declared-count discrepancy;
actual successful records count is 9,887. Snapshot is not rewritten.

RUNNING: shell 6832e6, verify_snapshot_fingerprints.py, streaming checksums
against ALL successful manifest records; report
reports/snapshot_fingerprints_20261029.json. At 1,000 files: zero mismatches.
Independent tiny runner smoke (tag unit_basis_smoke_20261029) Exit 0; further
benchmark arithmetic reconciliation pending.

Still pending: full run completion, independent equity/trade reconciliation,
actual full-universe speed/memory measurement, rule/parameter search in shared
engine, bounded concurrent interactions, chronological/cost validation and
final verdict. Existing reports/FT_ABLATION_REGISTER.md specifies 13 FT
ablation groups; no full combination campaign has been launched. Do not
claim an optimal strategy, target achievement, or research completion.

## Campaign verdicts and forensics (2026-11-05)

Comparability: decision_frame ATR->raw scaling changed between the first
integrity_fix baseline and the overlay runs. RE-BASELINE integrity_fix2
(current code): v8.1 = 11.93% CAGR, -34.22% DD, PF 1.089, 41.1% wins,
$1,861,762 - byte-identical to the 'breakeven' overlay run. Breakeven
ratchet is a NO-OP: check_exits never reads pos['stop_loss_price'], and
the engine's real ratchet (v8.9 BREAKEVEN_AT_PCT on highest_price) was
never triggered by the overlay hook. Re-verdicts vs 11.93%: ALL overlays
REJECTED (vetoes 9.91, cashbuffer 9.34, retracement 8.58, all-four 10.10).
FT corrected reruns: honest universe 0.77% CAGR/PF 0.981; watchlist 1.58%.
FT branch closed - no element adds value to v8.1.

scripts/analyze_trades.py: per-trade forensics (entry-day feature joins)
-> reports/forensics_v81_trades.csv. Signals found: entry-%K quartiles
monotone (K<48 PF 0.85; K>72 PF 1.82); top-quartile 1yr momentum
+$1.27M/PF 1.55; losses = 63% ATR stops + 28% time stops; top-3 winners
decide most years (regime-dependent convexity, NOT stable expectancy).

Pre-registered single-change tests, honest universe, identical costs,
ALL REJECTED vs 11.93% baseline:
- v8.10 STOCH_LOW 60: 6.94%/-43.4% (per-trade edge died in portfolio
  selection: entries rose to 4,773, win rate flat).
- v8.11 CAGR_MIN 1.00: 5.26%/-51.6% (momentum gate, worst drawdown).
- v8.1.1 TRAILING_STOP_MULT 2.0: 10.05%/-40.2%/PF 1.105.
- v8.5 PARTIAL_ENABLED: 6.13%/-43.1%.
CONCLUSION: neither tighter entries nor tighter exits beat plain v8.1.
The ~12% ceiling resists single-param tuning; the post-2015 decay is a
regime-convexity problem. Reaching ~20% needs a different engine
hypothesis and/or forward paper evidence on post-snapshot data.

## NextGen momentum engine campaign (2026-11-06): FAMILY DEAD

User-directed pivot to a literature-grounded engine (J-T 12-1 momentum,
MOP time-series momentum, PEAD, vol regime, inverse-ETF shorts) in
src/nextgen_comparator.py. Phase 0 added 11 ETFs to snapshot (9,898 ok).

ALL variants REJECTED catastrophically on honest universe:
- ng_a naive: 0.63% CAGR, -99.97% DD ($405M 2013 spike = DATA POISON:
  ZXZZT fake +199-billion-% bar, $0 prices, zero-vol names; response:
  min_price/|1d ret|>10x/zero-vol-share hygiene gates + exclude_tickers).
- ng_a2 clean: -20.89%, -99.86%, PF 0.95, $229 - loses relentlessly.
- ng_b +tsmom_gate: -19.43%, $368 - gate no help.
- ng_c +inverse book: -21.54%, $184 - shorts no help either.
NG-D..J (vol sizing, PEAD, trailing, combos) NOT RUN on a dead base.
A concentrated top-10 momentum book on this universe is a systematic
top-buyer; the academic decile effect needs hundreds of liquid names.

VERDICT after ~23 controlled experiments across 2 engine families
(FT + momentum): v8.1 = 11.93% CAGR/-34.2%/PF 1.089 is THE ONLY
validated system. Engine is at src/nextgen_comparator.py with
verify_nextgen.py (6 tests Exit 0) and NG_REGISTER.md - kept for any
future hypothesis, not for promotion.
Health gate Exit 0 (13 PASS, 1 IBKR-offline WARN). New code:
STOCH_LOW/HIGH and CAGR_MIN version-param overrides in scan_universe,
src/v81_overlay_comparator.py, scripts/verify_overlay.py (10 tests),
--tickers/--overlays/--ft-disable runner options, strategy-prefixed
report filenames. Verify suite all Exit 0.

## Live tracking phase (2026-11-06)

v8.1 FORWARD-VALIDATED out-of-sample: +11.36% total (14.3% ann.) on
untouched 2026-01-02..10-22 data, -19.4% DD, 178 trades. Production runs
v8.6 (v8.1 + earnings guard) - same engine. Committed 816bead + eec0e26.

IB Gateway fix: port stayed closed for 3 days (orchestrator timeouts).
Root cause = TWS persisted LocalServerPort=4000; auto_tws_manager now
forces 7497 in jts.ini pre-launch + user unchecked Read-Only API in GUI.
Health check now 14/14 PASS with port open. Task Scheduler task
VolatilityHunter_Daily_Live runs ~16:06 local next trading day (Mon
11/9). User wants several weeks of paper tracking of the live engine.

## Next work, in execution order

1. [DONE] Corrected v8.1 baseline on survivor universe (3.47%).
2. [DONE] Delisted supplement download: 9,887 ok tickers snapshot.
3. [DONE] Momentum comparator: REJECTED on honest data (2.39%, -99.6%).
4. [DONE] v8.1 honest-universe baseline: 8.54% CAGR, -31.9% DD.
   This is THE reference line for all future experiments.
5. [DONE] v8.8 experiment (REGIME_MAX_POS=0, pre-registered gates):
   REJECTED - CAGR 8.41% vs 8.54%, maxDD -42.1% vs -31.9%. Bear entries
   were few but removing them also removed profitable re-entries.
6. [DONE] Freedom Trader audit + backtest (user's master handoff doc):
   v8.1 shares DNA (stoch 32-80, SMA200, power stocks, earnings guard)
   but is NOT Freedom Trader. Ported the full deterministic spec to
   src/freedom_trader_comparator.py (long-only; shorts need margin -
   ledger forbids by design; intraday/spread/earnings not testable on
   daily data). RESULTS: FT long on 9,887-ticker universe = 0.50% CAGR,
   -23.5% DD, $114k. FT on Mo's own 19-name watchlist = 1.05% CAGR,
   -11.2% DD, $131k. The mechanical rules produce near-zero alpha;
   whatever edge exists in his live trading is discretionary, not in
   the written rules. REJECTED as a replacement; individual elements
   may still be worth isolated tests (breakeven ratchet, conviction
   sizing) but no evidence yet they add edge.
7. FULL PICTURE (honest universe, 2000-2025, identical costs):
   v8.1 8.54%/-31.9% | v8.8 8.41%/-42.1% REJECTED | momentum 2.39%/
   -99.6% REJECTED | FT-long 0.50%/-23.5% REJECTED | SPY 7.78%.
   v8.1 remains the best measured system - still ~11.5pp short of
   the 20% goal. Verdict delivered to user.
8. Health gate PASSED (13 OK / 1 WARN: IBKR offline). Docs updated.
   Committed + pushed foundation (4d3cf5b). Next: commit experiments
   or continue bounded hypothesis loop toward 20%.

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
