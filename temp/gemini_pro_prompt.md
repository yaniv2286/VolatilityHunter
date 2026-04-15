# GEMINI PRO CONSULTATION PROMPT - VOLATILITYHUNTER TRADING SYSTEM

## CONTEXT
I'm running an automated quantitative trading system called VolatilityHunter that trades stocks via Interactive Brokers (IBKR) Paper Trading account. The system is designed to run autonomously via Windows Task Scheduler at 17:06 IST daily, but we're experiencing critical recurring failures that are preventing reliable operation.

## SYSTEM ARCHITECTURE

**Tech Stack:**
- Python 3.10.9
- IBKR Paper Trading (Account: DUP663578, $100k initial capital)
- IB Gateway (TWS API) via ib_insync library
- Windows Task Scheduler for automation
- Tiingo API for market data
- Gmail SMTP for notifications

**Key Components:**
1. `scripts/daily_trading_loop.py` - Main trading orchestration (runs once daily)
2. `scripts/auto_tws_manager.py` - IB Gateway startup/management via IBC
3. `src/strategy_engine.py` - Position sizing and strategy logic
4. `src/brokerage_interface.py` - IBKR API wrapper
5. `data/portfolio.json` - Portfolio state persistence

**Trading Flow:**
1. Task Scheduler triggers at 17:06 IST
2. Launch IB Gateway via IBC (Java-based automation)
3. Connect to IBKR API on port 7497
4. Reconcile portfolio.json with IBKR account
5. Fetch latest prices from Tiingo
6. Calculate position sizes (20% of equity per position, max 10 positions)
7. Place market orders via IBKR
8. Monitor fills for 90 seconds
9. Save portfolio state and send email summary
10. Cleanup: disconnect and terminate Gateway

## CRITICAL RECURRING PROBLEMS

### PROBLEM 1: IB GATEWAY STARTUP FAILURES (80% failure rate)
**Symptoms:**
- Gateway process starts but API never becomes ready
- Waits 75+ seconds, then force-terminates
- Happens both in scheduled task (17:06) and manual runs
- No consistent pattern - sometimes works, usually fails

**What We've Tried:**
- Using IBC (Interactive Brokers Controller) for automation
- Java 17 classpath-based launch
- Ghost-Typist GUI automation for login
- 300-second timeout with 15-second status checks
- Process termination and retry logic

**Logs Show:**
```
2026-04-15 17:06:46,960 - INFO - Waiting up to 300s for IB Gateway API on port 7497...
2026-04-15 17:07:34,739 - INFO -   Still waiting... (15s)
2026-04-15 17:08:20,526 - INFO -   Still waiting... (30s)
...
2026-04-15 17:10:47,967 - ERROR - Gateway process stuck - forcing restart
```

**Questions:**
1. Why does IB Gateway start successfully sometimes but fail most times?
2. Is there a more reliable way to launch Gateway programmatically?
3. Should we use TWS instead of Gateway?
4. Are there Java/Windows environment issues causing this?

### PROBLEM 2: MASSIVE MARGIN USAGE BUG (Critical - Lost $100k)
**Symptoms:**
- System buys $180k-$410k of stock on $100k cash
- Creates -$184k to -$311k margin debt
- Happens when IBKR Paper account reports inflated cash balance

**Root Cause:**
IBKR Paper accounts ACCUMULATE liquidation proceeds instead of resetting. After multiple test runs:
- Started with: $100k
- IBKR now reports: $240k-$550k cash
- Actual available: -$3,991 (negative from losses)

**Fixes Implemented:**
1. Execution lock file (prevents multiple runs per day)
2. Relative sanity check (reject if IBKR > 2x portfolio.json)
3. Absolute sanity check (reject if IBKR > $150k) ← Latest fix

**Current Issue:**
Even with fixes, the sanity check was bypassed when portfolio cash was negative:
```python
# OLD (BROKEN):
if ibkr_cash > old_cash * 2.0 and old_cash > 10000:
    reject_ibkr = True
# Failed when old_cash = -$3,306

# NEW (FIXED):
if ibkr_cash > 150000:  # Absolute threshold
    reject_ibkr = True
    sys.exit(1)  # ABORT trading
```

**Questions:**
1. Is there a way to programmatically reset IBKR Paper account to $100k?
2. Should we abandon portfolio.json and use IBKR as single source of truth?
3. How do other algo traders handle IBKR Paper account quirks?
4. Is there a better reconciliation strategy?

