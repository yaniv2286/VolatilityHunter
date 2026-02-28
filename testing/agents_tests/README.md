# VolatilityHunter Tests Directory

## 📁 Test Suite Overview

This directory contains the complete test suite for the VolatilityHunter agent-based trading system. All tests are essential and actively used to validate system functionality.

---

## 🧪 Test Structure

### **🚀 Main Test Runner**
- **`run_tests_simple.py`** - Primary test runner
  - **Purpose**: Execute all system tests
  - **Usage**: `python run_tests_simple.py`
  - **Function**: Runs all 7 agent tests with timeout handling
  - **Referenced by**: Documentation and manual testing

---

## 📊 Individual Agent Tests

### **🤖 Core Agent Tests**
- **`test_data_agent.py`** - Data Agent validation
  - **Purpose**: Test data loading, processing, and smart data loader
  - **Coverage**: Yahoo Finance integration, data validation
  - **Size**: 8.4KB

- **`test_strategy_agent.py`** - Strategy Agent validation
  - **Purpose**: Test Sweet Spot v7.2 strategy implementation
  - **Coverage**: Signal generation, technical indicators
  - **Size**: 22.2KB (largest test suite)

- **`test_execution_agent.py`** - Execution Agent validation
  - **Purpose**: Test IBKR integration and trade execution
  - **Coverage**: Order placement, portfolio management
  - **Size**: 9.3KB

- **`test_sync_agent.py`** - Sync Agent validation
  - **Purpose**: Test portfolio synchronization
  - **Coverage**: Local ↔ TWS portfolio sync
  - **Size**: 9.3KB

### **⚙️ System Agent Tests**
- **`test_scheduler_agent.py`** - Scheduler Agent validation
  - **Purpose**: Test Windows Task Scheduler integration
  - **Coverage**: Task monitoring, script integrity
  - **Size**: 15.7KB

- **`test_notification_agent.py`** - Notification Agent validation
  - **Purpose**: Test email notification system
  - **Coverage**: Gmail SMTP, alert system
  - **Size**: 14.1KB

- **`test_daily_emails.py`** - Email System validation
  - **Purpose**: Test daily email reports and notifications
  - **Coverage**: Email formatting, delivery, content
  - **Size**: 11.3KB

---

## 🔄 Test Execution Flow

### **🚀 Running All Tests**
```bash
cd tests
python run_tests_simple.py
```

### **📊 Test Output**
```
VOLATILITYHUNTER TEST RUNNER
==================================================
[PASS] test_data_agent.py
[PASS] test_strategy_agent.py
[PASS] test_execution_agent.py
[PASS] test_sync_agent.py
[PASS] test_scheduler_agent.py
[PASS] test_notification_agent.py
[PASS] test_daily_emails.py

==================================================
TEST SUMMARY
==================================================
Total: 7
Passed: 7
Failed: 0
Success Rate: 100.0%

ALL TESTS PASSED!
```

### **⚡ Individual Test Execution**
```bash
# Run specific test
python test_strategy_agent.py

# Run with timeout
python run_tests_simple.py  # 300s timeout per test
```

---

## 📋 Test Coverage

### **🤖 Agent System Coverage**
- **Data Agent**: ✅ Yahoo Finance integration, smart data loader
- **Strategy Agent**: ✅ Sweet Spot v7.2, signal generation
- **Execution Agent**: ✅ IBKR integration, trade execution
- **Sync Agent**: ✅ Portfolio synchronization, TWS integration
- **Scheduler Agent**: ✅ Task scheduling, monitoring
- **Notification Agent**: ✅ Email notifications, alerts
- **Email System**: ✅ Daily reports, formatting

### **🔧 System Integration Coverage**
- **Message Bus**: ✅ Inter-agent communication
- **Configuration**: ✅ Agent configuration loading
- **Error Handling**: ✅ Exception management
- **Logging**: ✅ System logging and monitoring
- **Health Checks**: ✅ System validation

---

## 🎯 Test Categories

### **✅ Unit Tests**
- Individual agent functionality
- Component isolation
- Method-level testing

### **✅ Integration Tests**
- Agent-to-agent communication
- System integration
- End-to-end workflows

### **✅ System Tests**
- Complete system validation
- Production readiness
- Performance testing

---

## 🚨 Important Notes

### **⏱️ Timeout Handling**
- **Default Timeout**: 300 seconds (5 minutes) per test
- **Purpose**: Prevent hanging tests
- **Behavior**: Failed tests marked as TIMEOUT

### **🔧 Test Dependencies**
- Tests require proper environment setup
- `.env` file with valid credentials
- IBKR connection for execution tests
- Internet connection for data tests

### **📊 Test Results**
- **Success**: All tests must pass for production deployment
- **Failure**: Any failing test blocks deployment
- **Coverage**: Complete agent system validation

---

## 🛠️ Test Maintenance

### **📝 Adding New Tests**
1. Create test file following naming convention: `test_[agent_name].py`
2. Add to `run_tests_simple.py` test list
3. Update documentation
4. Ensure test follows existing patterns

### **🔧 Test Requirements**
- **Python 3.10+**: Required for all tests
- **Dependencies**: All requirements.txt packages
- **Environment**: Valid configuration in `.env`
- **Services**: IBKR TWS for execution tests

---

## 📊 Test Metrics

### **📈 Current Test Suite**
- **Total Tests**: 7 test files
- **Test Coverage**: Complete agent system
- **Execution Time**: ~2-3 minutes total
- **Success Rate**: 100% (all tests passing)

### **📊 Test Sizes**
| Test File | Size | Focus |
|-----------|------|-------|
| `test_strategy_agent.py` | 22.2KB | Strategy logic |
| `test_scheduler_agent.py` | 15.7KB | Task scheduling |
| `test_notification_agent.py` | 14.1KB | Email system |
| `test_daily_emails.py` | 11.3KB | Email reports |
| `test_execution_agent.py` | 9.3KB | Trade execution |
| `test_sync_agent.py` | 9.3KB | Portfolio sync |
| `test_data_agent.py` | 8.4KB | Data management |

---

## 🎯 Quick Reference

### **🚀 Run Tests:**
```bash
cd tests
python run_tests_simple.py
```

### **📊 Check Results:**
- **All Passed**: ✅ System ready for production
- **Any Failed**: ❌ Fix issues before deployment
- **Timeout**: ⚠️ Check system performance

### **🔧 Debug Tests:**
- **Individual**: Run specific test file
- **Verbose**: Check test output for errors
- **Logs**: Review `logs/test_results.log`

---

## 📞 Test Documentation

### **📋 Test Purpose:**
- **Validation**: Ensure system components work correctly
- **Regression**: Prevent breaking changes
- **Quality**: Maintain code quality standards
- **Deployment**: Validate production readiness

### **🎯 Success Criteria:**
- **All Tests Pass**: ✅ System is production-ready
- **No Timeouts**: ✅ Performance is acceptable
- **Clean Output**: ✅ No errors or warnings

---

**📋 Last Updated: 2026-02-26**
**🎯 Purpose: Complete test suite for VolatilityHunter agent-based trading system**
