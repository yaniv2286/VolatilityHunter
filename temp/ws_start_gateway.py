import os
import sys
import subprocess
import time
from pathlib import Path

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, '.env'))

def start_gateway():
    """Direct IB Gateway launcher with correct config"""
    try:
        # Paths
        ibc_jar = Path("C:/IBC/IBC.jar")
        gateway_jars = list(Path("D:/TWS/ibgateway/jars").glob("*.jar"))
        classpath = str(ibc_jar) + ";" + ";".join(str(j) for j in gateway_jars)
        
        # Java 17 path
        java_exe = "C:/Users/Yaniv/AppData/Local/Programs/Common/i4j_jres/Oda-jK0QgTEmVssfllLP/17.0.16.0.101-zulu_64/bin/javaw.exe"
        
        # Command
        add_opens = [
            "--add-opens=java.desktop/javax.swing=ALL-UNNAMED",
            "--add-opens=java.desktop/javax.swing.plaf.basic=ALL-UNNAMED",
            "--add-opens=java.desktop/sun.awt=ALL-UNNAMED",
            "--add-opens=java.desktop/sun.swing=ALL-UNNAMED",
            "--add-opens=java.base/java.lang=ALL-UNNAMED",
            "--add-opens=java.base/java.util=ALL-UNNAMED",
        ]
        
        cmd = [
            java_exe, *add_opens,
            "-cp", classpath,
            "ibcalpha.ibc.IbcGateway",
            "C:/IBC/config.ini",
            "D:/TWS/ibgateway",
            "paper",
        ]
        
        print("Starting IB Gateway with correct config...")
        print(f"Command: {' '.join(cmd[:5])}...")
        
        # Start process
        process = subprocess.Popen(cmd, cwd="D:/TWS/ibgateway")
        print(f"Gateway started (PID {process.pid})")
        
        # Wait for API
        print("Waiting for API on port 7497...")
        for i in range(60):  # 1 minute
            time.sleep(1)
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
        
        print("❌ API did not start within 60 seconds")
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    start_gateway()
