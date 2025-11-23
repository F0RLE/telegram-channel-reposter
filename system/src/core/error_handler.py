"""Centralized error handling and retry mechanism"""
import asyncio
import logging
import time
from typing import Callable, TypeVar, Optional, Any
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry mechanism"""
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_exceptions: tuple = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """Decorator for retry with exponential backoff"""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            delay = config.initial_delay
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < config.max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{config.max_attempts}): {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                        delay = min(delay * config.exponential_base, config.max_delay)
                    else:
                        logger.error(f"{func.__name__} failed after {config.max_attempts} attempts: {e}")
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            delay = config.initial_delay
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < config.max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{config.max_attempts}): {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                        delay = min(delay * config.exponential_base, config.max_delay)
                    else:
                        logger.error(f"{func.__name__} failed after {config.max_attempts} attempts: {e}")
            
            raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class ErrorHandler:
    """Centralized error handler for API and application errors"""
    
    @staticmethod
    def handle_api_error(error: Exception, context: str = "") -> str:
        """
        Handle API errors and return user-friendly message.
        
        Args:
            error: Exception that occurred
            context: Additional context string
            
        Returns:
            User-friendly error message in Russian
        """
        error_str = str(error).lower()
        
        if "connection" in error_str or "timeout" in error_str:
            return f"Ошибка соединения. Проверьте, запущен ли сервис. {context}"
        elif "404" in error_str or "not found" in error_str:
            return f"Ресурс не найден. {context}"
        elif "429" in error_str or "rate limit" in error_str:
            return f"Превышен лимит запросов. Подождите немного. {context}"
        elif "401" in error_str or "unauthorized" in error_str:
            return f"Ошибка авторизации. Проверьте токен. {context}"
        elif "500" in error_str or "internal server" in error_str:
            return f"Внутренняя ошибка сервера. {context}"
        else:
            return f"Неизвестная ошибка: {error}. {context}"
    
    @staticmethod
    def log_and_notify(
        error: Exception, 
        context: str = "", 
        notify_user: bool = False
    ) -> str:
        """
        Log error and optionally notify user.
        
        Args:
            error: Exception that occurred
            context: Additional context string
            notify_user: Whether to notify user (currently just logs)
            
        Returns:
            User-friendly error message
        """
        error_msg = ErrorHandler.handle_api_error(error, context)
        logger.error(f"{context}: {error}", exc_info=True)
        
        if notify_user:
            # This would be integrated with UI notification system
            logger.info(f"User notification: {error_msg}")
        
        return error_msg

