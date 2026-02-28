"""
System Monitor for VolatilityHunter Core System Layer
Provides resource monitoring with ASCII-formatted output
"""

import os
import sys
from typing import Dict, Any, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class SystemMonitor:
    """System resource monitoring with ASCII output"""
    
    def __init__(self):
        self.psutil_available = PSUTIL_AVAILABLE
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current system resource usage
        
        Returns:
            Dict with CPU and memory usage information
        """
        if not self.psutil_available:
            return {
                'cpu_percent': '[WARN] psutil not installed',
                'memory_mb': '[WARN] psutil not installed',
                'memory_percent': '[WARN] psutil not installed',
                'disk_usage': '[WARN] psutil not installed',
                'process_count': '[WARN] psutil not installed'
            }
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('.')
            disk_percent = disk.percent
            
            # Process count
            process_count = len(psutil.pids())
            
            return {
                'cpu_percent': f"{cpu_percent:.1f}%",
                'memory_mb': f"{memory_mb:.0f}MB",
                'memory_percent': f"{memory_percent:.1f}%",
                'disk_usage': f"{disk_percent:.1f}%",
                'process_count': str(process_count)
            }
            
        except Exception as e:
            return {
                'cpu_percent': f"[ERROR] {str(e)}",
                'memory_mb': f"[ERROR] {str(e)}",
                'memory_percent': f"[ERROR] {str(e)}",
                'disk_usage': f"[ERROR] {str(e)}",
                'process_count': f"[ERROR] {str(e)}"
            }
    
    def get_ascii_formatted(self) -> str:
        """
        Get ASCII-formatted system resource usage
        
        Returns:
            ASCII-formatted string: [SYSTEM] CPU: 12% | RAM: 154MB
        """
        usage = self.get_resource_usage()
        
        return f"[SYSTEM] CPU: {usage['cpu_percent']} | RAM: {usage['memory_mb']}"
    
    def get_detailed_ascii(self) -> str:
        """
        Get detailed ASCII-formatted system resource usage
        
        Returns:
            Multi-line ASCII-formatted string with all metrics
        """
        usage = self.get_resource_usage()
        
        lines = [
            "[SYSTEM] RESOURCE USAGE",
            f"  CPU Usage: {usage['cpu_percent']}",
            f"  Memory Usage: {usage['memory_mb']} ({usage['memory_percent']})",
            f"  Disk Usage: {usage['disk_usage']}",
            f"  Process Count: {usage['process_count']}"
        ]
        
        return "\n".join(lines)
    
    def check_system_health(self) -> Dict[str, Any]:
        """
        Check system health based on resource usage
        
        Returns:
            Dict with health assessment and recommendations
        """
        if not self.psutil_available:
            return {
                'status': 'UNKNOWN',
                'cpu_status': 'UNKNOWN',
                'memory_status': 'UNKNOWN',
                'disk_status': 'UNKNOWN',
                'recommendations': ['Install psutil for advanced monitoring']
            }
        
        usage = self.get_resource_usage()
        
        # Parse numeric values
        try:
            cpu_value = float(usage['cpu_percent'].replace('%', ''))
            memory_value = float(usage['memory_percent'].replace('%', ''))
            disk_value = float(usage['disk_usage'].replace('%', ''))
        except (ValueError, AttributeError):
            return {
                'status': 'ERROR',
                'cpu_status': 'ERROR',
                'memory_status': 'ERROR',
                'disk_status': 'ERROR',
                'recommendations': ['Error parsing system metrics']
            }
        
        # Health assessment
        recommendations = []
        
        # CPU health
        if cpu_value > 80:
            cpu_status = 'HIGH'
            recommendations.append('High CPU usage detected - consider optimization')
        elif cpu_value > 60:
            cpu_status = 'MODERATE'
        else:
            cpu_status = 'GOOD'
        
        # Memory health
        if memory_value > 80:
            memory_status = 'HIGH'
            recommendations.append('High memory usage detected - consider optimization')
        elif memory_value > 60:
            memory_status = 'MODERATE'
        else:
            memory_status = 'GOOD'
        
        # Disk health
        if disk_value > 90:
            disk_status = 'CRITICAL'
            recommendations.append('Critical disk usage - free up space immediately')
        elif disk_value > 80:
            disk_status = 'HIGH'
            recommendations.append('High disk usage - consider cleanup')
        elif disk_value > 60:
            disk_status = 'MODERATE'
        else:
            disk_status = 'GOOD'
        
        # Overall status
        if 'HIGH' in [cpu_status, memory_status, disk_status] or disk_status == 'CRITICAL':
            overall_status = 'WARNING'
        elif 'MODERATE' in [cpu_status, memory_status, disk_status]:
            overall_status = 'CAUTION'
        else:
            overall_status = 'HEALTHY'
        
        return {
            'status': overall_status,
            'cpu_status': cpu_status,
            'memory_status': memory_status,
            'disk_status': disk_status,
            'recommendations': recommendations
        }

# Global instance for easy access
system_monitor = SystemMonitor()
