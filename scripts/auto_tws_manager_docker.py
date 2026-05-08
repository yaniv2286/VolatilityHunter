#!/usr/bin/env python3
"""
AUTOMATED TWS MANAGER (Docker IBeam Edition)
=============================================
Headless IBKR Gateway management using Docker IBeam container.
Eliminates GUI automation, PyAutoGUI, and window focus dependencies.

- Launches IBeam via docker-compose
- Polls Port 7497 for API readiness
- Completely headless (no GUI interaction)
- Works in Session 0 (Task Scheduler compatible)

Modes:
  - Watchdog mode (default): Runs indefinitely, monitoring Gateway health
  - One-shot mode (--one-shot): Launches Gateway, waits for API ready, then exits

Requirements:
  - Docker Desktop installed and running
  - docker-compose.yml in project root
  - IBKR_PASSWORD in .env file
"""

import os
import sys
import time
import socket
import logging
import subprocess
import traceback
import argparse
from datetime import datetime
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────
ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# ── Logging (ASCII only) ───────────────────────────────────────────────────
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_DIR / "auto_tws_manager.log"), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("auto_tws_manager_docker")

# ── Config ─────────────────────────────────────────────────────────────────
IBKR_PASSWORD = os.getenv("IBKR_PASSWORD", "")
TWS_PORT = 7497
API_WAIT_SECS = 180  # max seconds to wait for API after Gateway starts
CHECK_INTERVAL = 300  # health check every 5 minutes

DOCKER_COMPOSE_FILE = ROOT / "docker-compose.yml"


