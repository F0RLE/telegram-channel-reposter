"""Application constants and configuration defaults"""
from typing import Final

# ==========================================
# PARSER CONSTANTS
# ==========================================
DEFAULT_MAX_POSTS_PER_CHANNEL: Final[int] = 5
DEFAULT_MAX_AGE_HOURS: Final[int] = 48
PARSER_CACHE_TTL: Final[int] = 300  # 5 minutes
PARSER_TIMEOUT: Final[int] = 15  # seconds
PARSER_MAX_RETRIES: Final[int] = 3

# ==========================================
# LLM CONSTANTS
# ==========================================
DEFAULT_LLM_TEMPERATURE: Final[float] = 0.7
DEFAULT_LLM_CONTEXT_WINDOW: Final[int] = 4096
LLM_REQUEST_TIMEOUT: Final[int] = 120  # seconds
LLM_MAX_RETRIES: Final[int] = 3
LLM_MAX_TEXT_LENGTH: Final[int] = 10000  # characters

# ==========================================
# STABLE DIFFUSION CONSTANTS
# ==========================================
DEFAULT_SD_STEPS: Final[int] = 30
DEFAULT_SD_CFG: Final[float] = 6.0
DEFAULT_SD_WIDTH: Final[int] = 896
DEFAULT_SD_HEIGHT: Final[int] = 1152
SD_GENERATION_TIMEOUT: Final[int] = 360  # seconds
SD_MAX_RETRIES: Final[int] = 2
SD_MIN_DIMENSION: Final[int] = 64
SD_MAX_DIMENSION: Final[int] = 2048
SD_DIMENSION_MULTIPLE: Final[int] = 8

# ==========================================
# TELEGRAM CONSTANTS
# ==========================================
TELEGRAM_MAX_MESSAGE_LENGTH: Final[int] = 4096
TELEGRAM_MAX_CAPTION_LENGTH: Final[int] = 1024
TELEGRAM_MAX_MEDIA_GROUP_SIZE: Final[int] = 10
TELEGRAM_MAX_FILE_SIZE: Final[int] = 50 * 1024 * 1024  # 50 MB

# ==========================================
# RATE LIMITING CONSTANTS
# ==========================================
RATE_LIMIT_LLM_CALLS: Final[int] = 10
RATE_LIMIT_LLM_PERIOD: Final[float] = 1.0
RATE_LIMIT_SD_CALLS: Final[int] = 5
RATE_LIMIT_SD_PERIOD: Final[float] = 2.0
RATE_LIMIT_PARSER_CALLS: Final[int] = 20
RATE_LIMIT_PARSER_PERIOD: Final[float] = 1.0

# ==========================================
# USER INTERACTION CONSTANTS
# ==========================================
USER_LOCK_TIMEOUT: Final[float] = 1.0  # seconds - prevent double-clicks
ANIMATION_UPDATE_INTERVAL: Final[float] = 0.5  # seconds

# ==========================================
# FILE CONSTANTS
# ==========================================
MAX_TEXT_FILE_SIZE: Final[int] = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_FILE_SIZE: Final[int] = 20 * 1024 * 1024  # 20 MB

# ==========================================
# SSL/TLS CONSTANTS
# ==========================================
# WARNING: SSL verification is disabled for local connections only
# This is safe for localhost (127.0.0.1) but should NOT be used for remote connections
SSL_VERIFY_LOCALHOST: Final[bool] = False  # Only for 127.0.0.1
SSL_VERIFY_REMOTE: Final[bool] = True  # Always verify remote connections

# ==========================================
# ERROR HANDLING CONSTANTS
# ==========================================
DEFAULT_RETRY_ATTEMPTS: Final[int] = 3
DEFAULT_RETRY_INITIAL_DELAY: Final[float] = 1.0
DEFAULT_RETRY_MAX_DELAY: Final[float] = 60.0
DEFAULT_RETRY_EXPONENTIAL_BASE: Final[float] = 2.0

# ==========================================
# MONITORING CONSTANTS
# ==========================================
METRICS_MAX_HISTORY: Final[int] = 1000
SYSTEM_METRICS_INTERVAL: Final[float] = 0.1  # seconds

