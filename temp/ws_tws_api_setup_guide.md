# 🔧 TWS API SETUP GUIDE

## 🚨 **TWS API NOT ENABLED - ACTION REQUIRED**

---

## 📋 **CURRENT STATUS**
```
✅ TWS Process: FOUND (tws.exe running)
❌ TWS API: NOT ENABLED
⏳ Status: Waiting for API to be enabled...
```

---

## 🔧 **ENABLE TWS API - STEP BY STEP**

### **1. OPEN TWS APPLICATION**
- Launch TWS (Trader Workstation)
- Wait for it to fully load
- Log in to your account

### **2. NAVIGATE TO API SETTINGS**
```
📋 Path: Configure > API > Settings
```

### **3. ENABLE API CONNECTION**
```
✅ Check "Enable ActiveX and Socket Clients"
✅ Check "Read-Only API" (optional, for safety)
🔢 Socket Port: 7497 (default)
🔢 Client ID: 0 (default)
🌐 Local Host: 127.0.0.1
```

### **4. CONFIGURE API SETTINGS**
```
📊 API Settings:
   • Enable ActiveX and Socket Clients: ✅ CHECKED
   • Socket port: 7497
   • Client ID: 0
   • Read-Only API: ✅ CHECKED (recommended for safety)
   • Master API Client ID: 0
   • Order Type: All orders
   • Allow connections from localhost: ✅ CHECKED
```

### **5. SAVE AND RESTART**
```
💾 Click "Apply" or "OK"
🔄 Restart TWS for changes to take effect
```

---

## 🔄 **AUTOMATION WORKFLOW**

### **✅ AFTER API IS ENABLED:**
1. **TWS Manager** will detect API is enabled
2. **Keep-alive service** will start automatically
3. **Portfolio synchronization** will begin
4. **24/7 monitoring** will be active

### **📊 EXPECTED OUTPUT:**
```
✅ Successfully connected to TWS
✅ Portfolio synchronized successfully
✅ Keep-alive service started successfully
✅ All systems operational - Next check in 5 minutes
```

---

## 🛠️ **TROUBLESHOOTING**

### **❌ IF API STILL NOT ENABLED:**

#### **Check 1: TWS Version**
- Ensure you're using TWS version 10.19+
- Older versions may have different API settings

#### **Check 2: Port Conflicts**
- Make sure port 7497 is not blocked
- Check firewall settings
- Try alternative port (7496, 7498)

#### **Check 3: Multiple TWS Instances**
- Close all TWS instances
- Restart single TWS instance
- Enable API before logging in

#### **Check 4: IB Gateway Alternative**
- Use IB Gateway instead of TWS
- IB Gateway has simpler API setup
- More stable for automated trading

---

## 🚀 **QUICK FIX COMMANDS**

### **RESTART TWS MANAGER (after API enabled):**
```bash
# Stop current task
schtasks /end /tn "Auto_TWS_Manager"

# Start manually for testing
scripts/DAILY_ROUTINE/run_auto_tws_manager.bat

# Or restart scheduled task
schtasks /run /tn "Auto_TWS_Manager"
```

### **CHECK API CONNECTION:**
```bash
# Test API connection manually
python -c "
import socket
s = socket.socket()
s.settimeout(5)
try:
    s.connect(('127.0.0.1', 7497))
    print('✅ API port 7497 is open')
except:
    print('❌ API port 7497 is closed')
finally:
    s.close()
"
```

---

## 📋 **VERIFICATION CHECKLIST**

### **✅ BEFORE ENABLING API:**
- [ ] TWS is fully loaded
- [ ] Logged into account
- [ ] No other API clients connected

### **✅ AFTER ENABLING API:**
- [ ] API settings saved
- [ ] TWS restarted
- [ ] API port 7497 is accessible
- [ ] TWS Manager shows "Successfully connected to TWS"

---

## 🎯 **NEXT STEPS**

### **IMMEDIATE ACTION:**
1. **Open TWS now**
2. **Navigate to Configure > API > Settings**
3. **Enable API as shown above**
4. **Restart TWS**
5. **Watch for successful connection message**

### **AUTOMATIC RESULT:**
Once API is enabled, the TWS Manager will automatically:
- ✅ Connect to TWS API
- ✅ Synchronize portfolio
- ✅ Start keep-alive service
- ✅ Begin 24/7 monitoring

---

## 🔄 **CURRENT SCHEDULE**

### **TWS MANAGER STATUS:**
- **Schedule**: Every 5 minutes
- **Next Check**: In ~3 minutes
- **Status**: Waiting for API enable
- **Action**: Manual API enable required

### **AFTER API ENABLE:**
- **Connection**: Immediate
- **Keep-alive**: 5-minute intervals
- **Monitoring**: 24/7 automated
- **Portfolio**: Real-time sync

---

## 🎉 **EXPECTED SUCCESS MESSAGE**

Once API is enabled, you should see:
```
✅ Successfully connected to TWS
✅ Portfolio synchronized successfully
✅ Keep-alive service started successfully
✅ All systems operational - Next check in 5 minutes
```

**Enable the TWS API now and the automation will work perfectly!** 🚀
