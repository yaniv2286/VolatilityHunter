#!/usr/bin/env python3
"""
IBGateway Launcher - Better than TWS for automation
- Auto-login
- Lightweight
- No GUI crashes
- Perfect for 24/7 operation
"""

import subprocess
from pathlib import Path

def find_ibgateway():
    """Find IBGateway installation"""
    common_paths = [
        r"C:\Jts\ibgateway.exe",
        r"C:\IBJts\ibgateway.exe",
        r"C:\Program Files\IBJts\ibgateway.exe",
        r"C:\Program Files (x86)\IBJts\ibgateway.exe",
        r"D:\TWS\ibgateway\ibgateway.exe"
    ]
    
    for path in common_paths:
        if Path(path).exists():
            return path
    
    return None

def launch_ibgateway():
    """Launch IBGateway for automation"""
    gateway_path = find_ibgateway()
    
    if not gateway_path:
        print("❌ IBGateway not found!")
        print("Please download and install IBGateway from:")
        print("https://www.interactivebrokers.com/en/trading/ibgateway-standalone.php")
        return False
    
    print(f"🚀 Launching IBGateway: {gateway_path}")
    print("✅ IBGateway is better for automation:")
    print("  - Auto-login")
    print("  - Lightweight")
    print("  - No GUI crashes")
    print("  - Perfect for 24/7 operation")
    
    try:
        subprocess.Popen([gateway_path], shell=True)
        print("✅ IBGateway launched!")
        print("📋 Next steps:")
        print("  1. Login with your credentials")
        print("  2. Enable API (Configure > API > Settings)")
        print("  3. Set port to 7497")
        print("  4. Check 'Save login info'")
        print("  5. The auto-manager will handle the rest")
        return True
    except Exception as e:
        print(f"❌ Failed to launch IBGateway: {e}")
        return False

if __name__ == "__main__":
    launch_ibgateway()
