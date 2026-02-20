#!/usr/bin/env python3
"""
TWS Keep-Alive Script
Prevents TWS from auto-logging out by maintaining connection
"""

import time
import logging
import socket
from datetime import datetime
from ib_insync import IB, util

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TWSKeepAlive:
    def __init__(self, host='127.0.0.1', port=7497, client_id=999):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()
        self.connected = False
        
    def check_port_open(self):
        """Check if TWS port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.error(f"Port check error: {e}")
            return False
    
    def connect_to_tws(self):
        """Connect to TWS/Gateway"""
        try:
            if not self.check_port_open():
                logger.error(f"TWS port {self.port} is CLOSED - Start TWS first!")
                return False
                
            logger.info(f"Connecting to TWS at {self.host}:{self.port}...")
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            
            if self.ib.isConnected():
                logger.info("✅ Successfully connected to TWS")
                self.connected = True
                return True
            else:
                logger.error("❌ Failed to connect to TWS")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def keep_alive_loop(self, interval=300):  # 5 minutes
        """Main keep-alive loop"""
        logger.info(f"Starting TWS Keep-Alive - Heartbeat every {interval} seconds")
        logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        while True:
            try:
                if not self.ib.isConnected():
                    logger.warning("❌ TWS disconnected - Attempting to reconnect...")
                    if self.connect_to_tws():
                        logger.info("✅ Reconnected to TWS")
                    else:
                        logger.error("❌ Reconnection failed - Will retry in 60 seconds")
                        time.sleep(60)
                        continue
                
                # Send heartbeat request to keep session alive
                try:
                    # Request account data as heartbeat
                    self.ib.reqAccountSummary('all', 'AccountType')
                    logger.info(f"💓 Heartbeat sent at {datetime.now().strftime('%H:%M:%S')}")
                    
                except Exception as e:
                    logger.warning(f"Heartbeat failed: {e}")
                
                # Wait for next heartbeat
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 TWS Keep-Alive stopped by user")
                break
            except Exception as e:
                logger.error(f"Keep-alive error: {e}")
                time.sleep(60)  # Wait before retry
    
    def disconnect(self):
        """Clean disconnect"""
        try:
            if self.ib.isConnected():
                self.ib.disconnect()
                logger.info("✅ Disconnected from TWS")
        except Exception as e:
            logger.error(f"Disconnect error: {e}")

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("TWS KEEP-ALIVE SERVICE")
    logger.info("=" * 60)
    
    keep_alive = TWSKeepAlive()
    
    try:
        # Initial connection
        if keep_alive.connect_to_tws():
            # Start keep-alive loop
            keep_alive.keep_alive_loop()
        else:
            logger.error("❌ Cannot start keep-alive - TWS not available")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down TWS Keep-Alive...")
    finally:
        keep_alive.disconnect()
    
    return 0

if __name__ == "__main__":
    exit(main())
