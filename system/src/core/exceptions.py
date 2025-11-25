"""Custom exceptions for better error handling"""
from typing import Optional


class BotBaseException(Exception):
    """Base exception for all bot-related errors"""
    def __init__(self, message: str, context: Optional[str] = None):
        self.message = message
        self.context = context
        super().__init__(self.message)


class ConfigurationError(BotBaseException):
    """Raised when configuration is invalid or missing"""
    pass


class ValidationError(BotBaseException):
    """Raised when data validation fails"""
    pass


class APIError(BotBaseException):
    """Raised when API call fails"""
    def __init__(self, message: str, status_code: Optional[int] = None, context: Optional[str] = None):
        self.status_code = status_code
        super().__init__(message, context)


class LLMError(APIError):
    """Raised when LLM API call fails"""
    pass


class SDError(APIError):
    """Raised when Stable Diffusion API call fails"""
    pass


class ParserError(BotBaseException):
    """Raised when parsing fails"""
    pass


class RateLimitError(BotBaseException):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str, retry_after: Optional[float] = None, context: Optional[str] = None):
        self.retry_after = retry_after
        super().__init__(message, context)


class MediaError(BotBaseException):
    """Raised when media processing fails"""
    pass


class StateError(BotBaseException):
    """Raised when FSM state is invalid"""
    pass

