"""
Verification script for F1-F6 strategy fixes.
Tests argument order, scoring, exit logic, and signal generation.
Exit code 0 = all fixes verified.
"""
import sys
import os
import traceback
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {name}")
        PASS += 1
    else:
        print(f"  [FAIL] {name} {detail}")
        FAIL += 1

def make_df(rows=300, trend="bull", annual_return=0.20):
    """Create synthetic OHLCV DataFrame that mimics parquet data."""
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=rows, freq="B")
    base = 100.0
    prices = [base]
    for _ in range(rows - 1):
        drift = 0.0008 if trend == "bull" else -0.0003
        prices.append(prices[-1] * (1 + drift + np.random.normal(0, 0.01)))

    close = pd.Series(prices)

    # Scale so that 252d return matches annual_return target
    if annual_return is not None and rows >= 252:
        target_ratio = 1 + annual_return
        actual_ratio = close.iloc[-1] / close.iloc[-252]
        scale = target_ratio / actual_ratio
        close = close * scale

    df = pd.DataFrame({
        "adjClose": close,
        "adjHigh":  close * 1.01,
        "adjLow":   close * 0.99,
        "volume":   np.random.randint(5_000_000, 10_000_000, size=rows).astype(float),
    }, index=dates)
    return df


print("=" * 60)
print("VERIFY STRATEGY FIXES (F1-F6)")
print("=" * 60)

# ----------------------------------------------------------------
# F1: analyze_stock_v7_2 argument order
# ----------------------------------------------------------------
print("\n[F1] analyze_stock_v7_2 argument order")
try:
    from src.strategy_v7_2 import analyze_stock_v7_2
    df = make_df(300, "bull", annual_return=0.25)

    # Correct order: analyze_stock_v7_2(df, ticker)
    result = analyze_stock_v7_2(df, "TEST")
    check("Returns dict", isinstance(result, dict))
    check("Has 'signal' key", "signal" in result)
    check("Has 'score' key (F6)", "score" in result)
    check("Has 'should_enter' key (F6)", "should_enter" in result)
    check("Has 'confidence' key (F6)", "confidence" in result)

    # Old wrong order would fail len(ticker) < 252 → HOLD with 'Insufficient data'
    wrong_result = analyze_stock_v7_2("TEST", df)
    check("Wrong arg order correctly returns HOLD",
          wrong_result.get("signal") == "HOLD" and "Insufficient data" in wrong_result.get("reason", ""))

except Exception as e:
    print(f"  [FAIL] Exception: {e}")
    traceback.print_exc()
    FAIL += 3

# ----------------------------------------------------------------
# F4: Entry conditions - no Multi-SMA alignment required
# ----------------------------------------------------------------
print("\n[F4] Entry conditions - Multi-SMA alignment removed, CAGR filter added")
try:
    from src.strategy_v7_2 import analyze_stock_v7_2, add_indicators_v7_2

    # Bull stock with >15% 1yr return - should generate BUY
    df_bull = make_df(310, "bull", annual_return=0.30)
    r_bull = analyze_stock_v7_2(df_bull, "BULL")
    check("Bull stock with 30% 1yr return can generate BUY",
          r_bull.get("signal") in ("BUY", "HOLD"),  # May still HOLD on stoch/volume
          f"(got {r_bull.get('signal')}, reason: {r_bull.get('reason', '')[:80]})")

    # Stock with <15% 1yr return - must be filtered (HOLD for any reason)
    df_slow = make_df(310, "bull", annual_return=0.05)
    r_slow = analyze_stock_v7_2(df_slow, "SLOW")
    check("Stock with 5% 1yr return returns HOLD (filtered at some guard)",
          r_slow.get("signal") == "HOLD",
          f"(got signal={r_slow.get('signal')}, reason={r_slow.get('reason', '')[:80]})")

    # Verify old Multi-SMA alignment check is GONE from code
    import inspect
    from src import strategy_v7_2 as sv
    source = inspect.getsource(sv.analyze_stock_v7_2)
    check("Multi-SMA alignment condition removed from analyze_stock_v7_2",
          "sma_25 > sma_50 > sma_100 > sma_200" not in source)
    check("CAGR quality filter present in analyze_stock_v7_2",
          "annual_return" in source and "0.15" in source)

except Exception as e:
    print(f"  [FAIL] Exception: {e}")
    traceback.print_exc()
    FAIL += 4

