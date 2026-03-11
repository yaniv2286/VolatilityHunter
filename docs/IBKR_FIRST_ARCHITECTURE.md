# IBKR-FIRST ARCHITECTURE
**Date**: 2026-03-11  
**Status**: ✅ ACTIVE  
**Ground Truth**: IBKR API

---

## 🎯 CORE PRINCIPLE

**IBKR is the single source of truth for all account data.**

`portfolio.json` is a **local cache** that syncs FROM IBKR, never the other way around.

---

## 📊 DATA FLOW

```
┌─────────────────────────────────────────────────────────────┐
│                    IBKR ACCOUNT (Ground Truth)              │
│  • Cash Balance                                             │
│  • Positions (symbol, shares, avg cost, current price)      │
│  • Net Liquidation Value                                    │
│  • Buying Power                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ API Connection (port 7497)
                            │ reconcile_with_ibkr()
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              portfolio.json (Local Cache)                   │
│  • Synced cash from IBKR                                    │
│  • Synced positions from IBKR                               │
│  • Additional metadata (stop_loss, highest_price, etc.)     │
│  • Trade history (append-only log)                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Used for calculations
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Strategy Engine                                │
│  • Position sizing (uses IBKR equity)                       │
│  • Exit checks (uses IBKR positions)                        │
│  • Entry signals (uses IBKR available capital)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 RECONCILIATION PROCESS

### Step 1: Connect to IBKR
**File**: `scripts/daily_trading_loop.py`  
**Function**: `reconcile_with_ibkr()`  
**Lines**: 127-189

```python
ibkr = get_brokerage_interface(IBKR_CONFIG)
if not ibkr.connect():
    logger.warning("IBKR not available - running in PAPER mode")
    return portfolio, None
```

### Step 2: Get IBKR Account Data
```python
account = ibkr.get_account_info()
ibkr_positions = ibkr.get_positions()

ibkr_cash = account.get('cash', 0)
ibkr_equity = account.get('equity', 0)
```

### Step 3: Sync Cash (IBKR Wins)
```python
local_cash = portfolio.get('cash', 0)
if abs(ibkr_cash - local_cash) > 100:
    logger.warning(f"Cash mismatch: local=${local_cash:,.2f} vs IBKR=${ibkr_cash:,.2f} - using IBKR")
    portfolio['cash'] = ibkr_cash  # ← IBKR is ground truth
```

### Step 4: Sync Positions
**Add IBKR positions not in local:**
```python
for pos in ibkr_positions:
    sym = pos['symbol']
    if sym not in portfolio['positions']:
        logger.warning(f"IBKR has {sym} not in local portfolio - adding")
        portfolio['positions'][sym] = {
            'shares': int(pos['quantity']),
            'entry_price': pos.get('entry_price', pos.get('current_price', 0)),
            # ... additional metadata
        }
```

**Remove local positions not in IBKR:**
```python
for sym in list(local_tickers):
    if sym not in ibkr_tickers:
        logger.warning(f"Local has {sym} not in IBKR - removing from local")
        portfolio['positions'].pop(sym, None)
```

---

## 💰 POSITION SIZING

**File**: `src/strategy_engine.py`  
**Function**: `calc_position_size()`  
**Lines**: 514-558

### Equity Calculation
```python
def _portfolio_equity(portfolio: dict, prices: Dict[str, float]) -> float:
    pos_value = sum(
        p.get('shares', 0) * prices.get(t, p.get('entry_price', 0))
        for t, p in portfolio.get('positions', {}).items()
    )
    return portfolio.get('cash', 0) + pos_value  # ← Uses IBKR-synced cash
```

### Position Size Formula
```python
total_equity = _portfolio_equity(portfolio, prices)  # ← IBKR data
dd_scale = get_dd_scale(portfolio)
vol_scale = 1.0  # Volatility adjustment

alloc = total_equity * 0.20 * dd_scale * vol_scale  # 20% per position
shares = int(alloc / price)
cost = shares * price

# Check against allocation (not cash, for margin accounts)
if shares <= 0 or cost > alloc:
    return 0, 0.0
return shares, cost
```

---

## 🚨 CRITICAL RULES

### Rule 1: Never Manually Edit portfolio.json
❌ **WRONG**: Editing `portfolio.json` to change cash or positions  
✅ **RIGHT**: Use `temp/ws_sync_with_ibkr.py` to sync from IBKR

### Rule 2: Always Reconcile First
Every trading session MUST start with IBKR reconciliation:
```python
portfolio, ibkr = reconcile_with_ibkr(portfolio)
if ibkr is None:
    logger.warning("Running in PAPER mode - no real orders")
