import os
import json
import logging
from dotenv import load_dotenv

# ==========================================
# 1. PATH CONFIGURATION
# ==========================================
# Priority 1: Get path from Launcher Environment Variable
CONFIG_DIR = os.getenv("BOT_CONFIG_DIR")

# Priority 2: Hardcoded AppData path
if not CONFIG_DIR:
    appdata = os.environ.get("APPDATA")
    if appdata:
        CONFIG_DIR = os.path.join(appdata, "TelegramBotData", "data", "configs")
    else:
        # Fallback for non-standard envs (just in case)
        CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure config directory exists
if not os.path.exists(CONFIG_DIR):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception:
        pass

# File Paths
ENV_PATH = os.path.join(CONFIG_DIR, ".env")
CHANNELS_PATH = os.path.join(CONFIG_DIR, "channels.json")
GEN_CONFIG_PATH = os.path.join(CONFIG_DIR, "generation_config.json")

# Data Directory (for logs/published posts)
DATA_DIR = os.path.dirname(CONFIG_DIR) 
PUBLISHED_POSTS_FILE = os.path.join(DATA_DIR, "published_posts.json")

# ==========================================
# 2. LOAD ENVIRONMENT VARIABLES
# ==========================================
load_dotenv(ENV_PATH)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Target Channel ID
try:
    TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID", "0"))
except ValueError:
    TARGET_CHANNEL_ID = 0

# ==========================================
# 3. LOAD JSON SETTINGS
# ==========================================

# Channels List
# Файл channels.json создается только при первом добавлении канала/темы через UI
# Не создается автоматически при инициализации
TELEGRAM_CHANNELS = {}

def reload_channels():
    """Перезагружает каналы из channels.json"""
    global TELEGRAM_CHANNELS
    if os.path.exists(CHANNELS_PATH):
        try:
            with open(CHANNELS_PATH, 'r', encoding='utf-8') as f:
                TELEGRAM_CHANNELS = json.load(f)
            logging.info(f"✅ Каналы перезагружены: {len(TELEGRAM_CHANNELS)} тем")
        except Exception as e:
            logging.error(f"❌ Ошибка чтения channels.json: {e}")
    else:
        TELEGRAM_CHANNELS = {}

# Загружаем каналы при старте
reload_channels()

# Generation Settings (Defaults)
LLM_TEMP = 0.7
LLM_CTX = 4096
SD_STEPS = 30
SD_CFG = 6.0
SD_WIDTH = 896
SD_HEIGHT = 1152

# Load overrides from JSON if exists
if os.path.exists(GEN_CONFIG_PATH):
    try:
        with open(GEN_CONFIG_PATH, 'r', encoding='utf-8') as f:
            gen_cfg = json.load(f)
            LLM_TEMP = float(gen_cfg.get("llm_temp", 0.7))
            LLM_CTX = int(gen_cfg.get("llm_ctx", 4096))
            SD_STEPS = int(gen_cfg.get("sd_steps", 30))
            SD_CFG = float(gen_cfg.get("sd_cfg", 6.0))
            SD_WIDTH = int(gen_cfg.get("sd_width", 896))
            SD_HEIGHT = int(gen_cfg.get("sd_height", 1152))
    except Exception:
        pass

# ==========================================
# 4. SERVICE URLs
# ==========================================

# LLM (Ollama Server with OpenAI-compatible API)
# Ollama использует порт 11434 по умолчанию
# Для OpenAI-совместимого API используем /v1/chat/completions
OLLAMA_API_BASE = "http://127.0.0.1:11434/v1"  # Стандартный порт Ollama

# Load model name from .env file (SELECTED_LLM_MODEL format: "type:name" or "type:name:path")
OLLAMA_MODEL = "local-model"  # Default fallback
try:
    from dotenv import get_key
    selected_model = get_key(ENV_PATH, "SELECTED_LLM_MODEL")
    if selected_model and selected_model.strip():
        # Parse format: "ollama:model-name" or "gguf:model-name:path"
        parts = selected_model.strip().split(":", 2)
        if len(parts) >= 2 and parts[1]:
            # Extract model name (second part)
            OLLAMA_MODEL = parts[1].strip()
            logging.info(f"✅ Loaded LLM model from .env: {OLLAMA_MODEL}")
        else:
            logging.warning(f"⚠️ Invalid SELECTED_LLM_MODEL format: {selected_model}, using default")
    else:
        logging.info("ℹ️ SELECTED_LLM_MODEL not set, using default: local-model")
except Exception as e:
    logging.warning(f"⚠️ Failed to load SELECTED_LLM_MODEL from .env: {e}, using default")

OLLAMA_API_KEY = "dummy"  # Ollama не требует ключ, но оставляем для совместимости

# Stable Diffusion (Forge API)
SD_API_URL = "http://127.0.0.1:7860/sdapi/v1/txt2img"
IMAGE_GENERATION_TIMEOUT = 360

# Stable Diffusion Generation Settings
SD_SAMPLER = "DPM++ 2M"
SD_SCHEDULER = "Karras"
SD_POSITIVE_PROMPT_PREFIX = "score_9, score_8_up, score_7_up, source_anime, "
SD_NEGATIVE_PROMPT_DEFAULT = (
    "score_6, score_5, score_4, (worst quality:1.2), (low quality:1.2), "
    "(normal quality:1.2), lowres, bad anatomy, bad hands, signature, watermarks, "
    "ugly, imperfect eyes, skewed eyes, unnatural face, unnatural body, error, "
    "extra limb, missing limbs, text, username, artist name"
)

# ADetailer Configuration
ADETAILER_FACE_CONFIG = {
    "ad_model": "face_yolov9c.pt",
    "ad_prompt": "detailed face, beautiful eyes, perfect skin, make up",
    "ad_negative_prompt": "ugly, blurry, lowres, bad anatomy",
    "ad_confidence": 0.3,
    "ad_mask_blur": 4,
    "ad_denoising_strength": 0.35,
    "ad_inpaint_only_masked": True,
    "ad_inpaint_width": 512,
    "ad_inpaint_height": 512
}

ADETAILER_HAND_CONFIG = {
    "ad_model": "hand_yolov9c.pt",
    "ad_prompt": "perfect hands, anatomical fingers, detailed skin texture",
    "ad_negative_prompt": "extra fingers, missing fingers, fused fingers, claws, mutation",
    "ad_confidence": 0.3,
    "ad_mask_blur": 4,
    "ad_denoising_strength": 0.4,
    "ad_inpaint_only_masked": True,
    "ad_use_noise_multiplier": True
}

ADETAILER_PERSON_CONFIG = {
    "ad_model": "person_yolov8s-seg.pt",
    "ad_prompt": "perfect anatomy, high quality body",
    "ad_confidence": 0.25,
    "ad_mask_blur": 8,
    "ad_denoising_strength": 0.2,
    "ad_inpaint_only_masked": True
}

ADETAILER_CLOTHING_CONFIG = {
    "ad_model": "deepfashion2_yolov8s-seg.pt",
    "ad_prompt": "detailed clothes, fabric texture, realistic folds",
    "ad_confidence": 0.25,
    "ad_mask_blur": 4,
    "ad_denoising_strength": 0.25,
    "ad_inpaint_only_masked": True
}