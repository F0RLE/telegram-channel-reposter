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
import sys
PYTHON_EXE = sys.executable
# Try to find git in env dir, otherwise assume it's in PATH
GIT_CMD_ENV = os.path.join(ENV_DIR, "git", "cmd", "git.exe")
GIT_CMD = GIT_CMD_ENV if os.path.exists(GIT_CMD_ENV) else "git"

# Ollama paths - using system installation for GPU support
# Check if system Ollama exists, otherwise fallback to embedded version
SYSTEM_OLLAMA_PATH = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
if os.path.exists(SYSTEM_OLLAMA_PATH):
    OLLAMA_EXE = SYSTEM_OLLAMA_PATH
    OLLAMA_DIR = os.path.dirname(SYSTEM_OLLAMA_PATH)
else:
    # Fallback to embedded version
    OLLAMA_DIR = os.path.join(DIR_ENGINE, "ollama")
    OLLAMA_EXE = os.path.join(OLLAMA_DIR, "ollama.exe")

# Data directory still in launcher folder
OLLAMA_DATA_DIR = os.path.join(DIR_ENGINE, "ollama", "data")
OLLAMA_MODELS_DIR = os.path.join(OLLAMA_DIR, "models")

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

def get_use_gpu():
    """Get GPU usage preference"""
    try:
        # Ensure config directory exists
        os.makedirs(DIR_CONFIGS, exist_ok=True)
        
        # Create .env if it doesn't exist
        if not os.path.exists(FILE_ENV):
            with open(FILE_ENV, 'w', encoding='utf-8') as f:
                f.write("USE_GPU=true\n")
            return True
        
        from dotenv import get_key
        val = get_key(FILE_ENV, "USE_GPU")
        if val is None:
            # Set default if key doesn't exist
            from dotenv import set_key
            set_key(FILE_ENV, "USE_GPU", "true")
            return True
        return val.lower() == "true"
    except Exception as e:
        # Default to GPU if any error
        return True

USE_GPU = get_use_gpu()

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
    'input_bg': '#1c2028',  # Input fields background (lighter than bg for contrast, ~5% brighter)
    'primary': '#3d7bff',  # Electric blue for actions
    'primary_hover': '#5a8fff',  # Lighter blue on hover
    'secondary': '#59d4c8',  # Turquoise for statuses
    'success': '#10b981',
    'danger': '#ef4444',
    'warning': '#ffb84d',  # Warm amber
    'text': '#E0E0E0',  # Light gray for body text (better readability)
    'text_secondary': '#C0C0C0',  # Medium gray for labels (14px, medium weight)
    'text_muted': '#8a8a8a',  # Muted gray for small elements (12-13px)
    'border': '#3a3f48',  # Default border (dark gray, more visible)
    'border_focus': '#3d7bff',  # Focus border (accent color)
    'border_hover': '#4a4f58',  # Hover border (slightly lighter)
    'accent': '#3d7bff',
}

