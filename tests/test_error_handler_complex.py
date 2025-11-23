"""Complex tests for error handler module"""
import pytest
import asyncio
import sys
import os
import time

# Add parent directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'system', 'src'))

try:
    from core.error_handler import RetryConfig, retry_with_backoff, ErrorHandler
except ImportError:
    pytest.skip("Could not import error_handler", allow_module_level=True)


class TestComplexRetryConfig:
    """Complex retry configuration tests"""
    
    def test_custom_retry_config(self):
        """Test custom retry configuration"""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=0.1,
            max_delay=10.0,
            exponential_base=2.0,
            retryable_exceptions=(ValueError, KeyError)
        )
        assert config.max_attempts == 5
        assert config.initial_delay == 0.1
        assert config.max_delay == 10.0
        assert config.exponential_base == 2.0
        assert ValueError in config.retryable_exceptions
        assert KeyError in config.retryable_exceptions


class TestComplexRetryDecorator:
    """Complex retry decorator tests"""
    
    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        """Test retry with exponential backoff timing"""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.1))
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "Success"
        
        start_time = time.time()
        result = await failing_function()
        elapsed_time = time.time() - start_time
        
        assert result == "Success"
        assert call_count == 3
        # Should have retried with delays (at least 0.1 + 0.2 = 0.3 seconds)
        assert elapsed_time >= 0.2
    
    @pytest.mark.asyncio
    async def test_retry_with_max_delay_limit(self):
        """Test that retry respects max_delay limit"""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(
            max_attempts=5,
            initial_delay=1.0,
            max_delay=2.0,
            exponential_base=10.0  # Very high base to test max_delay
        ))
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise ValueError("Temporary failure")
            return "Success"
        
        start_time = time.time()
        result = await failing_function()
        elapsed_time = time.time() - start_time
        
        assert result == "Success"
        # Should not exceed max_delay * (max_attempts - 1)
        # With max_delay=2.0 and 4 retries, should be around 8 seconds max
        assert elapsed_time < 10.0
    
    @pytest.mark.asyncio
    async def test_retry_only_retryable_exceptions(self):
        """Test that only retryable exceptions trigger retries"""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(
            max_attempts=3,
            retryable_exceptions=(ValueError,)
        ))
        async def function_raising_different_exception():
            nonlocal call_count
            call_count += 1
            raise KeyError("Non-retryable exception")
        
        with pytest.raises(KeyError):
            await function_raising_different_exception()
        
        # Should only be called once, not retried
        assert call_count == 1


class TestComplexErrorHandler:
    """Complex error handler tests"""
    
    def test_connection_error_handling(self):
        """Test connection error handling"""
        handler = ErrorHandler()
        
        # Simulate connection error
        error = ConnectionError("Connection refused")
        result = handler.handle_error(error)
        
        assert result is not None
        assert "connection" in result.lower() or "network" in result.lower()
    
    def test_404_error_handling(self):
        """Test 404 error handling"""
        handler = ErrorHandler()
        
        # Simulate 404 error
        class HTTP404Error(Exception):
            def __init__(self):
                self.status_code = 404
                super().__init__("Not Found")
        
        error = HTTP404Error()
        result = handler.handle_error(error)
        
        assert result is not None
        assert "404" in result or "not found" in result.lower()
    
    def test_429_rate_limit_error_handling(self):
        """Test 429 rate limit error handling"""
        handler = ErrorHandler()
        
        # Simulate 429 error
        class HTTP429Error(Exception):
            def __init__(self):
                self.status_code = 429
                super().__init__("Too Many Requests")
        
        error = HTTP429Error()
        result = handler.handle_error(error)
        
        assert result is not None
        assert "429" in result or "rate limit" in result.lower() or "too many" in result.lower()
    
    def test_401_unauthorized_error_handling(self):
        """Test 401 unauthorized error handling"""
        handler = ErrorHandler()
        
        # Simulate 401 error
        class HTTP401Error(Exception):
            def __init__(self):
                self.status_code = 401
                super().__init__("Unauthorized")
        
        error = HTTP401Error()
        result = handler.handle_error(error)
        
        assert result is not None
        assert "401" in result or "unauthorized" in result.lower() or "auth" in result.lower()
    
    def test_500_server_error_handling(self):
        """Test 500 server error handling"""
        handler = ErrorHandler()
        
        # Simulate 500 error
        class HTTP500Error(Exception):
            def __init__(self):
                self.status_code = 500
                super().__init__("Internal Server Error")
        
        error = HTTP500Error()
        result = handler.handle_error(error)
        
        assert result is not None
        assert "500" in result or "server" in result.lower() or "internal" in result.lower()
    
    def test_unknown_error_handling(self):
        """Test handling of unknown errors"""
        handler = ErrorHandler()
        
        # Simulate unknown error
        error = RuntimeError("Unknown error occurred")
        result = handler.handle_error(error)
        
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

