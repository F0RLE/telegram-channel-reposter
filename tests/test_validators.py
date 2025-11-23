"""Tests for validators module"""
import pytest
import sys
import os

# Add parent directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'system', 'src'))

from core.validators import (
    validate_bot_token,
    validate_channel_id,
    validate_url,
    validate_channel_name,
    validate_temperature,
    validate_positive_int,
    validate_image_dimensions,
    sanitize_text,
    validate_config
)


class TestBotTokenValidator:
    """Tests for bot token validation"""
    
    def test_valid_token(self):
        """Test valid bot token format"""
        token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789"
        assert validate_bot_token(token) is True
    
    def test_invalid_token_short(self):
        """Test invalid short token"""
        token = "123:ABC"
        assert validate_bot_token(token) is False
    
    def test_invalid_token_no_colon(self):
        """Test token without colon"""
        token = "123456789ABCdefGHIjklMNOpqrsTUVwxyz"
        assert validate_bot_token(token) is False
    
    def test_empty_token(self):
        """Test empty token"""
        assert validate_bot_token("") is False
        assert validate_bot_token(None) is False


class TestChannelIDValidator:
    """Tests for channel ID validation"""
    
    def test_valid_positive_id(self):
        """Test valid positive channel ID"""
        assert validate_channel_id(123456789) is True
    
    def test_valid_negative_id(self):
        """Test valid negative channel ID (group/channel)"""
        assert validate_channel_id(-1001234567890) is True
    
    def test_invalid_zero_id(self):
        """Test invalid zero ID"""
        assert validate_channel_id(0) is False
    
    def test_invalid_string_id(self):
        """Test invalid string ID"""
        assert validate_channel_id("invalid") is False


class TestURLValidator:
    """Tests for URL validation"""
    
    def test_valid_http_url(self):
        """Test valid HTTP URL"""
        assert validate_url("http://example.com") is True
    
    def test_valid_https_url(self):
        """Test valid HTTPS URL"""
        assert validate_url("https://example.com/path?query=1") is True
    
    def test_invalid_url_no_protocol(self):
        """Test URL without protocol"""
        assert validate_url("example.com") is False
    
    def test_invalid_empty_url(self):
        """Test empty URL"""
        assert validate_url("") is False


class TestChannelNameValidator:
    """Tests for channel name validation"""
    
    def test_valid_channel_name(self):
        """Test valid channel name"""
        assert validate_channel_name("testchannel") is True
        assert validate_channel_name("@testchannel") is True
    
    def test_invalid_short_name(self):
        """Test too short channel name"""
        assert validate_channel_name("test") is False
    
    def test_invalid_special_chars(self):
        """Test channel name with special characters"""
        assert validate_channel_name("test-channel!") is False


class TestTemperatureValidator:
    """Tests for temperature validation"""
    
    def test_valid_temperature(self):
        """Test valid temperature values"""
        assert validate_temperature(0.0) is True
        assert validate_temperature(0.7) is True
        assert validate_temperature(2.0) is True
    
    def test_invalid_negative_temperature(self):
        """Test negative temperature"""
        assert validate_temperature(-0.1) is False
    
    def test_invalid_high_temperature(self):
        """Test too high temperature"""
        assert validate_temperature(2.1) is False


class TestImageDimensionsValidator:
    """Tests for image dimensions validation"""
    
    def test_valid_dimensions(self):
        """Test valid image dimensions"""
        assert validate_image_dimensions(512, 512) is True
        assert validate_image_dimensions(896, 1152) is True
        assert validate_image_dimensions(1024, 1024) is True
    
    def test_invalid_not_multiple_of_8(self):
        """Test dimensions not multiple of 8"""
        assert validate_image_dimensions(513, 512) is False
        assert validate_image_dimensions(512, 515) is False
    
    def test_invalid_too_small(self):
        """Test too small dimensions"""
        assert validate_image_dimensions(32, 32) is False
    
    def test_invalid_too_large(self):
        """Test too large dimensions"""
        assert validate_image_dimensions(3000, 3000) is False


class TestSanitizeText:
    """Tests for text sanitization"""
    
    def test_sanitize_normal_text(self):
        """Test sanitizing normal text"""
        text = "Hello, World!"
        assert sanitize_text(text) == "Hello, World!"
    
    def test_sanitize_control_chars(self):
        """Test removing control characters"""
        text = "Hello\x00World\x01Test"
        result = sanitize_text(text)
        assert "\x00" not in result
        assert "\x01" not in result
    
    def test_sanitize_long_text(self):
        """Test truncating long text"""
        text = "A" * 20000
        result = sanitize_text(text, max_length=10000)
        assert len(result) == 10000
    
    def test_sanitize_empty_text(self):
        """Test sanitizing empty text"""
        assert sanitize_text("") == ""
        assert sanitize_text(None) == ""


class TestConfigValidator:
    """Tests for config validation"""
    
    def test_valid_config(self):
        """Test valid configuration"""
        config = {"key1": "value1", "key2": "value2"}
        assert validate_config(config, ["key1", "key2"]) is True
    
    def test_missing_key(self):
        """Test config with missing key"""
        config = {"key1": "value1"}
        assert validate_config(config, ["key1", "key2"]) is False
    
    def test_invalid_type(self):
        """Test invalid config type"""
        assert validate_config("not a dict", ["key1"]) is False
        assert validate_config(None, ["key1"]) is False

