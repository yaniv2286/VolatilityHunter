import os
import sys
import time
import subprocess
from pathlib import Path

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, '.env'))

def start_and_login():
    """Start Gateway and manually fill credentials"""
    try:
        # Start Gateway using IBC
        print("Starting IB Gateway with IBC...")
        ibc_cmd = [
            "C:/Users/Yaniv/AppData/Local/Programs/Common/i4j_jres/Oda-jK0QgTEmVssfllLP/17.0.16.0.101-zulu_64/bin/javaw.exe",
            "--add-opens=java.desktop/javax.swing=ALL-UNNAMED",
            "--add-opens=java.desktop/javax.swing.plaf.basic=ALL-UNNAMED", 
            "--add-opens=java.desktop/sun.awt=ALL-UNNAMED",
            "--add-opens=java.desktop/sun.swing=ALL-UNNAMED",
            "--add-opens=java.base/java.lang=ALL-UNNAMED",
            "--add-opens=java.base/java.util=ALL-UNNAMED",
            "-cp", "C:/IBC/IBC.jar;D:/TWS/ibgateway/jars/*",
            "ibcalpha.ibc.IbcGateway",
            "C:/IBC/config.ini",
            "D:/TWS/ibgateway",
            "paper"
        ]
        
        # Start Gateway
        process = subprocess.Popen(ibc_cmd, cwd="D:/TWS/ibgateway")
        print(f"Gateway started (PID {process.pid})")
        
        # Wait for window
        print("Waiting for login window...")
        time.sleep(10)
        
        # Start login helper
        print("Starting login helper...")
        helper_script = ROOT / "scripts" / "ibc_login_helper.py"
        if helper_script.exists():
            subprocess.Popen([sys.executable, str(helper_script)])
            print("Login helper started")
        
        # Wait for API
        print("Waiting for API port 7497...")
        for i in range(60):
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', 7497))
                sock.close()
                if result == 0:
                    print(f"✅ API ready on port 7497 (after {i+1}s)")
                    return True
            except:
                pass
            if i % 10 == 0:
                print(f"Still waiting... ({i+1}s)")
            time.sleep(1)
        
        print("❌ API did not start within 60 seconds")
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    start_and_login()
