#!/usr/bin/env python3
"""
IB Gateway Startup with Retry Logic
Launch IB Gateway via IBC with 120s timeout and 3 retries
"""

import os
import sys
import time
import logging
import subprocess
import socket
import psutil
from pathlib import Path
from datetime import datetime

# Add project root to path
ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT))

from src.notifications import log_info, log_warning, log_error
from src.config import IBC_PATH, TWS_PATH

# Configure logging
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / "gateway_startup.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GatewayStarter:
    """IB Gateway starter with retry logic and IBC integration"""
    
    def __init__(self):
        self.ibc_path = IBC_PATH
        self.tws_path = TWS_PATH
        self.gateway_port = 7497
        
    def is_port_ready(self, port=7497, timeout=2):
        """Check if port is ready for connections"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def find_gateway_process(self):
        """Find existing Gateway process"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline_list = proc.info.get('cmdline', []) or []
                cmdline = ' '.join(cmdline_list).lower()
                if ('ibgateway' in cmdline or 'ibc' in cmdline) and 'java' in cmdline:
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def kill_gateway_process(self):
        """Kill existing Gateway process"""
        logger.info("Killing existing Gateway process...")
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline_list = proc.info.get('cmdline', []) or []
                    cmdline = ' '.join(cmdline_list).lower()
                    if ('ibgateway' in cmdline or 'ibc' in cmdline) and 'java' in cmdline:
                        logger.info(f"Found Gateway process PID {proc.info['pid']}")
                        parent = psutil.Process(proc.info['pid'])
                        children = parent.children(recursive=True)
                        
                        # Kill children first
                        for child in children:
                            child.terminate()
                        parent.terminate()
                        
                        # Wait and force kill if needed
                        gone, alive = psutil.wait_procs([parent] + children, timeout=10)
                        for p in alive:
                            p.kill()
                        
                        logger.info("Gateway process killed successfully")
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error killing Gateway process: {e}")
        
        logger.warning("No Gateway process found to kill")
        return False
    
    def clean_jts_ini(self):
        """Strip saved SSO session tokens and force paper mode + username in jts.ini"""
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        ibkr_user = os.getenv('IBKR_USER', 'yanivl228')
        
        jts_candidates = [
            os.path.join(self.tws_path, "jts.ini"),
            os.path.join(self.tws_path, "ibgateway", "jts.ini"),
            os.path.join(self.tws_path, "ibgateway", "TWSibgateway", "jts.ini"),
        ]
        
        for jts_path in jts_candidates:
            if not os.path.exists(jts_path):
                logger.info(f"jts.ini not found at {jts_path} - skipping")
                continue
            
            logger.info(f"Processing jts.ini at {jts_path}")
            
            try:
                with open(jts_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                cleaned = []
                removed = []
                for line in lines:
                    if '=' in line:
                        key = line.split('=')[0].strip().lower()
                        # Remove problematic entries but preserve ApiOnly
                        if key in ('usernametodirectory', 's3store', 'useremotesettings'):
                            removed.append(line.strip())
                        else:
                            cleaned.append(line)
                    else:
                        cleaned.append(line)
                
                # Force paper mode + username in jts.ini
                final = []
                in_logon = False
                mode_set = False
                user_set = False
                
                for line in cleaned:
                    stripped = line.strip()
                    if stripped.startswith('['):
                        if in_logon:
                            if not mode_set:
                                final.append('tradingMode=p')
                                mode_set = True
                            if not user_set:
                                final.append(f'Username={ibkr_user}')
                                user_set = True
                        in_logon = stripped.lower() == '[logon]'
                        final.append(line)
                        continue
                    
                    key = line.split('=')[0].strip().lower()
                    if in_logon and key == 'tradingmode':
                        final.append('tradingMode=p')
                        mode_set = True
                    elif in_logon and key == 'username':
                        final.append(f'Username={ibkr_user}')
                        user_set = True
                    else:
                        final.append(line)
                
                # PERMANENT GUARD: Delete [Logon] section and rewrite from scratch
                final_lines = []
                skip_logon = False
                
                for line in final:
                    stripped = line.strip().lower()
                    
                    # Skip [Logon] section
                    if stripped == '[logon]':
                        skip_logon = True
                        continue
                    elif stripped.startswith('[') and skip_logon:
                        skip_logon = False
                        final_lines.append(line)
                    elif not skip_logon:
                        final_lines.append(line)
                
                # Rewrite [Logon] section from scratch with permanent guard
                # Do NOT include Username/Password to prevent IBC auto-login
                # Ghost-Typist will handle credential injection
                final_lines.extend([
                    '[Logon]',
                    'Logon.API=IB',
                    'TradingMode=p'
                ])
                
                logger.info("PERMANENT GUARD: Rewrote [Logon] section from scratch")
                logger.info("PERMANENT GUARD: Logon.API=IB (FIX CTCI permanently blocked)")
                logger.info(f"PERMANENT GUARD: LastUser={ibkr_user} (path bug eliminated)")
                
                final = final_lines
                
                with open(jts_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(final) + '\n')
                
                logger.info(f"jts.ini updated: paper mode + username in [Logon] section in {jts_path}")
                logger.info(f"Removed {len(removed)} problematic entries: {removed}")
                
                # TOTAL LOCKDOWN: Wait for OS to finish flushing file to disk
                logger.info("TOTAL LOCKDOWN: Waiting 2 seconds for OS to flush jts.ini to disk...")
                time.sleep(2)
                logger.info("TOTAL LOCKDOWN: jts.ini flush complete")
                
            except Exception as e:
                logger.warning(f"Could not clean jts.ini at {jts_path}: {e}")

    def launch_gateway_via_ibc(self):
        """Launch Gateway using IBC method (reusing auto_tws_manager.py logic)"""
        logger.info("Launching Gateway via IBC...")
        
        # Kill any existing Gateway first
        self.kill_gateway_process()
        
        # Wait a moment for cleanup
        time.sleep(2)
        
        # DO NOT MODIFY jts.ini - Gateway is already configured for IB API mode
        # Modifying it switches from IB API to CTCI which breaks Ghost-Typist
        # self.clean_jts_ini()
        
        try:
            # Build IBC command
            ibc_script = os.path.join(self.ibc_path, "StartGateway.bat")
            if not os.path.exists(ibc_script):
                ibc_script = os.path.join(self.ibc_path, "scripts", "StartGateway.bat")
            
            if not os.path.exists(ibc_script):
                logger.error(f"IBC script not found at {ibc_script}")
                return False
            
            # Launch IBC
            logger.info(f"Running IBC script: {ibc_script}")
            process = subprocess.Popen(
                [str(ibc_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.ibc_path)
            )
            
            # Spawn Ghost-Typist immediately (hands start moving when red screen appears)
            logger.info("Spawning Ghost-Typist for credential injection...")
            ghost_process = subprocess.Popen(
                [sys.executable, "scripts/ibc_login_helper.py"],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            logger.info(f"Ghost-Typist spawned with PID {ghost_process.pid}")
            
            # Give IBC time to start Gateway
            time.sleep(5)
            
            # Check if Gateway process started
            gateway_pid = self.find_gateway_process()
            if gateway_pid:
                logger.info(f"Gateway process started with PID {gateway_pid}")
                return True
            else:
                logger.error("Gateway process not found after IBC launch")
                return False
                
        except Exception as e:
            logger.error(f"Error launching Gateway via IBC: {e}")
            return False
    
    def wait_for_api(self, timeout=120):
        """Wait for Gateway API to be ready"""
        logger.info(f"Waiting for Gateway API on port {self.gateway_port} (timeout: {timeout}s)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_port_ready(self.gateway_port):
                logger.info(f"Gateway API ready on port {self.gateway_port}")
                return True
            time.sleep(2)  # Check every 2 seconds
        
        logger.error(f"Gateway API not ready after {timeout}s")
        return False
    
    def start_with_retry(self, max_attempts=3):
        """Start Gateway with retry logic"""
        logger.info(f"Starting Gateway startup with {max_attempts} attempts")
        
        for attempt in range(1, max_attempts + 1):
            logger.info(f"--- Attempt {attempt}/{max_attempts} ---")
            
            try:
                # Launch Gateway
                if self.launch_gateway_via_ibc():
                    # Wait for API
                    if self.wait_for_api(timeout=120):
                        logger.info("Gateway started successfully")
                        return 0  # Success
                    else:
                        logger.error(f"Attempt {attempt} failed - API not ready after 120s")
                        self.kill_gateway_process()
                else:
                    logger.error(f"Attempt {attempt} failed - IBC launch failed")
                
            except Exception as e:
                logger.error(f"Attempt {attempt} failed with exception: {e}")
                self.kill_gateway_process()
            
            if attempt < max_attempts:
                logger.info("Waiting 10 seconds before retry...")
                time.sleep(10)
        
        logger.error(f"All {max_attempts} attempts failed")
        return 1  # Failure

def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("IB Gateway Startup with Retry Logic")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    starter = GatewayStarter()
    exit_code = starter.start_with_retry(max_attempts=3)
    
    logger.info(f"Gateway startup completed with exit code: {exit_code}")
    logger.info("=" * 60)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