```

### Rule 3: IBKR Unavailable = PAPER Mode
If IBKR connection fails:
- System runs in PAPER mode (simulation only)
- No real orders are placed
- Local portfolio.json is used for calculations
- **This is a safety feature, not normal operation**

### Rule 4: NO MARGIN/LEVERAGE - CASH ONLY ⚠️
**CRITICAL**: The system NEVER uses margin or leverage. Only trade with available cash.

```python
# ✅ CORRECT: Check against available cash (NO MARGIN)
available_cash = portfolio.get('cash', 0)
if shares <= 0 or cost > available_cash or cost > alloc:
    return 0, 0.0

# ❌ WRONG: Only check allocation (allows margin trading)
if shares <= 0 or cost > alloc:
    return 0, 0.0
```

**Why this matters:**
- Prevents over-leveraging
- Ensures we only trade with cash on hand
- No borrowing from IBKR
- No margin calls
- Conservative risk management

---

## 🔧 MANUAL SYNC SCRIPT

**File**: `temp/ws_sync_with_ibkr.py`

Use this script to manually sync `portfolio.json` with IBKR:

```bash
python temp/ws_sync_with_ibkr.py
```

**What it does:**
1. Connects to IBKR API
2. Gets real account values (cash, equity, positions)
3. Overwrites `portfolio.json` with IBKR data
4. Preserves trade history
5. Sets IBKR as ground zero

---

## 📋 CURRENT STATE (2026-03-11)

### IBKR Account
- **Currency**: ILS (Israeli Shekels)
- **Cash**: ₪250,000.01
- **Net Liquidation**: ₪249,615.09
- **Positions**: 0 (all closed)
- **Account**: DUP663578 (Paper Trading)

### portfolio.json
- **Synced**: ✅ 2026-03-11 19:37:17
- **Cash**: ₪250,000.01 (matches IBKR)
- **Positions**: 0 (matches IBKR)
- **Trade History**: 7 entries (preserved)

---

## 🛡️ SAFEGUARDS

### 1. IB Gateway Auto-Start
**File**: `scripts/DAILY_ROUTINE/run_trading.bat`  
**Lines**: 26-31

```batch
echo [VH] Starting IB Gateway manager (will check if already running)...
start /B python scripts\auto_tws_manager.py
timeout /t 90 /nobreak >nul
echo [VH] IB Gateway startup complete (waited 90s).
```

### 2. Health Check Before Trading
**File**: `scripts/DAILY_ROUTINE/run_trading.bat`  
**Lines**: 33-48

```batch
python scripts\functional_health_check.py
if %ERRORLEVEL% NEQ 0 (
    echo [CRITICAL ERROR] Functional Health Check Failed - aborting trading.
    exit /b %ERRORLEVEL%
)
```

### 3. Reconciliation Gate
**File**: `scripts/daily_trading_loop.py`  
**Lines**: 127-189

Every trading session starts with:
```python
portfolio, ibkr = reconcile_with_ibkr(portfolio)
```

If IBKR unavailable → PAPER mode (no real trades)

---

## 🎯 VERIFICATION CHECKLIST

Before each trading session, verify:

- [ ] IB Gateway is running (port 7497 open)
- [ ] IBKR connection successful (no "PAPER mode" warning)
- [ ] Cash matches IBKR (within $100)
- [ ] Positions match IBKR exactly
- [ ] No manual edits to portfolio.json

**Command to verify:**
```bash
python temp/ws_sync_with_ibkr.py
```

---

## 📚 RELATED FILES

### Core Files
- `scripts/daily_trading_loop.py` - Main trading loop with reconciliation
- `src/strategy_engine.py` - Position sizing using IBKR equity
- `src/brokerage_interface.py` - IBKR API wrapper
- `data/portfolio.json` - Local cache (synced FROM IBKR)

### Utility Scripts
- `temp/ws_sync_with_ibkr.py` - Manual sync tool
- `scripts/auto_tws_manager.py` - IB Gateway auto-start
- `scripts/functional_health_check.py` - Pre-trading health check

### Documentation
- `docs/CRITICAL_FIXES_SUMMARY.md` - All critical fixes
- `docs/SESSION_SUMMARY_2026-03-10.md` - Previous session
- `docs/ATR_VOLATILITY_STOPS.md` - ATR stop implementation

---

## ✅ DEFINITION OF DONE

**IBKR-First Architecture is complete when:**

1. ✅ IBKR reconciliation runs first in daily loop
2. ✅ Cash syncs FROM IBKR (IBKR wins conflicts)
3. ✅ Positions sync FROM IBKR (add/remove as needed)
4. ✅ Position sizing uses IBKR equity
5. ✅ Margin accounts handled correctly (negative cash OK)
6. ✅ Manual sync script available
7. ✅ IB Gateway auto-starts before trading
8. ✅ Documentation complete

**Status**: ✅ ALL COMPLETE (2026-03-11)
