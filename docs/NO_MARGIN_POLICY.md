# NO MARGIN/LEVERAGE POLICY
**Date**: 2026-03-11  
**Status**: ✅ ENFORCED  
**Priority**: CRITICAL

---

## 🚨 CORE PRINCIPLE

**The VolatilityHunter system NEVER uses margin or leverage.**

**Only trade with available cash on hand. No borrowing from IBKR.**

---

## 💰 IMPLEMENTATION

### Position Sizing Enforcement
**File**: `src/strategy_engine.py`  
**Function**: `calc_position_size()`  
**Lines**: 554-558

```python
# NO MARGIN/LEVERAGE: Only trade with available cash
# Check cost against actual cash balance, not just allocation
available_cash = portfolio.get('cash', 0)
if shares <= 0 or cost > available_cash or cost > alloc:
    return 0, 0.0
return shares, cost
```

### How It Works

1. **Calculate allocation** based on equity and risk parameters:
   ```python
   alloc = total_equity * 0.20 * dd_scale * vol_scale
   ```

2. **Calculate shares and cost**:
   ```python
   shares = int(alloc / price)
   cost = shares * price
   ```

3. **Check against BOTH allocation AND available cash**:
   ```python
   available_cash = portfolio.get('cash', 0)
   if cost > available_cash or cost > alloc:
       return 0, 0.0  # Reject the trade
   ```

---

## 🛡️ WHY THIS MATTERS

### Risk Management
- **No margin calls** - Can't be forced to liquidate at bad prices
- **No interest charges** - No borrowing costs eating into profits
- **Sleep well** - No overnight leverage risk
- **Conservative** - Only risk what you have

### Real-World Example

**Scenario**: Account has ₪250,000 cash

**Without cash check (WRONG):**
- Allocation: ₪50,000 per position (20% of equity)
- Could open 10 positions = ₪500,000 total
- **Uses 2x leverage** (borrowed ₪250,000 from IBKR)
- ❌ Margin call risk if positions drop

**With cash check (CORRECT):**
- Allocation: ₪50,000 per position
- Cash available: ₪250,000
- Can open 5 positions = ₪250,000 total
- **No leverage** (only using own cash)
- ✅ No margin call risk

---

## 📋 VERIFICATION CHECKLIST

Before each trading session:

- [ ] Position sizing checks `cost > available_cash`
- [ ] No positions opened if insufficient cash
- [ ] IBKR account set to "Cash" (not "Margin")
- [ ] Total position value ≤ Available cash

**Command to verify**:
```bash
python temp/ws_sync_with_ibkr.py
# Check: cash > 0 and positions value < cash
```

---

## 🔧 IBKR ACCOUNT SETTINGS

### Recommended IBKR Configuration

1. **Account Type**: Cash Account (not Margin)
2. **Trading Permissions**: Stocks only (no options, futures)
3. **API Settings**: 
   - Enable API trading
   - Disable margin trading via API
   - Set max order size limits

### How to Change IBKR Account to Cash-Only

1. Log into IBKR Account Management
2. Navigate to: Settings → Account Settings
3. Find: "Account Type" or "Margin Settings"
4. Select: "Cash Account" or "Disable Margin"
5. Save changes

**Note**: This may require contacting IBKR support for paper trading accounts.

---

## 🚫 WHAT IS PROHIBITED

### Never Do This:
- ❌ Open positions totaling more than available cash
- ❌ Use IBKR's margin/buying power
- ❌ Borrow money from IBKR
- ❌ Short selling (requires margin)
- ❌ Options selling (requires margin)
- ❌ Futures trading (inherently leveraged)

### Always Do This:
- ✅ Check cost against available cash
- ✅ Only open positions you can pay for in full
- ✅ Keep cash buffer for emergencies
- ✅ Monitor total position value vs cash

---

## 📊 CURRENT STATUS (2026-03-11)

### Account Status
- **Cash**: ₪250,000.01
- **Positions**: 0 (all closed)
- **Total Value**: ₪249,615.09
- **Margin Used**: ₪0 (NONE)
- **Buying Power**: ₪250,000 (cash only)

### Position Sizing Logic
- ✅ Checks cost against available cash
- ✅ Enforced in `calc_position_size()`
- ✅ No margin/leverage possible
- ✅ Conservative risk management

---

## 📚 RELATED DOCUMENTATION

- `.windsurfrules` - Line 99: NO MARGIN/LEVERAGE rule
- `docs/IBKR_FIRST_ARCHITECTURE.md` - Rule 4: Cash-only policy
- `docs/CRITICAL_FIXES_SUMMARY.md` - No margin policy section
- `src/strategy_engine.py` - Lines 554-558: Implementation

---

## ✅ COMPLIANCE VERIFICATION

**How to verify the system is cash-only:**

1. **Check position sizing code**:
   ```bash
   grep -n "available_cash" src/strategy_engine.py
   # Should show line 556: if cost > available_cash
   ```

2. **Run test**:
   ```python
   # Test with ₪250,000 cash
   # Try to buy ₪300,000 worth of stock
   # Should return 0 shares (rejected)
   ```

3. **Monitor logs**:
   ```bash
   grep "shares=0" logs/trading_*.log
   # Shows when trades rejected due to insufficient cash
   ```

---

## 🎯 SUMMARY

**The VolatilityHunter system is designed to be conservative and safe.**

- **No margin** = No leverage
- **No leverage** = No margin calls
- **No margin calls** = Sleep well at night
- **Cash only** = Maximum safety

**This is a fundamental design principle that must NEVER be violated.**
