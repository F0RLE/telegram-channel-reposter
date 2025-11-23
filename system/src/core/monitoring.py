"""Monitoring and metrics collection"""
import time
import psutil
import logging
from typing import Dict, Optional, List
from collections import defaultdict, deque
from datetime import datetime

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and stores application metrics"""
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector
        
        Args:
            max_history: Maximum number of data points to keep
        """
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, List[float]] = defaultdict(list)
    
    def record_metric(self, name: str, value: float, timestamp: Optional[float] = None):
        """
        Record a metric value
        
        Args:
            name: Metric name
            value: Metric value
            timestamp: Optional timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()
        self.metrics[name].append((timestamp, value))
    
    def increment_counter(self, name: str, value: int = 1):
        """
        Increment a counter
        
        Args:
            name: Counter name
            value: Increment value
        """
        self.counters[name] += value
    
    def record_timing(self, name: str, duration: float):
        """
        Record a timing measurement
        
        Args:
            name: Timing name
            duration: Duration in seconds
        """
        self.timers[name].append(duration)
        if len(self.timers[name]) > self.max_history:
            self.timers[name] = self.timers[name][-self.max_history:]
    
    def get_metric_stats(self, name: str) -> Optional[Dict[str, float]]:
        """
        Get statistics for a metric
        
        Args:
            name: Metric name
            
        Returns:
            Dictionary with min, max, avg, count or None if no data
        """
        if name not in self.metrics or not self.metrics[name]:
            return None
        
        values = [v for _, v in self.metrics[name]]
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "count": len(values),
            "latest": values[-1]
        }
    
    def get_counter(self, name: str) -> int:
        """Get counter value"""
        return self.counters.get(name, 0)
    
    def get_timing_stats(self, name: str) -> Optional[Dict[str, float]]:
        """
        Get statistics for timing measurements
        
        Args:
            name: Timing name
            
        Returns:
            Dictionary with min, max, avg, count or None if no data
        """
        if name not in self.timers or not self.timers[name]:
            return None
        
        timings = self.timers[name]
        return {
            "min": min(timings),
            "max": max(timings),
            "avg": sum(timings) / len(timings),
            "count": len(timings),
            "total": sum(timings)
        }
    
    def get_system_metrics(self) -> Dict[str, float]:
        """
        Get current system metrics
        
        Returns:
            Dictionary with CPU, memory, and disk usage
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / 1024 / 1024,
                "memory_available_mb": memory.available / 1024 / 1024,
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / 1024 / 1024 / 1024
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}


# Global metrics collector instance
metrics = MetricsCollector()


def record_api_call(service: str, success: bool, duration: float):
    """
    Record an API call metric
    
    Args:
        service: Service name (llm, sd, parser)
        success: Whether the call was successful
        duration: Call duration in seconds
    """
    metrics.increment_counter(f"api_calls_{service}_total")
    if success:
        metrics.increment_counter(f"api_calls_{service}_success")
    else:
        metrics.increment_counter(f"api_calls_{service}_error")
    
    metrics.record_timing(f"api_call_{service}", duration)
    metrics.record_metric(f"api_call_{service}_duration", duration)


def record_error(error_type: str, context: str = ""):
    """
    Record an error metric
    
    Args:
        error_type: Type of error
        context: Additional context
    """
    metrics.increment_counter(f"errors_{error_type}")
    if context:
        metrics.increment_counter(f"errors_{error_type}_{context}")

