"""Data validation utilities"""
import re
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def validate_bot_token(token: str) -> bool:
    """
    Validate Telegram bot token format.
    
    Expected format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz (35 chars after colon)
    
    Args:
        token: Bot token string to validate
        
    Returns:
        True if token format is valid, False otherwise
    """
    if not token or not isinstance(token, str):
        return False
    # Telegram bot tokens are typically in format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
    pattern = r'^\d+:[A-Za-z0-9_-]{35}$'
    return bool(re.match(pattern, token))


def validate_channel_id(channel_id: Any) -> bool:
    """Validate Telegram channel ID"""
    try:
        channel_id_int = int(channel_id)
        # Channel IDs are typically negative integers for groups/channels
        # or positive for users, but we accept any integer
        return isinstance(channel_id_int, int) and channel_id_int != 0
    except (ValueError, TypeError):
        return False


def validate_url(url: str) -> bool:
    """Validate URL format"""
    if not url or not isinstance(url, str):
        return False
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def validate_channel_name(channel_name: str) -> bool:
    """Validate Telegram channel name format"""
    if not channel_name or not isinstance(channel_name, str):
        return False
    # Remove @ if present
    name = channel_name.lstrip('@')
    # Telegram channel names: 5-32 chars, alphanumeric and underscores
    pattern = r'^[a-zA-Z0-9_]{5,32}$'
    return bool(re.match(pattern, name))


def validate_temperature(temp: Any) -> bool:
    """Validate temperature value (0.0-2.0)"""
    try:
        temp_float = float(temp)
        return 0.0 <= temp_float <= 2.0
    except (ValueError, TypeError):
        return False


def validate_positive_int(value: Any, min_val: int = 1, max_val: Optional[int] = None) -> bool:
    """Validate positive integer within range"""
    try:
        value_int = int(value)
        if value_int < min_val:
            return False
        if max_val is not None and value_int > max_val:
            return False
        return True
    except (ValueError, TypeError):
        return False


def validate_image_dimensions(width: Any, height: Any) -> bool:
    """Validate image dimensions (must be multiples of 8, reasonable size)"""
    try:
        w = int(width)
        h = int(height)
        # Must be multiples of 8 for SD
        if w % 8 != 0 or h % 8 != 0:
            return False
        # Reasonable size limits
        if w < 64 or w > 2048 or h < 64 or h > 2048:
            return False
        return True
    except (ValueError, TypeError):
        return False


def sanitize_text(text: str, max_length: int = 10000) -> str:
    """Sanitize text input"""
    if not isinstance(text, str):
        return ""
    # Remove null bytes and control characters (except newlines and tabs)
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    return text.strip()


def validate_config(config: Dict[str, Any], required_keys: List[str]) -> bool:
    """Validate configuration dictionary has required keys"""
    if not isinstance(config, dict):
        return False
    return all(key in config for key in required_keys)

