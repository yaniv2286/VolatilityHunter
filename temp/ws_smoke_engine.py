import sys
sys.path.insert(0, '.')

print("1. Testing strategy_engine imports...")
from src.strategy_engine import (
    PARAMS, DEFAULT_VERSION, get_params,
    check_exits, scan_universe, calc_position_size,
    can_enter, get_spy_regime, get_regime_max_positions,
    get_sector, promote_power_stocks, update_highest_prices,
    update_high_water_mark, get_dd_scale,
)
p = get_params(DEFAULT_VERSION)
print(f"   DEFAULT_VERSION = {DEFAULT_VERSION}")
print(f"   HARD_STOP_PCT   = {p['HARD_STOP_PCT']}")
print(f"   TIME_STOP_DAYS  = {p['TIME_STOP_DAYS']}")
print(f"   REGIME_MAX_POS  = {p['REGIME_MAX_POS']}")
print(f"   SECTOR_MAX      = {p['SECTOR_MAX']}")
print(f"   VOL_SIZE        = {p['VOL_SIZE']}")
print("   strategy_engine OK")

print("2. Testing daily_trading_loop imports...")
from scripts.daily_trading_loop import (
    check_exits as dtl_exits,
    scan_universe as dtl_scan,
    execute_entries as dtl_entries,
    DEFAULT_VERSION as dtl_ver,
)
print(f"   DEFAULT_VERSION = {dtl_ver}")
print("   daily_trading_loop OK")

print("3. Testing simulate_monday imports...")
from scripts.simulate_monday import (
    check_exits as sim_exits,
    scan_universe as sim_scan,
    simulate_entries as sim_entries,
    DEFAULT_VERSION as sim_ver,
)
print(f"   DEFAULT_VERSION = {sim_ver}")
print("   simulate_monday OK")

print()
print("ALL 3 MODES use DEFAULT_VERSION =", DEFAULT_VERSION)
print("Change src/strategy_engine.py PARAMS to update all modes at once.")
print("EXIT CODE: 0")
