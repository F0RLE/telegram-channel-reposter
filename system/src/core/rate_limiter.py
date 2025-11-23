"""Rate limiting decorator for async functions"""
import asyncio
import time
from typing import Callable, TypeVar, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


def rate_limit(max_calls: int = 10, period: float = 1.0, key: str = "default"):
    """
    Decorator for rate limiting async functions
    
    Args:
        max_calls: Maximum number of calls allowed
        period: Time period in seconds
        key: Rate limit key (for different endpoints)
    """
    calls = {}
    locks = {}
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if key not in calls:
            calls[key] = []
            locks[key] = asyncio.Lock()
        
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            async with locks[key]:
                now = time.time()
                # Remove old calls
                calls[key] = [
                    call_time for call_time in calls[key]
                    if now - call_time < period
                ]
                
                if len(calls[key]) >= max_calls:
                    oldest_call = min(calls[key])
                    wait_time = period - (now - oldest_call)
                    if wait_time > 0:
                        logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {key}")
                        await asyncio.sleep(wait_time)
                
                calls[key].append(time.time())
                return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator

