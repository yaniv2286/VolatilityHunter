import sys
sys.path.insert(0, '.')
from scripts.daily_trading_loop import (
    HARD_STOP_PCT, OVERBOUGHT_EXIT, MOMENTUM_DAYS, MOMENTUM_MIN,
    REGIME_MAX_POS, SECTOR_MAX, TIME_STOP_DAYS, VOL_SIZE_ENABLED,
    _get_spy_regime, _get_sector
)
print(f'HARD_STOP_PCT   = {HARD_STOP_PCT}   (expect 0.08)')
print(f'OVERBOUGHT_EXIT = {OVERBOUGHT_EXIT}  (expect 78.0)')
print(f'REGIME_MAX_POS  = {REGIME_MAX_POS}    (expect 3)')
print(f'SECTOR_MAX      = {SECTOR_MAX}    (expect 3)')
print(f'TIME_STOP_DAYS  = {TIME_STOP_DAYS}   (expect 10)')
print(f'VOL_SIZE_ENABLED= {VOL_SIZE_ENABLED}  (expect True)')
print(f'SPY regime      = {_get_spy_regime()}')
print(f'Sector AAPL     = {_get_sector("AAPL")}')
print(f'Sector MSFT     = {_get_sector("MSFT")}')
print(f'Sector JPM      = {_get_sector("JPM")}')
print('All v8.1 params OK.')
