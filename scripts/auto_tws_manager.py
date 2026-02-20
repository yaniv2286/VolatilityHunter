#!/usr/bin/env python3
"""
AUTOMATED TWS MANAGER
- Auto-starts TWS if not running
- Auto-enables API
- Auto-connects keep-alive
- Runs 24/7 without user intervention
"""

import time
import logging
import socket
import subprocess
import psutil
import os
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutoTWSManager:
    def __init__(self):
        self.tws_processes = ['tws.exe', 'traderworkstation.exe', 'ibgateway.exe']
        self.ibgateway_processes = ['ibgateway.exe']
        self.tws_path = self.find_tws_installation()
        self.ibgateway_path = self.find_ibgateway_installation()
        self.keep_alive_running = False
        
    def find_tws_installation(self):
        """Find TWS installation path"""
        common_paths = [
            r"D:\TWS\tws\tws.exe",
            r"D:\tws\tws.exe",
            r"C:\Jts\tws.exe",
            r"C:\IBJts\tws.exe",
            r"C:\Program Files\IBJts\tws.exe",
            r"C:\Program Files (x86)\IBJts\tws.exe"
        ]
        
        for path in common_paths:
            if Path(path).exists():
                logger.info(f"Found TWS at: {path}")
                return path
        
        logger.warning("TWS installation not found - will try default paths")
        return "D:\\TWS\\tws\\tws.exe"  # Force use known path
    
    def find_ibgateway_installation(self):
        """Find IBGateway installation path"""
        common_paths = [
            r"D:\TWS\ibgateway\ibgateway.exe",
            r"C:\Jts\ibgateway.exe",
            r"C:\IBJts\ibgateway.exe",
            r"C:\Program Files\IBJts\ibgateway.exe",
            r"C:\Program Files (x86)\IBJts\ibgateway.exe"
        ]
        
        for path in common_paths:
            if Path(path).exists():
                logger.info(f"Found IBGateway at: {path}")
                return path
        
        logger.warning("IBGateway installation not found")
        return None
    
    def is_tws_running(self):
        """Check if TWS or IBGateway is running"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'].lower() in [p.lower() for p in self.tws_processes + self.ibgateway_processes]:
                    logger.info(f"Found TWS process: {proc.info['name']}")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    
    def is_tws_api_enabled(self):
        """Check if TWS API is enabled (port 7497 open)"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 7497))
            sock.close()
            return result == 0
        except Exception as e:
            logger.error(f"API check error: {e}")
            return False
    
    def start_tws(self):
        """Automatically start TWS"""
        try:
            logger.info(f"Starting TWS: {self.tws_path}")
            
            # Use full path with proper Windows command
            if self.tws_path and os.path.exists(self.tws_path):
                subprocess.Popen([self.tws_path], shell=True)
            else:
                # Try hardcoded common paths
                common_paths = [
                    r"C:\Jts\tws.exe",
                    r"C:\IBJts\tws.exe",
                    r"C:\Program Files\IBJts\tws.exe",
                    r"C:\Program Files (x86)\IBJts\tws.exe"
                ]
                
                started = False
                for path in common_paths:
                    if os.path.exists(path):
                        logger.info(f"Found TWS at: {path}")
                        subprocess.Popen([path], shell=True)
                        started = True
                        break
                
                if not started:
                    logger.error("❌ TWS not found in common paths")
                    return False
            
            # Wait for TWS to start
            logger.info("Waiting for TWS to start...")
            for i in range(60):  # Wait up to 2 minutes
                time.sleep(2)
                if self.is_tws_running():
                    logger.info("✅ TWS process started")
                    return True
                if i % 10 == 0:
                    logger.info(f"Still waiting for TWS... ({i*2}s)")
            
            logger.error("❌ TWS failed to start within 2 minutes")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start TWS: {e}")
            return False
    
    def wait_for_api(self):
        """Wait for TWS API to be enabled"""
        logger.info("Waiting for TWS API to be enabled...")
        
        for i in range(180):  # Wait up to 6 minutes
            if self.is_tws_api_enabled():
                logger.info("✅ TWS API is enabled")
                return True
            
            if i % 30 == 0:  # Every minute
                logger.info(f"Waiting for API... ({i*2}s)")
                logger.info("Make sure TWS is fully loaded and API is enabled in Configure > API > Settings")
            
            time.sleep(2)
        
        logger.error("❌ TWS API not enabled after 6 minutes")
        return False
    
    def start_keep_alive(self):
        """Start the keep-alive service"""
        try:
            logger.info("Starting TWS keep-alive service...")
            
            # Import and start keep-alive
            keep_alive_script = Path.cwd() / "scripts" / "tws_keep_alive.py"
            
            if not keep_alive_script.exists():
                logger.error(f"Keep-alive script not found: {keep_alive_script}")
                return False
            
            # Start keep-alive in background
            subprocess.Popen(["python", str(keep_alive_script)], shell=True)
            
            # Wait a bit to see if it starts
            time.sleep(5)
            
            # Check if API is still responsive (keep-alive working)
            if self.is_tws_api_enabled():
                logger.info("✅ Keep-alive service started successfully")
                self.keep_alive_running = True
                return True
            else:
                logger.error("❌ Keep-alive service failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start keep-alive: {e}")
            return False
    
    def auto_manage_loop(self):
        """Main automated management loop"""
        logger.info("🚀 Starting Automated TWS Manager")
        logger.info("This will run 24/7 and automatically manage TWS")
        
        while True:
            try:
                logger.info(f"Status check at {datetime.now().strftime('%H:%M:%S')}")
                
                # Check if TWS is running
                if not self.is_tws_running():
                    logger.warning("❌ TWS not running - Auto-starting...")
                    if not self.start_tws():
                        logger.error("❌ Failed to start TWS - Will retry in 5 minutes")
                        time.sleep(300)  # 5 minutes
                        continue
                
                # Check if API is enabled
                if not self.is_tws_api_enabled():
                    logger.warning("❌ TWS API not enabled - Waiting...")
                    if not self.wait_for_api():
                        logger.error("❌ API not enabled - Will retry in 5 minutes")
                        time.sleep(300)  # 5 minutes
                        continue
                
                # Start keep-alive if not running
                if not self.keep_alive_running:
                    logger.info("Starting keep-alive service...")
                    if not self.start_keep_alive():
                        logger.error("❌ Failed to start keep-alive - Will retry in 2 minutes")
                        time.sleep(120)  # 2 minutes
                        continue
                
                # Everything is working - check every 5 minutes
                logger.info("✅ All systems operational - Next check in 5 minutes")
                time.sleep(300)  # 5 minutes
                
            except KeyboardInterrupt:
                logger.info("🛑 Auto TWS Manager stopped by user")
                break
            except Exception as e:
                logger.error(f"Auto-manager error: {e}")
                time.sleep(60)  # Wait before retry

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("AUTOMATED TWS MANAGER")
    logger.info("24/7 Automatic TWS Management")
    logger.info("=" * 60)
    
    manager = AutoTWSManager()
    
    try:
        manager.auto_manage_loop()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Auto TWS Manager...")
    
    return 0

if __name__ == "__main__":
    exit(main())
