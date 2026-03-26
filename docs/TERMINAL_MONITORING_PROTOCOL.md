# Terminal Monitoring Protocol

## 🎯 MANDATORY RULES FOR TERMINAL OPERATIONS

### 1. BEFORE EXECUTION
- Always check existing logs for recent errors
- Verify system health with functional_health_check.py
- Ensure proper environment setup

### 2. DURING EXECUTION
- Monitor terminal output in real-time
- Watch for: ERROR, CRITICAL, FAILED, Exception, Traceback
- Stop immediately on any critical issues
- Document exit codes

### 3. AFTER EXECUTION
- Review complete log output
- Check for warnings or errors
- Verify expected outcomes
- Document any issues before proceeding

### 4. CRITICAL KEYWORDS TO WATCH
```
ERROR
CRITICAL
FAILED
Exception
Traceback
Permission denied
Connection refused
Error 10089 (Market data subscription)
unfilled after 90s (Order execution issues)
Market order failed
```
Timeout
403, 404, 500
KeyboardInterrupt
```

### 5. STOP CONDITIONS
- Any ERROR in log output
- Non-zero exit code
- Permission errors
- Connection failures
- Market data subscription errors

### 6. SUCCESS INDICATORS (NEW)
- Exit Code: 0
- "Daily loop complete" message
- "Portfolio saved" confirmation
- "Email sent successfully" 
- Order fills across multiple exchanges
- No Error 10089 messages

### 7. RESOLUTION PROTOCOL
1. Stop execution immediately
2. Document the exact error
3. Identify root cause
4. Apply targeted fix
5. Test with verification script
6. Re-run only after fix confirmed

## 🚨 EXAMPLES

### GOOD: Proper Monitoring
```bash
python scripts/daily_trading_loop.py
# Monitor output for ERROR keywords
# Exit code: 0 ✅
# Review logs: No critical errors ✅
# Proceed to next step ✅
```

### BAD: Ignoring Errors
```bash
python scripts/daily_trading_loop.py
# ERROR: Tiingo API 403 Forbidden ❌
# Continue execution anyway ❌
# Re-run without fixing ❌
```

## 🎯 VERIFICATION
Use `scripts/verify_log_monitoring.py` to test log monitoring capability.