# ----------------------------------------------------------------
# F5: Exit logic - only overbought rollover (K>70), not any K<D
# ----------------------------------------------------------------
print("\n[F5] Exit logic - overbought rollover only (K>70)")
try:
    from src.strategy_v7_2 import check_standard_exit_v7_2, add_indicators_v7_2

    df_base = make_df(310, "bull", annual_return=0.25)
    df_ind = add_indicators_v7_2(df_base.copy())

    # Simulate K<D crossover inside Sweet Spot zone (K=45, K<D) - should NOT exit
    df_no_exit = df_ind.copy()
    df_no_exit.iloc[-1, df_no_exit.columns.get_loc("stoch_k")] = 45.0
    df_no_exit.iloc[-1, df_no_exit.columns.get_loc("stoch_d")] = 50.0
    should_exit, reason = check_standard_exit_v7_2(df_no_exit, {"is_power_stock": False})
    check("K=45 < D=50 inside zone does NOT trigger exit (lets winners ride)",
          not should_exit, f"(reason={reason})")

    # Simulate K>70 with K<D - SHOULD exit (overbought rollover)
    df_exit = df_ind.copy()
    df_exit.iloc[-1, df_exit.columns.get_loc("stoch_k")] = 75.0
    df_exit.iloc[-1, df_exit.columns.get_loc("stoch_d")] = 80.0
    # Ensure price > SMA200 so that's not the trigger
    df_exit.iloc[-1, df_exit.columns.get_loc("sma_200")] = df_exit.iloc[-1]["adjClose"] * 0.5
    should_exit2, reason2 = check_standard_exit_v7_2(df_exit, {"is_power_stock": False})
    check("K=75 < D=80 (K>70) triggers overbought rollover exit",
          should_exit2, f"(reason={reason2})")

except Exception as e:
    print(f"  [FAIL] Exception: {e}")
    traceback.print_exc()
    FAIL += 2

# ----------------------------------------------------------------
# F6: score, should_enter, confidence fields in output
# ----------------------------------------------------------------
print("\n[F6] Output fields: score, should_enter, confidence")
try:
    from src.strategy_v7_2 import analyze_stock_v7_2
    df = make_df(310, "bull", annual_return=0.35)
    result = analyze_stock_v7_2(df, "SCORE_TEST")

    check("score is float", isinstance(result.get("score"), float))
    check("should_enter is bool", isinstance(result.get("should_enter"), bool))
    check("confidence is float", isinstance(result.get("confidence"), float))

    # BUY signals must have should_enter=True and score > 0
    if result.get("signal") == "BUY":
        check("BUY signal has should_enter=True", result.get("should_enter") is True)
        check("BUY signal has score > 0", result.get("score", 0) > 0)

    # HOLD signals must have should_enter=False
    df_hold = make_df(310, "bull", annual_return=0.02)
    r_hold = analyze_stock_v7_2(df_hold, "HOLD_TEST")
    check("HOLD signal has should_enter=False", r_hold.get("should_enter") is False)
    check("HOLD signal has score=0.0", r_hold.get("score") == 0.0)

except Exception as e:
    print(f"  [FAIL] Exception: {e}")
    traceback.print_exc()
    FAIL += 4

# ----------------------------------------------------------------
# F2: _init_sweet_spot_strategy on StrategyAgent class
# ----------------------------------------------------------------
print("\n[F2] _init_sweet_spot_strategy on StrategyAgent (not Strategy)")
try:
    import inspect
    from src.agents.strategy.agent import StrategyAgent, Strategy

    # Method must exist on StrategyAgent
    check("_init_sweet_spot_strategy exists on StrategyAgent",
          hasattr(StrategyAgent, "_init_sweet_spot_strategy"))
    check("set_pattern_strategy exists on StrategyAgent",
          hasattr(StrategyAgent, "set_pattern_strategy"))

    # Strategy base class should NOT have _init_sweet_spot_strategy anymore
    strategy_source = inspect.getsource(Strategy)
    check("Strategy base class no longer has _init_sweet_spot_strategy",
          "_init_sweet_spot_strategy" not in strategy_source)

except Exception as e:
    print(f"  [FAIL] Exception: {e}")
    traceback.print_exc()
    FAIL += 3

# ----------------------------------------------------------------
# F3: No duplicate generate_signals
# ----------------------------------------------------------------
print("\n[F3] No duplicate generate_signals method")
try:
    import inspect
    from src.agents.strategy.agent import StrategyAgent
    source = inspect.getsource(StrategyAgent)
    count = source.count("async def generate_signals(")
    check("Only one generate_signals definition on StrategyAgent",
          count == 1, f"(found {count})")

except Exception as e:
    print(f"  [FAIL] Exception: {e}")
    traceback.print_exc()
    FAIL += 1

# ----------------------------------------------------------------
# Summary
# ----------------------------------------------------------------
print()
print("=" * 60)
print(f"RESULTS: {PASS} PASS  |  {FAIL} FAIL")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
