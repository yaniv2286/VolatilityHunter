#!/usr/bin/env python3
"""
IB GATEWAY SHUTDOWN
===================
Gracefully shutdown IB Gateway after trading completes.
Kills entire process tree (parent + children) for clean shutdown.

Usage: python scripts/stop_gateway.py
"""

import os
import sys
import time
import logging
import psutil
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────
ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

# ── Logging (ASCII only) ───────────────────────────────────────────────────
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_DIR / "gateway_shutdown.log"), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("stop_gateway")

# ── Config ─────────────────────────────────────────────────────────────────
GRACE_PERIOD = 30  # seconds to wait for graceful shutdown


def find_gateway_processes():
    """Find all Gateway-related processes."""
    gateway_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = proc.info['name'].lower()
            cmdline = ' '.join(proc.info.get('cmdline') or []).lower()
            
            # Look for IB Gateway or IBC processes
            if 'ibgateway' in name or 'ibgateway' in cmdline:
                gateway_procs.append(proc)
            elif name == 'javaw.exe' and ('ibgateway' in cmdline or 'ibc' in cmdline):
                gateway_procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return gateway_procs


def kill_process_tree(proc):
    """Kill a process and all its children."""
    try:
        parent = psutil.Process(proc.pid)
        children = parent.children(recursive=True)
        
        logger.info(f"Terminating process tree for PID {proc.pid} ({proc.info['name']})")
        
        # Terminate children first
        for child in children:
            try:
                child.terminate()
                logger.info(f"  Terminated child PID {child.pid}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Terminate parent
        try:
            parent.terminate()
            logger.info(f"  Terminated parent PID {parent.pid}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        # Wait for graceful shutdown
        gone, alive = psutil.wait_procs([parent] + children, timeout=GRACE_PERIOD)
        
        # Force kill any survivors
        for p in alive:
            try:
                p.kill()
                logger.warning(f"  Force killed PID {p.pid} (did not exit gracefully)")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return True
    except Exception as e:
        logger.error(f"Error killing process tree: {e}")
        return False


def stop_gateway():
    """Main entry point: stop all Gateway processes."""
    logger.info("=" * 60)
    logger.info("IB GATEWAY SHUTDOWN")
    logger.info("=" * 60)
    
    # Find all Gateway processes
    gateway_procs = find_gateway_processes()
    
    if not gateway_procs:
        logger.info("No Gateway processes found (already stopped)")
        return 0
    
    logger.info(f"Found {len(gateway_procs)} Gateway process(es)")
    
    # Kill each process tree
    success = True
    for proc in gateway_procs:
        if not kill_process_tree(proc):
            success = False
    
    # Verify all processes are gone
    time.sleep(2)
    remaining = find_gateway_processes()
    
    if remaining:
        logger.warning(f"{len(remaining)} Gateway process(es) still running after shutdown")
        for proc in remaining:
            logger.warning(f"  PID {proc.pid}: {proc.info['name']}")
        return 1
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("SUCCESS: All Gateway processes stopped")
    logger.info("=" * 60)
    return 0


def main():
    exit_code = stop_gateway()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
