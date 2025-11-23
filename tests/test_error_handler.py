"""Tests for error handler module"""
import pytest
import asyncio
import sys
import os

# Add parent directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'system', 'src'))

try:
    from core.error_handler import RetryConfig, retry_with_backoff, ErrorHandler
except ImportError as e:
    pytest.skip(f"Could not import core.error_handler: {e}", allow_module_level=True)


class TestRetryConfig:
    """Tests for RetryConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=2.0,
            max_delay=30.0,
            exponential_base=1.5
        )
        assert config.max_attempts == 5
        assert config.initial_delay == 2.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 1.5


class TestRetryDecorator:
    """Tests for retry decorator"""
    
    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Test successful function call"""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(max_attempts=3))
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry on failure"""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.1))
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test max retries exceeded"""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.1))
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")
        
        with pytest.raises(ValueError):
            await test_func()
        
        assert call_count == 3


class TestErrorHandler:
    """Tests for ErrorHandler"""
    
    def test_connection_error(self):
        """Test handling connection errors"""
        error = Exception("Connection timeout")
        result = ErrorHandler.handle_api_error(error, "Test context")
        assert "соединения" in result.lower() or "connection" in result.lower()
    
    def test_404_error(self):
        """Test handling 404 errors"""
        error = Exception("404 Not Found")
        result = ErrorHandler.handle_api_error(error, "Test context")
        assert "не найден" in result.lower() or "not found" in result.lower()
    
    def test_429_error(self):
        """Test handling rate limit errors"""
        error = Exception("429 Rate Limit Exceeded")
        result = ErrorHandler.handle_api_error(error, "Test context")
        assert "лимит" in result.lower() or "rate limit" in result.lower()
    
    def test_401_error(self):
        """Test handling authorization errors"""
        error = Exception("401 Unauthorized")
        result = ErrorHandler.handle_api_error(error, "Test context")
        assert "авторизац" in result.lower() or "unauthorized" in result.lower()
    
    def test_500_error(self):
        """Test handling server errors"""
        error = Exception("500 Internal Server Error")
        result = ErrorHandler.handle_api_error(error, "Test context")
        assert "сервер" in result.lower() or "server" in result.lower()
    
    def test_unknown_error(self):
        """Test handling unknown errors"""
        error = Exception("Unknown error type")
        result = ErrorHandler.handle_api_error(error, "Test context")
        assert "неизвестная" in result.lower() or "unknown" in result.lower()
        assert "Unknown error type" in result