class DockerGatewayManager:
    """Manages IBKR Gateway via Docker IBeam container."""
    
    def __init__(self):
        self._api_last_seen_up = None
        self._api_closed_since = None
        self.USER_GRACE_PERIOD = 300
    
    # ── Docker Operations ────────────────────────────────────────────────
    
    def is_docker_running(self) -> bool:
        """Check if Docker Desktop is running."""
        try:
            result = subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                timeout=10,
                check=False
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Docker check failed: {e}")
            return False
    
    def start_gateway_via_docker(self) -> bool:
        """
        Launch IBeam Gateway via docker-compose.
        Completely headless - no GUI automation required.
        """
        if not DOCKER_COMPOSE_FILE.exists():
            logger.error(f"docker-compose.yml not found at {DOCKER_COMPOSE_FILE}")
            return False
        
        if not self.is_docker_running():
            logger.error("Docker Desktop is not running")
            logger.error("Please start Docker Desktop and try again")
            return False
        
        logger.info("Launching IBeam Gateway via Docker...")
        
        try:
            # Stop any existing containers first
            logger.info("Stopping existing IBeam containers...")
            subprocess.run(
                ['docker-compose', 'down'],
                cwd=str(ROOT),
                capture_output=True,
                timeout=30,
                check=False
            )
            
            # Start IBeam container
            logger.info("Starting IBeam container...")
            result = subprocess.run(
                ['docker-compose', 'up', '-d'],
                cwd=str(ROOT),
                capture_output=True,
                timeout=180,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"docker-compose up failed: {result.stderr}")
                return False
            
            logger.info("IBeam container started successfully")
            logger.info(result.stdout)
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("docker-compose command timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to start Docker container: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def stop_gateway(self) -> bool:
        """Stop IBeam Gateway container."""
        logger.info("Stopping IBeam Gateway container...")
        
        try:
            result = subprocess.run(
                ['docker-compose', 'down'],
                cwd=str(ROOT),
                capture_output=True,
                timeout=30,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("IBeam container stopped successfully")
                return True
            else:
                logger.error(f"docker-compose down failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to stop Docker container: {e}")
            return False
    
    def get_container_status(self) -> str:
        """Get IBeam container status."""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--filter', 'name=volatilityhunter_gateway', '--format', '{{.Status}}'],
                capture_output=True,
                timeout=10,
                text=True,
                check=False
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return "Not running"
            
        except Exception as e:
            logger.error(f"Failed to get container status: {e}")
            return "Unknown"
    
    # ── API Readiness Check ──────────────────────────────────────────────
    
    def ping_gateway_until_ready(self, max_wait_seconds=180) -> bool:
        """
        Robust polling mechanism for Gateway API readiness.
        Attempts TCP socket connection to 127.0.0.1:7497 every 5 seconds.
        
        Args:
            max_wait_seconds: Maximum time to wait for API (default 180s = 3 minutes)
        
        Returns:
            True if API becomes ready, False if timeout
        """
        logger.info(f"Waiting for Gateway API on port {TWS_PORT} (timeout: {max_wait_seconds}s)...")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < max_wait_seconds:
            attempt += 1
            
            try:
                # Attempt TCP connection to Gateway API port
                with socket.create_connection(('127.0.0.1', TWS_PORT), timeout=2):
                    elapsed = time.time() - start_time
                    logger.info(f"Gateway API ready on port {TWS_PORT} after {elapsed:.1f}s (attempt {attempt})")
                    return True
                    
            except (socket.timeout, ConnectionRefusedError, OSError) as e:
                # API not ready yet - this is expected during startup
                if attempt % 6 == 0:  # Log every 30 seconds (6 attempts * 5s)
                    elapsed = time.time() - start_time
                    logger.info(f"Still waiting for API... ({elapsed:.0f}s elapsed, attempt {attempt})")
                
                time.sleep(5)
                continue
        
        # Timeout reached
        elapsed = time.time() - start_time
        logger.error(f"Gateway API not ready after {elapsed:.1f}s ({attempt} attempts)")
        logger.error(f"Port {TWS_PORT} never became available")
        
        # Check container status for debugging
        status = self.get_container_status()
        logger.error(f"Container status: {status}")
        
        return False
    
    def is_api_ready(self) -> bool:
        """Quick check if Gateway API is currently reachable."""
        try:
            with socket.create_connection(('127.0.0.1', TWS_PORT), timeout=2):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
    
    # ── Watchdog Mode ────────────────────────────────────────────────────
    
    def run_watchdog(self):
        """
        Watchdog mode: Monitor Gateway health indefinitely.
        Restarts container if API becomes unreachable.
        """
        logger.info("=" * 60)
        logger.info("DOCKER GATEWAY MANAGER - WATCHDOG MODE")
        logger.info("=" * 60)
        
        while True:
            try:
                # Check if API is reachable
                if self.is_api_ready():
                    if self._api_closed_since:
                        # API recovered
                        logger.info("Gateway API recovered")
                        self._api_closed_since = None
                    
                    self._api_last_seen_up = datetime.now()
                    
                else:
                    # API not reachable
                    if not self._api_closed_since:
                        self._api_closed_since = datetime.now()
                        logger.warning(f"Gateway API not reachable on port {TWS_PORT}")
                    
                    # Check if grace period exceeded
                    downtime = (datetime.now() - self._api_closed_since).total_seconds()
                    if downtime > self.USER_GRACE_PERIOD:
                        logger.error(f"Gateway API down for {downtime:.0f}s - restarting container...")
                        
                        # Restart container
                        self.stop_gateway()
                        time.sleep(5)
                        
                        if self.start_gateway_via_docker():
                            if self.ping_gateway_until_ready(API_WAIT_SECS):
                                logger.info("Gateway restarted successfully")
                                self._api_closed_since = None
                            else:
                                logger.error("Gateway restart failed - API not ready")
                        else:
                            logger.error("Failed to restart Gateway container")
                
                # Sleep until next check
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Watchdog interrupted by user")
                break
            except Exception as e:
                logger.error(f"Watchdog error: {e}")
                logger.error(traceback.format_exc())
                time.sleep(60)
    
    # ── One-Shot Mode ────────────────────────────────────────────────────
    
    def run_one_shot(self) -> bool:
        """
        One-shot mode: Launch Gateway, wait for API ready, then exit.
        Returns True if successful, False otherwise.
        """
        logger.info("=" * 60)
        logger.info("DOCKER GATEWAY MANAGER - ONE-SHOT MODE")
        logger.info("=" * 60)
        
        # Launch Gateway
        if not self.start_gateway_via_docker():
            logger.error("Failed to launch Gateway")
            return False
        
        # Wait for API readiness
        if not self.ping_gateway_until_ready(API_WAIT_SECS):
            logger.error("Gateway API never became ready")
            return False
        
        logger.info("Gateway Online - API ready")
        logger.info("Gateway API ready - ONE-SHOT mode complete")
        logger.info("Headless Gateway successfully launched and ready")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Docker IBeam Gateway Manager")
    parser.add_argument('--one-shot', action='store_true',
                       help='Launch Gateway, wait for API ready, then exit')
    args = parser.parse_args()
    
    manager = DockerGatewayManager()
    
    if args.one_shot:
        # One-shot mode: Launch and exit
        success = manager.run_one_shot()
        sys.exit(0 if success else 1)
    else:
        # Watchdog mode: Monitor indefinitely
        manager.run_watchdog()


if __name__ == "__main__":
    main()
