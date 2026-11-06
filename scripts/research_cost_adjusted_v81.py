import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, str(ROOT))

from scripts.backtest_v8_vs_v8_1 import (
    DATA_DIR,
    INITIAL_CAPITAL,
    MIN_ROWS,
    POSITION_SIZE_PCT,
    REGIME_MAX_POS,
    SECTOR_MAX,
    build_spy_regime,
    calc_metrics,
    get_col,
    load_ticker,
)
from src.strategy_v8_1 import backtest_ticker_v8_1

ROUND_TRIP_COST_PCT = 0.20


def load_sectors():
    for name in ("sector_map.json", "ticker_metadata.json"):
        path = DATA_DIR / name
        if not path.exists():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            result = {}
            for ticker, value in raw.items():
                sector = value.get("sector") if isinstance(value, dict) else value
                if sector and str(sector).lower() != "unknown" and "not available" not in str(sector).lower():
                    result[str(ticker).upper()] = str(sector)
            if result:
                return result
        except Exception:
            continue
    return {}


def build_curve(trades, spy_regime, cost_pct, exclude_unknown=False):
    ordered = sorted(trades, key=lambda trade: trade["entry_date"])
    if not ordered:
        return pd.Series(dtype=float)
    equity = INITIAL_CAPITAL
    high_water = equity
    active = []
    curve = [(ordered[0]["entry_date"], equity)]

    def close_positions(current_date):
        nonlocal equity
        remaining = []
        for position in active:
            if position["exit_date"] <= current_date:
                net_pnl = position["pnl_pct"] - cost_pct
                equity += position["allocated"] * net_pnl / 100.0
                curve.append((position["exit_date"], equity))
            else:
                remaining.append(position)
        active[:] = remaining

    for trade in ordered:
        close_positions(trade["entry_date"])
        high_water = max(high_water, equity)
        drawdown = (equity - high_water) / high_water if high_water else 0.0
        drawdown_scale = 0.25 if drawdown < -0.20 else 0.50 if drawdown < -0.10 else 1.0
        entry_date = pd.Timestamp(trade["entry_date"])
        is_bull = bool(spy_regime.get(entry_date, True)) if not spy_regime.empty else True
        max_positions = 10 if is_bull else REGIME_MAX_POS
        if len(active) >= max_positions:
            continue
        sector = trade.get("sector", "Unknown")
        if exclude_unknown and sector == "Unknown":
            continue
        if sector != "Unknown" and sum(1 for position in active if position["sector"] == sector) >= SECTOR_MAX:
            continue
        atr_pct = float(trade.get("atr_pct", 0.02) or 0.02)
        active_atrs = [float(position.get("atr_pct", 0.02) or 0.02) for position in active]
        median_atr = float(np.median(active_atrs)) if active_atrs else atr_pct
        volatility_scale = min(max(median_atr / atr_pct, 0.5), 1.5) if atr_pct > 0 else 1.0
        allocated = min(equity * POSITION_SIZE_PCT * drawdown_scale * volatility_scale, equity)
        if allocated <= 0:
            continue
        active.append({
            "exit_date": trade["exit_date"],
            "pnl_pct": trade["pnl_pct"],
            "allocated": allocated,
            "sector": sector,
            "atr_pct": atr_pct,
        })
        curve.append((trade["entry_date"], equity))

    for position in sorted(active, key=lambda item: item["exit_date"]):
        net_pnl = position["pnl_pct"] - cost_pct
        equity += position["allocated"] * net_pnl / 100.0
        curve.append((position["exit_date"], equity))

    return pd.Series(
        [value for _, value in curve],
        index=pd.to_datetime([date for date, _ in curve]),
    ).sort_index()


def main():
    started = time.time()
    sector_map = load_sectors()
    spy = load_ticker(DATA_DIR / "SPY.parquet")
    if spy is None:
        raise RuntimeError("SPY.parquet is unavailable")
    spy_regime = build_spy_regime(spy)
    trades = []
    files = sorted(DATA_DIR.glob("*.parquet"))
    for index, path in enumerate(files, 1):
        frame = load_ticker(path)
        if frame is None or len(frame) < MIN_ROWS or get_col(frame, ["adjClose", "Close", "close"]) is None:
            continue
        ticker = path.stem.upper()
        sector = sector_map.get(ticker, "Unknown")
        ticker_trades = backtest_ticker_v8_1(ticker, frame, spy_sma200=spy_regime, sector=sector)
        for trade in ticker_trades:
            trade["sector"] = sector
        trades.extend(ticker_trades)
        if index % 300 == 0:
            print(f"[RESEARCH] {index}/{len(files)} files, {len(trades)} trades", flush=True)

    gross_curve = build_curve(trades, spy_regime, 0.0)
    net_curve = build_curve(trades, spy_regime, ROUND_TRIP_COST_PCT)
    known_sector_curve = build_curve(trades, spy_regime, ROUND_TRIP_COST_PCT, exclude_unknown=True)
    gross = calc_metrics(gross_curve, trades)
    net_trades = [{**trade, "pnl_pct": trade["pnl_pct"] - ROUND_TRIP_COST_PCT} for trade in trades]
    known_sector_trades = [trade for trade in net_trades if trade.get("sector") != "Unknown"]
    net = calc_metrics(net_curve, net_trades)
    known_sector_only = calc_metrics(known_sector_curve, known_sector_trades)
    unknown_trades = sum(1 for trade in trades if trade.get("sector") == "Unknown")
    result = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        "sector_coverage": len(sector_map),
        "total_trades": len(trades),
        "unknown_sector_trades": unknown_trades,
        "gross": gross,
        "cost_adjusted": net,
        "known_sector_only": known_sector_only,
        "elapsed_seconds": round(time.time() - started, 1),
    }
    output = ROOT / "logs" / f"cost_adjusted_v81_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    print(f"[RESEARCH] Saved: {output}", flush=True)


if __name__ == "__main__":
    main()
