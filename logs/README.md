# VolatilityHunter Logs Directory

## 📁 Log Files Overview

This directory contains essential system logs for monitoring and debugging the VolatilityHunter trading system.

---

## 📊 Current Log Files

### **✅ Essential Logs (Keep)**
- **`VH_YYYY-MM-DD.log`** - Daily system logs (current day only)
- **`system_log_YYYYMMDD.txt`** - Daily system summary report
- **`test_results.log`** - Test execution results
- **`scheduler_report_YYYYMMDD_HHMMSS.json`** - Latest scheduler health report

---

## 🧹 Log Management Policy

### **📅 Retention Policy**
- **Daily Logs**: Keep only current day's log file
- **System Summaries**: Keep current day's summary
- **Test Results**: Keep latest test results
- **Scheduler Reports**: Keep latest report only

### **🗑️ Automatic Cleanup**
- Old daily logs are deleted automatically
- Historical logs are not stored to save disk space
- Only essential current logs are maintained

### **📊 Log Rotation**
- **Daily**: `VH_YYYY-MM-DD.log` - Created daily, previous day deleted
- **Summary**: `system_log_YYYYMMDD.txt` - Created daily, previous day deleted
- **Scheduler**: `scheduler_report_*.json` - Keep only latest

---

## 🔍 Log File Contents

### **Daily System Logs (`VH_*.log`)**
- System startup and shutdown
- Agent initialization and status
- Data loading and processing
- Error messages and warnings
- Trading activity logs

### **System Summary (`system_log_*.txt`)**
- Daily trading session summary
- Portfolio performance metrics
- Signal generation statistics
- Execution results
- System health status

### **Test Results (`test_results.log`)**
- Test execution timestamps
- Individual test results
- Success/failure status
- Error details (if any)

### **Scheduler Reports (`scheduler_report_*.json`)**
- Task monitoring status
- System resource usage
- Agent health checks
- Alert notifications

---

## 🚨 Important Notes

### **📊 Current Day Focus**
- Only current day's logs are maintained
- Historical analysis should use archived data
- System health is monitored in real-time

### **💾 Disk Space Management**
- Log files are kept small and manageable
- Automatic cleanup prevents disk space issues
- Essential information preserved in summaries

### **🔍 Debugging**
- Use current day's log for real-time issues
- Check system summary for daily performance
- Review test results for system validation

---

## 📞 Log Analysis

For log analysis or troubleshooting:
1. Check current day's `VH_YYYY-MM-DD.log` for detailed events
2. Review `system_log_YYYYMMDD.txt` for daily summary
3. Examine `test_results.log` for system validation
4. Monitor `scheduler_report_*.json` for system health

---

## 🔄 Log File Lifecycle

```
Daily Process:
1. New day starts → New log files created
2. Previous day's logs → Automatically deleted
3. System runs → Logs written to current files
4. End of day → Summary generated
5. Next day → Process repeats
```

---

**📋 Last Updated: 2026-02-26**
**🎯 Purpose: Essential system logging with automatic cleanup**
