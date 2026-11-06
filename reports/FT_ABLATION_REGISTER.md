# Freedom Trader Ablation Register (pre-registered 2026-10-26)

Goal: determine which FT rule elements carry measurable edge, on the corrected
ledger/execution model, BEFORE running. All trials identical:

- Snapshot: data/research/snapshot_1998_20261022 (frozen, sha256 manifest)
- Window: 2000-01-03 -> 2025-12-31; $100k start; 5bps slippage +
  $0.005/sh ($1 min); T+1; long-only cash-only
- Universe: full 9,887-ticker honest universe (delistings included)
- Baseline comparator: corrected v8.1 engine run (tag integrity_fix)
- FT baseline: --strategy freedom with no ablations

## Single-element ablations (each run disables exactly one gate)

| # | Ablation flag | Element disabled |
|---|---------------|------------------|
| 1 | weekly      | Weekly Stoch(19,4,4) 32-80 gate |
| 2 | power       | 80+ power-stock weekly override |
| 3 | trapdoor    | %K<%D gap >6 / falling-%D vetoes |
| 4 | flagpole    | 4 green bars & 4d >8% veto |
| 5 | snapback    | >8% above SMA25 veto |
| 6 | candle      | Bullish candle confirmation gate |
| 7 | structure   | W-break / staircase / close>SMA25 gate |
| 8 | barrier     | SMA overhead-clearance veto + barrier targets |
| 9 | retracement | 50%-retracement limit routing on wide bars |
| 10 | breakeven  | +2% breakeven ratchet |
| 11 | rollover    | Stoch rollover exit (K>80, K<D) |
| 12 | conviction  | LOW/MED/HIGH sizing -> flat 10% |
| 13 | cashbuffer  | 20% equity cash buffer -> 0% |

Interpretation: if disabling an element IMPROVES CAGR/DD vs FT baseline,
that element was dead weight or harmful; if it DEGRADES results, the
element carries edge.

## Phase 2 (conditional)

Pairwise combinations only among elements shown to help, plus elements
weak alone that plausibly interact (e.g. barrier+retracement). Select on
the return/drawdown Pareto front; no single-metric cherry-pick.

Caveats: all history is inspected data, not an untouched holdout; multiple
comparisons inflate the best observed result. Forward paper evidence is
required before any promotion to DEFAULT_VERSION.

## Phase 3: FT elements as v8.1 overlays (user-selected 2026-10-30)

FT-full baseline corrected result: 0.77% CAGR, PF 0.981 (<1) - the
combined rulebook has no standalone edge. Pivot: test the four most
mechanistic FT elements as modifications to v8.1 (10.76% CAGR baseline),
via src/v81_overlay_comparator.py hooks (--strategy overlay --overlays).

Pre-registered trials (identical window/costs/universe, tag ov_*):

| # | Overlays enabled | Hypothesis |
|---|------------------|------------|
| 1 | breakeven        | +2% ratchet cuts avg loser size |
| 2 | cashbuffer       | 20% equity cash floor cuts maxDD |
| 3 | retracement      | 50% limit entries improve avg fill |
| 4 | vetoes           | flagpole+snapback+trapdoor cut bad entries |
| 5 | all four         | combined effect for Pareto check |

Gate: an overlay helps only if it improves CAGR OR maxDD vs the 10.76%/
-33.6% integrity_fix baseline without collapsing the other metric.
Verify: scripts/verify_overlay.py (10 fixture tests, Exit 0).

## Phase 4: comparability fix + forensics campaign (2026-11-05)

COMPARABILITY DEFECT FOUND: re-baselined v8.1 under current code =
11.93%/-34.2%/PF 1.089 (integrity_fix2) - BYTE-IDENTICAL to the
'breakeven' overlay run. decision_frame ATR scaling changed between the
old baseline and overlay runs; the breakeven hook was a no-op (check_exits
never reads stop_loss_price). ALL overlay results are re-read vs 11.93%:
breakeven = no-op; vetoes/cashbuffer/retracement/all-four = REJECTED.
FT branch closed at high confidence.

v8.10 (stoch floor 32->60, forensics quartile hypothesis): 6.94% CAGR,
-43.4% DD - REJECTED. Per-trade edge did not survive portfolio selection.

Forensics campaign (scripts/analyze_trades.py on integrity_fix trades):
- entry %K quartile monotone (K<48 PF 0.85; K>72 PF 1.82) -> v8.10 REJECTED
- top-quartile 1yr momentum (+182%+) = +$1.27M/PF 1.55 -> v8.11 test
- losses = 63% ATR stops + 28% time stops; edge = regime-dependent
  right-tail convexity, not stable per-trade expectancy

Phase-4 trials (tag campaign1, honest universe, identical costs):
| # | Version | Change | Hypothesis |
|---|---------|--------|------------|
| 1 | v8.11  | CAGR_MIN 0.15->1.00 | top-tail momentum gate |
| 2 | v8.1.1 | TRAILING_STOP_MULT 2.0 (+mom 2%, tstop 15) | exit-side loss-tail fix |
| 3 | v8.5   | PARTIAL_ENABLED half-out at K>80 rollover | bank wins earlier |

Reference: v8.1 integrity_fix2 = 11.93%/-34.22%/PF 1.089/41.1%.
