import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, str(ROOT))

from scripts.backtest_v8_vs_v8_1 import DATA_DIR, MIN_ROWS, build_spy_regime, calc_metrics, get_col, load_ticker
from scripts.research_cost_adjusted_v81 import ROUND_TRIP_COST_PCT, build_curve, load_sectors
import src.strategy_v8_1 as strategy


def main():
    started = time.time()
    sectors = load_sectors()
    spy = load_ticker(DATA_DIR / "SPY.parquet")
    if spy is None:
        raise RuntimeError("SPY.parquet is unavailable")
    spy_regime = build_spy_regime(spy)
    variants = {days: [] for days in (5, 10, 15, 20, 30)}
    files = sorted(DATA_DIR.glob("*.parquet"))
    for index, path in enumerate(files, 1):
        frame = load_ticker(path)
        if frame is None or len(frame) < MIN_ROWS or get_col(frame, ["adjClose", "Close", "close"]) is None:
            continue
        ticker = path.stem.upper()
        sector = sectors.get(ticker, "Unknown")
        for days in variants:
            strategy.TIME_STOP_DAYS = days
            trades = strategy.backtest_ticker_v8_1(ticker, frame, spy_sma200=spy_regime, sector=sector)
            for trade in trades:
                trade["sector"] = sector
            variants[days].extend(trades)
        if index % 300 == 0:
            counts = ", ".join(f"{days}d={len(variants[days])}" for days in variants)
            print(f"[RESEARCH] {index}/{len(files)} {counts}", flush=True)

    results = {}
    for days, trades in variants.items():
        adjusted = [{**trade, "pnl_pct": trade["pnl_pct"] - ROUND_TRIP_COST_PCT} for trade in trades]
        curve = build_curve(trades, spy_regime, ROUND_TRIP_COST_PCT)
        data = calc_metrics(curve, adjusted)
        data["time_stop_days"] = days
        data["time_stop_trades"] = sum(1 for trade in trades if trade.get("reason") == "Time stop")
        data["unknown_sector_trades"] = sum(1 for trade in trades if trade.get("sector") == "Unknown")
        results[str(days)] = data
        print(f"[RESEARCH] {days}d: {json.dumps(data)}", flush=True)

    output = ROOT / "logs" / f"time_stop_sensitivity_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.json"
    payload = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "results": results,
        "elapsed_seconds": round(time.time() - started, 1),
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[RESEARCH] Saved: {output}", flush=True)


if __name__ == "__main__":
    main()
