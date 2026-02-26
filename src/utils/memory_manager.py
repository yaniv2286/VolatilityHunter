"""
Memory Management Utilities - Prevents memory leaks and optimizes usage
"""

import gc
import logging
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class MemoryStats:
    """Memory statistics"""
    total_memory_mb: float
    used_memory_mb: float
    available_memory_mb: float
    process_memory_mb: float
    cache_size_mb: float
    gc_collections: int
    object_count: int

class MemoryManager:
    """Manages memory usage and prevents leaks"""
    
    def __init__(self, max_memory_mb: float = 1024):  # 1GB default
        self.logger = logging.getLogger("memory_manager")
        self.max_memory_mb = max_memory_mb
        self.cache_objects: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(hours=1)
        self.max_cache_size = 1000
        
        # Memory monitoring
        self.last_gc_time = datetime.now()
        self.gc_interval = timedelta(minutes=5)
        
    def add_to_cache(self, key: str, value: Any, ttl: timedelta = None):
        """Add item to cache with automatic cleanup"""
        try:
            # Check cache size limit
            if len(self.cache_objects) >= self.max_cache_size:
                self._cleanup_cache()
                
            # Add to cache
            self.cache_objects[key] = value
            self.cache_timestamps[key] = datetime.now()
            
            # Set TTL if provided
            if ttl:
                self.cache_timestamps[key] = datetime.now() + ttl
                
        except Exception as e:
            self.logger.error(f"Error adding to cache: {e}")
            
    def get_from_cache(self, key: str) -> Optional[Any]:
        """Get item from cache with TTL check"""
        try:
            if key not in self.cache_objects:
                return None
                
            # Check TTL
            timestamp = self.cache_timestamps.get(key)
            if timestamp and datetime.now() > timestamp:
                del self.cache_objects[key]
                del self.cache_timestamps[key]
                return None
                
            return self.cache_objects[key]
            
        except Exception as e:
            self.logger.error(f"Error getting from cache: {e}")
            return None
            
    def _cleanup_cache(self):
        """Clean up expired cache entries"""
        try:
            current_time = datetime.now()
            expired_keys = []
            
            for key, timestamp in self.cache_timestamps.items():
                if current_time > timestamp:
                    expired_keys.append(key)
                    
            # Remove expired entries
            for key in expired_keys:
                if key in self.cache_objects:
                    del self.cache_objects[key]
                if key in self.cache_timestamps:
                    del self.cache_timestamps[key]
                    
            # If still too many entries, remove oldest
            if len(self.cache_objects) >= self.max_cache_size:
                sorted_items = sorted(
                    self.cache_timestamps.items(),
                    key=lambda x: x[1]
                )
                
                # Remove oldest 25% of entries
                remove_count = len(sorted_items) // 4
                for key, _ in sorted_items[:remove_count]:
                    if key in self.cache_objects:
                        del self.cache_objects[key]
                    if key in self.cache_timestamps:
                        del self.cache_timestamps[key]
                        
            self.logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")
            
        except Exception as e:
            self.logger.error(f"Error in cache cleanup: {e}")
            
    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics"""
        try:
            process = psutil.Process(os.getpid())
            
            # System memory
            memory = psutil.virtual_memory()
            
            # Process memory
            process_memory = process.memory_info()
            
            # Cache size estimation
            cache_size = len(str(self.cache_objects)) / (1024 * 1024)  # Rough estimate
            
            # Object count
            object_count = len(self.cache_objects)
            
            return MemoryStats(
                total_memory_mb=memory.total / (1024 * 1024),
                used_memory_mb=memory.used / (1024 * 1024),
                available_memory_mb=memory.available / (1024 * 1024),
                process_memory_mb=process_memory.rss / (1024 * 1024),
                cache_size_mb=cache_size,
                gc_collections=gc.get_count()[0],
                object_count=object_count
            )
            
        except Exception as e:
            self.logger.error(f"Error getting memory stats: {e}")
            return MemoryStats(0, 0, 0, 0, 0, 0, 0)
            
    def check_memory_pressure(self) -> bool:
        """Check if memory usage is too high"""
        try:
            stats = self.get_memory_stats()
            
            # Check process memory
            if stats.process_memory_mb > self.max_memory_mb * 0.8:
                self.logger.warning(f"High memory usage: {stats.process_memory_mb:.1f}MB")
                return True
                
            # Check system memory
            if stats.available_memory_mb < 100:  # Less than 100MB available
                self.logger.warning(f"Low system memory: {stats.available_memory_mb:.1f}MB")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking memory pressure: {e}")
            return False
            
    def force_cleanup(self):
        """Force memory cleanup"""
        try:
            self.logger.info("Forcing memory cleanup...")
            
            # Clear cache
            self.cache_objects.clear()
            self.cache_timestamps.clear()
            
            # Force garbage collection
            collected = gc.collect()
            
            self.logger.info(f"Memory cleanup completed: {collected} objects collected")
            
        except Exception as e:
            self.logger.error(f"Error in force cleanup: {e}")
            
    def auto_cleanup_if_needed(self):
        """Auto cleanup if memory pressure is high"""
        try:
            current_time = datetime.now()
            
            # Check if it's time for GC
            if current_time - self.last_gc_time > self.gc_interval:
                if self.check_memory_pressure():
                    self.force_cleanup()
                self.last_gc_time = current_time
                
        except Exception as e:
            self.logger.error(f"Error in auto cleanup: {e}")

class ResourceManager:
    """Manages system resources like file handles, connections"""
    
    def __init__(self):
        self.logger = logging.getLogger("resource_manager")
        self.open_files: Dict[str, Any] = {}
        self.active_connections: Dict[str, Any] = {}
        self.max_open_files = 100
        self.max_connections = 50
        
    def register_file(self, file_path: str, file_handle: Any):
        """Register open file handle"""
        try:
            if len(self.open_files) >= self.max_open_files:
                self._cleanup_old_files()
                
            self.open_files[file_path] = {
                "handle": file_handle,
                "opened_at": datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error registering file: {e}")
            
    def register_connection(self, connection_id: str, connection: Any):
        """Register active connection"""
        try:
            if len(self.active_connections) >= self.max_connections:
                self._cleanup_old_connections()
                
            self.active_connections[connection_id] = {
                "connection": connection,
                "created_at": datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error registering connection: {e}")
            
    def close_file(self, file_path: str):
        """Close file handle"""
        try:
            if file_path in self.open_files:
                handle = self.open_files[file_path]["handle"]
                if hasattr(handle, 'close'):
                    handle.close()
                del self.open_files[file_path]
                
        except Exception as e:
            self.logger.error(f"Error closing file {file_path}: {e}")
            
    def close_connection(self, connection_id: str):
        """Close connection"""
        try:
            if connection_id in self.active_connections:
                connection = self.active_connections[connection_id]["connection"]
                if hasattr(connection, 'close'):
                    connection.close()
                del self.active_connections[connection_id]
                
        except Exception as e:
            self.logger.error(f"Error closing connection {connection_id}: {e}")
            
    def _cleanup_old_files(self):
        """Clean up old file handles"""
        try:
            current_time = datetime.now()
            old_files = [
                path for path, info in self.open_files.items()
                if (current_time - info["opened_at"]).total_seconds() > 3600  # 1 hour
            ]
            
            for file_path in old_files:
                self.close_file(file_path)
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old files: {e}")
            
    def _cleanup_old_connections(self):
        """Clean up old connections"""
        try:
            current_time = datetime.now()
            old_connections = [
                conn_id for conn_id, info in self.active_connections.items()
                if (current_time - info["created_at"]).total_seconds() > 1800  # 30 minutes
            ]
            
            for conn_id in old_connections:
                self.close_connection(conn_id)
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old connections: {e}")
            
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get resource usage statistics"""
        try:
            return {
                "open_files": len(self.open_files),
                "active_connections": len(self.active_connections),
                "max_open_files": self.max_open_files,
                "max_connections": self.max_connections
            }
            
        except Exception as e:
            self.logger.error(f"Error getting resource stats: {e}")
            return {}
