"""Rate limiting for API requests"""
import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with token bucket algorithm"""
    
    def __init__(self, max_calls: int = 10, period: float = 1.0):
        """
        Initialize rate limiter
        
        Args:
            max_calls: Maximum number of calls allowed
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls: Dict[str, list] = defaultdict(list)
        self.locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
    
    async def acquire(self, key: str = "default") -> bool:
        """
        Acquire permission to make a call
        
        Args:
            key: Rate limit key (for different endpoints)
            
        Returns:
            True if allowed, False if rate limited
        """
        async with self.locks[key]:
            now = time.time()
            # Remove old calls outside the period
            self.calls[key] = [
                call_time for call_time in self.calls[key]
                if now - call_time < self.period
            ]
            
            if len(self.calls[key]) >= self.max_calls:
                # Calculate wait time
                oldest_call = min(self.calls[key])
                wait_time = self.period - (now - oldest_call)
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit exceeded for {key}. "
                        f"Waiting {wait_time:.2f}s..."
                    )
                    await asyncio.sleep(wait_time)
                    # Retry after waiting
                    return await self.acquire(key)
            
            # Record this call
            self.calls[key].append(time.time())
            return True
    
    def reset(self, key: Optional[str] = None):
        """Reset rate limiter for a key or all keys"""
        if key:
            self.calls[key].clear()
        else:
            self.calls.clear()


# Global rate limiters for different services
llm_rate_limiter = RateLimiter(max_calls=5, period=1.0)  # 5 calls per second
sd_rate_limiter = RateLimiter(max_calls=2, period=1.0)   # 2 calls per second
parser_rate_limiter = RateLimiter(max_calls=10, period=1.0)  # 10 calls per second