### PROBLEM 3: COMPUTER SLEEP PREVENTING SCHEDULED TASK
**Symptoms:**
- Task Scheduler runs at 17:06 IST
- But computer is sleeping
- Task can't wake computer by default
- Trading doesn't execute

**What We Need:**
- Reliable way to ensure computer is awake at 17:06 IST
- OR configure Task Scheduler to wake computer
- OR alternative scheduling approach

**Questions:**
1. Best practice for Windows Task Scheduler wake-on-schedule?
2. Should we use a different scheduling mechanism?
3. How to prevent sleep during trading hours (17:00-18:00 IST)?

### PROBLEM 4: SHORT POSITIONS CREATED ACCIDENTALLY
**Symptoms:**
- Tried to close long positions
- System sold stocks we didn't own
- Created short positions (negative shares)
- Lost money buying back shorts at higher prices

**Root Cause:**
Portfolio.json showed we owned stocks, but IBKR account was already liquidated. When we tried to "close" positions, we sold stocks we didn't have.

**Questions:**
1. How to ensure portfolio.json and IBKR are always in sync?
2. Should we validate positions exist before closing?
3. Better error handling for position mismatches?

### PROBLEM 5: UNICODE LOGGING ERRORS IN TASK SCHEDULER
**Symptoms:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2705' in position 52
```

**Cause:**
Using emoji checkmarks (✅) in logs, but Task Scheduler uses cp1255 encoding

**Partial Fix:**
Removed some emojis, but still occurring

**Questions:**
1. How to force UTF-8 encoding in Task Scheduler environment?
2. Should we strip ALL unicode from logs?
3. Better logging strategy for scheduled tasks?

## CONSTRAINTS & REQUIREMENTS

**Must Haves:**
- Fully autonomous operation (no manual intervention)
- Run once daily at 17:06 IST
- No margin usage (cash-only trading)
- Reliable IB Gateway startup
- Accurate portfolio synchronization
- Email notifications on success/failure

**Environment:**
- Windows 10/11
- Python 3.10.9 (Tiingo requires ≤3.10)
- IB Gateway 10.19+ with IBC
- Task Scheduler (not cron)

**Risk Tolerance:**
- ZERO tolerance for margin usage
- ZERO tolerance for position sizing errors
- System should ABORT rather than trade with bad data

## WHAT WE NEED FROM YOU

**Primary Goal:**
Design a robust, production-ready solution that eliminates these recurring failures and allows the system to run autonomously for months without intervention.

**Specific Requests:**

1. **IB Gateway Reliability:**
   - Alternative launch methods or configurations
   - Diagnostic steps to identify why Gateway fails
   - Fallback strategies if Gateway won't start

2. **Portfolio Synchronization:**
   - Bulletproof reconciliation logic
   - Handle IBKR Paper account quirks
   - Prevent margin usage under ALL conditions

3. **Task Scheduler Reliability:**
   - Ensure computer wakes for scheduled task
   - Handle sleep/hibernate states
   - Alternative scheduling if Task Scheduler unreliable

4. **Error Recovery:**
   - Graceful degradation strategies
   - Automatic retry logic
   - Clear abort conditions

5. **Testing Strategy:**
   - How to test without corrupting Paper account further
   - Simulation mode for dry-runs
   - Validation before live execution

## CURRENT STATE

**Account Status:**
- IBKR Paper: -$3,991 cash (corrupted from testing)
- Portfolio.json: -$3,991 cash
- Positions: 0 (all liquidated)
- System: SAFE (will abort if IBKR > $150k)

**Last 3 Days:**
- April 13: Gateway failed, manual run succeeded with margin bug
- April 14: Gateway failed, manual run succeeded (no margin due to fix)
- April 15: Gateway failed, manual run had margin bug (sanity check bypassed)

**Success Rate:**
- Scheduled task: 0% (Gateway always fails)
- Manual runs: 100% (Gateway starts, but margin bugs occurred)

## QUESTION FOR GEMINI PRO

**Given this complete context, please provide:**

1. **Root cause analysis** of why IB Gateway fails so consistently
2. **Architectural recommendations** for a more reliable system
3. **Specific code changes** or configuration fixes
4. **Alternative approaches** if current architecture is fundamentally flawed
5. **Production hardening** checklist to prevent future issues
6. **Testing methodology** to validate fixes without risking more losses

**Please be specific and actionable.** We need solutions that work in production, not just theory. Code examples, configuration snippets, and step-by-step instructions are highly valued.

Thank you for your expertise!
