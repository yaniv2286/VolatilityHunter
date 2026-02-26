"""
Concurrency Management Utilities - Prevents race conditions and thread safety issues
"""

import asyncio
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass
import time

T = TypeVar('T')

class ThreadSafeDict(Generic[T]):
    """Thread-safe dictionary with atomic operations"""
    
    def __init__(self):
        self._dict: Dict[str, T] = {}
        self._lock = threading.RLock()
        self._access_count = 0
        self._last_access = datetime.now()
        
    def get(self, key: str, default: T = None) -> T:
        """Get value with thread safety"""
        try:
            with self._lock:
                self._access_count += 1
                self._last_access = datetime.now()
                return self._dict.get(key, default)
        except Exception as e:
            logging.getLogger("thread_safe_dict").error(f"Error in get: {e}")
            return default
            
    def set(self, key: str, value: T) -> None:
        """Set value with thread safety"""
        try:
            with self._lock:
                self._dict[key] = value
                self._access_count += 1
                self._last_access = datetime.now()
        except Exception as e:
            logging.getLogger("thread_safe_dict").error(f"Error in set: {e}")
            
    def update(self, key: str, update_func: Callable[[T], T]) -> bool:
        """Update value atomically"""
        try:
            with self._lock:
                if key in self._dict:
                    self._dict[key] = update_func(self._dict[key])
                    self._access_count += 1
                    self._last_access = datetime.now()
                    return True
                return False
        except Exception as e:
            logging.getLogger("thread_safe_dict").error(f"Error in update: {e}")
            return False
            
    def delete(self, key: str) -> bool:
        """Delete key with thread safety"""
        try:
            with self._lock:
                if key in self._dict:
                    del self._dict[key]
                    self._access_count += 1
                    self._last_access = datetime.now()
                    return True
                return False
        except Exception as e:
            logging.getLogger("thread_safe_dict").error(f"Error in delete: {e}")
            return False
            
    def items(self):
        """Get all items (snapshot)"""
        try:
            with self._lock:
                return list(self._dict.items())
        except Exception as e:
            logging.getLogger("thread_safe_dict").error(f"Error in items: {e}")
            return []
            
    def keys(self):
        """Get all keys (snapshot)"""
        try:
            with self._lock:
                return list(self._dict.keys())
        except Exception as e:
            logging.getLogger("thread_safe_dict").error(f"Error in keys: {e}")
            return []
            
    def values(self):
        """Get all values (snapshot)"""
        try:
            with self._lock:
                return list(self._dict.values())
        except Exception as e:
            logging.getLogger("thread_safe_dict").error(f"Error in values: {e}")
            return []
            
    def clear(self):
        """Clear dictionary"""
        try:
            with self._lock:
                self._dict.clear()
                self._access_count = 0
                self._last_access = datetime.now()
        except Exception as e:
            logging.getLogger("thread_safe_dict").error(f"Error in clear: {e}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Get dictionary statistics"""
        try:
            with self._lock:
                return {
                    "size": len(self._dict),
                    "access_count": self._access_count,
                    "last_access": self._last_access.isoformat()
                }
        except Exception as e:
            logging.getLogger("thread_safe_dict").error(f"Error in get_stats: {e}")
            return {}

class AsyncLock:
    """Async context manager for locks"""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        
    async def __aenter__(self):
        await self._lock.acquire()
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()

class AtomicCounter:
    """Thread-safe counter"""
    
    def __init__(self, initial_value: int = 0):
        self._value = initial_value
        self._lock = threading.Lock()
        
    def increment(self, amount: int = 1) -> int:
        """Increment counter atomically"""
        try:
            with self._lock:
                self._value += amount
                return self._value
        except Exception as e:
            logging.getLogger("atomic_counter").error(f"Error in increment: {e}")
            return self._value
            
    def decrement(self, amount: int = 1) -> int:
        """Decrement counter atomically"""
        try:
            with self._lock:
                self._value -= amount
                return self._value
        except Exception as e:
            logging.getLogger("atomic_counter").error(f"Error in decrement: {e}")
            return self._value
            
    def get(self) -> int:
        """Get current value"""
        try:
            with self._lock:
                return self._value
        except Exception as e:
            logging.getLogger("atomic_counter").error(f"Error in get: {e}")
            return 0
            
    def set(self, value: int) -> None:
        """Set value atomically"""
        try:
            with self._lock:
                self._value = value
        except Exception as e:
            logging.getLogger("atomic_counter").error(f"Error in set: {e}")

class RateLimiter:
    """Thread-safe rate limiter"""
    
    def __init__(self, max_requests: int, time_window: float):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = threading.Lock()
        
    def is_allowed(self) -> bool:
        """Check if request is allowed"""
        try:
            with self._lock:
                current_time = time.time()
                
                # Remove old requests
                self.requests = [
                    req_time for req_time in self.requests
                    if current_time - req_time < self.time_window
                ]
                
                # Check if under limit
                return len(self.requests) < self.max_requests
                
        except Exception as e:
            logging.getLogger("rate_limiter").error(f"Error in is_allowed: {e}")
            return False
            
    def record_request(self):
        """Record a request"""
        try:
            with self._lock:
                self.requests.append(time.time())
        except Exception as e:
            logging.getLogger("rate_limiter").error(f"Error in record_request: {e}")

class TaskQueue:
    """Thread-safe task queue"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._queue = []
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._closed = False
        
    def put(self, item: Any) -> bool:
        """Add item to queue"""
        try:
            with self._lock:
                if self._closed:
                    return False
                    
                if len(self._queue) >= self.max_size:
                    return False
                    
                self._queue.append(item)
                self._condition.notify()
                return True
                
        except Exception as e:
            logging.getLogger("task_queue").error(f"Error in put: {e}")
            return False
            
    def get(self, timeout: float = None) -> Optional[Any]:
        """Get item from queue"""
        try:
            with self._lock:
                if self._closed and not self._queue:
                    return None
                    
                start_time = time.time()
                
                while not self._queue and not self._closed:
                    if timeout is None:
                        self._condition.wait()
                    else:
                        remaining_time = timeout - (time.time() - start_time)
                        if remaining_time <= 0:
                            return None
                        self._condition.wait(remaining_time)
                        
                if self._queue:
                    return self._queue.pop(0)
                else:
                    return None
                    
        except Exception as e:
            logging.getLogger("task_queue").error(f"Error in get: {e}")
            return None
            
    def close(self):
        """Close the queue"""
        try:
            with self._lock:
                self._closed = True
                self._condition.notify_all()
        except Exception as e:
            logging.getLogger("task_queue").error(f"Error in close: {e}")
            
    def size(self) -> int:
        """Get queue size"""
        try:
            with self._lock:
                return len(self._queue)
        except Exception as e:
            logging.getLogger("task_queue").error(f"Error in size: {e}")
            return 0

class StateManager:
    """Thread-safe state manager"""
    
    def __init__(self):
        self._states = ThreadSafeDict()
        self._state_locks = ThreadSafeDict()
        self._state_history = ThreadSafeDict()
        
    def get_state(self, state_name: str) -> Optional[Any]:
        """Get state value"""
        return self._states.get(state_name)
        
    def set_state(self, state_name: str, value: Any) -> None:
        """Set state value"""
        old_value = self._states.get(state_name)
        self._states.set(state_name, value)
        
        # Record history
        history = self._state_history.get(state_name, [])
        history.append({
            "timestamp": datetime.now().isoformat(),
            "old_value": old_value,
            "new_value": value
        })
        self._state_history.set(state_name, history)
        
    def atomic_update(self, state_name: str, update_func: Callable[[Any], Any]) -> bool:
        """Atomically update state"""
        return self._states.update(state_name, update_func)
        
    def lock_state(self, state_name: str):
        """Get lock for specific state"""
        if state_name not in self._state_locks:
            self._state_locks.set(state_name, threading.RLock())
        return self._state_locks.get(state_name)
        
    def get_state_history(self, state_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get state change history"""
        history = self._state_history.get(state_name, [])
        return history[-limit:] if len(history) > limit else history

class ConcurrencyMonitor:
    """Monitor concurrency issues and performance"""
    
    def __init__(self):
        self.logger = logging.getLogger("concurrency_monitor")
        self.active_threads = set()
        self.thread_stats = ThreadSafeDict()
        self.lock_contentions = ThreadSafeDict()
        
    def register_thread(self, thread_id: str = None):
        """Register active thread"""
        if thread_id is None:
            thread_id = threading.current_thread().ident
            
        self.active_threads.add(thread_id)
        self.thread_stats.set(thread_id, {
            "started_at": datetime.now(),
            "last_activity": datetime.now()
        })
        
    def unregister_thread(self, thread_id: str = None):
        """Unregister thread"""
        if thread_id is None:
            thread_id = threading.current_thread().ident
            
        self.active_threads.discard(thread_id)
        self.thread_stats.delete(thread_id)
        
    def record_lock_acquisition(self, lock_name: str, duration: float):
        """Record lock acquisition"""
        current_contentions = self.lock_contentions.get(lock_name, [])
        current_contentions.append(duration)
        self.lock_contentions.set(lock_name, current_contentions)
        
    def get_concurrency_stats(self) -> Dict[str, Any]:
        """Get concurrency statistics"""
        return {
            "active_threads": len(self.active_threads),
            "thread_stats": self.thread_stats.get_stats(),
            "lock_contentions": {
                name: {
                    "count": len(contentions),
                    "avg_duration": sum(contentions) / len(contentions) if contents else 0,
                    "max_duration": max(contentions) if contents else 0
                }
                for name, contents in self.lock_contentions.items()
            }
        }
