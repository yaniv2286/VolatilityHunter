#!/usr/bin/env python3
"""
IB Gateway Stopper
Gracefully shutdown IB Gateway with process tree kill
"""

import os
import sys
import time
import logging
import psutil
from pathlib import Path
from datetime import datetime

# Add project root to path
ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT))

from src.notifications import log_info, log_warning, log_error

# Configure logging
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / "gateway_stop.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GatewayStopper:
    """IB Gateway stopper with process tree kill"""
    
    def __init__(self):
        self.gateway_processes = []
        
    def find_gateway_processes(self):
        """Find all Gateway-related processes"""
        gateway_pids = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline_list = proc.info.get('cmdline', []) or []
                cmdline = ' '.join(cmdline_list).lower()
                if ('ibgateway' in cmdline or 'ibc' in cmdline) and 'java' in cmdline:
                    gateway_pids.append(proc.info['pid'])
                    logger.info(f"Found Gateway process PID {proc.info['pid']}: {proc.info['name']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
                continue
        
        self.gateway_processes = gateway_pids
        return gateway_pids
    
    def stop_gateway(self):
        """Stop Gateway with graceful then force kill"""
        logger.info("Stopping IB Gateway...")
        
        # Find Gateway processes
        gateway_pids = self.find_gateway_processes()
        
        if not gateway_pids:
            logger.warning("No Gateway processes found (already stopped?)")
            return 0
        
        # Kill each Gateway process tree
        for pid in gateway_pids:
            try:
                parent = psutil.Process(pid)
                children = parent.children(recursive=True)
                
                logger.info(f"Stopping Gateway process {pid} with {len(children)} children")
                
                # Terminate children first
                for child in children:
                    try:
                        child.terminate()
                        logger.debug(f"Terminated child process {child.pid}")
                    except psutil.NoSuchProcess:
                        pass
                
                # Terminate parent
                parent.terminate()
                logger.debug(f"Terminated parent process {pid}")
                
                # Wait for graceful shutdown
                all_procs = [parent] + children
                gone, alive = psutil.wait_procs(all_procs, timeout=30)
                
                # Force kill any remaining processes
                for p in alive:
                    try:
                        p.kill()
                        logger.debug(f"Force killed process {p.pid}")
                    except psutil.NoSuchProcess:
                        pass
                
                logger.info(f"Gateway process {pid} stopped successfully")
                
            except psutil.NoSuchProcess:
                logger.warning(f"Process {pid} already terminated")
            except Exception as e:
                logger.error(f"Error stopping process {pid}: {e}")
        
        # Final verification
        time.sleep(2)
        remaining = self.find_gateway_processes()
        
        if remaining:
            logger.error(f"Failed to stop all Gateway processes. Still running: {remaining}")
            return 1
        else:
            logger.info("All Gateway processes stopped successfully")
            return 0

def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("IB Gateway Stopper")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    stopper = GatewayStopper()
    exit_code = stopper.stop_gateway()
    
    logger.info(f"Gateway stop completed with exit code: {exit_code}")
    logger.info("=" * 60)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
