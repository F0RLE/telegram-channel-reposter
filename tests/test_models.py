"""Tests for Pydantic models"""
import pytest
from datetime import datetime
from core.models import (
    ChannelConfig, TopicConfig, LLMConfig, SDConfig,
    PostData, PublishedPost, APICallMetrics
)
from pydantic import ValidationError


class TestChannelConfig:
    """Tests for ChannelConfig model"""
    
    def test_valid_channel(self):
        """Test valid channel configuration"""
        config = ChannelConfig(name="testchannel")
        assert config.name == "testchannel"
    
    def test_channel_with_at_prefix(self):
        """Test channel name with @ prefix is stripped"""
        config = ChannelConfig(name="@testchannel")
        assert config.name == "testchannel"
    
    def test_invalid_channel_name_too_short(self):
        """Test channel name validation - too short"""
        with pytest.raises(ValidationError):
            ChannelConfig(name="test")
    
    def test_invalid_channel_name_too_long(self):
        """Test channel name validation - too long"""
        with pytest.raises(ValidationError):
            ChannelConfig(name="a" * 33)


class TestTopicConfig:
    """Tests for TopicConfig model"""
    
    def test_valid_topic(self):
        """Test valid topic configuration"""
        config = TopicConfig(name="Test Topic", channels=["channel1", "channel2"])
        assert config.name == "Test Topic"
        assert len(config.channels) == 2
    
    def test_topic_with_channel_at_prefix(self):
        """Test channels with @ prefix are stripped"""
        config = TopicConfig(name="Test", channels=["@channel1", "@channel2"])
        assert config.channels == ["channel1", "channel2"]
    
    def test_invalid_channel_in_topic(self):
        """Test invalid channel name in topic"""
        with pytest.raises(ValidationError):
            TopicConfig(name="Test", channels=["short"])


class TestLLMConfig:
    """Tests for LLMConfig model"""
    
    def test_valid_llm_config(self):
        """Test valid LLM configuration"""
        config = LLMConfig(model="test-model", temperature=0.7)
        assert config.model == "test-model"
        assert config.temperature == 0.7
    
    def test_invalid_temperature_too_high(self):
        """Test temperature validation - too high"""
        with pytest.raises(ValidationError):
            LLMConfig(model="test", temperature=3.0)
    
    def test_invalid_temperature_negative(self):
        """Test temperature validation - negative"""
        with pytest.raises(ValidationError):
            LLMConfig(model="test", temperature=-1.0)


class TestSDConfig:
    """Tests for SDConfig model"""
    
    def test_valid_sd_config(self):
        """Test valid SD configuration"""
        config = SDConfig(width=896, height=1152)
        assert config.width == 896
        assert config.height == 1152
    
    def test_invalid_dimension_not_multiple_of_8(self):
        """Test dimension validation - not multiple of 8"""
        with pytest.raises(ValidationError):
            SDConfig(width=900, height=1152)
    
    def test_valid_dimensions_multiple_of_8(self):
        """Test valid dimensions that are multiples of 8"""
        config = SDConfig(width=896, height=1152)
        assert config.width % 8 == 0
        assert config.height % 8 == 0


class TestPostData:
    """Tests for PostData model"""
    
    def test_valid_post_data(self):
        """Test valid post data"""
        post = PostData(
            channel="testchannel",
            text="Test post",
            link="https://t.me/test/1",
            has_media=True
        )
        assert post.channel == "testchannel"
        assert post.text == "Test post"
        assert post.has_media is True
    
    def test_post_data_with_extra_fields(self):
        """Test post data with extra fields (for saved progress)"""
        post = PostData(
            channel="test",
            saved_text="Saved text",
            saved_gen_bytes=b"test"
        )
        assert hasattr(post, "saved_text")
        assert hasattr(post, "saved_gen_bytes")


class TestPublishedPost:
    """Tests for PublishedPost model"""
    
    def test_valid_published_post(self):
        """Test valid published post"""
        post = PublishedPost(
            link="https://t.me/test/1",
            published_at=datetime.now()
        )
        assert post.link == "https://t.me/test/1"
        assert isinstance(post.published_at, datetime)


class TestAPICallMetrics:
    """Tests for APICallMetrics model"""
    
    def test_valid_metrics(self):
        """Test valid API call metrics"""
        metrics = APICallMetrics(
            service="llm",
            success=True,
            duration=1.5
        )
        assert metrics.service == "llm"
        assert metrics.success is True
        assert metrics.duration == 1.5
    
    def test_invalid_service(self):
        """Test invalid service name"""
        with pytest.raises(ValidationError):
            APICallMetrics(service="invalid", success=True, duration=1.0)
    
    def test_negative_duration(self):
        """Test negative duration validation"""
        with pytest.raises(ValidationError):
            APICallMetrics(service="llm", success=True, duration=-1.0)

