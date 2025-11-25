"""Pydantic models for data validation and type safety"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, HttpUrl, ConfigDict
from datetime import datetime


class ChannelConfig(BaseModel):
    """Configuration for a Telegram channel"""
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(..., min_length=5, max_length=32, description="Channel name without @")
    url: Optional[str] = Field(None, description="Channel URL")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Remove @ prefix if present"""
        return v.lstrip('@')


class TopicConfig(BaseModel):
    """Configuration for a topic with channels"""
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(..., min_length=1, max_length=100)
    channels: List[str] = Field(default_factory=list, min_length=0)
    
    @field_validator('channels', mode='before')
    @classmethod
    def validate_channels(cls, v: List[str]) -> List[str]:
        """Validate each channel name"""
        if not isinstance(v, list):
            return []
        validated = []
        for channel in v:
            name = channel.lstrip('@')
            if not (5 <= len(name) <= 32):
                raise ValueError(f"Channel name must be 5-32 characters: {channel}")
            validated.append(name)
        return validated


class LLMConfig(BaseModel):
    """LLM generation configuration"""
    model_config = ConfigDict(extra="forbid")
    
    model: str = Field(..., min_length=1, max_length=200)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    context_window: int = Field(4096, ge=512, le=32768)
    system_prompt: str = Field(default="", max_length=5000)
    user_prompt_template: str = Field(default="", max_length=2000)
    cliches: List[str] = Field(default_factory=list)


class SDConfig(BaseModel):
    """Stable Diffusion generation configuration"""
    model_config = ConfigDict(extra="forbid")
    
    steps: int = Field(30, ge=1, le=150)
    cfg_scale: float = Field(6.0, ge=1.0, le=30.0)
    width: int = Field(896, ge=64, le=2048)
    height: int = Field(1152, ge=64, le=2048)
    sampler: str = Field("DPM++ 2M", max_length=100)
    scheduler: str = Field("Karras", max_length=100)
    timeout: int = Field(360, ge=30, le=1800)
    
    @field_validator('width', 'height')
    @classmethod
    def validate_dimensions(cls, v: int) -> int:
        """Dimensions must be multiples of 8"""
        if v % 8 != 0:
            raise ValueError(f"Dimension must be multiple of 8: {v}")
        return v


class PostData(BaseModel):
    """Parsed post data from channel"""
    model_config = ConfigDict(extra="allow")  # Allow additional fields for saved progress
    
    channel: str
    text: str = ""
    link: Optional[str] = None
    timestamp: Optional[str] = None
    has_media: bool = False
    media_urls: List[str] = Field(default_factory=list)
    media_type: Optional[str] = Field(None, pattern="^(photo|video)$")


class PublishedPost(BaseModel):
    """Published post record"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    link: str = Field(..., min_length=1)
    published_at: datetime
    channel: Optional[str] = None


class APICallMetrics(BaseModel):
    """API call metrics"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    service: str = Field(..., pattern="^(llm|sd|parser|telegram)$")
    success: bool
    duration: float = Field(..., ge=0.0)
    timestamp: Optional[datetime] = None

