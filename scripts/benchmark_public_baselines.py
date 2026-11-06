import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
INITIAL_CAPITAL = 100000.0
MAX_POSITIONS = 10
ONE_WAY_COST_BPS = 10.0


def load_monthly_prices():
    series = {}
    for path in sorted(DATA_DIR.glob("*.parquet")):
        ticker = path.stem.upper()
        try:
            df = pd.read_parquet(path)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
            if not isinstance(df.index, pd.DatetimeIndex):
                continue
            column = next((name for name in ("adjClose", "Close", "close") if name in df.columns), None)
            if column is None:
                continue
            values = pd.to_numeric(df[column], errors="coerce").dropna()
            if values.index.tz is not None:
                values.index = values.index.tz_localize(None)
            values = values[~values.index.duplicated(keep="last")].sort_index()
            if len(values) < 300:
                continue
            monthly = values.resample("M").last()
            if len(monthly) >= 14:
                series[ticker] = monthly
        except Exception:
            continue
    if not series:
        raise RuntimeError("No eligible market data found")
    return pd.DataFrame(series).sort_index()


def load_sector_map():
    for name in ("sector_map.json", "ticker_metadata.json"):
        path = DATA_DIR / name
        if not path.exists():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            mapping = {}
            for ticker, value in raw.items():
                if isinstance(value, dict):
                    sector = value.get("sector")
                else:
                    sector = value
                if sector and "not available" not in str(sector).lower() and str(sector).lower() != "unknown":
                    mapping[str(ticker).upper()] = str(sector)
            if mapping:
                return mapping
        except Exception:
            continue
    return {}


def turnover(previous, current):
    tickers = set(previous) | set(current)
    return sum(abs(current.get(ticker, 0.0) - previous.get(ticker, 0.0)) for ticker in tickers)


def choose_weights(momentum, mode, sectors):
    valid = momentum.replace([np.inf, -np.inf], np.nan).dropna()
    valid = valid[valid > 0]
    if valid.empty:
        return {}
    if mode == "sector_neutral":
        selected = []
        used = set()
        for ticker in valid.sort_values(ascending=False).index:
            sector = sectors.get(ticker)
            if not sector or sector in used:
                continue
            selected.append(ticker)
            used.add(sector)
            if len(selected) == MAX_POSITIONS:
                break
        if len(selected) < MAX_POSITIONS:
            for ticker in valid.sort_values(ascending=False).index:
                if ticker not in selected:
                    selected.append(ticker)
                    if len(selected) == MAX_POSITIONS:
                        break
    else:
        selected = list(valid.nlargest(MAX_POSITIONS).index)
    return {ticker: 1.0 / len(selected) for ticker in selected} if selected else {}


def run_strategy(prices, mode, sectors):
    returns = prices.pct_change(fill_method=None)
    equity = INITIAL_CAPITAL
    previous = {}
    curve = []
    for index in range(13, len(prices) - 1):
        signal_date = prices.index[index]
        next_date = prices.index[index + 1]
        momentum = prices.iloc[index - 1] / prices.iloc[index - 12] - 1.0
        weights = choose_weights(momentum, mode, sectors)
        period_returns = returns.iloc[index + 1]
        gross_return = sum(
            weight * (-1.0 if pd.isna(period_returns.get(ticker)) else float(period_returns.get(ticker)))
            for ticker, weight in weights.items()
        )
        cost = turnover(previous, weights) * ONE_WAY_COST_BPS / 10000.0
        net_return = gross_return - cost
        equity = max(0.0, equity * (1.0 + net_return))
        curve.append((next_date, equity, net_return, len(weights), cost))
        previous = weights
    return curve


def run_spy(prices):
    if "SPY" not in prices:
        raise RuntimeError("SPY data not found")
    values = prices["SPY"].dropna()
    values = values[values.index >= prices.index[min(13, len(prices) - 1)]]
    equity = INITIAL_CAPITAL
    curve = []
    bought = False
    for date, value in values.items():
        if not bought:
            equity *= 1.0 - ONE_WAY_COST_BPS / 10000.0
            start = value
            bought = True
        else:
            equity = INITIAL_CAPITAL * (1.0 - ONE_WAY_COST_BPS / 10000.0) * value / start
        curve.append((date, equity, 0.0, 1, 0.0))
    return curve


def metrics(curve):
    if len(curve) < 2:
        return {}
    dates = pd.DatetimeIndex([item[0] for item in curve])
    equity = pd.Series([item[1] for item in curve], index=dates)
    monthly = equity.pct_change(fill_method=None).dropna()
    years = max((dates[-1] - dates[0]).days / 365.25, 1 / 12)
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if equity.iloc[-1] > 0 else -1.0
    drawdown = equity / equity.cummax() - 1
    sharpe = math.sqrt(12) * monthly.mean() / monthly.std() if monthly.std() > 0 else 0.0
    downside = monthly[monthly < 0].std()
    sortino = math.sqrt(12) * monthly.mean() / downside if downside and downside > 0 else 0.0
    return {
        "start": dates[0].date().isoformat(),
        "end": dates[-1].date().isoformat(),
        "years": round(years, 2),
        "final_equity": round(float(equity.iloc[-1]), 2),
        "total_return_pct": round((float(equity.iloc[-1]) / INITIAL_CAPITAL - 1) * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "max_drawdown_pct": round(float(drawdown.min()) * 100, 2),
        "sharpe": round(float(sharpe), 3),
        "sortino": round(float(sortino), 3),
        "positive_months_pct": round(float((monthly > 0).mean()) * 100, 2),
        "rebalance_periods": len(monthly),
    }


def main():
    print("[BENCHMARK] Loading repaired market data", flush=True)
    prices = load_monthly_prices()
    sectors = load_sector_map()
    common_start = prices.notna().sum(axis=1)
    prices = prices.loc[common_start[common_start >= 100].index.min():]
    results = {
        "generated_at": datetime.now().isoformat(),
        "method": "monthly 12-1 momentum, top 10 equal weight, 10 bps one-way turnover cost",
        "limitations": [
            "Current ticker universe may introduce survivorship bias",
            "Monthly bars do not model intramonth execution or market impact",
            "Results are research baselines, not expected live returns",
        ],
        "universe_size": int(prices.shape[1]),
        "sector_coverage": len(sectors),
        "strategies": {},
    }
    strategies = {
        "spy_buy_hold": run_spy(prices),
        "momentum_top10": run_strategy(prices, "momentum", sectors),
        "sector_neutral_momentum": run_strategy(prices, "sector_neutral", sectors),
    }
    for name, curve in strategies.items():
        results["strategies"][name] = metrics(curve)
        print(f"[BENCHMARK] {name}: {results['strategies'][name]}", flush=True)
    output = LOG_DIR / f"public_baselines_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"[BENCHMARK] Saved: {output}", flush=True)


if __name__ == "__main__":
    main()
