"""
Configuration and path definitions for launcher
"""
import os

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # system/src
APPDATA_ROOT = os.path.join(os.environ["APPDATA"], "TelegramBotData")
DATA_ROOT = os.path.join(APPDATA_ROOT, "data")
ENV_DIR = os.path.join(APPDATA_ROOT, "env")

# Engine directories
DIR_ENGINE = os.path.join(DATA_ROOT, "Engine")
DIR_CONFIGS = os.path.join(DATA_ROOT, "configs")
DIR_LOGS = os.path.join(DATA_ROOT, "logs")
DIR_TEMP = os.path.join(DATA_ROOT, "temp")

# Executables
PYTHON_EXE = os.path.join(ENV_DIR, "python", "python.exe")
GIT_CMD = os.path.join(ENV_DIR, "git", "cmd", "git.exe")

# Ollama paths
OLLAMA_DIR = os.path.join(DIR_ENGINE, "ollama")
OLLAMA_EXE = os.path.join(OLLAMA_DIR, "ollama.exe")
OLLAMA_MODELS_DIR = os.path.join(OLLAMA_DIR, "models")
OLLAMA_DATA_DIR = os.path.join(OLLAMA_DIR, "data")

# Models directory
def get_models_llm_dir():
    """Get models directory from settings or use default"""
    try:
        from dotenv import get_key
        # FILE_ENV is defined below, but we need it here
        env_file = os.path.join(DIR_CONFIGS, ".env")
        custom_path = get_key(env_file, "MODELS_LLM_DIR")
        if custom_path and os.path.exists(custom_path):
            return custom_path
    except:
        pass
    # Default path: AppData\Roaming\TelegramBotData\data\Engine\LLM_Models
    default_path = os.path.join(DIR_ENGINE, "LLM_Models")
    return default_path

MODELS_LLM_DIR = get_models_llm_dir()

# Stable Diffusion paths
SD_DIR = os.path.join(DIR_ENGINE, "stable-diffusion-webui-reforge")
MODELS_SD_DIR = os.path.join(SD_DIR, "models", "Stable-diffusion")
AD_MODELS_DIR = os.path.join(SD_DIR, "models", "adetailer")
ADETAILER_DIR = os.path.join(SD_DIR, "extensions", "adetailer")

# Configuration files (FILE_ENV is used in get_models_llm_dir, so define it here)
FILE_ENV = os.path.join(DIR_CONFIGS, ".env")
FILE_CHANNELS = os.path.join(DIR_CONFIGS, "channels.json")
FILE_GEN_CONFIG = os.path.join(DIR_CONFIGS, "generation_config.json")
FILE_PID = os.path.join(DIR_TEMP, "launcher.pid")
FILE_SD_CACHE = os.path.join(DIR_CONFIGS, "sd_compatibility_cache.json")

# URLs
SD_REPO = "https://github.com/lllyasviel/stable-diffusion-webui-forge.git"
ADETAILER_REPO = "https://github.com/Bing-su/adetailer.git"
MODEL_SD_URL = "https://civitai.com/api/download/models/2334591?type=Model&format=SafeTensor&size=full&fp=fp32"
MODEL_SD_FILENAME = "cyberrealisticPony_v141.safetensors"

AD_MODELS_URLS = {
    "face_yolov9c.pt": "https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov9c.pt",
    "hand_yolov9c.pt": "https://huggingface.co/Bingsu/adetailer/resolve/main/hand_yolov9c.pt"
}

# Color scheme - Modern dark theme with glassmorphism
COLORS = {
    'bg': '#0f1117',  # Deep charcoal base
    'surface': '#181c24',  # Graphite cards
    'surface_light': '#1f2329',  # Lighter cards
    'surface_dark': '#0a0d12',  # Darker surfaces
    'card_bg': '#181c24',  # Card background (graphite)
    'sidebar': '#141820',  # Sidebar background
    'primary': '#3d7bff',  # Electric blue for actions
    'primary_hover': '#5a8fff',  # Lighter blue on hover
    'secondary': '#59d4c8',  # Turquoise for statuses
    'success': '#10b981',
    'danger': '#ef4444',
    'warning': '#ffb84d',  # Warm amber
    'text': '#ffffff',  # White for headings
    'text_secondary': '#a0a0a0',  # Gray for labels
    'text_muted': '#6b7280',  # Muted gray
    'border': '#2a2f38',  # Subtle borders
    'accent': '#3d7bff',
}

