# 🪟 Windows Task Scheduler Setup Guide

Complete guide to run VolatilityHunter automatically on Windows with proper power management.

---

## 📅 Method 1: Windows Task Scheduler (Recommended)

### **Step 1: Create the Task**

1. Press `Win + R` and type: `taskschd.msc`
2. Click **Create Basic Task**
3. Name: `VolatilityHunter Daily Scan`
4. Description: `Automated stock scanner with email alerts`
5. Click **Next**

### **Step 2: Set Trigger**

1. Select **Daily**
2. Start date: Today
3. Start time: `09:00:00` (9:00 AM)
4. Recur every: `1` days
5. Click **Next**

### **Step 3: Set Action**

1. Select **Start a program**
2. Program/script: `C:\Path\To\Python\python.exe`
   - Find your Python path: `where python` in PowerShell
   - Example: `D:\GitHub\VolatilityHunter\venv\Scripts\python.exe`
3. Add arguments: `scheduler.py`
4. Start in: `D:\GitHub\VolatilityHunter`
5. Click **Next**, then **Finish**

### **Step 4: Configure Advanced Settings**

1. Right-click the task → **Properties**
2. Go to **General** tab:
   - ✅ Check **Run whether user is logged on or not**
   - ✅ Check **Run with highest privileges**
   - ✅ Check **Hidden** (optional)

3. Go to **Conditions** tab:
   - ❌ Uncheck **Start the task only if the computer is on AC power**
   - ❌ Uncheck **Stop if the computer switches to battery power**
   - ✅ Check **Wake the computer to run this task**

4. Go to **Settings** tab:
   - ✅ Check **Allow task to be run on demand**
   - ✅ Check **Run task as soon as possible after a scheduled start is missed**
   - ✅ Check **If the task fails, restart every: 1 minute**
   - Set **Attempt to restart up to: 3 times**
   - ❌ Uncheck **Stop the task if it runs longer than**

5. Click **OK**

---

## ⚡ Power Settings Configuration

### **Prevent Sleep/Hibernate During Scans**

#### **Option 1: Disable Sleep (Recommended for Desktop)**

1. Press `Win + X` → **Power Options**
2. Click **Additional power settings**
3. Select your power plan → **Change plan settings**
4. **Put the computer to sleep**: Set to **Never**
5. Click **Change advanced power settings**
6. Expand **Sleep**:
   - **Sleep after**: Set to **Never**
   - **Hibernate after**: Set to **Never**
7. Expand **Hard disk**:
   - **Turn off hard disk after**: Set to **Never** (or 20 minutes)
8. Click **OK**

#### **Option 2: Wake Timers (For Laptops)**

1. Press `Win + X` → **Power Options**
2. Click **Additional power settings**
3. Select your power plan → **Change plan settings**
4. Click **Change advanced power settings**
5. Expand **Sleep** → **Allow wake timers**:
   - **On battery**: **Enable**
   - **Plugged in**: **Enable**
6. Click **OK**

#### **Option 3: PowerShell Script (Advanced)**

Create a script to prevent sleep during scans:

```powershell
# prevent_sleep.ps1
Add-Type -AssemblyName System.Windows.Forms
$null = [System.Windows.Forms.Application]::SetSuspendState("Suspend", $false, $false)
```

---

## 🔧 Method 2: Run as Windows Service (Advanced)

For always-running scheduler without Task Scheduler:

### **Install NSSM (Non-Sucking Service Manager)**

1. Download NSSM: https://nssm.cc/download
2. Extract to `C:\nssm`
3. Open PowerShell as Administrator
4. Run:

```powershell
cd C:\nssm\win64
.\nssm.exe install VolatilityHunter
```

5. Configure:
   - **Path**: `D:\GitHub\VolatilityHunter\venv\Scripts\python.exe`
   - **Startup directory**: `D:\GitHub\VolatilityHunter`
   - **Arguments**: `scheduler.py`
   - **Service name**: `VolatilityHunter`

6. Click **Install service**

7. Start the service:
```powershell
Start-Service VolatilityHunter
```

---

## 🔍 Verify Scheduler is Running

### **Check Task Scheduler**

1. Open Task Scheduler (`taskschd.msc`)
2. Find **VolatilityHunter Daily Scan**
3. Check **Last Run Result**: Should be `0x0` (success)
4. Check **Next Run Time**: Should show next scheduled time

### **Check Running Process**

```powershell
Get-Process python | Where-Object {$_.Path -like "*VolatilityHunter*"}
```

### **Check Logs**

Create a log file by modifying the task:

1. Task Scheduler → Right-click task → **Properties**
2. **Actions** tab → **Edit**
3. Add arguments: `scheduler.py > scheduler.log 2>&1`
4. Check `D:\GitHub\VolatilityHunter\scheduler.log` for output

---

## 📧 Verify Email Alerts

After the first scheduled run (9:00 AM), check:

1. ✅ Email received at `lugassy.ai@gmail.com`
2. ✅ Subject: "VolatilityHunter Daily Scan - X BUY Signals"
3. ✅ Body contains BUY/SELL signals

---

## 🛠️ Troubleshooting

### **Task Not Running**

**Check task history:**
1. Task Scheduler → View → **Show All Running Tasks**
2. Right-click task → **Properties** → **History** tab

**Common issues:**
- ❌ Python path incorrect → Use full path to `python.exe`
- ❌ Working directory not set → Set "Start in" to project folder
- ❌ Permissions → Run with highest privileges
- ❌ Computer asleep → Enable wake timers

### **Computer Still Sleeping**

**Check power plan:**
```powershell
powercfg /list
powercfg /query SCHEME_CURRENT SUB_SLEEP
```

**Disable hybrid sleep:**
```powershell
powercfg /change hibernate-timeout-ac 0
powercfg /change hibernate-timeout-dc 0
```

### **Task Runs But No Email**

1. Check `.env` file has correct email settings
2. Run `python test_email_direct.py` manually
3. Check Task Scheduler history for errors
4. Check `scheduler.log` for error messages

---

## 🎯 Recommended Setup

**For Desktop PC:**
- ✅ Use Task Scheduler
- ✅ Disable sleep completely
- ✅ Enable wake timers
- ✅ Run with highest privileges

**For Laptop:**
- ✅ Use Task Scheduler
- ✅ Enable wake timers
- ✅ Keep plugged in during scan times
- ✅ Set sleep to 30+ minutes

**For Always-On Server:**
- ✅ Use Windows Service (NSSM)
- ✅ Disable sleep/hibernate
- ✅ Auto-start on boot

---

## 📊 Expected Behavior

**Daily (9:00 AM):**
1. Computer wakes up (if asleep)
2. Task Scheduler starts Python
3. Scheduler updates data (~3 min)
4. Scheduler scans stocks (~2 min)
5. Email sent with results
6. Python exits
7. Computer can sleep again

**Weekly (Sunday 6:00 AM):**
1. Full data refresh (~15 min)
2. Computer stays awake during process

---

## 🔐 Security Notes

- ✅ Task runs under your user account
- ✅ Email password stored in `.env` (not in task)
- ✅ Can be disabled anytime from Task Scheduler
- ❌ Never share `.env` file

---

## 🎉 You're All Set!

Your VolatilityHunter will now:
- ✅ Run automatically every day at 9:00 AM
- ✅ Wake your computer if needed
- ✅ Send email alerts with trading signals
- ✅ Work even if you're not logged in
- ✅ Continue running after power outages (once PC restarts)

**Happy Automated Trading! 📈🚀**
