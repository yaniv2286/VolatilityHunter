# 📅 VolatilityHunter Scheduler Guide

Automate daily stock scans and receive email alerts with trading signals.

---

## 🎯 What It Does

The scheduler automatically:
1. ✅ **Updates stock data** every morning (T+1 data)
2. ✅ **Scans all 2,150 stocks** for BUY/SELL signals
3. ✅ **Sends email alerts** with results
4. ✅ **Runs weekly full refresh** (Sundays)

---

## ⚙️ Setup

### **Step 1: Configure Email Settings**

Edit `.env` file:

```bash
# Email Notifications
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
RECIPIENT_EMAIL=your_email@gmail.com
```

### **Step 2: Get Gmail App Password**

For Gmail users:
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to "App passwords"
4. Generate password for "Mail"
5. Copy the 16-character password
6. Use it as `SENDER_PASSWORD` in `.env`

**Note:** Never use your actual Gmail password!

### **Step 3: Install Dependencies**

```bash
pip install schedule
```

Or reinstall all:
```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

### **Run Scheduler**

```bash
python scheduler.py
```

This will:
- Run an immediate scan (for testing)
- Schedule daily scans at 9:00 AM
- Schedule weekly full updates on Sundays at 6:00 AM
- Keep running in the background

### **Test Email Configuration**

```python
from src.email_notifier import EmailNotifier

notifier = EmailNotifier()
notifier.send_test_email()
```

---

## 📅 Schedule

### **Daily Scan (9:00 AM)**
- Incremental data update (~3 minutes)
- Scan all 2,150 stocks (~2 minutes)
- Send email with BUY/SELL signals
- **Total time:** ~5 minutes

### **Weekly Full Update (Sunday 6:00 AM)**
- Full data refresh (~15 minutes)
- Downloads 2 years of data for all stocks
- Ensures data quality

---

## 📧 Email Format

You'll receive emails like this:

```
Subject: VolatilityHunter Daily Scan - 85 BUY Signals

VolatilityHunter Daily Scan Results
============================================================
Scan Date: 2026-01-31 09:00:00
Total Stocks Scanned: 2150

SUMMARY
============================================================
🟢 BUY Signals:  85
🔴 SELL Signals: 42
⚪ HOLD Signals: 2023
❌ Errors:       0

🟢 BUY SIGNALS (85 stocks)
============================================================

AAPL: $259.48
  CAGR: 18.50%
  Stochastic K: 45.23
  Reason: Price above SMA 200 and Stochastic K in sweet spot

NVDA: $890.50
  CAGR: 125.40%
  Stochastic K: 67.89
  Reason: Price above SMA 200 and Stochastic K in sweet spot

...
```

---

## 🔧 Customization

### **Change Schedule Times**

Edit `scheduler.py`:

```python
# Daily scan at 8:30 AM instead of 9:00 AM
schedule.every().day.at("08:30").do(daily_job)

# Weekly update on Saturday instead of Sunday
schedule.every().saturday.at("06:00").do(weekly_full_update)
```

### **Run Multiple Times Per Day**

```python
# Scan at market open and close
schedule.every().day.at("09:30").do(daily_job)  # Market open
schedule.every().day.at("16:00").do(daily_job)  # Market close
```

---

## 🪟 Windows Setup (Run on Startup)

### **Method 1: Task Scheduler**

1. Open Task Scheduler
2. Create Basic Task
3. Name: "VolatilityHunter Scheduler"
4. Trigger: "When I log on"
5. Action: "Start a program"
6. Program: `C:\Path\To\Python\python.exe`
7. Arguments: `C:\Path\To\VolatilityHunter\scheduler.py`
8. ✅ Done!

### **Method 2: Startup Folder**

1. Press `Win + R`
2. Type: `shell:startup`
3. Create shortcut to `scheduler.py`
4. Restart computer

---

## 🐧 Linux Setup (systemd)

Create `/etc/systemd/system/volatility-hunter.service`:

```ini
[Unit]
Description=VolatilityHunter Scheduler
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/VolatilityHunter
ExecStart=/path/to/python /path/to/VolatilityHunter/scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable volatility-hunter
sudo systemctl start volatility-hunter
sudo systemctl status volatility-hunter
```

---

## 📊 Monitoring

### **Check Logs**

Logs are written to console and can be redirected:

```bash
python scheduler.py > scheduler.log 2>&1
```

### **View Running Process**

Windows:
```powershell
Get-Process python
```

Linux:
```bash
ps aux | grep scheduler.py
```

---

## 🛑 Stopping the Scheduler

### **Interactive Mode**
Press `Ctrl + C`

### **Background Process**
Windows:
```powershell
Stop-Process -Name python
```

Linux:
```bash
pkill -f scheduler.py
```

---

## 🔍 Troubleshooting

### **Email Not Sending**

**Check configuration:**
```python
from src.email_notifier import EmailNotifier
notifier = EmailNotifier()
print(f"Sender: {notifier.sender_email}")
print(f"Recipient: {notifier.recipient_email}")
```

**Common issues:**
- ❌ Using actual Gmail password (use App Password)
- ❌ 2-Step Verification not enabled
- ❌ Wrong SMTP server/port
- ❌ Firewall blocking port 587

### **Scheduler Not Running**

**Check if Python is running:**
```bash
python scheduler.py
```

**Check for errors:**
- Missing dependencies: `pip install -r requirements.txt`
- Wrong Python path in Task Scheduler
- Permissions issues

### **No Signals Found**

- Data might be outdated (run full update)
- Market conditions (no stocks meeting criteria)
- Check logs for errors

---

## 💡 Best Practices

1. **Test email first** before scheduling
2. **Run manually once** to verify everything works
3. **Check logs daily** for the first week
4. **Keep .env secure** (never commit to git)
5. **Monitor email inbox** for alerts

---

## 📈 Expected Results

**Daily Email:**
- Receive at 9:00 AM (or your scheduled time)
- 80-120 BUY signals on average
- 40-60 SELL signals
- Processing time: ~5 minutes

**Weekly Update:**
- Runs Sunday 6:00 AM
- Takes ~15 minutes
- Ensures data quality

---

## 🎉 You're All Set!

Your VolatilityHunter is now fully automated:
- ✅ Daily scans
- ✅ Email alerts
- ✅ 2,150 stocks monitored
- ✅ Zero manual work required

**Happy Trading! 📈🚀**
