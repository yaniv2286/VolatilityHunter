# NextGen Engine Register (pre-registered 2026-11-06)

Literature-grounded engine family in src/nextgen_comparator.py, run via
`--strategy nextgen --ng-config '{...}'`. Same corrected ledger, fills,
costs, frozen snapshot as all prior campaigns.

Reference baseline: v8.1 integrity_fix2 = **11.93% CAGR, -34.22% maxDD,
PF 1.089, 41.1% win** (reports/backtest_v8.1_..._integrity_fix2_summary.json).

Fixed conditions: snapshot_1998_20261022 (now 9,898 ok tickers incl. new
inverse/vol ETFs), 2000-01-03 -> 2025-12-31, $100k, 5bps + $0.005/sh
($1 min), T+1. Acceptance: CAGR >= 15% AND maxDD <= 30% (user target);
a run "helps" if it beats baseline CAGR or cuts DD >=3pp at equal CAGR.

## Registered configs

| Tag | Config delta vs DEFAULT_CFG | Hypothesis |
|-----|------------------------------|------------|
| ng_a | {} (top-10, mom12_1, monthly, fixed 10% frac, 20% hard stop, cash bear) | clean cross-sectional momentum baseline |
| ng_a2 | {} under hygiene-enabled engine | NG-A retest after data-poison fix |
| ng_b | {"tsmom_gate": true} | time-series momentum gate improves regime behavior (MOP) |
| ng_c | {"tsmom_gate": true, "bear_mode": "inverse", "inverse_level": 1, "inverse_alloc": 0.30} | inverse ETFs monetize bear regimes |
| ng_d | {"tsmom_gate": true, "sizing": "vol_target", "risk_pct": 0.01, "per_pos_cap": 0.15} | vol-target sizing improves Sharpe |
| ng_e | {"tsmom_gate": true, "bear_mode": "inverse", "inverse_alloc": 0.30, "sizing": "vol_target", "risk_pct": 0.01, "per_pos_cap": 0.15} | combined sleeves |
| ng_f | {"pead": true} | gap-event drift adds event alpha (PEAD) |
| ng_g | {"pead": true, "tsmom_gate": true} | PEAD only inside momentum winners |
| ng_h | {"trailing_atr": 3.0, "tsmom_gate": true} | ATR trailing on winners (loss-tail fix) |
| ng_i | {"sizing": "vol_target", "risk_pct": 0.02, "per_pos_cap": 0.15, "tsmom_gate": true} | higher risk budget vol sizing |
| ng_j | best Phase-1/2 combination | Pareto selection |

Interpretation rules: identical to prior registers - a config must beat
the baseline on CAGR or maxDD without collapsing the other; no
single-metric cherry-pick; all results logged below.

## Results

| Tag | CAGR | maxDD | PF | Win% | Verdict |
|-----|------|-------|----|------|---------|
| ng_a | 0.63% | **-99.97%** | 1.286 | 40.2% | REJECTED (catastrophic) |
| ng_a2 | **-20.89%** | **-99.86%** | 0.95 | 43.2% | REJECTED (worse than dirty) |
| ng_b | **-19.43%** | **-99.77%** | 0.958 | 43.7% | REJECTED (tsmom gate no help) |
| ng_c | **-21.54%** | **-99.89%** | 0.944 | 41.5% | REJECTED (inverse book no help) |

## CAMPAIGN VERDICT (2026-11-06): MOMENTUM FAMILY DEAD

All three structural variants wipe out (<$400 final equity, -99.8%+ DD):
- NG-A2 clean data loses RELENTLESSLY (PF 0.95) - the 2013 $405M spike
  in NG-A was data poison, not alpha.
- tsmom gate (NG-B): no effect, same death spiral.
- inverse book (NG-C): no effect - long book bleeds even in bulls.
- Root cause: concentrated top-10 momentum book on junk-inclusive
  universe = systematic top-buyer. The academic decile effect needs
  hundreds of diversified liquid names we can't run at this scale.
- NG-D through NG-J (vol sizing, PEAD, ATR trail, combos): NOT RUN -
  base engine already rejected; no point layering on a dead base.
- v8.1 (11.93%/-34.2%/PF 1.089) remains the ONLY validated system after
  ~23 controlled experiments across 2 engine families.

## Phase 1.5: portfolio-scale momentum (user-directed 2026-11-06)

NG-A's failure mode was concentration: top-10 book on junk-inclusive
universe. Literature runs decile books of hundreds of liquid names.
Retest at proper scale: bigger books, liquidity floor, smaller caps.

| Tag | Config delta | Hypothesis |
|-----|--------------|------------|
| ng_d1 | top_n=50, decay_mult=1.6, per_pos_cap=0.02, min_dollar_vol=2e7, tsmom_gate=true, cash_buffer=0.02 | 50-name liquid book |
| ng_d2 | top_n=100, decay_mult=1.5, per_pos_cap=0.01, min_dollar_vol=5e7, tsmom_gate=true, cash_buffer=0.02 | 100-name liquid book (closest to academic form) |
| ng_d3 | ng_d2 + bear_mode=inverse, inverse_level=1, inverse_alloc=0.30 | + inverse bear sleeve |

Results: ng_d1 -8.83%/-93.6%/PF 0.972 | ng_d2 -6.24%/-86.2%/PF 0.981 |
ng_d3 -7.7%/-90.5%/PF 0.941. ALL REJECTED. Scaling 10->100 positions
raised PF 0.95->0.98 (near breakeven) - concentration WAS the killer -
but the raw momentum signal has no edge on this universe; inverse
sleeve hurt again. Momentum family closed for good at 27+ experiments.
v8.1 11.93%/-34.2% remains the only validated system.

## Phase 3: ETF dual-momentum rotation (2026-11-06) - REJECTED

19-instrument universe (sector SPDRs + index ETFs + TLT/GLD shelter),
monthly nextgen engine. top1 -0.03%, top2 +0.91%, top3 +2.38% CAGR.
Win rate improved with diversification (top3 60%, PF 1.22 - best PF of
campaign) but monthly ETF rotation too slow. Third family closed.
~30 experiments, 3 families, all dead vs v8.1.

NG-A autopsy: +$385M in 2013 (momentum melt-up captured), -$183M in 2014
(real momentum crash), finished $117k. Junk data: ZXZZT fake +199-billion-%
bar, $0 prices, zero-volume names in rankings. Response: hygiene gates in
_metrics (min_price 1.0, |1d ret|>10x untradeable, >10% zero-vol days skip,
exclude_tickers cfg). NG-A's naive spec is invalid; ng_a2 is the clean
retest. Note: momentum edge was REAL (2013) - the question is whether
hygiene + gates + inverse book can keep it without the wipeout.
