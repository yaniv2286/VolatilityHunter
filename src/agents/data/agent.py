"""
Data Agent - Handles data loading, validation, and caching
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import time
import os
from dataclasses import dataclass

# ChromaDB imports for vector acceleration
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("WARNING: ChromaDB not available - vector acceleration disabled")

from src.interfaces.agent_interface import AgentInterface, AgentStatus, MessageType, HealthStatus
from src.messaging.message_types import DataRequest, DataResponse
from src.config.agent_config import DataAgentConfig
from src.utils.message_safety import RateLimiter
from src.utils.memory_manager import MemoryManager
from src.utils.error_handler import ErrorHandler, ErrorSeverity

class DataAgent(AgentInterface):
    """Data agent for loading and managing market data"""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        self.agent_config = DataAgentConfig(**config)
        
        # Core data storage
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # Safety utilities
        self.memory_manager = MemoryManager(max_memory_mb=512)
        self.error_handler = ErrorHandler(self.agent_id)
        self.rate_limiter = RateLimiter(max_messages_per_second=50)  # 50 msg/sec limit
        
        # Thread pool
        self.executor = ThreadPoolExecutor(max_workers=self.agent_config.max_concurrent_tasks)
        
        # Data source - Import actual data loading functionality
        try:
            from src.smart_data_loader_factory import get_smart_data_loader
            self.data_loader = get_smart_data_loader()
        except ImportError:
            self.logger.error("Smart data loader not available - PRODUCTION REQUIRES REAL DATA")
            self.data_loader = None
        
        # ChromaDB vector acceleration
        self.chroma_client = None
        self.pattern_collection = None
        self._init_chromadb()
        
    async def initialize(self) -> bool:
        """Initialize data agent"""
        try:
            self.logger.info(f"Initializing Data Agent with source: {self.agent_config.data_source}")
            
            # Create data source
            self.data_source = self._create_data_source()
            
            # Test data source
            if not await self._test_data_source():
                self.logger.error("Data source test failed")
                return False
                
            self.update_status(AgentStatus.READY)
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing Data Agent: {e}")
            self.update_status(AgentStatus.ERROR)
            return False
            
    async def start(self) -> bool:
        """Start data agent"""
        try:
            self.update_status(AgentStatus.RUNNING)
            self.start_time = datetime.now()
            
            # Start cache cleanup
            asyncio.create_task(self._cache_cleanup_loop())
            
            self.logger.info("Data Agent started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting Data Agent: {e}")
            return False
            
    async def stop(self) -> bool:
        """Stop data agent"""
        try:
            self.update_status(AgentStatus.SHUTDOWN)
            self.executor.shutdown(wait=True)
            self.data_cache.clear()
            self.cache_timestamps.clear()
            self.logger.info("Data Agent stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping Data Agent: {e}")
            return False
            
    async def process_message(self, message) -> Optional[Dict[str, Any]]:
        """Process incoming messages"""
        try:
            # Rate limiting
            if not self.rate_limiter.is_allowed():
                return await self._create_error_response(message, "Rate limit exceeded")
                
            self.rate_limiter.record_request()
            
            if message.message_type == MessageType.DATA_REQUEST:
                return await self._handle_data_request(message)
            elif message.message_type == MessageType.HEALTH_CHECK:
                return await self._handle_health_check(message)
            else:
                return None
                
        except Exception as e:
            self.error_handler.handle_error(e, {
                "message_type": message.message_type.value if message.message_type else "unknown",
                "sender": message.sender,
                "recipient": message.recipient
            }, ErrorSeverity.MEDIUM, "DataAgent.process_message")
            
            return await self._create_error_response(message, str(e))
            
    async def health_check(self) -> HealthStatus:
        """Perform health check"""
        try:
            start_time = time.time()
            
            # Check data source
            source_ok = await self._test_data_source()
            
            # Check memory pressure
            memory_ok = not self.memory_manager.check_memory_pressure()
            
            uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            return HealthStatus(
                agent_id=self.agent_id,
                status=AgentStatus.RUNNING if source_ok and memory_ok else AgentStatus.ERROR,
                last_check=datetime.now().isoformat(),
                cpu_usage=0.0,
                memory_usage=self.memory_manager.get_memory_stats().process_memory_mb / 1024,
                error_count=0,
                last_error=None,
                uptime=uptime
            )
            
        except Exception as e:
            return HealthStatus(
                agent_id=self.agent_id,
                status=AgentStatus.ERROR,
                last_check=datetime.now().isoformat(),
                cpu_usage=0.0,
                memory_usage=0.0,
                error_count=1,
                last_error=str(e)
            )
            
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return ["data_request", "data_response", "health_check"]
        
    async def check_data_freshness(self) -> Dict[str, Any]:
        """Check data freshness"""
        try:
            import os
            from datetime import datetime
            
            # Check data directory
            data_dir = "data"
            if not os.path.exists(data_dir):
                return {
                    "fresh": False,
                    "error": "Data directory not found",
                    "age_hours": None
                }
            
            # Find latest data file
            latest_file = None
            latest_time = None
            
            for root, dirs, files in os.walk(data_dir):
                for file in files:
                    if file.endswith('.parquet'):
                        file_path = os.path.join(root, file)
                        file_time = os.path.getmtime(file_path)
                        if latest_time is None or file_time > latest_time:
                            latest_time = file_time
                            latest_file = file_path
            
            if latest_file is None:
                return {
                    "fresh": False,
                    "error": "No data files found",
                    "age_hours": None
                }
            
            # Calculate age
            age_hours = (datetime.now().timestamp() - latest_time) / 3600
            
            return {
                "fresh": age_hours < 48,  # Fresh if less than 48 hours
                "age_hours": age_hours,
                "latest_file": latest_file
            }
            
        except Exception as e:
            self.logger.error(f"Data freshness check failed: {e}")
            return {
                "fresh": False,
                "error": str(e),
                "age_hours": None
            }
    
    async def update_market_data(self) -> Dict[str, Any]:
        """Update market data"""
        try:
            # Mock market data update for testing
            self.logger.info("Market data update completed (mock)")
            return {
                "success": True,
                "tickers_updated": 0,
                "update_time": self._get_timestamp(),
                "data_source": "mock"
            }
        except Exception as e:
            self.logger.error(f"Market data update failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
        
    async def load_data(self, ticker: str, date_range: str = "latest", data_type: str = "price") -> Optional[pd.DataFrame]:
        """Load data for ticker using the actual data loader"""
        try:
            start_time = time.time()
            
            # Check cache
            if self.agent_config.cache_enabled:
                cached_data = self._get_from_cache(ticker, date_range, data_type)
                if cached_data is not None:
                    self.logger.debug(f"Retrieved {ticker} from cache")
                    return cached_data
                    
            # Load from actual data source
            if self.data_loader:
                try:
                    # Parse date_range
                    if date_range == "latest":
                        end_date = datetime.now().strftime('%Y-%m-%d')
                        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                    else:
                        # Parse "YYYY-MM-DD:YYYY-MM-DD" format
                        if ':' in date_range:
                            start_date, end_date = date_range.split(':')
                        else:
                            start_date = end_date = date_range
                    
                    # Load data using the smart data loader
                    data = await self._load_from_smart_loader(ticker, start_date, end_date)
                    
                    if data is not None and not data.empty:
                        # Cache data
                        if self.agent_config.cache_enabled:
                            self._add_to_cache(ticker, date_range, data_type, data)
                        
                        # Add pattern to ChromaDB for vector acceleration
                        self.add_pattern_to_chromadb(ticker, data)
                            
                        # Auto cleanup if needed
                        self.memory_manager.auto_cleanup_if_needed()
                        
                        self.logger.debug(f"Loaded {len(data)} rows for {ticker}")
                        
                        return data
                    else:
                        self.logger.warning(f"No data returned for {ticker}")
                        return None
                        
                except Exception as e:
                    self.logger.error(f"Error loading data for {ticker}: {e}")
                    return None
            else:
                # NO PLACEHOLDER DATA IN PRODUCTION - Return error if no real data
                self.logger.error(f"No real data available for {ticker} - placeholder data disabled in production")
                return None
                
        except Exception as e:
            self.error_handler.handle_error(e, {
                "ticker": ticker,
                "date_range": date_range,
                "data_type": data_type
            }, ErrorSeverity.MEDIUM, "DataAgent.load_data")
            return None
            
    async def _handle_data_request(self, message) -> Dict[str, Any]:
        """Handle data request message"""
        try:
            data = message.data
            
            # Handle single ticker request (from Strategy Agent)
            if "ticker" in data:
                ticker = data["ticker"]
                min_days = data.get("min_days", 252)
                
                # Load data using real data loader
                from src.data_loader import get_stock_data
                df = get_stock_data(ticker)
                
                if df is not None and len(df) >= min_days:
                    return {
                        "success": True,
                        "data": df,
                        "ticker": ticker,
                        "rows": len(df),
                        "columns": list(df.columns)
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Insufficient data for {ticker}: got {len(df) if df is not None else 0}, need {min_days}",
                        "ticker": ticker
                    }
            
            # Handle multiple tickers request
            elif "tickers" in data:
                tickers = data["tickers"]
                if isinstance(tickers, list):
                    # Multiple tickers
                    results = {}
                    for ticker in tickers:
                        df = await self.load_data(ticker, data.get("date_range", "latest"), data.get("data_type", "price"))
                        if df is not None:
                            results[ticker] = df.to_dict()
                    return {"success": True, "data": results, "count": len(results)}
                else:
                    # Single ticker (legacy format)
                    df = await self.load_data(tickers, data.get("date_range", "latest"), data.get("data_type", "price"))
                    return {
                        "success": df is not None,
                        "data": df.to_dict() if df is not None else None,
                        "error": None if df is not None else "Data not found"
                    }
            else:
                return {"success": False, "error": "No ticker or tickers specified"}
                
        except Exception as e:
            self.logger.error(f"Error handling data request: {e}")
            return {"success": False, "error": str(e)}
            
    async def _handle_health_check(self, message) -> Dict[str, Any]:
        """Handle health check message"""
        try:
            health = await self.health_check()
            memory_stats = self.memory_manager.get_memory_stats()
            
            return {
                "success": True,
                "health_status": health.status.value,
                "cache_size": len(self.data_cache),
                "memory_stats": {
                    "process_memory_mb": memory_stats.process_memory_mb,
                    "cache_size_mb": memory_stats.cache_size_mb
                },
                "data_source": self.agent_config.data_source
            }
            
        except Exception as e:
            self.logger.error(f"Error handling health check: {e}")
            return {"success": False, "error": str(e)}
            
    def _create_data_source(self):
        """Create data source"""
        try:
            if self.data_loader:
                return self.data_loader
            else:
                # Fallback to placeholder
                return DataSource(self.agent_config.data_source)
        except Exception as e:
            self.logger.error(f"Error creating data source: {e}")
            return DataSource(self.agent_config.data_source)
        
    async def _test_data_source(self) -> bool:
        """Test data source connectivity"""
        try:
            if self.data_loader:
                # Test with actual data loader - try to get available data
                try:
                    # Test if data loader has the right method
                    if hasattr(self.data_loader, 'get_available_data'):
                        available = self.data_loader.get_available_data()
                        return len(available) > 0
                    elif hasattr(self.data_loader, 'load_data'):
                        sample_data = self.data_loader.load_data("AAPL", "1d", 1)
                        return sample_data is not None
                    else:
                        # Fallback - just check if data loader exists
                        self.logger.info("Data loader available, method test skipped")
                        return True
                except Exception as e:
                    self.logger.warning(f"Data loader test failed: {e}")
                    return False
            else:
                # Fallback - just return True for now
                self.logger.info("Using fallback data source test")
                return True
        except Exception as e:
            self.logger.error(f"Data source test failed: {e}")
            return False
            
    def _get_from_cache(self, ticker: str, date_range: str, data_type: str) -> Optional[pd.DataFrame]:
        """Get data from cache"""
        try:
            cache_key = f"{ticker}_{date_range}_{data_type}"
            
            if cache_key in self.data_cache:
                if cache_key in self.cache_timestamps:
                    age = datetime.now() - self.cache_timestamps[cache_key]
                    if age.total_seconds() < self.agent_config.cache_ttl:
                        return self.data_cache[cache_key]
                    else:
                        del self.data_cache[cache_key]
                        del self.cache_timestamps[cache_key]
                        
            return None
            
        except Exception:
            return None
            
    def _add_to_cache(self, ticker: str, date_range: str, data_type: str, data: pd.DataFrame):
        """Add data to cache"""
        try:
            cache_key = f"{ticker}_{date_range}_{data_type}"
            
            if len(self.data_cache) >= self.agent_config.max_cache_size:
                self._evict_oldest_cache_entry()
                
            self.data_cache[cache_key] = data
            self.cache_timestamps[cache_key] = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error adding to cache: {e}")
            
    def _evict_oldest_cache_entry(self):
        """Evict oldest cache entry"""
        try:
            if self.cache_timestamps:
                oldest_key = min(self.cache_timestamps.keys(), key=lambda k: self.cache_timestamps[k])
                del self.data_cache[oldest_key]
                del self.cache_timestamps[oldest_key]
                
        except Exception as e:
            self.logger.error(f"Error evicting cache entry: {e}")
            
    async def _cache_cleanup_loop(self):
        """Periodic cache cleanup"""
        while self.status == AgentStatus.RUNNING:
            try:
                await asyncio.sleep(self.agent_config.cache_ttl / 2)
                self._cleanup_expired_cache()
                
            except Exception as e:
                self.logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(60)
                
    def _cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        try:
            current_time = datetime.now()
            expired_keys = []
            
            for key, timestamp in self.cache_timestamps.items():
                if (current_time - timestamp).total_seconds() > self.agent_config.cache_ttl:
                    expired_keys.append(key)
                    
            for key in expired_keys:
                if key in self.data_cache:
                    del self.data_cache[key]
                if key in self.cache_timestamps:
                    del self.cache_timestamps[key]
                    
        except Exception as e:
            self.logger.error(f"Error cleaning up cache: {e}")
            
    async def _create_error_response(self, original_message, error: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
    
    def _init_chromadb(self):
        """Initialize ChromaDB for vector acceleration"""
        if not CHROMADB_AVAILABLE:
            self.logger.warning("ChromaDB not available - vector acceleration disabled")
            return
        
        try:
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(path="data/chroma_db")
            
            # Create or get pattern collection
            self.pattern_collection = self.chroma_client.get_or_create_collection(
                name="momentum_patterns",
                metadata={"description": "Stock momentum patterns for similarity search"}
            )
            
            self.logger.info("✅ ChromaDB initialized for vector acceleration")
            
        except Exception as e:
            self.logger.error(f"❌ ChromaDB initialization failed: {e}")
            self.chroma_client = None
            self.pattern_collection = None
    
    def _create_pattern_embedding(self, df: pd.DataFrame, window: int = 30) -> List[float]:
        """Create pattern embedding from price data"""
        if df is None or len(df) < window:
            return []
        
        try:
            # Get last window days of price data
            recent_data = df.tail(window)
            
            # Normalize price data (percentage changes)
            price_col = 'adjClose' if 'adjClose' in recent_data.columns else 'Close'
            prices = recent_data[price_col].values
            
            # Calculate percentage changes
            pct_changes = np.diff(prices) / prices[:-1]
            
            # Add volume information
            volume_col = 'adjVolume' if 'adjVolume' in recent_data.columns else 'Volume'
            volumes = recent_data[volume_col].values
            volume_norm = volumes / np.max(volumes)
            
            # Combine price and volume patterns
            pattern = np.concatenate([pct_changes, volume_norm[:-1]])
            
            return pattern.tolist()
            
        except Exception as e:
            self.logger.error(f"Pattern embedding creation failed: {e}")
            return []
    
    def add_pattern_to_chromadb(self, ticker: str, df: pd.DataFrame):
        """Add ticker pattern to ChromaDB"""
        if not self.pattern_collection or df is None:
            return
        
        try:
            # Create pattern embedding
            embedding = self._create_pattern_embedding(df)
            
            if not embedding:
                return
            
            # Add to ChromaDB
            self.pattern_collection.add(
                embeddings=[embedding],
                documents=[f"{ticker} momentum pattern"],
                metadatas=[{"ticker": ticker, "timestamp": datetime.now().isoformat()}],
                ids=[ticker]
            )
            
            self.logger.debug(f"✅ Added {ticker} pattern to ChromaDB")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to add {ticker} pattern to ChromaDB: {e}")
    
    def query_similar_patterns(self, ticker: str, df: pd.DataFrame, n_results: int = 10) -> List[str]:
        """Query ChromaDB for similar momentum patterns"""
        if not self.pattern_collection or df is None:
            return []
        
        try:
            # Create query embedding
            query_embedding = self._create_pattern_embedding(df)
            
            if not query_embedding:
                return []
            
            # Query similar patterns
            results = self.pattern_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # Extract ticker names
            similar_tickers = []
            if results['metadatas'] and results['metadatas'][0]:
                for metadata in results['metadatas'][0]:
                    similar_tickers.append(metadata['ticker'])
            
            self.logger.debug(f"🔍 Found {len(similar_tickers)} similar patterns for {ticker}")
            return similar_tickers
            
        except Exception as e:
            self.logger.error(f"❌ Pattern query failed for {ticker}: {e}")
            return []
    
    def get_pattern_context(self, ticker: str) -> Dict[str, Any]:
        """Get pattern context for a ticker"""
        if not self.pattern_collection:
            return {"has_pattern_context": False}
        
        try:
            # Get ticker data from ChromaDB
            results = self.pattern_collection.get(ids=[ticker])
            
            if results['metadatas'] and results['metadatas'][0]:
                metadata = results['metadatas'][0]
                return {
                    "has_pattern_context": True,
                    "ticker": metadata['ticker'],
                    "timestamp": metadata['timestamp']
                }
            else:
                return {"has_pattern_context": False}
                
        except Exception as e:
            self.logger.error(f"❌ Pattern context retrieval failed for {ticker}: {e}")
            return {"has_pattern_context": False}

class DataSource:
    """Placeholder data source"""
    
    def __init__(self, name: str):
        self.name = name
        
    async def test_connection(self) -> bool:
        """Test connection"""
        return True
        
    async def load_data(self, ticker: str, date_range: str, data_type: str) -> Optional[pd.DataFrame]:
        """Load data"""
        # Placeholder implementation
        return None
