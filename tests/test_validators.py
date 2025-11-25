"""Tests for validation utilities"""
import pytest
from core.validators import (
    validate_bot_token, validate_channel_id, validate_url,
    validate_channel_name, validate_temperature, validate_positive_int,
    validate_image_dimensions, sanitize_text, validate_config
)


class TestBotTokenValidation:
    """Tests for bot token validation"""
    
    def test_valid_token(self):
        """Test valid bot token"""
        token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789"
        assert validate_bot_token(token) is True
    
    def test_invalid_token_short(self):
        """Test invalid token - too short"""
        token = "123:ABC"
        assert validate_bot_token(token) is False
    
    def test_invalid_token_wrong_format(self):
        """Test invalid token - wrong format"""
        token = "not-a-token"
        assert validate_bot_token(token) is False
    
    def test_empty_token(self):
        """Test empty token"""
        assert validate_bot_token("") is False
        assert validate_bot_token(None) is False


class TestChannelValidation:
    """Tests for channel validation"""
    
    def test_valid_channel_id(self):
        """Test valid channel ID"""
        assert validate_channel_id(-1001234567890) is True
        assert validate_channel_id(123456789) is True
    
    def test_invalid_channel_id_zero(self):
        """Test invalid channel ID - zero"""
        assert validate_channel_id(0) is False
    
    def test_invalid_channel_id_string(self):
        """Test invalid channel ID - string"""
        assert validate_channel_id("not-a-number") is False
    
    def test_valid_channel_name(self):
        """Test valid channel name"""
        assert validate_channel_name("testchannel") is True
        assert validate_channel_name("@testchannel") is True
    
    def test_invalid_channel_name_too_short(self):
        """Test invalid channel name - too short"""
        assert validate_channel_name("test") is False
    
    def test_invalid_channel_name_too_long(self):
        """Test invalid channel name - too long"""
        assert validate_channel_name("a" * 33) is False


class TestURLValidation:
    """Tests for URL validation"""
    
    def test_valid_url(self):
        """Test valid URL"""
        assert validate_url("https://t.me/test") is True
        assert validate_url("http://example.com") is True
    
    def test_invalid_url(self):
        """Test invalid URL"""
        assert validate_url("not-a-url") is False
        assert validate_url("") is False


class TestTemperatureValidation:
    """Tests for temperature validation"""
    
    def test_valid_temperature(self):
        """Test valid temperature"""
        assert validate_temperature(0.7) is True
        assert validate_temperature(0.0) is True
        assert validate_temperature(2.0) is True
    
    def test_invalid_temperature_too_high(self):
        """Test invalid temperature - too high"""
        assert validate_temperature(3.0) is False
    
    def test_invalid_temperature_negative(self):
        """Test invalid temperature - negative"""
        assert validate_temperature(-1.0) is False


class TestImageDimensionsValidation:
    """Tests for image dimensions validation"""
    
    def test_valid_dimensions(self):
        """Test valid dimensions"""
        assert validate_image_dimensions(896, 1152) is True
        assert validate_image_dimensions(512, 512) is True
    
    def test_invalid_dimensions_not_multiple_of_8(self):
        """Test invalid dimensions - not multiple of 8"""
        assert validate_image_dimensions(900, 1152) is False
    
    def test_invalid_dimensions_too_small(self):
        """Test invalid dimensions - too small"""
        assert validate_image_dimensions(32, 32) is False
    
    def test_invalid_dimensions_too_large(self):
        """Test invalid dimensions - too large"""
        assert validate_image_dimensions(3000, 3000) is False


class TestTextSanitization:
    """Tests for text sanitization"""
    
    def test_sanitize_normal_text(self):
        """Test sanitization of normal text"""
        text = "Normal text here"
        assert sanitize_text(text) == text
    
    def test_sanitize_control_characters(self):
        """Test sanitization removes control characters"""
        text = "Text\x00with\x01control\x02chars"
        result = sanitize_text(text)
        assert "\x00" not in result
        assert "\x01" not in result
    
    def test_sanitize_preserves_newlines(self):
        """Test sanitization preserves newlines"""
        text = "Line 1\nLine 2\nLine 3"
        assert "\n" in sanitize_text(text)
    
    def test_sanitize_truncates_long_text(self):
        """Test sanitization truncates very long text"""
        text = "a" * 20000
        result = sanitize_text(text, max_length=10000)
        assert len(result) <= 10000


class TestConfigValidation:
    """Tests for configuration validation"""
    
    def test_valid_config(self):
        """Test valid configuration"""
        config = {"key1": "value1", "key2": "value2"}
        assert validate_config(config, ["key1", "key2"]) is True
    
    def test_invalid_config_missing_key(self):
        """Test invalid configuration - missing key"""
        config = {"key1": "value1"}
        assert validate_config(config, ["key1", "key2"]) is False
    
    def test_invalid_config_not_dict(self):
        """Test invalid configuration - not a dictionary"""
        assert validate_config("not-a-dict", ["key1"]) is False

