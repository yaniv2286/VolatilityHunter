#!/usr/bin/env python3
"""
Stop Gateway (Docker Edition)
==============================
Stops the IBeam Gateway Docker container.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stop_gateway_docker")

def stop_gateway():
    """Stop IBeam Gateway container via docker-compose."""
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
            logger.info(result.stdout)
            return 0
        else:
            logger.error(f"docker-compose down failed: {result.stderr}")
            return 1
            
    except Exception as e:
        logger.error(f"Failed to stop Docker container: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(stop_gateway())
