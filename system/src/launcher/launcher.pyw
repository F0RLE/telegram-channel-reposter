import sys
import os
import glob
import subprocess
import threading
import queue
import json
import time
import shutil
import ctypes
import urllib.request
from collections import OrderedDict

if not hasattr(sys, '_launcher_redirected'):
    sys._launcher_redirected = True
    sys.stderr = sys.stdout

try:
    if sys.stdout and hasattr(sys.stdout, 'buffer'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'buffer'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError, ValueError):
    pass

_launcher_dir = os.path.dirname(os.path.abspath(__file__))
if _launcher_dir not in sys.path:
    sys.path.insert(0, _launcher_dir)

try:
    from .installer import Installer
    from .service_manager import ServiceManager
    from .model_manager import ModelManager
    from .animations import (
        fade_in, fade_out, slide_in, slide_out, scale_in, pulse,
        button_hover_effect, smooth_color_transition, shake, bounce_in,
        stagger_children, interpolate_color
    )
    from .analytics import get_analytics, Analytics
    from .updater import get_updater, Updater
    from .security import get_security, Security
except (ImportError, ValueError):
    try:
        from installer import Installer
        from service_manager import ServiceManager
        from model_manager import ModelManager
        from animations import (
            fade_in, fade_out, slide_in, slide_out, scale_in, pulse,
            button_hover_effect, smooth_color_transition, shake, bounce_in,
            stagger_children, interpolate_color
        )
        from analytics import get_analytics, Analytics
        from updater import get_updater, Updater
        from security import get_security, Security
    except ImportError as e:
        import traceback
        print(f"ERROR: Failed to import required modules: {e}\n{traceback.format_exc()}")
        raise

    try:
        from .i18n import init_i18n, set_language, get_language, t, LANGUAGE_NAMES, SUPPORTED_LANGUAGES
    except (ImportError, ValueError):
        from i18n import init_i18n, set_language, get_language, t, LANGUAGE_NAMES, SUPPORTED_LANGUAGES
except ImportError:
    def t(key, default=None, **kwargs):
        return default or key
    def init_i18n(lang=None):
        return "en"
    def set_language(lang):
        return True
    def get_language():
        return "en"
    LANGUAGE_NAMES = {"en": "English", "ru": "Русский"}
    SUPPORTED_LANGUAGES = ["en", "ru"]
missing_modules = []
try:
    import requests  # type: ignore
except ImportError:
    missing_modules.append("requests")

try:
    import psutil  # type: ignore
except ImportError:
    missing_modules.append("psutil")

try:
    import tkinter as tk
    from tkinter import messagebox, filedialog
except ImportError:
    missing_modules.append("tkinter")

try:
    import webbrowser
except ImportError:
    pass  # webbrowser is usually built-in

try:
    from PIL import Image, ImageDraw  # type: ignore
except ImportError:
    Image = None
    ImageDraw = None

if missing_modules:
    def show_error(title, msg):
        try:
            ctypes.windll.user32.MessageBoxW(0, msg, title, 0x10)
        except:
            print(f"[ERROR] {title}: {msg}", flush=True)
    
    modules_str = ', '.join(missing_modules)
    error_msg = t(
        "ui.launcher.error.missing_modules_message",
        default="Отсутствуют необходимые модули Python!\n\nНе найдены: {modules}\n\nРЕШЕНИЕ:\n1. Запустите 'Install.bat' для установки всех зависимостей\n2. Или установите вручную:\n   pip install {modules}",
        modules=modules_str
    )
    show_error(t("ui.launcher.error.missing_modules", default="Ошибка: Отсутствуют модули"), error_msg)
    sys.exit(1)
def fix_tkinter_paths():
    base = os.path.dirname(sys.executable)
    lib = os.path.join(base, "Lib")
    tcl = os.path.join(lib, "tcl")
    tk_path = os.path.join(lib, "tk")
    
    if os.path.exists(tcl) and os.path.exists(tk_path):
        os.environ["TCL_LIBRARY"] = tcl
        os.environ["TK_LIBRARY"] = tk_path

    try:
        import tkinter_embed  # type: ignore
        bin_dir = os.path.join(os.path.dirname(tkinter_embed.__file__), "data", "bin")
        if os.path.exists(bin_dir):
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(bin_dir)
    except ImportError:
        pass

fix_tkinter_paths()

def show_error(title, msg):
    show_error_ui(title, msg)

try:
    import customtkinter as ctk  # type: ignore
    from dotenv import set_key, get_key  # type: ignore
except ImportError as e:
    error_msg = t(
        "ui.launcher.error.libraries_not_found",
        default="Libraries not found!\nPlease run 'Install.bat'.\n\nError: {error}",
        error=str(e)
    )
    show_error("Error", error_msg)
    sys.exit(1)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # system/src
APPDATA_ROOT = os.path.join(os.environ["APPDATA"], "TelegramBotData")
DATA_ROOT = os.path.join(APPDATA_ROOT, "data")
ENV_DIR = os.path.join(APPDATA_ROOT, "env")

DIR_ENGINE = os.path.join(DATA_ROOT, "Engine")
DIR_CONFIGS = os.path.join(DATA_ROOT, "configs")
DIR_LOGS = os.path.join(DATA_ROOT, "logs")
DIR_TEMP = os.path.join(DATA_ROOT, "temp")

PYTHON_EXE = os.path.join(ENV_DIR, "python", "python.exe")
GIT_CMD = os.path.join(ENV_DIR, "git", "cmd", "git.exe")

# Define FILE_ENV early so it can be used in functions
FILE_ENV = os.path.join(DIR_CONFIGS, ".env")

# Universal folder for all LLM models (GGUF and Ollama)
OLLAMA_DIR = os.path.join(DIR_ENGINE, "ollama")
OLLAMA_EXE = os.path.join(OLLAMA_DIR, "ollama.exe")
OLLAMA_MODELS_DIR = os.path.join(OLLAMA_DIR, "models")  # Universal folder for all models
OLLAMA_DATA_DIR = os.path.join(OLLAMA_DIR, "data")

# MODELS_LLM_DIR will be loaded from settings or use default folder
def get_models_llm_dir():
    """Get path to models folder from settings or use default folder"""
    try:
        from dotenv import get_key  # type: ignore
        custom_path = get_key(FILE_ENV, "MODELS_LLM_DIR")
        if custom_path and os.path.exists(custom_path):
            return custom_path
    except (ImportError, KeyError, OSError):
        pass
    # Default folder: AppData\Roaming\TelegramBotData\data\Engine\LLM_Models
    return os.path.join(DIR_ENGINE, "LLM_Models")

MODELS_LLM_DIR = get_models_llm_dir()  # Will be updated when settings are loaded

SD_DIR = os.path.join(DIR_ENGINE, "stable-diffusion-webui-reforge")
MODELS_SD_DIR = os.path.join(SD_DIR, "models", "Stable-diffusion")
AD_MODELS_DIR = os.path.join(SD_DIR, "models", "adetailer")
ADETAILER_DIR = os.path.join(SD_DIR, "extensions", "adetailer")
FILE_CHANNELS = os.path.join(DIR_CONFIGS, "channels.json")
FILE_GEN_CONFIG = os.path.join(DIR_CONFIGS, "generation_config.json")
FILE_PID = os.path.join(DIR_TEMP, "launcher.pid")
FILE_SD_CACHE = os.path.join(DIR_CONFIGS, "sd_compatibility_cache.json")

# SD_REPO and ADETAILER_REPO are now in config.py
MODEL_SD_URL = "https://civitai.com/api/download/models/2334591?type=Model&format=SafeTensor&size=full&fp=fp32"
MODEL_SD_FILENAME = "cyberrealisticPony_v141.safetensors"

AD_MODELS_URLS = {
    "face_yolov9c.pt": "https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov9c.pt",
    "hand_yolov9c.pt": "https://huggingface.co/Bingsu/adetailer/resolve/main/hand_yolov9c.pt"
}



COLORS = {
    'bg': '#1e1f22',  # Very dark background (darker than Discord)
    'surface': '#232428',  # Dark surface
    'surface_light': '#2b2d31',  # Lighter surface
    'surface_dark': '#18191c',  # Darkest surface
    'sidebar': '#1e1f22',  # Sidebar background
    'primary': '#5865f2',  # Discord blurple
    'primary_hover': '#4752c4',  # Discord blurple hover
    'primary_light': '#7289da',  # Discord blurple light
    'secondary': '#5865f2',  # Discord blurple
    'success': '#57f287',  # Discord green
    'danger': '#ed4245',  # Discord red
    'warning': '#fee75c',  # Discord yellow
    'text': '#dbdee1',  # Light text
    'text_secondary': '#b5bac1',  # Secondary text
    'text_muted': '#949ba4',  # Muted text
    'border': '#18191c',  # Border color
    'accent': '#5865f2',  # Accent color
    'card_bg': '#232428',  # Card background
    'card_bg_light': '#2b2d31',  # Lighter card
    'active': '#5865f2',  # Active state
    'hover': '#2b2d31',  # Hover state
    'glass': '#232428cc',  # Glassmorphism overlay
}

# Константы для логирования
LOG_SKIP_PATTERNS = (
    "warning:xformers", "warning:bitsandbytes", "no module named 'triton'",
    "modulenotfounderror: no module named 'triton'", "fatal: not a git repository",
    "note: redirects are currently not", "could not find the bitsandbytes cuda binary",
    "8-bit optimizers, 8-bit multiplication", "compiled without gpu support",
    "unable to install insightface automatically", "traceback (most recent call last):",
    "import triton", "^^^^^^^^^^^^^",
    # Прогресс-бары SD
    "%|", "it/s]", "it]",
    # Технические логи SD
    "[unload]", "[memory management]", "moving model(s) has taken",
    "target:", "free gpu:", "model require:", "previously loaded:",
    "inference require:", "remaining:", "all loaded to gpu",
    "cpu swap loaded", "gpu loaded", "current free memory is",
    "unload model", "done.",
    # Логи Ollama
    "time=", "level=info", "level=error", "source=", "msg=",
    "server config", "total blobs:", "total unused blobs removed:",
    "listening on", "discovering available gpus", "starting runner",
    "inference compute", "entering low vram mode",
    # HTTP логи
    "[gin]", "| post", "| get", "| put", "| delete",
    # Детальные логи SD
    "speed:", "preprocess,", "inference,", "postprocess per image",
    "stateDict keys:", "working with z of shape", "k-model created:",
    "storage_dtype", "computation_dtype", "model loaded in",
    "unload existing model:", "forge model load:",
    # Другие технические детали
    "hint:", "device:", "pytorch version:", "xformers version:",
    "set vram state to:", "cuda using stream:", "using xformers",
    "vae dtype preferences:", "controlnet preprocessor location:",
    "adetailer initialized", "controlnet ui callback registered",
    "model selected:", "using online loras", "startup time:",
    "prepare environment:", "launcher:", "import torch:", "initialize shared:",
    "other imports:", "load scripts:", "started server process",
    "waiting for application startup", "application startup complete",
    "uvicorn running on", "loading model:"
)

LOG_TAB_MAP = {
    "BOT": "Бот", "Bot": "Бот", "LLM": "LLM", "SD": "SD",
    "SYSTEM": "Бот", "SETTINGS": "Бот"
}

LOG_PREFIX_MAP = {"Бот": "🤖", "LLM": "🧠", "SD": "🎨"}

STATUS_COLOR_MAP = {
    "gray": COLORS['text_muted'],
    "orange": COLORS['warning'],
    "green": COLORS['success'],
    "red": COLORS['danger']
}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

try:
    from .ui_helpers import load_app_icon, show_error as show_error_ui
except (ImportError, ValueError):
    try:
        import sys
        import os
        launcher_dir = os.path.dirname(os.path.abspath(__file__))
        if launcher_dir not in sys.path:
            sys.path.insert(0, launcher_dir)
        from ui_helpers import load_app_icon, show_error as show_error_ui
    except ImportError:
        def load_app_icon(window):
            pass
        def show_error_ui(title, msg):
            try:
                ctypes.windll.user32.MessageBoxW(0, msg, title, 0x10)
            except:
                print(f"[ERROR] {title}: {msg}", flush=True)

class ModernLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Оптимизированная загрузка языка
        saved_lang = None
        try:
            if os.path.exists(FILE_ENV):
                with open(FILE_ENV, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('LANGUAGE='):
                            saved_lang = line.split('=', 1)[1].strip()
                            if saved_lang not in SUPPORTED_LANGUAGES:
                                saved_lang = None
                            break
        except (OSError, IOError):
            pass
        
        current_lang = init_i18n(saved_lang if saved_lang else None)
        
        # Сохраняем язык в фоне
        def save_language():
            try:
                from dotenv import set_key  # type: ignore
                set_key(FILE_ENV, "LANGUAGE", current_lang)
            except (ImportError, OSError):
                pass
        threading.Thread(target=save_language, daemon=True).start()
        self._detected_lang = current_lang
        
        self.title(t("ui.launcher.title"))
        self.geometry("1400x900")
        self.minsize(1200, 800)
        self.after(100, lambda: load_app_icon(self))
        self.log_queue = queue.Queue()
        self.consoles = {}
        self.entries = {} 
        self.selected_llm_model = tk.StringVar()
        self.current_topic = None
        self.current_frame = 0
        self.debug_mode = tk.BooleanVar(value=False)
        # Drag and drop для тем
        self.topic_dragging = False
        self.dragged_topic = None
        self.drag_start_y = 0
        self.current_language = current_lang
        self.animations_enabled = True
        
        self.status_indicators = {}
        self.service_buttons = {}
        self.service_status_labels = {}
        self.installer = Installer(log_callback=self.log)
        self.model_manager = ModelManager(log_callback=self.log)
        
        # Initialize analytics and updater
        try:
            self.analytics = get_analytics()
            self.updater = get_updater(log_callback=self.log)
            self.security = get_security()
        except:
            self.analytics = None
            self.updater = None
            self.security = None
        
        # Track session
        self.session_start = time.time()
        if self.analytics:
            self.analytics.track_session()
        
        # Bind hotkeys
        self.bind_hotkeys()
        
        def status_callback(name, status, color_key):
            color = STATUS_COLOR_MAP.get(color_key, COLORS['text_muted'])
            self.after(0, lambda: self._set_service_indicator(name, color))
            
            btn_text = "▶" if status in ["stopped", "error"] else "⏹"
            btn_color = COLORS['primary'] if status in ["stopped", "error"] else COLORS['danger']
            self.after(0, lambda: self._set_service_button(name, text=btn_text, fg_color=btn_color))
            
            status_text_map = {
                "stopped": t("ui.launcher.status.stopped"),
                "starting": t("ui.launcher.status.starting_short"),
                "running": t("ui.launcher.status.running"),
                "error": t("ui.launcher.status.error")
            }
            status_text = status_text_map.get(status, status)
            self.after(0, lambda: self._set_service_status_label(name, text=status_text, color=color))

        # Initialize ServiceManager immediately
        self._status_callback = status_callback
        self.service_manager = ServiceManager(
            log_callback=self.log,
            status_callback=status_callback,
            installer=self.installer,
            log_queue=self.log_queue
        )
        
        # Backward compatibility: expose procs for legacy code
        self.procs = self.service_manager.procs

        # Initialize
        try:
            self.init_filesystem()
        except Exception as e: 
            show_error(t("ui.launcher.error.title"), t("ui.launcher.error.message", error=str(e)))
            sys.exit(1)
        
        if self.check_running(): 
            self.show_lock_screen()
        else: 
            self.register_pid()
            self.build_ui()
            # Start monitoring after a small delay to avoid blocking UI
            self.after(100, self.start_monitor)
        
        # Window close handler (set here for reliability)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def init_filesystem(self):
        # Create only critical directories synchronously
        critical_dirs = [
            DATA_ROOT, 
            DIR_CONFIGS, 
            DIR_LOGS, 
            DIR_TEMP
        ]
        for d in critical_dirs:
            try:
                os.makedirs(d, exist_ok=True)
            except (OSError, PermissionError):
                pass  # Ignore errors when creating folders
        
        # Create remaining directories asynchronously
        def create_remaining_dirs():
            remaining_dirs = [
                DIR_ENGINE, 
                MODELS_LLM_DIR, 
                OLLAMA_DIR,
                OLLAMA_MODELS_DIR,
                OLLAMA_DATA_DIR,
                os.path.join(DATA_ROOT, "backups")
            ]
            for d in remaining_dirs:
                try:
                    os.makedirs(d, exist_ok=True)
                except (OSError, PermissionError):
                    pass
        
        threading.Thread(target=create_remaining_dirs, daemon=True).start()
        
        # Create files only if they don't exist
        if not os.path.exists(FILE_ENV):
            try:
                open(FILE_ENV, "w", encoding="utf-8").close()
            except (OSError, PermissionError):
                pass

        if not os.path.exists(FILE_GEN_CONFIG):
            try:
                with open(FILE_GEN_CONFIG, "w", encoding="utf-8") as f:
                    json.dump({"llm_temp": 0.7, "sd_steps": 30, "sd_cfg": 6.0}, f, indent=4)
            except (OSError, PermissionError, json.JSONDecodeError):
                pass
        
        # Create initial backup in background thread (deferred)
        self.after(2000, lambda: threading.Thread(target=self._create_backup, daemon=True).start())

    def check_running(self):
        """Quick check if another launcher instance is running"""
        if not os.path.exists(FILE_PID):
            return False
        
        try:
            with open(FILE_PID, 'r') as f:
                pid = int(f.read().strip())
            
            # Быстрая проверка без детального анализа процесса
            try:
                if psutil.pid_exists(pid): 
                    # Простая проверка без детального статуса для скорости
                    try:
                        proc = psutil.Process(pid)
                        if proc.is_running():
                            self.old_pid = pid
                            return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        try:
                            os.remove(FILE_PID)
                        except:
                            pass
                        return False
            except Exception:
                try:
                    os.remove(FILE_PID)
                except:
                    pass
                return False
        except (ValueError, IOError, OSError):
            try:
                os.remove(FILE_PID)
            except:
                pass
            return False
        
        return False

    def register_pid(self):
        try:
            with open(FILE_PID, 'w') as f:
                f.write(str(os.getpid()))
        except:
            pass

    def kill_old(self):
        try:
            psutil.Process(self.old_pid).kill()
        except:
            pass
        self.register_pid()
        self.build_ui()
    
    def bind_hotkeys(self):
        """Привязка горячих клавиш"""
        # Ctrl+S - сохранить настройки
        self.bind("<Control-s>", lambda e: self._auto_save_settings())
        self.bind("<Control-S>", lambda e: self._auto_save_settings())
        
        # Ctrl+1/2/3/4 - переключение вкладок
        self.bind("<Control-Key-1>", lambda e: self.show_page(0))
        self.bind("<Control-Key-2>", lambda e: self.show_page(1))
        self.bind("<Control-Key-3>", lambda e: self.show_page(2))
        self.bind("<Control-Key-4>", lambda e: self.show_page(3))
        
        # F5 - обновить список моделей
        self.bind("<F5>", lambda e: self.scan_llm_models() if hasattr(self, 'scan_llm_models') else None)
        
        # Ctrl+R - перезагрузить интерфейс
        self.bind("<Control-r>", lambda e: self.build_ui())
        self.bind("<Control-R>", lambda e: self.build_ui())
        
        # Escape - закрыть диалоги (обработка на уровне окна)
        self.bind("<Escape>", lambda e: self.focus_set())
    
    def show_lock_screen(self):
        for w in self.winfo_children():
            w.destroy()
        
        frame = ctk.CTkFrame(self, fg_color=COLORS['card_bg'])
        frame.pack(fill="both", expand=True)
        
        ctk.CTkLabel(
            frame,
            text="⚠️ " + t("ui.launcher.status.already_running"),
            font=("Segoe UI", 28, "bold"),
            text_color=COLORS['text']
        ).pack(pady=50)
        
        ctk.CTkButton(
            frame,
            text=t("ui.launcher.button.kill_and_restart"),
            command=self.kill_old,
            fg_color=COLORS['danger'],
            hover_color="#dc2626",
            font=("Segoe UI", 16),
            width=300,
            height=50
        ).pack(pady=20)

    def build_ui(self):
        for w in self.winfo_children():
            w.destroy()
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left sidebar
        self.create_sidebar()
        self.content_frame = ctk.CTkFrame(self, fg_color=COLORS['bg'], corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Lazy loading: создаем страницы только при первом показе
        self.pages = [None, None, None, None]
        self.pages_created = [False, False, False, False]
        
        # Создаем только первую страницу (консоль) сразу
        self.pages[0] = self.create_console_page()
        self.pages_created[0] = True
        
        self.show_page(0)
        
        # Запускаем циклы с минимальной задержкой для быстрого старта
        self.after(50, self.console_loop)
        self.after(500, self.service_status_loop)
        
        # Добавляем одно начальное логирование
        self.after(200, lambda: self.log(t("ui.launcher.log.startup", default="✅ [SYSTEM] Система запущена"), "BOT"))
    
    def on_language_change(self, value):
        """Handle language change"""
        lang_code = value.split(' - ')[0] if ' - ' in value else value
        if lang_code in SUPPORTED_LANGUAGES and lang_code != self.current_language:
            # Set new language
            set_language(lang_code)
            self.current_language = lang_code
            set_key(FILE_ENV, "LANGUAGE", lang_code)
            # Log language change
            self.log(t("ui.launcher.log.language_changed", default="🌐 [SYSTEM] Language changed to: {lang}", lang=LANGUAGE_NAMES.get(lang_code, lang_code)), "SYSTEM")
            # Rebuild UI with new language
            self.title(t("ui.launcher.title"))
            self.build_ui()
    
    def create_glass_card(self, parent, **kwargs):
        """Создает карточку с glassmorphism эффектом"""
        default_kwargs = {
            'fg_color': COLORS['card_bg'],
            'corner_radius': 16,
            'border_width': 1,
            'border_color': COLORS['border']
        }
        default_kwargs.update(kwargs)
        card = ctk.CTkFrame(parent, **default_kwargs)
        return card
    
    def create_sidebar(self):
        """Создает боковую панель с glassmorphism дизайном"""
        sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=COLORS['sidebar'])
        sidebar.grid(row=0, column=0, sticky="nsew", padx=0)
        sidebar.grid_propagate(False)

        # Logo section
        logo_card = self.create_glass_card(sidebar, fg_color=COLORS['surface'])
        logo_card.pack(fill="x", padx=16, pady=(20, 16))
        
        logo_content = ctk.CTkFrame(logo_card, fg_color="transparent")
        logo_content.pack(fill="x", padx=16, pady=16)
        
        logo_icon = ctk.CTkFrame(logo_content, fg_color=COLORS['primary'], width=48, height=48, corner_radius=24)
        logo_icon.pack(side="left", padx=(0, 12))
        logo_icon.pack_propagate(False)
        ctk.CTkLabel(
            logo_icon,
            text="▼",
            font=("Segoe UI", 24),
            text_color="white"
        ).pack(expand=True)
        
        title_frame = ctk.CTkFrame(logo_content, fg_color="transparent")
        title_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            title_frame,
            text="Launcher",
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['text']
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame,
            text="Control Panel",
            font=("Segoe UI", 11),
            text_color=COLORS['text_muted']
        ).pack(anchor="w")
        
        # Navigation
        nav_card = self.create_glass_card(sidebar, fg_color=COLORS['surface'])
        nav_card.pack(fill="x", padx=16, pady=(0, 16))
        
        nav_content = ctk.CTkFrame(nav_card, fg_color="transparent")
        nav_content.pack(fill="x", padx=12, pady=12)
        
        self.nav_buttons = []
        nav_items = [
            (t("ui.launcher.console", default="Консоль"), "💻", 0),
            (t("ui.launcher.settings", default="Настройки"), "⚙️", 1),
            (t("ui.launcher.channels", default="Каналы"), "📡", 2),
            (t("ui.launcher.analytics", default="Аналитика"), "📈", 3)
        ]

        for i, (text, icon, idx) in enumerate(nav_items):
            btn = ctk.CTkButton(
                nav_content,
                text=f"  {icon}  {text}",
                command=lambda i=idx: self.show_page(i),
                fg_color="transparent",
                anchor="w",
                height=50,
                font=("Segoe UI", 14),
                corner_radius=12,
                hover_color=COLORS['hover'],
                text_color=COLORS['text_secondary']
            )
            btn.pack(fill="x", pady=4)
            self.nav_buttons.append(btn)
            
            # Add Windows-style hover animations for buttons only
            if self.animations_enabled:
                try:
                    button_hover_effect(btn, hover_color=COLORS['hover'], normal_color="transparent", duration=100)
                except:
                    pass
        
        # Сохраняем текущую активную страницу для правильного выделения
        self.current_page_index = 0
        
        # Highlight first button
        if len(self.nav_buttons) > 0:
            self.nav_buttons[0].configure(
                fg_color=COLORS['primary'],
                text_color="white"
            )
        
        # Services status
        services_card = self.create_glass_card(sidebar, fg_color=COLORS['surface'])
        services_card.pack(fill="x", padx=16, pady=(0, 16), side="bottom")
        
        ctk.CTkLabel(
            services_card,
            text=t("ui.launcher.services"),
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS['text']
        ).pack(anchor="w", padx=16, pady=(16, 12))
        
        services_content = ctk.CTkFrame(services_card, fg_color="transparent")
        services_content.pack(fill="x", padx=12, pady=(0, 12))
        
        for key, label in [("bot", t("ui.launcher.service.bot")), ("llm", t("ui.launcher.service.llm")), ("sd", t("ui.launcher.service.sd"))]:
            self.create_service_indicator(services_content, key, label)
        
        # System monitor
        monitor_card = self.create_glass_card(sidebar, fg_color=COLORS['surface'])
        monitor_card.pack(fill="x", padx=16, pady=(0, 16), side="bottom")
        
        monitor_content = ctk.CTkFrame(monitor_card, fg_color="transparent")
        monitor_content.pack(fill="x", padx=16, pady=16)
        
        self.lbl_net = ctk.CTkLabel(
            monitor_content,
            text=t("ui.launcher.monitoring.network", speed="0"),
            font=("Consolas", 13),
            text_color=COLORS['primary_light']
        )
        self.lbl_net.pack(anchor="w", pady=(0, 8))
        
        self.lbl_disk = ctk.CTkLabel(
            monitor_content,
            text=t("ui.launcher.monitoring.disk", speed="0"),
            font=("Consolas", 13),
            text_color=COLORS['success']
        )
        self.lbl_disk.pack(anchor="w")
    
    # Drag and drop для тем
    def _on_topic_drag_start(self, event, topic_name):
        """Начало перетаскивания темы"""
        self.dragged_topic = topic_name
        self.drag_start_y = event.y_root
        self.drag_start_x = event.x_root
        self.topic_dragging = False
        if not hasattr(event.widget, 'drag_started'):
            event.widget.drag_started = False
    
    def _on_topic_drag(self, event, topic_name):
        """Перетаскивание темы"""
        if self.dragged_topic != topic_name:
            return
        
        # Проверяем, началось ли перетаскивание (движение больше 5 пикселей)
        if not hasattr(event.widget, 'drag_started'):
            event.widget.drag_started = False
        
        delta_y = abs(event.y_root - self.drag_start_y)
        
        if not event.widget.drag_started and delta_y > 5:
            # Начинаем перетаскивание
            event.widget.drag_started = True
            self.topic_dragging = True
            # Визуальная обратная связь
            event.widget.configure(fg_color=COLORS['primary_light'])
            # Отменяем команду выбора темы
            event.widget.configure(command=lambda: None)
        
        if not self.topic_dragging:
            return
    
    def _on_topic_drag_stop(self, event, topic_name):
        """Окончание перетаскивания темы"""
        # Восстанавливаем команду кнопки
        if hasattr(event.widget, 'drag_started') and event.widget.drag_started:
            event.widget.configure(command=lambda tp=topic_name: self.select_topic(tp))
        
        if not self.topic_dragging or self.dragged_topic != topic_name:
            # Просто клик - выбираем тему
            if not (hasattr(event.widget, 'drag_started') and event.widget.drag_started):
                self.select_topic(topic_name)
            self.dragged_topic = None
            return
        
        self.topic_dragging = False
        
        # Находим новую позицию
        widget = event.widget.master
        if isinstance(widget, ctk.CTkFrame):
            try:
                if os.path.exists(FILE_CHANNELS):
                    with open(FILE_CHANNELS, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    data = {}
            except:
                data = {}
            
            topics = list(data.keys())
            if self.dragged_topic not in topics:
                self.dragged_topic = None
                return
            
            # Определяем новую позицию на основе Y координаты
            parent = widget.master
            if hasattr(parent, 'winfo_children'):
                children = [w for w in parent.winfo_children() if isinstance(w, ctk.CTkFrame)]
                
                try:
                    current_index = children.index(widget)
                    y = event.y_root
                    new_index = current_index
                    
                    # Находим новую позицию на основе Y координаты
                    for i, child in enumerate(children):
                        if child == widget:
                            continue
                        try:
                            child_y = child.winfo_rooty()
                            child_height = child.winfo_height()
                            child_center = child_y + child_height // 2
                            
                            if y < child_center and i < current_index:
                                new_index = i
                                break
                            elif y > child_center and i > current_index:
                                new_index = i + 1
                        except:
                            pass
                    
                    # Переставляем тему
                    topics.remove(self.dragged_topic)
                    if new_index > len(topics):
                        new_index = len(topics)
                    topics.insert(new_index, self.dragged_topic)
                    
                    # Сохраняем новый порядок
                    new_data = {}
                    for topic in topics:
                        if topic in data:
                            new_data[topic] = data[topic]
                    
                    with open(FILE_CHANNELS, 'w', encoding='utf-8') as f:
                        json.dump(new_data, f, indent=4, ensure_ascii=False)
                    
                    # Обновляем список тем
                    self.refresh_topics()
                except (ValueError, IndexError):
                    pass
        
        self.dragged_topic = None
    
    def create_service_indicator(self, parent, key, label):
        """Создает индикатор сервиса с glassmorphism стилем"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=4)
        
        dot = ctk.CTkLabel(
            frame,
            text="●",
            font=("Arial", 16),
            text_color=COLORS['text_muted'],
            width=24
        )
        dot.pack(side="left")
        self.status_indicators[key] = dot
        
        ctk.CTkLabel(
            frame,
            text=label,
            font=("Segoe UI", 13),
            text_color=COLORS['text'],
            anchor="w"
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))
        
        btn = ctk.CTkButton(
            frame,
            text="▶",
            width=36,
            height=28,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            command=lambda k=key: self.toggle_service(k),
            font=("Segoe UI", 11),
            corner_radius=8
        )
        btn.pack(side="right")
        self.service_buttons[key] = btn
        
        # Add hover animation
        if self.animations_enabled:
            try:
                button_hover_effect(btn, hover_color=COLORS['primary_hover'], normal_color=COLORS['primary'], duration=150)
            except:
                pass

    def show_page(self, idx):
        # Проверяем, что индекс валидный
        if idx < 0 or idx >= len(self.pages) or not hasattr(self, 'nav_buttons'):
            return
        
        self.current_frame = idx
        self.current_page_index = idx
        
        # Lazy loading: создаем страницу только при первом показе
        if not self.pages_created[idx]:
            try:
                if idx == 1:
                    # Создаем страницу настроек в фоне для плавности
                    self.pages[1] = ctk.CTkFrame(self.content_frame, fg_color=COLORS['bg'])
                    loading_label = ctk.CTkLabel(
                        self.pages[1],
                        text=t("ui.launcher.loading", default="Загрузка..."),
                        font=("Segoe UI", 16),
                        text_color=COLORS['text_muted']
                    )
                    loading_label.pack(expand=True)
                    self.pages[1].grid(row=0, column=0, sticky="nsew")
                    self.pages_created[idx] = True
                    
                    # Создаем реальную страницу в фоне
                    def create_settings_async():
                        try:
                            settings_page = self.create_settings_page()
                            # Заменяем placeholder на реальную страницу
                            self.pages[1].destroy()
                            self.pages[1] = settings_page
                            self.pages[1].grid(row=0, column=0, sticky="nsew")
                        except Exception as e:
                            self.log(f"❌ [SYSTEM] Ошибка создания страницы настроек: {e}", "SYSTEM")
                    
                    # Запускаем создание в отдельном потоке
                    threading.Thread(target=create_settings_async, daemon=True).start()
                elif idx == 2:
                    self.pages[2] = self.create_channels_page()
                    self.pages_created[idx] = True
                elif idx == 3:
                    self.pages[3] = self.create_analytics_page()
                    self.pages_created[idx] = True
            except Exception as e:
                self.log(f"❌ [SYSTEM] Ошибка создания страницы {idx}: {e}", "SYSTEM")
                # Create error page
                error_frame = ctk.CTkFrame(self.content_frame, fg_color=COLORS['bg'])
                error_label = ctk.CTkLabel(
                    error_frame,
                    text=f"Error loading page: {str(e)}",
                    text_color=COLORS['danger'],
                    font=("Segoe UI", 16)
                )
                error_label.pack(expand=True)
                self.pages[idx] = error_frame
                self.pages_created[idx] = True
        
        # Simple page switching without animations
        for i, page in enumerate(self.pages):
            if page is not None:
                if i == idx:
                    page.grid(row=0, column=0, sticky="nsew")
                    page.lift()
                    page.update()
                else:
                    page.grid_forget()
        
        # Обновляем выделение кнопок навигации
        if hasattr(self, 'nav_buttons') and len(self.nav_buttons) > idx:
            for i, btn in enumerate(self.nav_buttons):
                if i == idx:
                    # Активная кнопка
                    if self.animations_enabled:
                        try:
                            old_color = btn.cget('fg_color')
                            old_text_color = btn.cget('text_color')
                            smooth_color_transition(btn, 'fg_color', old_color, COLORS['primary'], duration=150, steps=8)
                            smooth_color_transition(btn, 'text_color', old_text_color, "white", duration=150, steps=8)
                        except:
                            btn.configure(
                                fg_color=COLORS['primary'],
                                text_color="white",
                                font=("Segoe UI", 14, "bold")
                            )
                    else:
                        btn.configure(
                            fg_color=COLORS['primary'],
                            text_color="white",
                            font=("Segoe UI", 14, "bold")
                        )
                else:
                    # Неактивная кнопка
                    if self.animations_enabled:
                        try:
                            old_color = btn.cget('fg_color')
                            old_text_color = btn.cget('text_color')
                            smooth_color_transition(btn, 'fg_color', old_color, "transparent", duration=150, steps=8)
                            smooth_color_transition(btn, 'text_color', old_text_color, COLORS['text_secondary'], duration=150, steps=8)
                        except:
                            btn.configure(
                                fg_color="transparent",
                                text_color=COLORS['text_secondary'],
                                font=("Segoe UI", 14)
                            )
                    else:
                        btn.configure(
                            fg_color="transparent",
                            text_color=COLORS['text_secondary'],
                            font=("Segoe UI", 14)
                        )

    def create_console_page(self):
        """Создает страницу консоли с glassmorphism дизайном и статус-карточками"""
        frame = ctk.CTkFrame(self.content_frame, fg_color=COLORS['bg'])
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)
        
        # Header
        header = ctk.CTkFrame(frame, fg_color="transparent", height=80)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 16))
        header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            header,
            text=t("ui.launcher.console.title", default="Консоль"),
            font=("Segoe UI", 32, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, sticky="w")
        
        ctk.CTkButton(
            header,
            text=f"🗑️ {t('ui.launcher.logs.clear', default='Очистить')}",
            width=130,
            height=36,
            fg_color=COLORS['surface'],
            hover_color=COLORS['danger'],
            text_color=COLORS['text'],
            border_width=1,
            border_color=COLORS['border'],
            command=self.clear_console,
            font=("Segoe UI", 12),
            corner_radius=10
        ).grid(row=0, column=1, sticky="e")
        
        # Status cards row
        status_container = ctk.CTkFrame(frame, fg_color="transparent")
        status_container.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 16))
        status_container.grid_columnconfigure((0, 1, 2), weight=1, uniform="status")
        
        status_cards_data = [
            ("bot", "🤖", t("ui.launcher.service.bot"), COLORS['primary']),
            ("llm", "🧠", t("ui.launcher.service.llm"), COLORS['secondary']),
            ("sd", "🎨", t("ui.launcher.service.sd"), COLORS['success'])
        ]
        
        self.status_cards = {}
        for idx, (key, icon, title, color) in enumerate(status_cards_data):
            card = self.create_status_card(status_container, key, icon, title, color)
            card.grid(row=0, column=idx, sticky="ew", padx=8)
            self.status_cards[key] = card
        
        # Console area with tabs
        console_card = ctk.CTkFrame(frame, fg_color=COLORS['surface'], corner_radius=16)
        console_card.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 24))
        console_card.grid_columnconfigure(0, weight=1)
        console_card.grid_rowconfigure(1, weight=1)
        
        # Tab buttons
        tab_frame = ctk.CTkFrame(console_card, fg_color="transparent", height=50)
        tab_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        
        # Вкладки: Все, Бот, LLM, SD
        self.console_tabs = ["Все", "Бот", "LLM", "SD"]
        self.current_console_tab = "Все"
        self.console_tab_buttons = {}
        
        tab_configs = [
            ("Все", "📋", COLORS['text_secondary']),
            ("Бот", "🤖", COLORS['primary']),
            ("LLM", "🧠", COLORS['secondary']),
            ("SD", "🎨", COLORS['success'])
        ]
        
        for idx, (name, icon, color) in enumerate(tab_configs):
            is_active = name == self.current_console_tab
            btn = ctk.CTkButton(
                tab_frame,
                text=f"{icon} {name}",
                width=80,
                height=32,
                fg_color=COLORS['surface_light'] if is_active else "transparent",
                hover_color=COLORS['surface_light'],
                text_color=COLORS['text'] if is_active else COLORS['text_muted'],
                font=("Segoe UI", 11, "bold") if is_active else ("Segoe UI", 11),
                corner_radius=8,
                command=lambda n=name: self._switch_console_tab(n)
            )
            btn.pack(side="left", padx=(0, 4))
            self.console_tab_buttons[name] = btn
        
        # Console container
        console_container = ctk.CTkFrame(console_card, fg_color="transparent")
        console_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        console_container.grid_columnconfigure(0, weight=1)
        console_container.grid_rowconfigure(0, weight=1)
        
        # Create console frames
        self.console_frames = {}
        for tab_name in self.console_tabs:
            frame_inner = ctk.CTkFrame(console_container, fg_color="transparent")
            frame_inner.grid(row=0, column=0, sticky="nsew")
            frame_inner.grid_columnconfigure(0, weight=1)
            frame_inner.grid_rowconfigure(0, weight=1)
            
            console = ctk.CTkTextbox(
                frame_inner,
                font=("Consolas", 12),
                fg_color=COLORS['bg'],
                text_color=COLORS['text'],
                corner_radius=10,
                wrap="word",
                border_width=1,
                border_color=COLORS['border']
            )
            console.grid(row=0, column=0, sticky="nsew")
            console.configure(state="normal")
            self.setup_console_context_menu(console)
            self.consoles[tab_name] = console
            self.console_frames[tab_name] = frame_inner
            
            if tab_name != self.current_console_tab:
                frame_inner.grid_remove()
        
        return frame
    
    def _switch_console_tab(self, tab_name):
        """Переключает вкладку консоли"""
        if tab_name == self.current_console_tab:
            return
        
        # Update buttons
        for name, btn in self.console_tab_buttons.items():
            if name == tab_name:
                btn.configure(fg_color=COLORS['surface_light'], text_color=COLORS['text'], font=("Segoe UI", 11, "bold"))
            else:
                btn.configure(fg_color="transparent", text_color=COLORS['text_muted'], font=("Segoe UI", 11))
        
        # Switch frames
        self.console_frames[self.current_console_tab].grid_remove()
        self.console_frames[tab_name].grid()
        self.current_console_tab = tab_name
    
    def create_status_card(self, parent, key, icon, title, color):
        """Создает карточку статуса для dashboard"""
        card = self.create_glass_card(parent, fg_color=COLORS['surface'])
        card.grid_columnconfigure(0, weight=1)
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=16, pady=16)
        
        # Icon
        icon_frame = ctk.CTkFrame(content, fg_color=color, width=48, height=48, corner_radius=24)
        icon_frame.pack(anchor="w", pady=(0, 12))
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(
            icon_frame,
            text=icon,
            font=("Segoe UI", 24),
            text_color="white"
        ).pack(expand=True)
        
        # Title
        ctk.CTkLabel(
            content,
            text=title,
            font=("Segoe UI", 13),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(0, 4))
        
        # Status
        status_label = ctk.CTkLabel(
            content,
            text=t("ui.launcher.status.stopped", default="Stopped"),
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS['text_muted']
        )
        status_label.pack(anchor="w")
        
        # Store reference
        if not hasattr(self, 'status_card_labels'):
            self.status_card_labels = {}
        self.status_card_labels[key] = status_label
        
        return card
    
    def create_services_page(self):
        frame = ctk.CTkFrame(self.content_frame, fg_color=COLORS['bg'])
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(frame, fg_color="transparent", height=70)
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 25))
        header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            header,
            text=t("ui.launcher.services.title"),
            font=("Segoe UI", 32, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, sticky="w")
        summary_container = ctk.CTkFrame(frame, fg_color="transparent")
        summary_container.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 25))
        summary_container.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="summary")
        
        services = [
            ("bot", t("ui.launcher.service.telegram_bot"), "🤖"),
            ("llm", t("ui.launcher.service.llm_server"), "🧠"),
            ("sd", t("ui.launcher.service.stable_diffusion"), "🎨"),
            ("system", "System", "⚙️")
        ]
        
        for idx, (key, title, icon) in enumerate(services):
            card = self.create_summary_card(summary_container, key, title, icon)
            card.grid(row=0, column=idx, sticky="ew", padx=8)
        
        # Services detail cards (3 cards in row)
        services_container = ctk.CTkFrame(frame, fg_color="transparent")
        services_container.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 30))
        services_container.grid_columnconfigure((0, 1, 2), weight=1, uniform="service")
        
        detail_services = [
            ("bot", t("ui.launcher.service.telegram_bot"), "🤖", t("ui.launcher.service.description.bot")),
            ("llm", t("ui.launcher.service.llm_server"), "🧠", t("ui.launcher.service.description.llm")),
            ("sd", t("ui.launcher.service.stable_diffusion"), "🎨", t("ui.launcher.service.description.sd"))
        ]
        
        for idx, (key, title, icon, desc) in enumerate(detail_services):
            card = self.create_service_card(services_container, key, title, icon, desc)
            card.grid(row=0, column=idx, sticky="ew", padx=10)
        
        return frame
    
    def create_summary_card(self, parent, key, title, icon):
        """Create dashboard-style summary card (like the 4 cards in top row)"""
        card = ctk.CTkFrame(parent, fg_color=COLORS['card_bg'], corner_radius=12, height=140)
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 13),
            text_color=COLORS['text_secondary'],
            anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        value_label = ctk.CTkLabel(
            card,
            text="—",
            font=("Segoe UI", 32, "bold"),
            text_color=COLORS['text'],
            anchor="w"
        )
        value_label.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))
        status_frame = ctk.CTkFrame(card, fg_color="transparent")
        status_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        dot = ctk.CTkLabel(
            status_frame,
            text="●",
            font=("Segoe UI", 12),
            text_color=COLORS['text_muted']
        )
        dot.pack(side="left", padx=(0, 6))
        
        status_text = ctk.CTkLabel(
            status_frame,
            text=t("ui.launcher.status.stopped"),
            font=("Segoe UI", 12),
            text_color=COLORS['text_muted']
        )
        status_text.pack(side="left")
        
        # Store references for updates
        if not hasattr(self, 'summary_cards'):
            self.summary_cards = {}
        self.summary_cards[key] = {
            'value': value_label,
            'status': status_text,
            'dot': dot
        }
        
        return card
    
    def create_service_card(self, parent, key, title, icon, desc):
        """Create detailed service card (Dashboard style)"""
        card = ctk.CTkFrame(parent, fg_color=COLORS['card_bg'], corner_radius=12)
        card.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 12))
        
        ctk.CTkLabel(
            header,
            text=icon,
            font=("Segoe UI", 36)
        ).pack(side="left", padx=(0, 12))
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(
            title_frame,
            text=title,
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['text'],
            anchor="w"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_frame,
            text=desc,
            font=("Segoe UI", 12),
            text_color=COLORS['text_secondary'],
            anchor="w"
        ).pack(anchor="w")
        status_frame = ctk.CTkFrame(card, fg_color="transparent")
        status_frame.pack(fill="x", padx=20, pady=12)
        
        status_label = ctk.CTkLabel(
            status_frame,
            text=t("ui.launcher.status.stopped"),
            font=("Segoe UI", 13),
            text_color=COLORS['text_muted']
        )
        status_label.pack(side="left")
        self.status_labels = getattr(self, 'status_labels', {})
        self.status_labels[key] = status_label
        
        # Создаем кнопку и сохраняем в словарь для обновления
        service_btn = ctk.CTkButton(
            card,
            text=t("ui.launcher.button.start"),
            command=lambda k=key: self.toggle_service(k),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            font=("Segoe UI", 14, "bold"),
            height=45,
            corner_radius=8
        )
        service_btn.pack(fill="x", padx=20, pady=(0, 20))
        
        # Сохраняем кнопку в словарь для обновления
        self.service_buttons = getattr(self, 'service_buttons', {})
        self.service_buttons[key] = service_btn
        
        return card
    
    def create_settings_page(self):
        """Создает страницу настроек"""
        # Инициализируем словари для вкладок, если еще не инициализированы
        if not hasattr(self, 'settings_tab_frames'):
            self.settings_tab_frames = {}
        if not hasattr(self, 'settings_tab_buttons'):
            self.settings_tab_buttons = []
        
        # Settings are loaded directly in tab creation methods
        
        frame = ctk.CTkFrame(self.content_frame, fg_color=COLORS['bg'])
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(frame, fg_color="transparent", height=70)
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 25))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)
        
        ctk.CTkLabel(
            header,
            text=t("ui.launcher.settings"),
            font=("Segoe UI", 32, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, sticky="w")
        
        # Right side: Save indicator + Language selector
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="e")
        
        # Save indicator (animated)
        self.save_indicator = ctk.CTkLabel(
            right_frame,
            text="",
            font=("Segoe UI", 12),
            text_color=COLORS['success'],
            width=120
        )
        self.save_indicator.pack(side="left", padx=(0, 16))
        
        # Language selector with flags
        lang_flags = {"ru": "🇷🇺", "en": "🇬🇧"}
        lang_values = [f"{lang_flags.get(code, '🌐')} {LANGUAGE_NAMES[code]}" for code in SUPPORTED_LANGUAGES]
        current_lang_display = f"{lang_flags.get(self.current_language, '🌐')} {LANGUAGE_NAMES.get(self.current_language, self.current_language)}"
        
        self.language_var = tk.StringVar(value=current_lang_display)
        lang_menu = ctk.CTkOptionMenu(
            right_frame,
            values=lang_values,
            variable=self.language_var,
            command=self.on_language_change,
            font=("Segoe UI", 13),
            width=150,
            height=36,
            fg_color=COLORS['surface_light'],
            button_color=COLORS['primary'],
            button_hover_color=COLORS['primary_hover'],
            corner_radius=8
        )
        lang_menu.pack(side="left")

        # Settings tabs container
        tabs_container = ctk.CTkFrame(frame, fg_color=COLORS['surface'], corner_radius=8)
        tabs_container.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        tabs_container.grid_columnconfigure(0, weight=1)
        tabs_container.grid_rowconfigure(1, weight=1)
        
        # Tab buttons row
        tab_buttons_frame = ctk.CTkFrame(tabs_container, fg_color="transparent")
        tab_buttons_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        tab_buttons_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Content area
        content_area = ctk.CTkFrame(tabs_container, fg_color=COLORS['bg'], corner_radius=8)
        content_area.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        content_area.grid_columnconfigure(0, weight=1)
        content_area.grid_rowconfigure(0, weight=1)
        
        # Create tab frames
        self.settings_tab_frames = {}
        self.settings_tab_buttons = []
        
        tab_configs = [
            ("general", "⚙️ " + t("ui.launcher.settings.general"), self._create_main_settings_tab),
            ("text", "📝 " + t("ui.launcher.settings.text"), self._create_text_settings_tab),
            ("image", "🎨 " + t("ui.launcher.settings.images"), self._create_image_settings_tab)
        ]
        
        for idx, (key, label, create_func) in enumerate(tab_configs):
            # Create button
            btn = ctk.CTkButton(
                tab_buttons_frame,
                text=label,
                command=lambda k=key: self._switch_settings_tab(k),
                fg_color=COLORS['primary'] if idx == 0 else COLORS['surface_light'],
                hover_color=COLORS['primary_hover'] if idx == 0 else COLORS['surface'],
                text_color="white" if idx == 0 else COLORS['text_secondary'],
                font=("Segoe UI", 13, "bold" if idx == 0 else "normal"),
                corner_radius=8,
                height=40
            )
            btn.grid(row=0, column=idx, sticky="ew", padx=4, pady=8)
            self.settings_tab_buttons.append((key, btn))
            
            # Create content frame
            tab_frame = ctk.CTkFrame(content_area, fg_color=COLORS['bg'])
            tab_frame.grid(row=0, column=0, sticky="nsew")
            tab_frame.grid_columnconfigure(0, weight=1)
            tab_frame.grid_rowconfigure(0, weight=1)
            
            # Create content
            try:
                create_func(tab_frame)
            except Exception as e:
                self.log(f"❌ [SETTINGS] Ошибка создания вкладки {key}: {e}", "SYSTEM")
                # Create error label
                error_label = ctk.CTkLabel(
                    tab_frame,
                    text=t("ui.launcher.error.tab_load_failed", default="Ошибка загрузки вкладки"),
                    text_color=COLORS['danger']
                )
                error_label.pack(expand=True)
            
            # Hide all except first
            if idx > 0:
                tab_frame.grid_remove()
            
            self.settings_tab_frames[key] = tab_frame
        
        # Set first tab as active
        self.current_settings_tab = "general"
        
        return frame
    
    def _switch_settings_tab(self, tab_key):
        """Переключает вкладку настроек"""
        if not hasattr(self, 'settings_tab_frames') or not self.settings_tab_frames:
            return
        if tab_key not in self.settings_tab_frames:
            return
        
        # Hide all tabs
        for key, tab_frame in self.settings_tab_frames.items():
            tab_frame.grid_remove()
        
        # Show selected tab
        self.settings_tab_frames[tab_key].grid()
        
        # Update button styles
        for key, btn in self.settings_tab_buttons:
            if key == tab_key:
                btn.configure(
                    fg_color=COLORS['primary'],
                    hover_color=COLORS['primary_hover'],
                    text_color="white",
                    font=("Segoe UI", 13, "bold")
                )
            else:
                btn.configure(
                    fg_color=COLORS['surface_light'],
                    hover_color=COLORS['surface'],
                    text_color=COLORS['text_secondary'],
                    font=("Segoe UI", 13, "normal")
                )
        
        self.current_settings_tab = tab_key
    
    def _create_main_settings_tab(self, parent):
        """Создает вкладку основных настроек"""
        scroll = ctk.CTkScrollableFrame(parent, fg_color=COLORS['bg'])
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        scroll.grid_columnconfigure(0, weight=1)
        
        # Telegram Bot settings
        bot_card = self.create_setting_card(scroll, t("ui.launcher.service.telegram_bot"), [
            ("BOT_TOKEN", t("ui.launcher.settings.bot_token"), t("ui.launcher.settings.bot_token.placeholder", default="Bot token from @BotFather")),
            ("TARGET_CHANNEL_ID", t("ui.launcher.settings.target_channel"), t("ui.launcher.settings.target_channel.placeholder", default="Target channel ID"))
        ])
        bot_card.pack(fill="x", pady=(0, 15))
        
        # Debug режим
        debug_card = ctk.CTkFrame(scroll, fg_color=COLORS['card_bg'], corner_radius=12)
        debug_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            debug_card,
            text=t("ui.launcher.settings.debug", default="Debug"),
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 15))
        
        debug_frame = ctk.CTkFrame(debug_card, fg_color="transparent")
        debug_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            debug_frame,
            text=t("ui.launcher.settings.debug_mode", default="Debug mode"),
            font=("Segoe UI", 13),
            text_color=COLORS['text_secondary']
        ).pack(side="left", padx=(0, 10))
        
        debug_switch = ctk.CTkSwitch(
            debug_frame,
            text=t("ui.launcher.settings.show_debug", default="Show debug messages"),
            variable=self.debug_mode,
            font=("Segoe UI", 13),
            onvalue=True,
            offvalue=False
        )
        debug_switch.pack(side="left")
        
        # Загружаем значение из настроек
        try:
            debug_value = get_key(FILE_ENV, "DEBUG_MODE")
            if debug_value and debug_value.lower() in ("true", "1", "yes"):
                self.debug_mode.set(True)
        except:
            pass
    
    def _create_text_settings_tab(self, parent):
        """Создает компактную вкладку настроек генерации текста"""
        scroll = ctk.CTkScrollableFrame(parent, fg_color=COLORS['bg'])
        scroll.pack(fill="both", expand=True, padx=16, pady=16)
        scroll.grid_columnconfigure(0, weight=1)
        
        gen_config = {}
        if os.path.exists(FILE_GEN_CONFIG):
            try:
                with open(FILE_GEN_CONFIG, 'r', encoding='utf-8') as f:
                    gen_config = json.load(f)
            except:
                pass
        
        # LLM Generation Settings - Compact
        llm_gen_card = ctk.CTkFrame(scroll, fg_color=COLORS['card_bg'], corner_radius=12)
        llm_gen_card.pack(fill="x", pady=(0, 12))
        llm_gen_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            llm_gen_card,
            text=t("ui.launcher.settings.text_generation", default="Генерация текста"),
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(12, 10))
        
        # Temperature
        ctk.CTkLabel(
            llm_gen_card,
            text=t("ui.launcher.settings.llm_temp", default="Температура"),
            font=("Segoe UI", 12),
            text_color=COLORS['text_secondary']
        ).grid(row=1, column=0, sticky="w", padx=15, pady=6)
        
        temp_var = tk.DoubleVar(value=float(gen_config.get("llm_temp", 0.7)))
        temp_slider = ctk.CTkSlider(
            llm_gen_card,
            from_=0.0,
            to=2.0,
            number_of_steps=200,
            variable=temp_var,
            width=250
        )
        temp_slider.grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        
        temp_label = ctk.CTkLabel(
            llm_gen_card,
            textvariable=temp_var,
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS['text'],
            width=50
        )
        temp_label.grid(row=1, column=2, padx=(0, 15), pady=6)
        self.llm_temp_var = temp_var
        temp_var.trace_add("write", lambda *args: self._save_generation_config())
        
        # Context Window
        ctk.CTkLabel(
            llm_gen_card,
            text=t("ui.launcher.settings.llm_ctx", default="Контекст"),
            font=("Segoe UI", 12),
            text_color=COLORS['text_secondary']
        ).grid(row=2, column=0, sticky="w", padx=15, pady=6)
        
        ctx_var = tk.IntVar(value=int(gen_config.get("llm_ctx", 4096)))
        ctx_entry = ctk.CTkEntry(
            llm_gen_card,
            textvariable=ctx_var,
            font=("Segoe UI", 12),
            width=120
        )
        ctx_entry.grid(row=2, column=1, sticky="w", padx=8, pady=6)
        self.llm_ctx_var = ctx_var
        ctx_var.trace_add("write", lambda *args: self._save_generation_config())
        
        ctk.CTkLabel(
            llm_gen_card,
            text="токенов",
            font=("Segoe UI", 11),
            text_color=COLORS['text_muted']
        ).grid(row=2, column=2, sticky="w", padx=(0, 15), pady=6)
        
        # LLM Model Management - Unified
        llm_card = ctk.CTkFrame(scroll, fg_color=COLORS['card_bg'], corner_radius=12)
        llm_card.pack(fill="both", expand=True, pady=(0, 12))
        llm_card.grid_columnconfigure(0, weight=1)
        llm_card.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            llm_card,
            text=t("ui.launcher.settings.llm_model_management", default="Модели LLM"),
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 10))
        
        # Container for unified models tab content
        models_content = ctk.CTkFrame(llm_card, fg_color="transparent")
        models_content.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 12))
        models_content.grid_columnconfigure(0, weight=1)
        models_content.grid_rowconfigure(1, weight=1)
        
        self._create_unified_llm_models_tab(models_content)
        
        # Models folder - Compact
        models_dir_card = ctk.CTkFrame(scroll, fg_color=COLORS['card_bg'], corner_radius=12)
        models_dir_card.pack(fill="x", pady=(0, 12))
        models_dir_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            models_dir_card,
            text=t("ui.launcher.settings.models_folder_label", default="Папка моделей"),
            font=("Segoe UI", 12),
            text_color=COLORS['text_secondary']
        ).grid(row=0, column=0, sticky="w", padx=15, pady=8)
        
        current_path = get_models_llm_dir()
        models_dir_entry = ctk.CTkEntry(
            models_dir_card,
            font=("Segoe UI", 11),
            fg_color=COLORS['bg'],
            border_color=COLORS['border'],
            height=32
        )
        models_dir_entry.insert(0, current_path)
        models_dir_entry.grid(row=0, column=1, sticky="ew", padx=(8, 8), pady=8)
        self.models_dir_entry = models_dir_entry
        
        ctk.CTkButton(
            models_dir_card,
            text="📁",
            width=40,
            height=32,
            command=lambda: self._select_models_folder(models_dir_entry),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            font=("Segoe UI", 12)
        ).grid(row=0, column=2, padx=(0, 15), pady=8)
    
    def _create_image_settings_tab(self, parent):
        """Создает вкладку настроек генерации изображений с Discord-стилем"""
        scroll = ctk.CTkScrollableFrame(parent, fg_color=COLORS['bg'])
        scroll.pack(fill="both", expand=True, padx=16, pady=16)
        scroll.grid_columnconfigure(0, weight=1)
        
        gen_config = {}
        if os.path.exists(FILE_GEN_CONFIG):
            try:
                with open(FILE_GEN_CONFIG, 'r', encoding='utf-8') as f:
                    gen_config = json.load(f)
            except:
                pass
        
        # Card 1: Параметры генерации
        gen_card = self.create_glass_card(scroll, fg_color=COLORS['surface'])
        gen_card.pack(fill="x", pady=(0, 16))
        gen_card.grid_columnconfigure(1, weight=1)
        
        card_header = ctk.CTkFrame(gen_card, fg_color="transparent")
        card_header.pack(fill="x", padx=20, pady=(20, 16))
        
        ctk.CTkLabel(
            card_header,
            text="🎨 " + t("ui.launcher.settings.image_generation", default="Параметры генерации"),
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['text']
        ).pack(side="left")
        
        card_content = ctk.CTkFrame(gen_card, fg_color="transparent")
        card_content.pack(fill="x", padx=20, pady=(0, 20))
        card_content.grid_columnconfigure(1, weight=1)
        
        # Steps with live value
        ctk.CTkLabel(
            card_content,
            text=t("ui.launcher.settings.sd_steps", default="Количество шагов"),
            font=("Segoe UI", 14),
            text_color=COLORS['text_secondary']
        ).grid(row=0, column=0, sticky="w", padx=(0, 16), pady=12)
        
        steps_var = tk.IntVar(value=int(gen_config.get("sd_steps", 30)))
        steps_frame = ctk.CTkFrame(card_content, fg_color="transparent")
        steps_frame.grid(row=0, column=1, sticky="ew", pady=12)
        steps_frame.grid_columnconfigure(0, weight=1)
        
        steps_slider = ctk.CTkSlider(
            steps_frame,
            from_=1,
            to=100,
            number_of_steps=99,
            variable=steps_var,
            progress_color=COLORS['primary'],
            button_color=COLORS['primary'],
            button_hover_color=COLORS['primary_hover']
        )
        steps_slider.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        
        steps_label = ctk.CTkLabel(
            steps_frame,
            textvariable=steps_var,
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS['primary'],
            width=60,
            fg_color=COLORS['surface_light'],
            corner_radius=8
        )
        steps_label.grid(row=0, column=1)
        self.sd_steps_var = steps_var
        steps_var.trace_add("write", lambda *args: self._save_generation_config())
        
        # CFG Scale with live value
        ctk.CTkLabel(
            card_content,
            text=t("ui.launcher.settings.sd_cfg", default="CFG Scale"),
            font=("Segoe UI", 14),
            text_color=COLORS['text_secondary']
        ).grid(row=1, column=0, sticky="w", padx=(0, 16), pady=12)
        
        cfg_var = tk.DoubleVar(value=float(gen_config.get("sd_cfg", 6.0)))
        cfg_frame = ctk.CTkFrame(card_content, fg_color="transparent")
        cfg_frame.grid(row=1, column=1, sticky="ew", pady=12)
        cfg_frame.grid_columnconfigure(0, weight=1)
        
        cfg_slider = ctk.CTkSlider(
            cfg_frame,
            from_=1.0,
            to=20.0,
            number_of_steps=190,
            variable=cfg_var,
            progress_color=COLORS['primary'],
            button_color=COLORS['primary'],
            button_hover_color=COLORS['primary_hover']
        )
        cfg_slider.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        
        cfg_label = ctk.CTkLabel(
            cfg_frame,
            textvariable=cfg_var,
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS['primary'],
            width=60,
            fg_color=COLORS['surface_light'],
            corner_radius=8
        )
        cfg_label.grid(row=0, column=1)
        self.sd_cfg_var = cfg_var
        cfg_var.trace_add("write", lambda *args: self._save_generation_config())
        
        # Card 2: Размер изображения
        size_card = self.create_glass_card(scroll, fg_color=COLORS['surface'])
        size_card.pack(fill="x", pady=(0, 16))
        size_card.grid_columnconfigure(1, weight=1)
        
        size_header = ctk.CTkFrame(size_card, fg_color="transparent")
        size_header.pack(fill="x", padx=20, pady=(20, 16))
        
        ctk.CTkLabel(
            size_header,
            text="📐 " + t("ui.launcher.settings.image_size", default="Размер изображения"),
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['text']
        ).pack(side="left")
        
        size_content = ctk.CTkFrame(size_card, fg_color="transparent")
        size_content.pack(fill="x", padx=20, pady=(0, 20))
        size_content.grid_columnconfigure((1, 3), weight=1)
        
        # Width
        ctk.CTkLabel(
            size_content,
            text=t("ui.launcher.settings.sd_width", default="Ширина"),
            font=("Segoe UI", 14),
            text_color=COLORS['text_secondary']
        ).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=12)
        
        width_var = tk.IntVar(value=int(gen_config.get("sd_width", 896)))
        width_entry = ctk.CTkEntry(
            size_content,
            textvariable=width_var,
            font=("Segoe UI", 13),
            width=140,
            fg_color=COLORS['bg'],
            border_color=COLORS['border'],
            corner_radius=8
        )
        width_entry.grid(row=0, column=1, sticky="w", padx=(0, 24), pady=12)
        self.sd_width_var = width_var
        width_var.trace_add("write", lambda *args: self._save_generation_config())
        
        # Height
        ctk.CTkLabel(
            size_content,
            text=t("ui.launcher.settings.sd_height", default="Высота"),
            font=("Segoe UI", 14),
            text_color=COLORS['text_secondary']
        ).grid(row=0, column=2, sticky="w", padx=(0, 12), pady=12)
        
        height_var = tk.IntVar(value=int(gen_config.get("sd_height", 1152)))
        height_entry = ctk.CTkEntry(
            size_content,
            textvariable=height_var,
            font=("Segoe UI", 13),
            width=140,
            fg_color=COLORS['bg'],
            border_color=COLORS['border'],
            corner_radius=8
        )
        height_entry.grid(row=0, column=3, sticky="w", pady=12)
        self.sd_height_var = height_var
        height_var.trace_add("write", lambda *args: self._save_generation_config())
        
        # Card 3: Параметры сэмплинга
        sampling_card = self.create_glass_card(scroll, fg_color=COLORS['surface'])
        sampling_card.pack(fill="x", pady=(0, 16))
        sampling_card.grid_columnconfigure(1, weight=1)
        
        sampling_header = ctk.CTkFrame(sampling_card, fg_color="transparent")
        sampling_header.pack(fill="x", padx=20, pady=(20, 16))
        
        ctk.CTkLabel(
            sampling_header,
            text="⚙️ " + t("ui.launcher.settings.sampling", default="Параметры сэмплинга"),
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['text']
        ).pack(side="left")
        
        sampling_content = ctk.CTkFrame(sampling_card, fg_color="transparent")
        sampling_content.pack(fill="x", padx=20, pady=(0, 20))
        sampling_content.grid_columnconfigure(1, weight=1)
        
        # Sampler
        ctk.CTkLabel(
            sampling_content,
            text=t("ui.launcher.settings.sd_sampler", default="Семплер"),
            font=("Segoe UI", 14),
            text_color=COLORS['text_secondary']
        ).grid(row=0, column=0, sticky="w", padx=(0, 16), pady=12)
        
        sampler_options = ["DPM++ 2M", "DPM++ 2M Karras", "DPM++ SDE", "DPM++ SDE Karras", "Euler", "Euler a", "LMS", "LMS Karras", "DDIM", "PLMS"]
        sampler_var = tk.StringVar(value=gen_config.get("sd_sampler", "DPM++ 2M"))
        sampler_menu = ctk.CTkOptionMenu(
            sampling_content,
            values=sampler_options,
            variable=sampler_var,
            width=220,
            font=("Segoe UI", 13),
            fg_color=COLORS['surface_light'],
            button_color=COLORS['primary'],
            button_hover_color=COLORS['primary_hover']
        )
        sampler_menu.grid(row=0, column=1, sticky="w", pady=12)
        self.sd_sampler_var = sampler_var
        sampler_var.trace_add("write", lambda *args: self._save_generation_config())
        
        # Scheduler
        ctk.CTkLabel(
            sampling_content,
            text=t("ui.launcher.settings.sd_scheduler", default="Планировщик"),
            font=("Segoe UI", 14),
            text_color=COLORS['text_secondary']
        ).grid(row=1, column=0, sticky="w", padx=(0, 16), pady=12)
        
        scheduler_options = ["Karras", "Exponential", "SGM Uniform", "Simple", "DDIM Uniform"]
        scheduler_var = tk.StringVar(value=gen_config.get("sd_scheduler", "Karras"))
        scheduler_menu = ctk.CTkOptionMenu(
            sampling_content,
            values=scheduler_options,
            variable=scheduler_var,
            width=220,
            font=("Segoe UI", 13),
            fg_color=COLORS['surface_light'],
            button_color=COLORS['primary'],
            button_hover_color=COLORS['primary_hover']
        )
        scheduler_menu.grid(row=1, column=1, sticky="w", pady=12)
        self.sd_scheduler_var = scheduler_var
        scheduler_var.trace_add("write", lambda *args: self._save_generation_config())
        
        # Card 4: Промпты
        prompts_card = self.create_glass_card(scroll, fg_color=COLORS['surface'])
        prompts_card.pack(fill="x", pady=(0, 16))
        prompts_card.grid_columnconfigure(1, weight=1)
        
        prompts_header = ctk.CTkFrame(prompts_card, fg_color="transparent")
        prompts_header.pack(fill="x", padx=20, pady=(20, 16))
        
        ctk.CTkLabel(
            prompts_header,
            text="✍️ " + t("ui.launcher.settings.prompts", default="Промпты"),
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['text']
        ).pack(side="left")
        
        prompts_content = ctk.CTkFrame(prompts_card, fg_color="transparent")
        prompts_content.pack(fill="x", padx=20, pady=(0, 20))
        prompts_content.grid_columnconfigure(1, weight=1)
        
        # Positive Prompt Prefix
        ctk.CTkLabel(
            prompts_content,
            text=t("ui.launcher.settings.sd_positive_prefix", default="Префикс позитивного промпта"),
            font=("Segoe UI", 14),
            text_color=COLORS['text_secondary']
        ).grid(row=0, column=0, sticky="nw", padx=(0, 16), pady=12)
        
        positive_prefix_var = tk.StringVar(value=gen_config.get("sd_positive_prefix", "score_9, score_8_up, score_7_up, source_anime, "))
        positive_prefix_entry = ctk.CTkTextbox(
            prompts_content,
            height=70,
            font=("Segoe UI", 12),
            wrap="word",
            fg_color=COLORS['bg'],
            border_color=COLORS['border'],
            corner_radius=8
        )
        positive_prefix_entry.insert("1.0", positive_prefix_var.get())
        positive_prefix_entry.grid(row=0, column=1, sticky="ew", pady=12)
        self.sd_positive_prefix_entry = positive_prefix_entry
        def save_positive_prefix(*args):
            self.after(500, self._save_generation_config())
        positive_prefix_entry.bind("<KeyRelease>", save_positive_prefix)
        
        # Negative Prompt
        ctk.CTkLabel(
            prompts_content,
            text=t("ui.launcher.settings.sd_negative_prompt", default="Негативный промпт"),
            font=("Segoe UI", 14),
            text_color=COLORS['text_secondary']
        ).grid(row=1, column=0, sticky="nw", padx=(0, 16), pady=12)
        
        negative_prompt_default = gen_config.get("sd_negative_prompt", "score_6, score_5, score_4, (worst quality:1.2), (low quality:1.2), (normal quality:1.2), lowres, bad anatomy, bad hands, signature, watermarks, ugly, imperfect eyes, skewed eyes, unnatural face, unnatural body, error, extra limb, missing limbs, text, username, artist name")
        negative_prompt_entry = ctk.CTkTextbox(
            prompts_content,
            height=90,
            font=("Segoe UI", 12),
            wrap="word",
            fg_color=COLORS['bg'],
            border_color=COLORS['border'],
            corner_radius=8
        )
        negative_prompt_entry.insert("1.0", negative_prompt_default)
        negative_prompt_entry.grid(row=1, column=1, sticky="ew", pady=12)
        self.sd_negative_prompt_entry = negative_prompt_entry
        def save_negative_prompt(*args):
            self.after(500, self._save_generation_config())
        negative_prompt_entry.bind("<KeyRelease>", save_negative_prompt)
        
        # Card 5: Управление SD
        delete_sd_card = self.create_glass_card(scroll, fg_color=COLORS['surface'])
        delete_sd_card.pack(fill="x", pady=(0, 16))
        
        delete_sd_header = ctk.CTkFrame(delete_sd_card, fg_color="transparent")
        delete_sd_header.pack(fill="x", padx=20, pady=(20, 16))
        
        ctk.CTkLabel(
            delete_sd_header,
            text="🗑️ " + t("ui.launcher.settings.sd_management", default="Управление Stable Diffusion"),
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['text']
        ).pack(side="left")
        
        delete_sd_content = ctk.CTkFrame(delete_sd_card, fg_color="transparent")
        delete_sd_content.pack(fill="x", padx=20, pady=(0, 20))
        delete_sd_content.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            delete_sd_content,
            text=t("ui.launcher.settings.delete_sd_description", default="Удалить Stable Diffusion и все связанные файлы"),
            font=("Segoe UI", 13),
            text_color=COLORS['text_secondary']
        ).grid(row=0, column=0, sticky="w", padx=(0, 16), pady=12)
        
        delete_btn = ctk.CTkButton(
            delete_sd_content,
            text="🗑️ Удалить SD",
            width=140,
            height=40,
            command=self._delete_sd,
            fg_color=COLORS['danger'],
            hover_color="#dc2626",
            font=("Segoe UI", 13, "bold"),
            corner_radius=8
        )
        delete_btn.grid(row=0, column=1, sticky="e", pady=12)
        
        # Настройки модели SD
        model_card = ctk.CTkFrame(scroll, fg_color=COLORS['card_bg'], corner_radius=12)
        model_card.pack(fill="x", pady=(0, 15))
        model_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            model_card,
            text=t("ui.launcher.settings.sd_model"),
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(20, 15))
        
        ctk.CTkLabel(
            model_card,
            text=t("ui.launcher.settings.sd_model_url"),
            font=("Segoe UI", 13),
            text_color=COLORS['text_secondary']
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))
        
        # Поле для ссылки на модель
        model_url_entry = ctk.CTkEntry(
            model_card,
            placeholder_text="https://civitai.com/api/download/models/...",
            font=("Segoe UI", 12),
            height=35
        )
        model_url_entry.grid(row=1, column=1, sticky="ew", padx=(10, 10), pady=(0, 10))
        
        # Загружаем сохраненную ссылку
        try:
            saved_url = get_key(FILE_ENV, "SD_MODEL_URL")
            if saved_url:
                model_url_entry.insert(0, saved_url)
            else:
                # Устанавливаем значение по умолчанию
                default_url = MODEL_SD_URL
                model_url_entry.insert(0, default_url)
        except:
            default_url = MODEL_SD_URL
            model_url_entry.insert(0, default_url)
        
        # Кнопка скачивания модели
        download_btn = ctk.CTkButton(
            model_card,
            text=t("ui.launcher.button.download_model", default="📥 Скачать модель"),
            width=150,
            height=35,
            command=lambda: self._download_sd_model(model_url_entry.get()),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            font=("Segoe UI", 13, "bold")
        )
        download_btn.grid(row=1, column=2, sticky="e", padx=(0, 20), pady=(0, 10))
        
        # Информация о текущей модели
        model_info_label = ctk.CTkLabel(
            model_card,
            text="",
            font=("Segoe UI", 12),
            text_color=COLORS['text_secondary'],
            wraplength=600
        )
        model_info_label.grid(row=2, column=0, columnspan=3, sticky="w", padx=20, pady=(0, 20))
        
        # Обновляем информацию о модели
        self._update_sd_model_info(model_info_label)
        
        # Сохраняем ссылки для обновления информации
        self.sd_model_url_entry = model_url_entry
        self.sd_model_info_label = model_info_label
    
    def create_setting_card(self, parent, title, fields):
        card = ctk.CTkFrame(parent, fg_color=COLORS['card_bg'], corner_radius=12)
        card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 15))
        
        row = 1
        for key, label, placeholder in fields:
            ctk.CTkLabel(
                card,
                text=label,
                font=("Segoe UI", 13),
                text_color=COLORS['text_secondary']
            ).grid(row=row, column=0, sticky="w", padx=(20, 10), pady=10)
            
            if key == "model":
                combo = ctk.CTkComboBox(
                    card,
                    values=[],
                    variable=self.selected_llm_model,
                    font=("Segoe UI", 13),
                    fg_color=COLORS['bg'],
                    button_color=COLORS['primary'],
                    button_hover_color=COLORS['primary_hover']
                )
                combo.grid(row=row, column=1, sticky="ew", padx=(0, 20), pady=10)
                self.llm_combo = combo
                
                ctk.CTkButton(
                    card,
                    text=t("ui.launcher.settings.update"),
                    width=80,
                    command=self.scan_llm_models,
                    fg_color=COLORS['surface_dark'],
                    hover_color=COLORS['card_bg']
                ).grid(row=row, column=2, padx=(5, 20), pady=10)
            else:
                entry = ctk.CTkEntry(
                    card,
                    placeholder_text=placeholder,
                    font=("Segoe UI", 13),
                    fg_color=COLORS['bg'],
                    border_color=COLORS['border']
                )
                entry.insert(0, get_key(FILE_ENV, key) or "")
                entry.grid(row=row, column=1, sticky="ew", padx=(0, 20), pady=10)
                self.entries[key] = entry
                # Привязка автосохранения
                entry.bind("<KeyRelease>", lambda e: self._auto_save_settings())
                entry.bind("<FocusOut>", lambda e: self._auto_save_settings())
            
            row += 1
        
        return card
    
    def create_channels_page(self):
        """Создает страницу управления каналами в стиле Master-Detail"""
        frame = ctk.CTkFrame(self.content_frame, fg_color=COLORS['bg'])
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=3)
        frame.grid_rowconfigure(0, weight=1)
        
        # Левая панель (25%): Темы
        topics_panel = ctk.CTkFrame(frame, fg_color=COLORS['surface'], corner_radius=0)
        topics_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 1))
        topics_panel.grid_columnconfigure(0, weight=1)
        topics_panel.grid_rowconfigure(0, weight=1)
        topics_panel.grid_rowconfigure(1, weight=0)
        
        # Заголовок левой панели
        topics_header = ctk.CTkLabel(
            topics_panel,
            text=t("ui.launcher.channels.topics", default="Темы"),
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['text'],
            anchor="w"
        )
        topics_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        # Список тем (ScrollableFrame)
        self.scroll_topics = ctk.CTkScrollableFrame(
            topics_panel,
            fg_color=COLORS['bg'],
            corner_radius=0
        )
        self.scroll_topics.grid(row=0, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.scroll_topics.grid_columnconfigure(0, weight=1)
        
        # Кнопка "+ Новая тема" (закреплена внизу)
        new_topic_btn = ctk.CTkButton(
            topics_panel,
            text=t("ui.launcher.channels.new_topic", default="Новая тема"),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            font=("Segoe UI", 14, "bold"),
            height=45,
            corner_radius=8,
            command=self.new_topic
        )
        new_topic_btn.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Add Windows-style hover animation
        if self.animations_enabled:
            try:
                button_hover_effect(new_topic_btn, hover_color=COLORS['primary_hover'], normal_color=COLORS['primary'], duration=100)
            except:
                pass
        
        # Правая панель (75%): Каналы
        channels_panel = ctk.CTkFrame(frame, fg_color=COLORS['bg'], corner_radius=0)
        channels_panel.grid(row=0, column=1, sticky="nsew")
        channels_panel.grid_columnconfigure(0, weight=1)
        channels_panel.grid_rowconfigure(1, weight=1)
        
        # Верхняя шапка правой панели
        channels_header = ctk.CTkFrame(channels_panel, fg_color="transparent")
        channels_header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 16))
        channels_header.grid_columnconfigure(0, weight=1)
        channels_header.grid_columnconfigure(1, weight=0)
        
        # Название текущей темы (слева)
        self.topic_title_label = ctk.CTkLabel(
            channels_header,
            text=t("ui.launcher.channels.select_topic", default="Выберите тему"),
            font=("Segoe UI", 24, "bold"),
            text_color=COLORS['text'],
            anchor="w"
        )
        self.topic_title_label.grid(row=0, column=0, sticky="w")
        
        # Группа ввода канала (справа)
        input_group = ctk.CTkFrame(channels_header, fg_color=COLORS['surface'], corner_radius=8)
        input_group.grid(row=0, column=1, sticky="e", padx=(20, 0))
        
        self.entry_chan = ctk.CTkEntry(
            input_group,
            placeholder_text=t("ui.launcher.channels.entry_placeholder", default="Ссылка или @username"),
            font=("Segoe UI", 13),
            width=280,
            height=40,
            fg_color=COLORS['bg'],
            border_color=COLORS['border']
        )
        self.entry_chan.pack(side="left", padx=(12, 8), pady=8)
        self.entry_chan.bind("<Return>", lambda e: self.add_channel())
        
        add_btn = ctk.CTkButton(
            input_group,
            text="+",
            width=40,
            height=40,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            font=("Segoe UI", 20, "bold"),
            corner_radius=8,
            command=self.add_channel
        )
        add_btn.pack(side="left", padx=(0, 12), pady=8)
        
        # Add Windows-style hover animation
        if self.animations_enabled:
            try:
                button_hover_effect(add_btn, hover_color=COLORS['primary_hover'], normal_color=COLORS['primary'], duration=100)
            except:
                pass
        
        # Список каналов (Frame с условной прокруткой)
        # Создаем контейнер для прокрутки
        scroll_container = ctk.CTkFrame(channels_panel, fg_color=COLORS['bg'], corner_radius=0)
        scroll_container.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        scroll_container.grid_columnconfigure(0, weight=1)
        scroll_container.grid_rowconfigure(0, weight=1)
        
        # Canvas для прокрутки
        self.channels_canvas = tk.Canvas(
            scroll_container,
            bg=COLORS['bg'],
            highlightthickness=0,
            borderwidth=0
        )
        self.channels_canvas.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar (скрыта по умолчанию)
        self.channels_scrollbar = ctk.CTkScrollbar(
            scroll_container,
            orientation="vertical",
            command=self.channels_canvas.yview
        )
        self.channels_scrollbar.grid(row=0, column=1, sticky="ns")
        self.channels_scrollbar.grid_remove()  # Скрываем по умолчанию
        
        # Frame для контента внутри Canvas
        self.scroll_chans = ctk.CTkFrame(
            self.channels_canvas,
            fg_color=COLORS['bg'],
            corner_radius=0
        )
        self.channels_canvas_window = self.channels_canvas.create_window(
            0, 0,
            anchor="nw",
            window=self.scroll_chans
        )
        
        # Настройка прокрутки
        self.scroll_chans.bind("<Configure>", self._on_channels_frame_configure)
        self.channels_canvas.bind("<Configure>", self._on_channels_canvas_configure)
        
        # Привязка прокрутки колесиком мыши (только когда курсор над canvas)
        def on_mousewheel(event):
            if hasattr(self, 'channels_canvas') and self.channels_canvas.winfo_ismapped():
                if self.channels_scrollbar.winfo_viewable():
                    self.channels_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        self.channels_canvas.bind("<MouseWheel>", on_mousewheel)
        self.scroll_chans.bind("<MouseWheel>", on_mousewheel)
        
        # Инициализация
        if not hasattr(self, 'current_topic'):
            self.current_topic = None
        self.refresh_channels()
    
        return frame
    
    # SERVICE MANAGEMENT
    
    def safe_widget_configure(self, widget, **kwargs):
        """Безопасный вызов configure из фоновых потоков."""
        if widget is None:
            return

        def _apply():
            try:
                widget.configure(**kwargs)
            except tk.TclError:
                pass

        if threading.current_thread() is threading.main_thread():
            _apply()
        else:
            self.after(0, _apply)

    def _set_service_indicator(self, name, color):
        indicator = self.status_indicators.get(name)
        if indicator and self.animations_enabled:
            try:
                old_color = indicator.cget('text_color')
                smooth_color_transition(indicator, 'text_color', old_color, color, duration=200, steps=10)
            except:
                self.safe_widget_configure(indicator, text_color=color)
        else:
            self.safe_widget_configure(indicator, text_color=color)

    def _set_service_button(self, name, text=None, fg_color=None):
        button = getattr(self, 'service_buttons', {}).get(name)
        if button:
            kwargs = {}
            if text is not None:
                kwargs["text"] = text
            if fg_color is not None:
                if self.animations_enabled:
                    try:
                        old_color = button.cget('fg_color')
                        smooth_color_transition(button, 'fg_color', old_color, fg_color, duration=200, steps=10)
                    except:
                        kwargs["fg_color"] = fg_color
                else:
                    kwargs["fg_color"] = fg_color
            if kwargs:
                self.safe_widget_configure(button, **kwargs)

    def _set_service_status_label(self, name, text=None, color=None):
        # Update both old status labels and new status cards
        label = self.service_status_labels.get(name)
        if label:
            kwargs = {}
            if text is not None:
                kwargs["text"] = text
            if color is not None:
                if self.animations_enabled:
                    try:
                        old_color = label.cget('text_color')
                        smooth_color_transition(label, 'text_color', old_color, color, duration=200, steps=10)
                    except:
                        kwargs["text_color"] = color
                else:
                    kwargs["text_color"] = color
            if kwargs:
                self.safe_widget_configure(label, **kwargs)

        # Update status card if exists
        if hasattr(self, 'status_card_labels') and name in self.status_card_labels:
            card_label = self.status_card_labels.get(name)
            if card_label:
                kwargs = {}
                if text is not None:
                    kwargs["text"] = text
                if color is not None:
                    kwargs["text_color"] = color
                if kwargs:
                    self.safe_widget_configure(card_label, **kwargs)
        
        # Also update summary card if it exists
        if hasattr(self, 'summary_cards') and name in self.summary_cards:
            card = self.summary_cards[name]
            if text is not None:
                self.safe_widget_configure(card['status'], text=text)
                new_color = None
                if "running" in text.lower() or "запущен" in text.lower():
                    new_color = COLORS['success']
                elif "error" in text.lower() or "ошибка" in text.lower():
                    new_color = COLORS['danger']
                else:
                    new_color = COLORS['text_muted']
                
                if new_color and self.animations_enabled:
                    try:
                        old_color = card['dot'].cget('text_color')
                        smooth_color_transition(card['dot'], 'text_color', old_color, new_color, duration=200, steps=10)
                    except:
                        self.safe_widget_configure(card['dot'], text_color=new_color)
                elif new_color:
                    self.safe_widget_configure(card['dot'], text_color=new_color)
            
            if color is not None:
                if self.animations_enabled:
                    try:
                        old_color = card['status'].cget('text_color')
                        smooth_color_transition(card['status'], 'text_color', old_color, color, duration=200, steps=10)
                    except:
                        self.safe_widget_configure(card['status'], text_color=color)
                else:
                    self.safe_widget_configure(card['status'], text_color=color)
    
    def _get_service_name(self, name):
        """Получает локализованное название сервиса"""
        service_names = {
            "bot": t("ui.launcher.service.telegram_bot", default="Telegram Бот"),
            "llm": t("ui.launcher.service.llm_server", default="LLM Сервер"),
            "sd": t("ui.launcher.service.stable_diffusion", default="Stable Diffusion")
        }
        return service_names.get(name, name)

    def toggle_service(self, name):
        # Add click animation
        if self.animations_enabled:
            button = self.service_buttons.get(name)
            if button:
                try:
                    # Bounce effect on click
                    bounce_in(button, duration=200, steps=10)
                except:
                    pass
        threading.Thread(target=self._manage_service, args=(name,), daemon=True).start()

    def _manage_service(self, name):
        """Управляет запуском/остановкой сервиса"""
        try:
            # Проверяем, что service_manager инициализирован
            if not self.service_manager:
                self.log(t("ui.launcher.log.service_manager_not_ready", default="❌ [{service}] Service manager not ready", service=name.upper()), name.upper())
                return
            
            # Логируем действие сразу
            if self.service_manager.procs.get(name):
                # Сервис запущен - останавливаем
                self.log(t("ui.launcher.log.stopping_service", default="⏹️ [{service}] Остановка сервиса...", service=name.upper()), name.upper())
                # Обновляем кнопку сразу
                self.after(0, lambda: self._set_service_button(name, text="⏸", fg_color=COLORS['primary']))
                threading.Thread(target=self.service_manager.stop_service, args=(name,), daemon=True).start()
            else:
                # Сервис не запущен - запускаем
                self.log(t("ui.launcher.log.starting_service", default="▶️ [{service}] Запуск сервиса...", service=name.upper()), name.upper())
                # Обновляем кнопку сразу
                self.after(0, lambda: self._set_service_button(name, text="⏸", fg_color=COLORS['primary']))
                self.after(0, lambda: self._set_service_status_label(name, text=t("ui.launcher.status.starting", default="Запуск..."), color=COLORS['warning']))
                
                # For LLM we use model from settings
                llm_config = None
                if name == "llm":
                    llm_config = self._get_llm_model_from_settings()
                    if not llm_config:
                        self.log(t("ui.launcher.log.model_not_selected", default="❌ [LLM] Модель не выбрана в настройках"), "LLM")
                        # Возвращаем кнопку в исходное состояние
                        self.after(0, lambda: self._set_service_button(name, text="▶", fg_color=COLORS['primary']))
                        self.after(0, lambda: self._set_service_status_label(name, text=t("ui.launcher.status.stopped", default="Остановлен"), color=COLORS['text_muted']))
                        self.show_warning(
                            t("ui.launcher.model.no_model", default="Модель не выбрана"),
                            t("ui.launcher.model.select_in_settings", default="Выберите модель в настройках перед запуском")
                        )
                        return
                    
                # Run start in thread
                threading.Thread(target=self.service_manager.start_service, 
                               args=(name, llm_config), daemon=True).start()
        except Exception as e:
            self.log(t("ui.launcher.log.service_error", default="❌ [{service}] Ошибка: {error}", service=name.upper(), error=str(e)), name.upper())
            # Возвращаем кнопку в исходное состояние при ошибке
            self.after(0, lambda: self._set_service_button(name, text="▶", fg_color=COLORS['primary']))
            self.after(0, lambda: self._set_service_status_label(name, text=t("ui.launcher.status.error", default="Ошибка"), color=COLORS['danger']))
            import traceback
            self.log(f"❌ [{name.upper()}] Критическая ошибка: {e}", name.upper())

    # Old _manage_service code removed - functionality moved to service_manager.py
    # Old methods (_download_ollama, _install_sd, etc.) removed - moved to installer.py
    
    def _create_unified_llm_models_tab(self, parent):
        """Создает объединенное меню управления моделями LLM"""
        # Popular models from Ollama
        POPULAR_MODELS = {
            "gemma3": {
                "name": "gemma3",
                "sizes": ["270m", "1b", "4b", "12b", "27b"],
                "description": "Google's most capable model"
            },
            "qwen3": {
                "name": "qwen3",
                "sizes": ["0.6b", "1.7b", "4b", "8b", "14b", "30b", "32b", "235b"],
                "description": "Latest Qwen generation"
            },
            "gpt-oss": {
                "name": "gpt-oss",
                "sizes": ["20b", "120b"],
                "description": "OpenAI's open-weight models"
            },
            "llama3.1": {
                "name": "llama3.1",
                "sizes": ["8b", "70b", "405b"],
                "description": "Meta's state-of-the-art model"
            },
            "deepseek-r1": {
                "name": "deepseek-r1",
                "sizes": ["1.5b", "7b", "8b", "14b", "32b", "70b", "671b"],
                "description": "Open reasoning models"
            },
            "qwen2.5": {
                "name": "qwen2.5",
                "sizes": ["0.5b", "1.5b", "3b", "7b", "14b", "32b", "72b"],
                "description": "Qwen 2.5 models"
            }
        }
        
        # Download section
        download_frame = ctk.CTkFrame(parent, fg_color=COLORS['bg'], corner_radius=12)
        download_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        download_frame.grid_columnconfigure(0, weight=1)
        download_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            download_frame,
            text=t("ui.launcher.model.download_popular", default="Скачать популярную модель"),
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 12))
        
        download_controls = ctk.CTkFrame(download_frame, fg_color="transparent")
        download_controls.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        download_controls.grid_columnconfigure(1, weight=1)
        
        model_names = list(POPULAR_MODELS.keys())
        self.selected_model_var = tk.StringVar(value=model_names[0] if model_names else "")
        model_menu = ctk.CTkOptionMenu(
            download_controls,
            values=model_names,
            variable=self.selected_model_var,
            width=180,
            font=("Segoe UI", 13),
            fg_color=COLORS['surface_light'],
            button_color=COLORS['primary'],
            button_hover_color=COLORS['primary_hover'],
            command=lambda v: self._update_model_sizes(POPULAR_MODELS[v]['sizes'])
        )
        model_menu.grid(row=0, column=0, sticky="w", padx=(0, 8))
        
        initial_sizes = POPULAR_MODELS[model_names[0]]['sizes'] if model_names else []
        self.selected_size_var = tk.StringVar(value=initial_sizes[0] if initial_sizes else "")
        self.size_menu = ctk.CTkOptionMenu(
            download_controls,
            values=initial_sizes,
            variable=self.selected_size_var,
            width=120,
            font=("Segoe UI", 13),
            fg_color=COLORS['surface_light'],
            button_color=COLORS['primary'],
            button_hover_color=COLORS['primary_hover']
        )
        self.size_menu.grid(row=0, column=1, sticky="w", padx=(0, 8))
        self.popular_models = POPULAR_MODELS
        
        download_btn = ctk.CTkButton(
            download_controls,
            text="📥 Скачать",
            width=120,
            height=36,
            command=self._download_selected_model,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            font=("Segoe UI", 13, "bold"),
            corner_radius=8
        )
        download_btn.grid(row=0, column=2, sticky="e")
        
        # Installed models
        installed_label = ctk.CTkLabel(
            parent,
            text=t("ui.launcher.model.installed_models", default="Установленные модели"),
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS['text']
        )
        installed_label.grid(row=1, column=0, sticky="w", pady=(0, 12))
        
        models_list_card = self.create_glass_card(parent, fg_color=COLORS['bg'])
        models_list_card.grid(row=2, column=0, sticky="nsew", pady=(0, 16))
        parent.grid_rowconfigure(2, weight=1)
        models_list_card.grid_columnconfigure(0, weight=1)
        models_list_card.grid_rowconfigure(0, weight=1)
        
        self.ollama_models_frame = ctk.CTkScrollableFrame(
            models_list_card,
            fg_color="transparent",
            height=220,
            corner_radius=12
        )
        self.ollama_models_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        
        # GGUF files
        gguf_label = ctk.CTkLabel(
            parent,
            text=t("ui.launcher.model.gguf_files", default="GGUF файлы"),
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS['text']
        )
        gguf_label.grid(row=3, column=0, sticky="w", pady=(0, 12))
        
        gguf_list_card = self.create_glass_card(parent, fg_color=COLORS['bg'])
        gguf_list_card.grid(row=4, column=0, sticky="nsew")
        parent.grid_rowconfigure(4, weight=1)
        gguf_list_card.grid_columnconfigure(0, weight=1)
        gguf_list_card.grid_rowconfigure(0, weight=1)
        
        self.gguf_models_frame = ctk.CTkScrollableFrame(
            gguf_list_card,
            fg_color="transparent",
            height=180,
            corner_radius=12
        )
        self.gguf_models_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        
        self.after(500, self.scan_llm_models)
    
    def _update_model_sizes(self, sizes):
        """Обновляет список размеров модели"""
        self.size_menu.configure(values=sizes)
        if sizes:
            self.selected_size_var.set(sizes[0])
    
    def _download_selected_model(self):
        """Скачивает выбранную модель"""
        model_name = self.selected_model_var.get()
        size = self.selected_size_var.get()
        if not model_name or not size:
            return
        
        full_model_name = f"{model_name}:{size}"
        self._download_ollama_model(full_model_name)
    
    def _select_models_folder(self, entry):
        """Выбор папки с моделями"""
        current_path = entry.get().strip() or get_models_llm_dir()
        folder = filedialog.askdirectory(
            title=t("ui.launcher.settings.select_models_folder"),
            initialdir=current_path if os.path.exists(current_path) else OLLAMA_MODELS_DIR
        )
        if folder:
            entry.delete(0, "end")
            entry.insert(0, folder)
            set_key(FILE_ENV, "MODELS_LLM_DIR", folder)
            global MODELS_LLM_DIR
            MODELS_LLM_DIR = folder
            self.scan_llm_models()
    
    def _create_ollama_models_tab(self, parent):
        """Legacy method - redirects to unified"""
        self._create_unified_llm_models_tab(parent)
    
    def _create_gguf_models_tab(self, parent):
        """Legacy method - not used in unified view"""
        pass
    
    def _download_ollama_model(self, model_name):
        """Скачивает модель Ollama"""
        if not model_name or not model_name.strip():
            self.show_warning(
                t("ui.launcher.model.no_name", default="Имя модели не указано"),
                t("ui.launcher.model.enter_name", default="Введите имя модели (например: llama3.2:3b)")
            )
            return
        
        model_name = model_name.strip()
        threading.Thread(
            target=self._download_ollama_model_thread,
            args=(model_name,),
            daemon=True
        ).start()
    
    def _download_ollama_model_thread(self, model_name):
        """Поток для скачивания модели Ollama"""
        try:
            self.log(t("ui.launcher.log.downloading_model", default="📥 [LLM] Скачивание модели {model}...", model=model_name), "LLM")
            
            if not os.path.exists(OLLAMA_EXE):
                if not self.installer.download_ollama():
                    self.log(t("ui.launcher.log.ollama_not_installed", default="❌ [LLM] Ollama не установлен"), "LLM")
                    return
            
            # Проверяем, запущен ли сервер Ollama
            server_running = False
            try:
                req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
                with urllib.request.urlopen(req, timeout=3) as response:
                    if response.status == 200:
                        server_running = True
                        self.log("[LLM] Используется существующий сервер Ollama", "LLM")
            except:
                pass
                                
            # Если сервер не запущен, используем метод из model_manager
            if not server_running:
                if hasattr(self.model_manager, 'is_ollama_running'):
                    if not self.model_manager.is_ollama_running():
                        self.log("[LLM] Сервер Ollama не запущен, команда pull запустит его автоматически", "LLM")
            
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    
            # Устанавливаем переменные окружения для pull
            pull_env = os.environ.copy()
            pull_env["OLLAMA_HOST"] = "127.0.0.1:11434"
            pull_env["OLLAMA_MODELS"] = get_models_llm_dir()
            
            process = subprocess.Popen(
                [OLLAMA_EXE, "pull", model_name],
                cwd=OLLAMA_DIR,
                env=pull_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                        text=True,
                bufsize=1,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        startupinfo=startupinfo
                    )
                    
            output_lines = []
            for line in iter(process.stdout.readline, ''):
                if line:
                    line = line.strip()
                    if line:
                        # Пропускаем предупреждения о логах и других неважных сообщениях
                        if "WARN" in line and "Failed to rotate log" in line:
                            continue
                        if "existing instance found" in line.lower():
                            continue
                        if "not focusing due to startHidden" in line.lower():
                            continue
                        output_lines.append(line)
                        self.log(f"[LLM] {line}", "LLM")
            
            process.wait()
            
            # Проверяем успешность скачивания
            if process.returncode == 0:
                self.log(t("ui.launcher.log.model_downloaded", default="✅ [LLM] Модель {model} успешно скачана", model=model_name), "LLM")
                self.after(0, self.scan_llm_models)
            else:
                # Если сервер уже был запущен, проверяем, скачалась ли модель
                if server_running or any("existing instance" in line.lower() for line in output_lines):
                    time.sleep(2)
                    try:
                        models = self.model_manager.get_ollama_models()
                        if model_name in models or any(model_name in m for m in models):
                            self.log(t("ui.launcher.log.model_downloaded", default="✅ [LLM] Модель {model} успешно скачана", model=model_name), "LLM")
                            self.after(0, self.scan_llm_models)
                            return
                    except:
                        pass
                self.log(t("ui.launcher.log.model_download_failed", default="❌ [LLM] Ошибка скачивания модели", model=model_name), "LLM")
        except Exception as e:
            self.log(t("ui.launcher.log.model_download_error", default="❌ [LLM] Ошибка: {error}", error=str(e)), "LLM")
    
    def _delete_ollama_model(self, model_name):
        """Удаляет модель Ollama"""
        if not self.show_confirm(
            t("ui.launcher.model.delete_confirm", default="Подтверждение удаления"),
            t("ui.launcher.model.delete_confirm_message", default="Удалить модель {model}?", model=model_name),
            yes_text="Удалить", danger=True
        ):
                            return
                    
        threading.Thread(
            target=self._delete_ollama_model_thread,
            args=(model_name,),
            daemon=True
        ).start()
    
    def _delete_ollama_model_thread(self, model_name):
        """Поток для удаления модели Ollama"""
        try:
            self.log(t("ui.launcher.log.deleting_model", default="🗑️ [LLM] Удаление модели {model}...", model=model_name), "LLM")
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            result = subprocess.run(
                [OLLAMA_EXE, "rm", model_name],
                cwd=OLLAMA_DIR,
                                        capture_output=True,
                                        text=True,
                                        timeout=60,
                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                        startupinfo=startupinfo
                                    )
                                    
            if result.returncode == 0:
                self.log(t("ui.launcher.log.model_deleted", default="✅ [LLM] Модель {model} удалена", model=model_name), "LLM")
                self.after(0, self.scan_llm_models)
            else:
                self.log(t("ui.launcher.log.model_delete_failed", default="❌ [LLM] Ошибка удаления модели: {error}", error=result.stderr), "LLM")
        except Exception as e:
            self.log(t("ui.launcher.log.model_delete_error", default="❌ [LLM] Ошибка: {error}", error=str(e)), "LLM")
    
    def _select_model_for_use(self, model_info):
        """Выбирает модель для использования"""
        try:
            from dotenv import set_key  # type: ignore
            
            # Ensure model_info has required fields
            if not isinstance(model_info, dict):
                raise ValueError("model_info must be a dictionary")
            
            model_name = model_info.get('name')
            if not model_name:
                raise ValueError("model_info must contain 'name' field")
            
            # Get type, default to 'ollama' if not specified
            model_type = model_info.get('type', 'ollama')
            
            # Format: "type:name:path" or "type:name"
            if model_type == 'gguf' and model_info.get('path'):
                model_str = f"{model_type}:{model_name}:{model_info['path']}"
            else:
                model_str = f"{model_type}:{model_name}"
            
            set_key(FILE_ENV, "SELECTED_LLM_MODEL", model_str)
            self.log(t("ui.launcher.log.model_selected", default="✅ [LLM] Выбрана модель: {model}", model=model_name), "LLM")
            
            # Обновляем UI сразу
            self.after(50, self.scan_llm_models)
            
            self.show_success(
                t("ui.launcher.model.selected", default="Модель выбрана"),
                t("ui.launcher.model.selected_message", default="Модель {model} выбрана для использования", model=model_name)
            )
        except Exception as e:
            self.log(t("ui.launcher.log.model_select_error", default="❌ [LLM] Ошибка при выборе модели: {error}", error=str(e)), "LLM")

    def _get_llm_model_from_settings(self):
        """Получает выбранную модель LLM из настроек"""
        try:
            from dotenv import get_key  # type: ignore
            model_str = get_key(FILE_ENV, "SELECTED_LLM_MODEL")
            if not model_str:
                return None
            
            # Parse model string: "type:name:path" or "type:name"
            parts = model_str.split(":", 2)
            if len(parts) < 2:
                return None
            
            model_type = parts[0]
            model_name = parts[1]
            model_path = parts[2] if len(parts) > 2 else None
            
            return {
                'name': model_name,
                'type': model_type,
                'path': model_path
            }
        except Exception as e:
            self.log(t("ui.launcher.log.model_load_error", default="❌ [LLM] Ошибка загрузки модели из настроек: {error}", error=str(e)), "LLM")
            return None
    
    def service_status_loop(self):
        # Проверяем, что service_manager инициализирован
        if not self.service_manager or not hasattr(self.service_manager, 'procs'):
            self.after(500, self.service_status_loop)
            return
        
        # Используем procs из service_manager
        procs = self.service_manager.procs
        for n, p in procs.items():
            if p and p.poll() is not None:
                self.procs[n] = None
                self._set_service_indicator(n, COLORS['danger'])
                self._set_service_button(n, text="▶", fg_color=COLORS['primary'])
                self._set_service_status_label(n, text=t("ui.launcher.status.error", default="Ошибка"), color=COLORS['danger'])
                service_name = self._get_service_name(n)
                self.log(t("ui.launcher.log.service_crashed", default="❌ Сервис {service} завершился с ошибкой", service=service_name), n.upper())
            elif p:
                self._set_service_indicator(n, COLORS['success'])
                self._set_service_button(n, text="⏸", fg_color=COLORS['danger'])
                self._set_service_status_label(n, text=t("ui.launcher.status.working", default="Работает"), color=COLORS['success'])
        
        self.after(500, self.service_status_loop)

    
    # CHANNELS MANAGEMENT
    
    class ModernInputDialog(ctk.CTkToplevel):
        """Кастомное модальное окно для ввода текста в стиле приложения"""
        def __init__(self, parent, title="", placeholder=""):
            super().__init__(parent)
            self.result = None
            self.parent_window = parent
            
            # Убираем стандартные рамки
            self.overrideredirect(True)
            self.attributes("-topmost", True)
            
            # Размер
            self.geometry("400x200")
            
            # Стиль окна с закруглениями
            self.configure(fg_color="transparent")
            
            # Рамка с закруглением
            outer = ctk.CTkFrame(self, fg_color=COLORS['primary'], corner_radius=16)
            outer.pack(fill="both", expand=True, padx=2, pady=2)
            
            content_frame = ctk.CTkFrame(outer, fg_color=COLORS['surface'], corner_radius=14)
            content_frame.pack(fill="both", expand=True, padx=2, pady=2)
            content_frame.grid_columnconfigure(0, weight=1)
            content_frame.grid_rowconfigure(1, weight=1)
            
            # Заголовок
            header_label = ctk.CTkLabel(
                content_frame,
                text=title or t("ui.launcher.channels.new_topic_title", default="Создать новую тему"),
                font=("Segoe UI", 16, "bold"),
                text_color=COLORS['text'],
                anchor="w"
            )
            header_label.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
            
            # Поле ввода
            self.entry = ctk.CTkEntry(
                content_frame,
                placeholder_text=placeholder or t("ui.launcher.channels.new_topic_dialog", default="Название..."),
                font=("Segoe UI", 14),
                        height=40,
                fg_color=COLORS['bg'],
                border_color=COLORS['border']
            )
            self.entry.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
            # Очищаем поле при создании
            self.entry.delete(0, "end")
            self.entry.bind("<Return>", lambda e: self.confirm())
            self.entry.bind("<Escape>", lambda e: self.cancel())
            
            # Кнопки (правый нижний угол)
            buttons_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            buttons_frame.grid(row=2, column=0, sticky="e", padx=20, pady=(0, 20))
            
            cancel_btn = ctk.CTkButton(
                buttons_frame,
                text=t("ui.launcher.button.cancel", default="Отмена"),
                fg_color="transparent",
                hover_color=COLORS['surface_light'],
                text_color=COLORS['text_secondary'],
                font=("Segoe UI", 13),
                width=100,
                height=35,
                command=self.cancel
            )
            cancel_btn.pack(side="left", padx=(0, 10))
            
            confirm_btn = ctk.CTkButton(
                buttons_frame,
                text=t("ui.launcher.button.create", default="Создать"),
                fg_color=COLORS['primary'],
                hover_color=COLORS['primary_hover'],
                text_color="white",
                font=("Segoe UI", 13, "bold"),
                width=100,
                height=35,
                command=self.confirm
            )
            confirm_btn.pack(side="left")
            
            # Модальность
            self.transient(parent)
            self.grab_set()
            self.lift()
            self.focus_force()
            self.bind("<Escape>", lambda e: self.cancel())
            
            # Центрируем и показываем
            self.after(50, self._center_and_show)
            
            # Фокус на поле ввода (с задержкой и принудительно)
            def set_focus():
                try:
                    self.entry.focus_force()
                    self.entry.icursor(0)
                except:
                    pass
            
            self.after(200, set_focus)
        
        def _center_and_show(self):
            """Центрирует окно и делает его видимым"""
            try:
                self.update_idletasks()
                try:
                    px = self.parent_window.winfo_x()
                    py = self.parent_window.winfo_y()
                    pw = self.parent_window.winfo_width()
                    ph = self.parent_window.winfo_height()
                    x = px + (pw - 400) // 2
                    y = py + (ph - 200) // 2
                except:
                    sw = self.winfo_screenwidth()
                    sh = self.winfo_screenheight()
                    x = (sw - 400) // 2
                    y = (sh - 200) // 2
                
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                x = max(0, min(x, sw - 400))
                y = max(0, min(y, sh - 200))
                
                self.geometry(f"400x200+{x}+{y}")
                self.deiconify()
                self.lift()
                self.focus_force()
            except:
                try:
                    self.deiconify()
                    self.lift()
                except:
                    pass
        
        def confirm(self):
            """Подтверждение ввода"""
            text = self.entry.get().strip()
            if text:  # Валидация: нельзя создать пустую тему
                self.result = text
                self.destroy()
        
        def cancel(self):
            """Отмена"""
            self.result = None
            self.destroy()
        
        def get_input(self):
            """Возвращает введенный текст или None"""
            self.wait_window()
            return self.result
    
    class ModernConfirmDialog(ctk.CTkToplevel):
        """Кастомное модальное окно подтверждения в стиле приложения"""
        def __init__(self, parent, message="", title=""):
            super().__init__(parent)
            self.result = False
            self.parent_window = parent
            
            # Убираем стандартные рамки
            self.overrideredirect(True)
            self.attributes("-topmost", True)
            
            # Размер
            self.geometry("420x180")
            
            # Стиль окна с закруглениями
            self.configure(fg_color="transparent")
            
            # Рамка с закруглением (красная для опасного действия)
            outer = ctk.CTkFrame(self, fg_color=COLORS['danger'], corner_radius=16)
            outer.pack(fill="both", expand=True, padx=2, pady=2)
            
            content_frame = ctk.CTkFrame(outer, fg_color=COLORS['surface'], corner_radius=14)
            content_frame.pack(fill="both", expand=True, padx=2, pady=2)
            content_frame.grid_columnconfigure(0, weight=1)
            content_frame.grid_rowconfigure(0, weight=1)
            
            # Текст сообщения
            message_label = ctk.CTkLabel(
                content_frame,
                text=message,
                font=("Segoe UI", 13),
                text_color=COLORS['text'],
                wraplength=300,
                justify="center"
            )
            message_label.grid(row=0, column=0, padx=20, pady=20)
            
            # Кнопки
            buttons_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            buttons_frame.grid(row=1, column=0, sticky="e", padx=20, pady=(0, 20))
            
            cancel_btn = ctk.CTkButton(
                buttons_frame,
                text=t("ui.launcher.button.cancel", default="Отмена"),
                fg_color="transparent",
                hover_color=COLORS['surface_light'],
                text_color=COLORS['text_secondary'],
                font=("Segoe UI", 13),
                width=100,
                height=35,
                command=self.cancel
            )
            cancel_btn.pack(side="left", padx=(0, 10))
            
            delete_btn = ctk.CTkButton(
                buttons_frame,
                text=t("ui.launcher.button.delete", default="Удалить"),
                fg_color="#ef4444",
                hover_color="#dc2626",
                text_color="white",
                font=("Segoe UI", 13, "bold"),
                width=100,
                height=35,
                command=self.confirm
            )
            delete_btn.pack(side="left")
            
            # Модальность
            self.transient(parent)
            self.grab_set()
            self.lift()
            self.focus_force()
            self.bind("<Escape>", lambda e: self.cancel())
            
            # Центрируем и показываем
            self.after(50, self._center_and_show)
            
            # Фокус на кнопке отмены (безопаснее)
            self.after(200, lambda: cancel_btn.focus())
        
        def _center_and_show(self):
            """Центрирует окно и делает его видимым"""
            try:
                self.update_idletasks()
                try:
                    px = self.parent_window.winfo_x()
                    py = self.parent_window.winfo_y()
                    pw = self.parent_window.winfo_width()
                    ph = self.parent_window.winfo_height()
                    x = px + (pw - 420) // 2
                    y = py + (ph - 180) // 2
                except:
                    sw = self.winfo_screenwidth()
                    sh = self.winfo_screenheight()
                    x = (sw - 420) // 2
                    y = (sh - 180) // 2
                
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                x = max(0, min(x, sw - 420))
                y = max(0, min(y, sh - 180))
                
                self.geometry(f"420x180+{x}+{y}")
                self.deiconify()
                self.lift()
                self.focus_force()
            except:
                try:
                    self.deiconify()
                    self.lift()
                except:
                    pass
        
        def confirm(self):
            """Подтверждение удаления"""
            self.result = True
            self.destroy()
        
        def cancel(self):
            """Отмена"""
            self.result = False
            self.destroy()
        
        def get_result(self):
            """Возвращает True если подтверждено, False если отменено"""
            self.wait_window()
            return self.result
    
    class ModernDialog(ctk.CTkToplevel):
        """Универсальный диалог в стиле лаунчера"""
        
        def __init__(self, parent, title="", message="", dialog_type="info", width=420, height=180):
            super().__init__(parent)
            self.result = None
            self.parent_window = parent
            self.dialog_width = width
            self.dialog_height = height
            
            # Убираем Windows рамки
            self.overrideredirect(True)
            
            # Устанавливаем размер сразу
            self.geometry(f"{width}x{height}")
            
            # Делаем окно поверх всех
            self.attributes("-topmost", True)
            
            # Цвета для типов
            type_config = {
                "info": (COLORS['primary'], "ℹ️"),
                "success": (COLORS['success'], "✅"),
                "warning": ("#f59e0b", "⚠️"),
                "error": (COLORS['danger'], "❌"),
                "question": (COLORS['secondary'], "❓"),
            }
            self.accent_color, icon = type_config.get(dialog_type, type_config["info"])
            
            self.configure(fg_color="transparent")
            
            # Рамка с закруглением
            outer = ctk.CTkFrame(self, fg_color=self.accent_color, corner_radius=16)
            outer.pack(fill="both", expand=True, padx=2, pady=2)
            
            inner = ctk.CTkFrame(outer, fg_color=COLORS['surface'], corner_radius=14)
            inner.pack(fill="both", expand=True, padx=2, pady=2)
            inner.grid_columnconfigure(0, weight=1)
            
            # Header
            header = ctk.CTkFrame(inner, fg_color="transparent")
            header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
            header.grid_columnconfigure(1, weight=1)
            
            ctk.CTkLabel(header, text=icon, font=("Segoe UI", 24), text_color=self.accent_color).grid(row=0, column=0, padx=(0, 12))
            ctk.CTkLabel(header, text=title, font=("Segoe UI", 16, "bold"), text_color=COLORS['text'], anchor="w").grid(row=0, column=1, sticky="w")
            
            ctk.CTkButton(
                header, text="✕", width=28, height=28,
                fg_color="transparent", hover_color=COLORS['surface_light'],
                text_color=COLORS['text_muted'], font=("Segoe UI", 14),
                corner_radius=6, command=self._close
            ).grid(row=0, column=2)
            
            # Message
            msg_frame = ctk.CTkFrame(inner, fg_color="transparent")
            msg_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=12)
            inner.grid_rowconfigure(1, weight=1)
            
            ctk.CTkLabel(
                msg_frame, text=message, font=("Segoe UI", 13),
                text_color=COLORS['text_secondary'], wraplength=width - 60,
                justify="left", anchor="nw"
            ).pack(fill="both", expand=True)
            
            # Buttons
            self.buttons_frame = ctk.CTkFrame(inner, fg_color="transparent")
            self.buttons_frame.grid(row=2, column=0, sticky="e", padx=20, pady=(0, 16))
            
            # Модальность и фокус
            self.transient(parent)
            self.grab_set()
            self.lift()
            self.focus_force()
            self.bind("<Escape>", lambda e: self._close())
            
            # Центрируем и показываем после создания всех виджетов
            self.after(50, self._center_and_show)
        
        def _center_and_show(self):
            """Центрирует окно и делает его видимым"""
            try:
                self.update_idletasks()
                
                # Получаем размеры родительского окна
                try:
                    px = self.parent_window.winfo_x()
                    py = self.parent_window.winfo_y()
                    pw = self.parent_window.winfo_width()
                    ph = self.parent_window.winfo_height()
                except:
                    # Если не удалось получить размеры родителя, центрируем на экране
                    sw = self.winfo_screenwidth()
                    sh = self.winfo_screenheight()
                    x = (sw - self.dialog_width) // 2
                    y = (sh - self.dialog_height) // 2
                    self.geometry(f"{self.dialog_width}x{self.dialog_height}+{x}+{y}")
                    self.deiconify()
                    return
                
                # Центрируем относительно родителя
                x = px + (pw - self.dialog_width) // 2
                y = py + (ph - self.dialog_height) // 2
                
                # Не выходим за границы экрана
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                x = max(0, min(x, sw - self.dialog_width))
                y = max(0, min(y, sh - self.dialog_height))
                
                self.geometry(f"{self.dialog_width}x{self.dialog_height}+{x}+{y}")
                self.deiconify()  # Убеждаемся, что окно видимо
                self.lift()  # Поднимаем наверх
                self.focus_force()  # Устанавливаем фокус
            except Exception as e:
                # В случае ошибки просто показываем окно
                try:
                    self.deiconify()
                    self.lift()
                except:
                    pass
        
        def _close(self):
            self.result = False
            self.destroy()
        
        def add_button(self, text, command, primary=False, danger=False):
            fg = COLORS['danger'] if danger else (self.accent_color if primary else "transparent")
            hover = "#dc2626" if danger else (COLORS['primary_hover'] if primary else COLORS['surface_light'])
            btn = ctk.CTkButton(
                self.buttons_frame, text=text, width=100, height=36,
                fg_color=fg, hover_color=hover,
                text_color="white" if (primary or danger) else COLORS['text_secondary'],
                font=("Segoe UI", 12, "bold") if (primary or danger) else ("Segoe UI", 12),
                corner_radius=8, command=command
            )
            btn.pack(side="left", padx=(8, 0))
            return btn
        
        def wait_result(self):
            self.wait_window()
            return self.result
    
    def show_info(self, title, message):
        """Информационный диалог"""
        dialog = self.ModernDialog(self, title, message, "info")
        dialog.add_button("OK", lambda: [setattr(dialog, 'result', True), dialog.destroy()], primary=True)
        return dialog.wait_result()
    
    def show_success(self, title, message):
        """Диалог успеха"""
        dialog = self.ModernDialog(self, title, message, "success")
        dialog.add_button("OK", lambda: [setattr(dialog, 'result', True), dialog.destroy()], primary=True)
        return dialog.wait_result()
    
    def show_warning(self, title, message):
        """Предупреждение"""
        dialog = self.ModernDialog(self, title, message, "warning", height=200)
        dialog.add_button("OK", lambda: [setattr(dialog, 'result', True), dialog.destroy()], primary=True)
        return dialog.wait_result()
    
    def show_error(self, title, message):
        """Ошибка"""
        dialog = self.ModernDialog(self, title, message, "error", height=200)
        dialog.add_button("OK", lambda: [setattr(dialog, 'result', True), dialog.destroy()], danger=True)
        return dialog.wait_result()
    
    def show_confirm(self, title, message, yes_text="Да", no_text="Отмена", danger=False):
        """Диалог подтверждения"""
        dialog = self.ModernDialog(self, title, message, "error" if danger else "question", height=200)
        dialog.add_button(no_text, lambda: [setattr(dialog, 'result', False), dialog.destroy()])
        dialog.add_button(yes_text, lambda: [setattr(dialog, 'result', True), dialog.destroy()], danger=danger, primary=not danger)
        return dialog.wait_result()
    
    def create_analytics_page(self):
        """Создает страницу аналитики с графиками и статистикой"""
        frame = ctk.CTkFrame(self.content_frame, fg_color=COLORS['bg'])
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Header with title and update check
        header = ctk.CTkFrame(frame, fg_color="transparent", height=70)
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 20))
        header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            header,
            text="📈 " + t("ui.launcher.analytics", default="Аналитика"),
            font=("Segoe UI", 32, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, sticky="w")
        
        # Version and update check
        update_frame = ctk.CTkFrame(header, fg_color="transparent")
        update_frame.grid(row=0, column=1, sticky="e")
        
        version_text = self.updater.get_current_version() if self.updater else "v1.0.0"
        self.version_label = ctk.CTkLabel(
            update_frame,
            text=f"Версия: {version_text}",
            font=("Segoe UI", 11),
            text_color=COLORS['text_muted']
        )
        self.version_label.pack(side="left", padx=(0, 12))
        
        self.update_btn = ctk.CTkButton(
            update_frame,
            text="🔄 Проверить обновления",
            font=("Segoe UI", 12),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            text_color="white",
            width=200,
            height=36,
            corner_radius=8,
            command=self._check_for_updates
        )
        self.update_btn.pack(side="left")
        
        # Main content
        content = ctk.CTkScrollableFrame(frame, fg_color=COLORS['bg'])
        content.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        content.grid_columnconfigure(0, weight=1)
        
        # Get stats
        stats = self.analytics.get_stats() if self.analytics else {}
        
        # Stats cards in 2x2 grid
        stats_container = ctk.CTkFrame(content, fg_color="transparent")
        stats_container.pack(fill="x", pady=(0, 16))
        stats_container.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        stat_cards = [
            ("📝", "Постов", stats.get('posts_total', 0), stats.get('posts_today', 0), COLORS['primary']),
            ("🤖", "Текст", stats.get('text_generations_total', 0), stats.get('text_generations_today', 0), COLORS['success']),
            ("🎨", "Картинки", stats.get('image_generations_total', 0), stats.get('image_generations_today', 0), COLORS['warning']),
            ("✏️", "Правки", stats.get('manual_edits_total', 0), 0, COLORS['secondary']),
        ]
        
        for idx, (icon, title, total, today, color) in enumerate(stat_cards):
            card = ctk.CTkFrame(stats_container, fg_color=COLORS['surface'], corner_radius=12)
            card.grid(row=0, column=idx, sticky="nsew", padx=6, pady=6)
            
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=16, pady=16)
            
            # Icon and value row
            top_row = ctk.CTkFrame(inner, fg_color="transparent")
            top_row.pack(fill="x")
            
            ctk.CTkLabel(
                top_row,
                text=icon,
                font=("Segoe UI", 24),
                text_color=color
            ).pack(side="left")
            
            ctk.CTkLabel(
                top_row,
                text=str(total),
                font=("Segoe UI", 24, "bold"),
                text_color=COLORS['text']
            ).pack(side="right")
            
            # Title and today
            ctk.CTkLabel(
                inner,
                text=title,
                font=("Segoe UI", 12),
                text_color=COLORS['text_secondary'],
                anchor="w"
            ).pack(fill="x", pady=(8, 0))
            
            if today > 0:
                ctk.CTkLabel(
                    inner,
                    text=f"+{today} сегодня",
                    font=("Segoe UI", 10),
                    text_color=COLORS['success'],
                    anchor="w"
                ).pack(fill="x")
        
        # Two column layout for rest
        two_col = ctk.CTkFrame(content, fg_color="transparent")
        two_col.pack(fill="both", expand=True, pady=(0, 16))
        two_col.grid_columnconfigure((0, 1), weight=1)
        two_col.grid_rowconfigure(0, weight=1)
        
        # Left: Activity chart
        chart_card = ctk.CTkFrame(two_col, fg_color=COLORS['surface'], corner_radius=12)
        chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        
        ctk.CTkLabel(
            chart_card,
            text="📊 Активность (7 дней)",
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS['text'],
            anchor="w"
        ).pack(fill="x", padx=16, pady=(16, 12))
        
        # Chart data
        chart_data = self.analytics.get_chart_data(7) if self.analytics else {"dates": [], "posts": [], "text_generations": [], "image_generations": []}
        dates = chart_data.get('dates', [])
        posts = chart_data.get('posts', [])
        text_gens = chart_data.get('text_generations', [])
        img_gens = chart_data.get('image_generations', [])
        
        # Calculate max for scaling
        all_vals = posts + text_gens + img_gens
        max_val = max(all_vals) if all_vals and max(all_vals) > 0 else 1
        
        chart_inner = ctk.CTkFrame(chart_card, fg_color=COLORS['bg'], corner_radius=8)
        chart_inner.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        
        if dates:
            for i, date in enumerate(dates):
                row = ctk.CTkFrame(chart_inner, fg_color="transparent", height=28)
                row.pack(fill="x", padx=12, pady=2)
                row.pack_propagate(False)
                
                # Date label
                ctk.CTkLabel(
                    row,
                    text=date,
                    font=("Consolas", 10),
                    text_color=COLORS['text_muted'],
                    width=45,
                    anchor="w"
                ).pack(side="left")
                
                # Bars container
                bars = ctk.CTkFrame(row, fg_color="transparent")
                bars.pack(side="left", fill="x", expand=True, padx=8)
                
                p = posts[i] if i < len(posts) else 0
                t_val = text_gens[i] if i < len(text_gens) else 0
                im = img_gens[i] if i < len(img_gens) else 0
                
                # Create stacked horizontal bars
                bar_frame = ctk.CTkFrame(bars, fg_color=COLORS['surface_light'], height=16, corner_radius=4)
                bar_frame.pack(fill="x", pady=4)
                bar_frame.pack_propagate(False)
                
                total_width = 300  # Base width for calculations
                if p > 0:
                    w = max(int((p / max_val) * total_width), 8)
                    ctk.CTkFrame(bar_frame, fg_color=COLORS['primary'], width=w, corner_radius=4).pack(side="left", fill="y")
                if t_val > 0:
                    w = max(int((t_val / max_val) * total_width), 8)
                    ctk.CTkFrame(bar_frame, fg_color=COLORS['success'], width=w, corner_radius=4).pack(side="left", fill="y", padx=(1, 0))
                if im > 0:
                    w = max(int((im / max_val) * total_width), 8)
                    ctk.CTkFrame(bar_frame, fg_color=COLORS['warning'], width=w, corner_radius=4).pack(side="left", fill="y", padx=(1, 0))
                
                # Values
                ctk.CTkLabel(
                    row,
                    text=f"{p}/{t_val}/{im}",
                    font=("Consolas", 9),
                    text_color=COLORS['text_muted'],
                    width=50,
                    anchor="e"
                ).pack(side="right")
        else:
            ctk.CTkLabel(
                chart_inner,
                text="Нет данных",
                font=("Segoe UI", 12),
                text_color=COLORS['text_muted']
            ).pack(expand=True, pady=30)
        
        # Legend
        legend = ctk.CTkFrame(chart_card, fg_color="transparent")
        legend.pack(fill="x", padx=16, pady=(0, 12))
        
        for color, name in [(COLORS['primary'], "Посты"), (COLORS['success'], "Текст"), (COLORS['warning'], "Картинки")]:
            item = ctk.CTkFrame(legend, fg_color="transparent")
            item.pack(side="left", padx=(0, 16))
            ctk.CTkFrame(item, fg_color=color, width=10, height=10, corner_radius=2).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(item, text=name, font=("Segoe UI", 10), text_color=COLORS['text_muted']).pack(side="left")
        
        # Right: Hotkeys + Info
        right_col = ctk.CTkFrame(two_col, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        right_col.grid_rowconfigure(1, weight=1)
        
        # Hotkeys card
        hotkeys_card = ctk.CTkFrame(right_col, fg_color=COLORS['surface'], corner_radius=12)
        hotkeys_card.pack(fill="x", pady=(0, 12))
        
        ctk.CTkLabel(
            hotkeys_card,
            text="⌨️ Горячие клавиши",
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS['text'],
            anchor="w"
        ).pack(fill="x", padx=16, pady=(16, 12))
        
        hotkeys = [
            ("Ctrl+S", "Сохранить"),
            ("Ctrl+1-4", "Вкладки"),
            ("F5", "Обновить модели"),
            ("Ctrl+R", "Перезагрузить"),
        ]
        
        for key, desc in hotkeys:
            hk_row = ctk.CTkFrame(hotkeys_card, fg_color="transparent")
            hk_row.pack(fill="x", padx=16, pady=3)
            
            ctk.CTkLabel(
                hk_row,
                text=key,
                font=("Consolas", 11, "bold"),
                text_color=COLORS['primary'],
                width=80,
                anchor="w"
            ).pack(side="left")
            
            ctk.CTkLabel(
                hk_row,
                text=desc,
                font=("Segoe UI", 11),
                text_color=COLORS['text_secondary']
            ).pack(side="left")
        
        ctk.CTkFrame(hotkeys_card, fg_color="transparent", height=12).pack()
        
        # Topics stats card
        topics_card = ctk.CTkFrame(right_col, fg_color=COLORS['surface'], corner_radius=12)
        topics_card.pack(fill="both", expand=True)
        
        ctk.CTkLabel(
            topics_card,
            text="📁 По темам",
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS['text'],
            anchor="w"
        ).pack(fill="x", padx=16, pady=(16, 12))
        
        topics_data = stats.get('posts_by_topic', {})
        if topics_data:
            for topic, count in sorted(topics_data.items(), key=lambda x: x[1], reverse=True)[:5]:
                t_row = ctk.CTkFrame(topics_card, fg_color="transparent")
                t_row.pack(fill="x", padx=16, pady=3)
                
                ctk.CTkLabel(
                    t_row,
                    text=topic[:20] + "..." if len(topic) > 20 else topic,
                    font=("Segoe UI", 11),
                    text_color=COLORS['text'],
                    anchor="w"
                ).pack(side="left", fill="x", expand=True)
                
                ctk.CTkLabel(
                    t_row,
                    text=str(count),
                    font=("Segoe UI", 11, "bold"),
                    text_color=COLORS['primary']
                ).pack(side="right")
        else:
            ctk.CTkLabel(
                topics_card,
                text="Нет данных",
                font=("Segoe UI", 11),
                text_color=COLORS['text_muted']
            ).pack(pady=20)
        
        ctk.CTkFrame(topics_card, fg_color="transparent", height=12).pack()
        
        return frame
        
        # Topics stats
        topics_card = self.create_glass_card(content, fg_color=COLORS['surface'])
        topics_card.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            topics_card,
            text="📁 " + t("ui.launcher.analytics.by_topic", default="По темам"),
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['text']
        ).pack(anchor="w", padx=20, pady=(20, 16))
        
        topics_data = stats.get('posts_by_topic', {})
        if topics_data:
            for topic, count in sorted(topics_data.items(), key=lambda x: x[1], reverse=True)[:10]:
                topic_row = ctk.CTkFrame(topics_card, fg_color="transparent")
                topic_row.pack(fill="x", padx=20, pady=4)
                
                ctk.CTkLabel(
                    topic_row,
                    text=topic,
                    font=("Segoe UI", 13),
                    text_color=COLORS['text']
                ).pack(side="left")
                
                ctk.CTkLabel(
                    topic_row,
                    text=str(count),
                    font=("Segoe UI", 13, "bold"),
                    text_color=COLORS['primary']
                ).pack(side="right")
        else:
            ctk.CTkLabel(
                topics_card,
                text=t("ui.launcher.analytics.no_data", default="Нет данных"),
                font=("Segoe UI", 13),
                text_color=COLORS['text_muted']
            ).pack(padx=20, pady=(0, 20))
        
        ctk.CTkFrame(topics_card, fg_color="transparent", height=20).pack()
        
        # Hotkeys info
        hotkeys_card = self.create_glass_card(content, fg_color=COLORS['surface'])
        hotkeys_card.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            hotkeys_card,
            text="⌨️ " + t("ui.launcher.analytics.hotkeys", default="Горячие клавиши"),
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['text']
        ).pack(anchor="w", padx=20, pady=(20, 16))
        
        hotkeys = [
            ("Ctrl+S", t("ui.launcher.hotkey.save", default="Сохранить настройки")),
            ("Ctrl+1/2/3/4", t("ui.launcher.hotkey.switch_tab", default="Переключить вкладку")),
            ("F5", t("ui.launcher.hotkey.refresh", default="Обновить список моделей")),
            ("Ctrl+R", t("ui.launcher.hotkey.reload", default="Перезагрузить интерфейс")),
        ]
        
        for key, desc in hotkeys:
            hk_row = ctk.CTkFrame(hotkeys_card, fg_color="transparent")
            hk_row.pack(fill="x", padx=20, pady=4)
            
            ctk.CTkLabel(
                hk_row,
                text=key,
                font=("Consolas", 12, "bold"),
                text_color=COLORS['primary'],
                width=100,
                anchor="w"
            ).pack(side="left")
            
            ctk.CTkLabel(
                hk_row,
                text=desc,
                font=("Segoe UI", 12),
                text_color=COLORS['text_secondary']
            ).pack(side="left")
        
        ctk.CTkFrame(hotkeys_card, fg_color="transparent", height=20).pack()
        
        return frame
    
    def _check_for_updates(self):
        """Проверяет наличие обновлений"""
        if not self.updater:
            return
        
        self.update_btn.configure(text="🔄 Проверка...", state="disabled")
        
        def on_check_complete(available, info):
            def update_ui():
                if available:
                    self.update_btn.configure(
                        text="📥 Скачать обновление",
                        state="normal",
                        fg_color=COLORS['success'],
                        hover_color="#059669",
                        command=self._download_update
                    )
                    if info:
                        self.version_label.configure(
                            text=f"Доступно: {info.get('commit', '?')[:7]}",
                            text_color=COLORS['success']
                        )
                else:
                    self.update_btn.configure(
                        text="✅ Актуальная версия",
                        state="normal",
                        fg_color=COLORS['surface_light']
                    )
            self.after(0, update_ui)
        
        self.updater.check_for_updates(callback=on_check_complete)
    
    def _download_update(self):
        """Скачивает и устанавливает обновление"""
        if not self.updater:
            return
        
        # Create progress dialog
        progress_dialog = ctk.CTkToplevel(self)
        progress_dialog.title(t("ui.launcher.update.downloading", default="Загрузка обновления"))
        progress_dialog.geometry("400x200")
        progress_dialog.transient(self)
        progress_dialog.grab_set()
        progress_dialog.configure(fg_color=COLORS['surface'])
        
        # Center dialog
        progress_dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 100
        progress_dialog.geometry(f"400x200+{x}+{y}")
        
        ctk.CTkLabel(
            progress_dialog,
            text="📥 " + t("ui.launcher.update.in_progress", default="Загрузка обновления..."),
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS['text']
        ).pack(pady=(30, 20))
        
        progress_bar = ctk.CTkProgressBar(progress_dialog, width=300)
        progress_bar.pack(pady=10)
        progress_bar.set(0)
        
        status_label = ctk.CTkLabel(
            progress_dialog,
            text="Подготовка...",
            font=("Segoe UI", 12),
            text_color=COLORS['text_secondary']
        )
        status_label.pack(pady=10)
        
        def on_progress(percent, status):
            def update():
                progress_bar.set(percent / 100)
                status_label.configure(text=status)
            self.after(0, update)
        
        def on_complete(success, message):
            def update():
                progress_dialog.destroy()
                if success:
                    self.show_success(
                        t("ui.launcher.update.complete", default="Обновление завершено"),
                        message + "\n\nПерезапустите приложение для применения изменений."
                    )
                else:
                    self.show_error(
                        t("ui.launcher.update.error", default="Ошибка обновления"),
                        f"Ошибка: {message}"
                    )
            self.after(0, update)
        
        self.updater.download_update(progress_callback=on_progress, complete_callback=on_complete)
    
    def _update_topic_highlight(self):
        """Обновляет только подсветку активной темы без полной перерисовки"""
        if not hasattr(self, 'scroll_topics'):
            return
        
        # Проходим по всем существующим кнопкам тем и обновляем их стиль
        for child in self.scroll_topics.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                # Собираем все кнопки в фрейме
                topic_btn = None
                delete_btn = None
                
                for widget in child.winfo_children():
                    if isinstance(widget, ctk.CTkButton):
                        btn_text = widget.cget("text")
                        if btn_text.startswith("📂 "):
                            topic_btn = widget
                        elif btn_text == "×":
                            delete_btn = widget
                
                # Обновляем кнопку темы
                if topic_btn:
                    topic_name = topic_btn.cget("text")[2:]  # Убираем "📂 "
                    is_active = (topic_name == self.current_topic)
                    
                    topic_btn.configure(
                        fg_color=COLORS['primary'] if is_active else COLORS['surface_light'],
                        text_color="white" if is_active else COLORS['text_secondary'],
                        hover_color=COLORS['primary_hover'] if is_active else COLORS['surface']
                    )
                    
                    # Показываем/скрываем кнопку удаления
                    if delete_btn:
                        if is_active:
                            delete_btn.grid()
                        else:
                            delete_btn.grid_remove()
    
    def refresh_topics(self):
        """Обновляет только список тем (полная перерисовка)"""
        if not hasattr(self, 'scroll_topics'):
            return
            
        for w in self.scroll_topics.winfo_children():
                w.destroy()
        
        try:
            if os.path.exists(FILE_CHANNELS):
                with open(FILE_CHANNELS, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}
        
        topics = list(data.keys())
        
        if topics and (not self.current_topic or self.current_topic not in topics):
            self.current_topic = topics[0]
        if not topics:
            self.current_topic = None
        
        # Draw topics
        for idx, t in enumerate(topics):
            is_active = (t == self.current_topic)
            
            # Фрейм для кнопки темы и кнопки удаления
            topic_frame = ctk.CTkFrame(self.scroll_topics, fg_color="transparent")
            topic_frame.grid(row=idx, column=0, sticky="ew", padx=4, pady=4)
            topic_frame.grid_columnconfigure(0, weight=1)
            
            # Сохраняем название темы в фрейме для drag-and-drop
            topic_frame.topic_name = t
            
            # Кнопка темы с drag-and-drop
            btn = ctk.CTkButton(
                topic_frame,
                text=f"📂 {t}",
                fg_color=COLORS['primary'] if is_active else COLORS['surface_light'],
                text_color="white" if is_active else COLORS['text_secondary'],
                anchor="w",
                hover_color=COLORS['primary_hover'] if is_active else COLORS['surface'],
                command=lambda tp=t: self.select_topic(tp),
                font=("Segoe UI", 14),
                height=45,
                corner_radius=8
            )
            btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
            
            # Добавляем drag-and-drop обработчики к кнопке
            btn.bind("<Button-1>", lambda e, tp=t: self._on_topic_drag_start(e, tp))
            btn.bind("<B1-Motion>", lambda e, tp=t: self._on_topic_drag(e, tp))
            btn.bind("<ButtonRelease-1>", lambda e, tp=t: self._on_topic_drag_stop(e, tp))
            
            # Кнопка удаления (создаем для всех тем, но показываем только для активной)
            delete_btn = ctk.CTkButton(
                topic_frame,
                text="×",
                width=40,
                height=45,
                fg_color=COLORS['danger'],
                hover_color="#dc2626",
                text_color="white",
                font=("Segoe UI", 20, "bold"),
                corner_radius=8,
                command=lambda tp=t: self.delete_topic(tp)
            )
            if is_active:
                delete_btn.grid(row=0, column=1, sticky="e")
            else:
                delete_btn.grid(row=0, column=1, sticky="e")
                delete_btn.grid_remove()  # Скрываем для неактивных тем
            
            # Add Windows-style hover animation for delete topic button
            if self.animations_enabled:
                try:
                    button_hover_effect(delete_btn, hover_color="#dc2626", normal_color=COLORS['danger'], duration=100)
                except:
                    pass
    
    def refresh_channels_only(self):
        """Обновляет только список каналов (плавно)"""
        # Очищаем старые каналы
        if hasattr(self, 'scroll_chans'):
            for w in self.scroll_chans.winfo_children():
                w.destroy()
        
        # Небольшая задержка для плавности перед отрисовкой новых
        self.after(50, self._draw_channels)
    
    def _draw_channels(self):
        """Рисует каналы для текущей темы"""
        if not hasattr(self, 'scroll_chans'):
            return
            
        try:
            if os.path.exists(FILE_CHANNELS):
                with open(FILE_CHANNELS, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}
        
        topics = list(data.keys())
        
        # Обновляем заголовок темы
        if hasattr(self, 'topic_title_label'):
            if self.current_topic:
                self.topic_title_label.configure(text=self.current_topic)
            else:
                self.topic_title_label.configure(text=t("ui.launcher.channels.select_topic", default="Выберите тему"))
        
        # Проверяем наличие каналов в выбранной теме
        has_channels = False
        if self.current_topic and self.current_topic in data:
            channels = data[self.current_topic]
            has_channels = len(channels) > 0
        
        # Draw channels или Empty State
        if not topics:
            # Нет тем вообще
            self._show_empty_state(
                icon="📁",
                title=t("ui.launcher.channels.create_topic_first", default="Создайте тему для начала"),
                subtitle=""
            )
        elif not self.current_topic:
            # Тема не выбрана
            self._show_empty_state(
                icon="📂",
                title=t("ui.launcher.channels.select_topic", default="Выберите тему"),
                subtitle=""
            )
        elif not has_channels:
            # Тема выбрана, но каналов нет - показываем Empty State
            self._show_empty_state(
                icon="📭",
                title=t("ui.launcher.channels.no_channels_in_topic", default="В этой теме пока нет каналов"),
                subtitle=t("ui.launcher.channels.add_channel_hint", default="Добавьте канал через поле сверху")
            )
        else:
            # Есть каналы - показываем список
            for idx, ch in enumerate(data[self.current_topic]):
                self.draw_channel_card(ch, idx)
        
        # Обновляем прокрутку после отрисовки
        self.after(100, self._update_channels_scrollbar)
    
    def _on_channels_frame_configure(self, event):
        """Обновляет область прокрутки при изменении размера фрейма"""
        self.channels_canvas.configure(scrollregion=self.channels_canvas.bbox("all"))
    
    def _on_channels_canvas_configure(self, event):
        """Обновляет ширину фрейма при изменении размера canvas"""
        canvas_width = event.width
        self.channels_canvas.itemconfig(self.channels_canvas_window, width=canvas_width)
    
    def _update_channels_scrollbar(self):
        """Обновляет видимость scrollbar в зависимости от количества контента"""
        if not hasattr(self, 'channels_canvas') or not hasattr(self, 'scroll_chans'):
            return
        
        try:
            # Обновляем scrollregion
            self.channels_canvas.update_idletasks()
            self.channels_canvas.configure(scrollregion=self.channels_canvas.bbox("all"))
            
            # Проверяем, нужна ли прокрутка
            canvas_height = self.channels_canvas.winfo_height()
            frame_height = self.scroll_chans.winfo_reqheight()
            
            if frame_height > canvas_height:
                # Нужна прокрутка - показываем scrollbar
                self.channels_scrollbar.grid()
                self.channels_canvas.configure(yscrollcommand=self.channels_scrollbar.set)
            else:
                # Прокрутка не нужна - скрываем scrollbar
                self.channels_scrollbar.grid_remove()
                self.channels_canvas.configure(yscrollcommand=None)
        except:
            pass
    
    def _show_empty_state(self, icon, title, subtitle=""):
        """Показывает красивое пустое состояние (Empty State)"""
        # Очищаем все виджеты
        for widget in self.scroll_chans.winfo_children():
            widget.destroy()
        
        # Контейнер для центрирования
        empty_container = ctk.CTkFrame(self.scroll_chans, fg_color="transparent")
        empty_container.grid(row=0, column=0, sticky="", pady=100)
        empty_container.grid_columnconfigure(0, weight=1)
        
        # Большая иконка
        icon_label = ctk.CTkLabel(
            empty_container,
            text=icon,
            font=("Segoe UI", 80),
            text_color=COLORS['text_muted'],
            fg_color="transparent"
        )
        icon_label.grid(row=0, column=0, pady=(0, 20))
        
        # Основной текст
        title_label = ctk.CTkLabel(
            empty_container,
            text=title,
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['text_secondary'],
            fg_color="transparent"
        )
        title_label.grid(row=1, column=0, pady=(0, 8))
        
        # Подсказка (если есть)
        if subtitle:
            subtitle_label = ctk.CTkLabel(
                empty_container,
                text=subtitle,
                font=("Segoe UI", 13),
                text_color=COLORS['text_muted'],
                fg_color="transparent"
            )
            subtitle_label.grid(row=2, column=0)
        
        # Обновляем прокрутку - скрываем, так как контента мало
        self.after(100, self._update_channels_scrollbar)
    
    def refresh_channels(self):
        """Полное обновление (темы + каналы)"""
        self.refresh_topics()
        self.refresh_channels_only()
    
    def select_topic(self, t):
        """Выбирает тему и обновляет только каналы"""
        if self.current_topic == t:
            return  # Уже выбрана эта тема
        
        self.current_topic = t
        # Обновляем только подсветку активной темы (без полной перерисовки)
        self._update_topic_highlight()
        # Обновляем каналы
        self.refresh_channels_only()
    
    def new_topic(self):
        dialog = self.ModernInputDialog(
            self,
            title=t("ui.launcher.channels.new_topic_title", default="Создать новую тему"),
            placeholder=t("ui.launcher.channels.new_topic_dialog", default="Название...")
        )
        topic = dialog.get_input()
        if topic:
            try:
                with open(FILE_CHANNELS, 'r', encoding='utf-8') as f:
                    db = json.load(f)
                if topic.strip() not in db:
                    db[topic.strip()] = []
                    with open(FILE_CHANNELS, 'w', encoding='utf-8') as f:
                        json.dump(db, f, indent=4, ensure_ascii=False)
                    self.current_topic = topic.strip()
                    self.refresh_channels()  # Полное обновление, так как добавлена новая тема
            except:
                pass
    
    def delete_topic(self, topic):
        """Удаляет тему с подтверждением и показом количества каналов"""
        try:
            # Загружаем данные для подсчета каналов
            if os.path.exists(FILE_CHANNELS):
                with open(FILE_CHANNELS, 'r', encoding='utf-8') as f:
                    db = json.load(f)
            else:
                db = {}
            
            # Подсчитываем количество каналов в теме
            channel_count = 0
            if topic in db:
                channel_count = len(db[topic])
            
            # Формируем сообщение подтверждения
            if channel_count > 0:
                # Есть каналы - показываем предупреждение с количеством
                message = t(
                    "ui.launcher.channels.delete_topic_with_channels",
                    default="Вы уверены, что хотите удалить тему '{topic}' и все {count} каналов внутри?\n\nЭто действие нельзя отменить!",
                    topic=topic,
                    count=channel_count
                )
            else:
                # Нет каналов - простое подтверждение
                message = t(
                    "ui.launcher.channels.delete_topic_confirm",
                    default="Удалить тему '{topic}'?",
                    topic=topic
                )
            
            # Показываем кастомное модальное окно подтверждения
            dialog = self.ModernConfirmDialog(
                self,
                message=message,
                title=t("ui.launcher.confirm.title", default="Подтверждение удаления")
            )
            if dialog.get_result():
                # Пользователь подтвердил - удаляем
                if topic in db:
                    del db[topic]
                    # Если файл стал пустым, удаляем его
                    if not db:
                        os.remove(FILE_CHANNELS)
                    else:
                        with open(FILE_CHANNELS, 'w', encoding='utf-8') as f:
                            json.dump(db, f, indent=4, ensure_ascii=False)
                    
                    # Обновляем текущую тему
                    if self.current_topic == topic:
                        self.current_topic = None
                        # Выбираем первую доступную тему, если есть
                        remaining_topics = list(db.keys())
                        if remaining_topics:
                            self.current_topic = remaining_topics[0]
                    
                    self.refresh_channels()  # Полное обновление, так как тема удалена
        except Exception as e:
            self.log(f"❌ Ошибка при удалении темы: {e}", "SYSTEM")
    
    def draw_channel_card(self, link, row_idx=0):
        """Создает карточку канала в современном стиле с иконками"""
        from functools import partial
        
        # Сохраняем оригинальный link
        original_link = link
        clean = link.replace("https://t.me/", "").replace("@", "").strip()
        display_name = clean if clean else link
        username = f"@{clean}" if clean else link
        
        # Создаем карточку
        card = ctk.CTkFrame(self.scroll_chans, fg_color=COLORS['card_bg'], corner_radius=12)
        card.grid(row=row_idx, column=0, sticky="ew", pady=8, padx=0)
        card.grid_columnconfigure(1, weight=1)
        
        # Аватарка/Иконка канала (слева)
        avatar_frame = ctk.CTkFrame(card, fg_color=COLORS['primary'], width=48, height=48, corner_radius=24)
        avatar_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)
        avatar_frame.grid_propagate(False)
        ctk.CTkLabel(
            avatar_frame,
            text="📢",
            font=("Segoe UI", 24),
            text_color="white"
        ).pack(expand=True)
        
        # Центральная часть: Название и username
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="w", padx=(0, 16), pady=12)
        
        name_label = ctk.CTkLabel(
            info_frame,
            text=display_name,
            font=("Segoe UI", 15, "bold"),
            text_color=COLORS['text'],
            anchor="w"
        )
        name_label.pack(anchor="w")
        
        username_label = ctk.CTkLabel(
            info_frame,
            text=username,
            font=("Segoe UI", 12),
            text_color=COLORS['text_muted'],
            anchor="w"
        )
        username_label.pack(anchor="w")
        
        # Правая часть: Иконки действий
        actions_frame = ctk.CTkFrame(card, fg_color="transparent")
        actions_frame.grid(row=0, column=2, sticky="e", padx=(0, 16), pady=12)
        
        # Иконка "Ссылка" (открыть)
        def open_channel(channel_link=original_link):
            clean_link = channel_link.replace("https://t.me/", "").replace("@", "").strip()
            webbrowser.open(f"https://t.me/{clean_link}")
        
        open_btn = ctk.CTkButton(
            actions_frame,
            text="🔗",
            width=40,
            height=40,
            fg_color="transparent",
            hover_color=COLORS['surface_light'],
            font=("Segoe UI", 18),
            corner_radius=8,
            command=open_channel
        )
        open_btn.pack(side="left", padx=4)
        
        # Add Windows-style hover animation for open button
        if self.animations_enabled:
            try:
                button_hover_effect(open_btn, hover_color=COLORS['surface_light'], normal_color="transparent", duration=100)
            except:
                pass
        
        # Иконка "Корзина" (удалить, красная при наведении)
        delete_handler = partial(self.delete_channel, original_link)
        delete_btn = ctk.CTkButton(
            actions_frame,
            text="🗑️",
            width=40,
            height=40,
            fg_color="transparent",
            hover_color=COLORS['danger'],
            font=("Segoe UI", 18),
            corner_radius=8,
            command=delete_handler
        )
        delete_btn.pack(side="left", padx=4)
        
        # Add Windows-style hover animation for delete button
        if self.animations_enabled:
            try:
                button_hover_effect(delete_btn, hover_color=COLORS['danger'], normal_color="transparent", duration=100)
            except:
                pass
    
    def add_channel(self):
        if not self.current_topic:
            return
        txt = self.entry_chan.get().strip().replace("https://t.me/", "").replace("@", "")
        if not txt:
            return
        try:
            # Создаем файл channels.json при первом добавлении канала, если его нет
            if not os.path.exists(FILE_CHANNELS):
                db = {self.current_topic: []}
            else:
                with open(FILE_CHANNELS, 'r', encoding='utf-8') as f:
                    db = json.load(f)
            # Убеждаемся, что тема существует
            if self.current_topic not in db:
                db[self.current_topic] = []
            if txt not in db[self.current_topic]:
                db[self.current_topic].append(txt)
                with open(FILE_CHANNELS, 'w', encoding='utf-8') as f:
                    json.dump(db, f, indent=4, ensure_ascii=False)
            self.entry_chan.delete(0, "end")
            self.refresh_channels_only()  # Только каналы, тема не изменилась
        except:
            pass
    
    def delete_channel(self, link):
        try:
            if not os.path.exists(FILE_CHANNELS):
                return
            with open(FILE_CHANNELS, 'r', encoding='utf-8') as f:
                db = json.load(f)
            if self.current_topic in db:
                # Нормализуем входной link
                clean_input = link.replace("https://t.me/", "").replace("@", "").strip()
                
                # Ищем и удаляем канал в любом формате
                channels = db[self.current_topic]
                found = False
                for i, ch in enumerate(channels):
                    # Нормализуем канал из базы
                    clean_ch = str(ch).replace("https://t.me/", "").replace("@", "").strip()
                    if clean_ch == clean_input or ch == link or ch == clean_input:
                        db[self.current_topic].pop(i)
                        found = True
                        break
                
                if found:
                    # Если список каналов стал пустым, удаляем тему, а если тем не осталось - удаляем файл
                    topic_was_deleted = False
                    if not db[self.current_topic]:
                        del db[self.current_topic]
                        topic_was_deleted = True
                        # Обновляем текущую тему
                        remaining_topics = list(db.keys())
                        if remaining_topics:
                            self.current_topic = remaining_topics[0]
                        else:
                            self.current_topic = None
                    
                    if not db:
                        os.remove(FILE_CHANNELS)
                    else:
                        with open(FILE_CHANNELS, 'w', encoding='utf-8') as f:
                            json.dump(db, f, indent=4, ensure_ascii=False)
                    
                    # Если тема была удалена - полное обновление, иначе только каналы
                    if topic_was_deleted:
                        self.refresh_channels()  # Полное обновление, так как тема удалена
                    else:
                        self.refresh_channels_only()  # Только каналы, тема не изменилась
        except Exception as e:
            self.log(f"❌ [CHANNELS] Ошибка при удалении канала: {e}", "SYSTEM")
    
    
    # SETTINGS
    
    def scan_llm_models(self):
        """Сканирует и обновляет списки моделей с glassmorphism дизайном"""
        if self.model_manager is None:
            self._init_managers()
        
        if hasattr(self, 'ollama_models_frame'):
            for widget in self.ollama_models_frame.winfo_children():
                widget.destroy()
            
            ollama_models = self.model_manager.get_ollama_models()
            if ollama_models:
                for model in ollama_models:
                    model_row = self.create_model_row(
                        self.ollama_models_frame,
                        model,
                        "🧠",
                        lambda m=model: self._select_model_for_use({'name': m, 'type': 'ollama'}),
                        lambda m=model: self._delete_ollama_model(m)
                    )
                    model_row.pack(fill="x", pady=6, padx=4)
            else:
                empty_frame = ctk.CTkFrame(self.ollama_models_frame, fg_color="transparent")
                empty_frame.pack(fill="x", pady=40)
                ctk.CTkLabel(
                    empty_frame,
                    text=t("ui.launcher.model.ollama_not_found", default="Модели не найдены"),
                    font=("Segoe UI", 13),
                    text_color=COLORS['text_muted']
                ).pack()
        
        if hasattr(self, 'gguf_models_frame'):
            for widget in self.gguf_models_frame.winfo_children():
                widget.destroy()
            
            gguf_models = self.model_manager.get_gguf_models()
            if gguf_models:
                for model_info in gguf_models:
                    model_row = self.create_model_row(
                        self.gguf_models_frame,
                        model_info['name'],
                        "📄",
                        lambda m=model_info: self._select_model_for_use(m),
                        lambda m=model_info: self._delete_gguf_model(m)
                    )
                    model_row.pack(fill="x", pady=6, padx=4)
            else:
                empty_frame = ctk.CTkFrame(self.gguf_models_frame, fg_color="transparent")
                empty_frame.pack(fill="x", pady=40)
                ctk.CTkLabel(
                    empty_frame,
                    text=t("ui.launcher.model.gguf_not_found", default="GGUF файлы не найдены"),
                    font=("Segoe UI", 13),
                    text_color=COLORS['text_muted']
                ).pack()
    
    def create_model_row(self, parent, model_name, icon, select_callback, delete_callback):
        """Создает красивую строку модели с glassmorphism эффектом"""
        row = self.create_glass_card(parent, fg_color=COLORS['surface_light'], corner_radius=12)
        row.grid_columnconfigure(1, weight=1)
        
        left_frame = ctk.CTkFrame(row, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="w", padx=16, pady=12)
        
        icon_label = ctk.CTkLabel(
            left_frame,
            text=icon,
            font=("Segoe UI", 20),
            text_color=COLORS['primary']
        )
        icon_label.pack(side="left", padx=(0, 12))
        
        name_label = ctk.CTkLabel(
            left_frame,
            text=model_name,
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS['text']
        )
        name_label.pack(side="left")
        
        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e", padx=16, pady=12)
        
        # Check if model is currently selected
        selected_model = self._get_llm_model_from_settings()
        is_active = selected_model and selected_model.get('name') == model_name
        
        if is_active:
            select_btn = ctk.CTkButton(
                btn_frame,
                text="✓ Активно",
                width=100,
                height=32,
                command=select_callback,
                fg_color=COLORS['success'],
                hover_color="#059669",
                font=("Segoe UI", 12, "bold"),
                corner_radius=8
            )
        else:
            select_btn = ctk.CTkButton(
                btn_frame,
                text="✓ Выбрать",
                width=100,
                height=32,
                command=select_callback,
                fg_color=COLORS['primary'],
                hover_color=COLORS['primary_hover'],
                font=("Segoe UI", 12, "bold"),
                corner_radius=8
            )
        select_btn.pack(side="left", padx=(0, 8))
        
        delete_btn = ctk.CTkButton(
            btn_frame,
            text="🗑️",
            width=36,
            height=32,
            command=delete_callback,
            fg_color=COLORS['danger'],
            hover_color="#dc2626",
            font=("Segoe UI", 12),
            corner_radius=8
        )
        delete_btn.pack(side="left")
        
        return row
    
    def _show_save_indicator(self, text="✅ Сохранено"):
        """Показывает анимированный индикатор сохранения"""
        if not hasattr(self, 'save_indicator'):
            return
        
        try:
            self.save_indicator.configure(text=text, text_color=COLORS['success'])
            
            # Fade out after 2 seconds
            def fade_out():
                try:
                    self.save_indicator.configure(text="")
                except:
                    pass
            
            self.after(2000, fade_out)
        except:
            pass
    
    def _auto_save_settings(self):
        """Автоматически сохраняет настройки с индикатором"""
        try:
            from dotenv import set_key  # type: ignore
            
            # Сохраняем entries
            for k, e in self.entries.items():
                try:
                    set_key(FILE_ENV, k, e.get().strip())
                except:
                    pass
            
            # Сохраняем debug режим
            if hasattr(self, 'debug_mode'):
                set_key(FILE_ENV, "DEBUG_MODE", "true" if self.debug_mode.get() else "false")
            
            # Сохраняем путь к папке с моделями
            if hasattr(self, 'models_dir_entry'):
                models_path = self.models_dir_entry.get().strip()
                if models_path and os.path.exists(models_path):
                    set_key(FILE_ENV, "MODELS_LLM_DIR", models_path)
                    global MODELS_LLM_DIR
                    MODELS_LLM_DIR = models_path
            
            # Сохраняем URL модели SD
            if hasattr(self, 'sd_model_url_entry'):
                model_url = self.sd_model_url_entry.get().strip()
                if model_url:
                    set_key(FILE_ENV, "SD_MODEL_URL", model_url)
            
            # Показываем индикатор
            self._show_save_indicator()
        except Exception as e:
            self.log(f"❌ [SETTINGS] Ошибка автосохранения: {e}", "SYSTEM")
    
    def _save_generation_config(self):
        """Сохраняет конфигурацию генерации"""
        try:
            gen_config = {}
            
            # LLM settings
            if hasattr(self, 'llm_temp_var'):
                gen_config['llm_temp'] = float(self.llm_temp_var.get())
            if hasattr(self, 'llm_ctx_var'):
                try:
                    gen_config['llm_ctx'] = int(self.llm_ctx_var.get())
                except:
                    gen_config['llm_ctx'] = 4096
            
            # SD settings
            if hasattr(self, 'sd_steps_var'):
                gen_config['sd_steps'] = int(self.sd_steps_var.get())
            if hasattr(self, 'sd_cfg_var'):
                gen_config['sd_cfg'] = float(self.sd_cfg_var.get())
            if hasattr(self, 'sd_width_var'):
                try:
                    gen_config['sd_width'] = int(self.sd_width_var.get())
                except:
                    gen_config['sd_width'] = 1024
            if hasattr(self, 'sd_height_var'):
                try:
                    gen_config['sd_height'] = int(self.sd_height_var.get())
                except:
                    gen_config['sd_height'] = 1152
            if hasattr(self, 'sd_sampler_var'):
                gen_config['sd_sampler'] = self.sd_sampler_var.get()
            if hasattr(self, 'sd_scheduler_var'):
                gen_config['sd_scheduler'] = self.sd_scheduler_var.get()
            
            # Сохраняем в файл
            with open(FILE_GEN_CONFIG, 'w', encoding='utf-8') as f:
                json.dump(gen_config, f, indent=4, ensure_ascii=False)
            
            # Показываем индикатор
            self._show_save_indicator()
        except Exception as e:
            self.log(f"❌ [SETTINGS] Ошибка сохранения конфигурации: {e}", "SYSTEM")
    
    def save_settings(self):
        # Создаем резервную копию перед сохранением
        self._create_backup()
        
        for k, e in self.entries.items():
            set_key(FILE_ENV, k, e.get().strip())
        
        # Сохраняем путь к папке с моделями
        if hasattr(self, 'models_dir_entry'):
            models_path = self.models_dir_entry.get().strip()
            if models_path and os.path.exists(models_path):
                set_key(FILE_ENV, "MODELS_LLM_DIR", models_path)
                # Обновляем глобальную переменную
                global MODELS_LLM_DIR
                MODELS_LLM_DIR = models_path
                # Обновляем список моделей
                self.scan_llm_models()
                self.log(t("ui.launcher.log.settings_models_folder_updated", default="✅ [SETTINGS] Папка с моделями обновлена: {path}", path=models_path), "SETTINGS")
            else:
                self.log(t("ui.launcher.log.settings_models_folder_not_exists", default="⚠️ [SETTINGS] Указанная папка не существует: {path}", path=models_path), "SETTINGS")
        
        # Сохраняем debug режим
        set_key(FILE_ENV, "DEBUG_MODE", "true" if self.debug_mode.get() else "false")
        
        # Сохраняем язык
        if hasattr(self, 'language_var'):
            lang_value = self.language_var.get()
            lang_code = lang_value.split(' - ')[0] if ' - ' in lang_value else lang_value
            set_key(FILE_ENV, "LANGUAGE", lang_code)
            self.current_language = lang_code
        
        # Сохраняем URL модели SD
        if hasattr(self, 'sd_model_url_entry'):
            model_url = self.sd_model_url_entry.get().strip()
            if model_url:
                set_key(FILE_ENV, "SD_MODEL_URL", model_url)
                self.log(t("ui.launcher.log.settings_sd_model_url_saved", default="✅ [SETTINGS] URL модели SD сохранен"), "SETTINGS")
        
        self.show_success(t("ui.launcher.success.title", default="Успешно"), t("ui.launcher.settings.saved", default="Настройки сохранены"))
    
    def _create_backup(self):
        """Создает резервную копию конфигурационных файлов"""
        try:
            import datetime
            backup_dir = os.path.join(DATA_ROOT, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Копируем важные файлы
            files_to_backup = [
                (FILE_ENV, "env"),
                (FILE_CHANNELS, "channels"),
                (FILE_GEN_CONFIG, "gen_config")
            ]
            
            for file_path, prefix in files_to_backup:
                if os.path.exists(file_path):
                    backup_name = f"{prefix}_{timestamp}.backup"
                    backup_path = os.path.join(backup_dir, backup_name)
                    shutil.copy2(file_path, backup_path)
            
            # Удаляем старые резервные копии (оставляем последние 10)
            self._cleanup_old_backups(backup_dir)
            
        except Exception as e:
            # Не критично, просто логируем
            if hasattr(self, 'log'):
                self.log(t("ui.launcher.log.backup_failed", default="⚠️ [BACKUP] Не удалось создать резервную копию: {error}", error=str(e)), "SYSTEM")
    
    def _cleanup_old_backups(self, backup_dir, keep_count=10):
        """Удаляет старые резервные копии, оставляя только последние"""
        try:
            backups = []
            for f in os.listdir(backup_dir):
                if f.endswith(".backup"):
                    file_path = os.path.join(backup_dir, f)
                    backups.append((os.path.getmtime(file_path), file_path))
            
            # Сортируем по времени (новые первыми)
            backups.sort(reverse=True)
            
            # Удаляем старые
            for _, file_path in backups[keep_count:]:
                try:
                    os.remove(file_path)
                except:
                    pass
        except:
            pass
    
    
    # MONITORING
    
    def start_monitor(self):
        threading.Thread(target=self._monitor_loop, daemon=True).start()
    
    def _monitor_loop(self):
        try:
            last_net = psutil.net_io_counters().bytes_recv
            last_disk = psutil.disk_io_counters().read_bytes + psutil.disk_io_counters().write_bytes
        except:
            return
        
        while True:
            time.sleep(1)
            try:
                # Добавляем защиту от зависания при вызове psutil
                curr_net = psutil.net_io_counters().bytes_recv
                disk = psutil.disk_io_counters()
                curr_disk = disk.read_bytes + disk.write_bytes
                
                ns = (curr_net - last_net) / 1024 / 1024
                ds = (curr_disk - last_disk) / 1024 / 1024
                
                net_label = getattr(self, 'lbl_net', None)
                disk_label = getattr(self, 'lbl_disk', None)
                self.safe_widget_configure(net_label, text=t("ui.launcher.monitoring.network", default="🌐 Сеть: {speed} МБ/с", speed=f"{ns:.1f}"))
                self.safe_widget_configure(disk_label, text=t("ui.launcher.monitoring.disk", default="💾 Диск: {speed} МБ/с", speed=f"{ds:.1f}"))
                
                last_net = curr_net
                last_disk = curr_disk
            except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
                # Игнорируем ошибки доступа или отсутствия процессов
                pass
            except:
                # Для других ошибок делаем паузу перед повтором
                time.sleep(5)
    
    
    # CONSOLE
    
    def log(self, txt, tab="BOT"):
        """Логирование сообщений в консоль с фильтрацией"""
        if not txt:
            return
        
        try:
            # Фильтрация пустых строк и пробелов
            txt_stripped = txt.strip()
            if not txt_stripped or txt_stripped == "\n":
                return
            
            # Быстрая фильтрация через lower() один раз
            txt_lower = txt.lower()
            
            # Фильтруем по паттернам
            if any(pattern in txt_lower for pattern in LOG_SKIP_PATTERNS):
                return
            
            # Фильтруем прогресс-бары (строки с процентами и барами)
            if ("%" in txt and "|" in txt) or txt.strip().startswith(("0%", "1%", "2%", "3%", "4%", "5%", "6%", "7%", "8%", "9%")):
                # Проверяем, не является ли это важным сообщением
                if not any(keyword in txt_lower for keyword in ["error", "warning", "failed", "success", "complete"]):
                    return
            
            # Фильтруем строки только с техническими данными (только цифры, проценты, скобки)
            if len(txt_stripped) < 10 and all(c in "0123456789%|[]()/\\-:., " for c in txt_stripped):
                return
            
            # Маппинг на названия вкладок
            target_tab = LOG_TAB_MAP.get(tab, "Бот")
            
            # Записываем в конкретную вкладку (без префикса)
            self.log_queue.put((txt, target_tab))
            
            # Записываем в общую вкладку (с префиксом)
            prefix = LOG_PREFIX_MAP.get(target_tab, "📝")
            self.log_queue.put((f"{prefix} {txt}", "Все"))
            
        except Exception as e:
            import sys
            print(f"[LOG ERROR] {e}", file=sys.stderr, flush=True)

    def clear_console(self):
        """Очищает все консоли"""
        for console in self.consoles.values():
            try:
                console.configure(state="normal")
                console.delete("1.0", "end")
            except (AttributeError, tk.TclError):
                pass
    
    def setup_console_context_menu(self, textbox):
        """Добавляет контекстное меню для копирования текста как в Windows"""
        try:
            from .console_manager import ConsoleManager
        except (ImportError, ValueError):
            try:
                from console_manager import ConsoleManager
            except ImportError:
                # Если ConsoleManager не найден, используем встроенное меню
                def show_context_menu(event):
                    try:
                        try:
                            if textbox.tag_ranges("sel"):
                                selected = textbox.get("sel.first", "sel.last")
                            else:
                                selected = None
                        except:
                            selected = None
                        menu = tk.Menu(self, tearoff=0, bg=COLORS['card_bg'], fg=COLORS['text'],
                              activebackground=COLORS['primary'], activeforeground='white',
                              font=("Segoe UI", 10))
                        if selected:
                            menu.add_command(label=t("ui.launcher.console.copy", default="Копировать"), command=lambda: self.copy_selected(textbox))
                        else:
                            menu.add_command(label=t("ui.launcher.console.copy_all", default="Копировать всё"), command=lambda: self.copy_all_to_clipboard(textbox))
                        menu.add_separator()
                        menu.add_command(label=t("ui.launcher.console.select_all", default="Выделить всё"), command=lambda: self.select_all(textbox))
                        menu.add_separator()
                        menu.add_command(label=t("ui.launcher.console.clear", default="Очистить"), command=lambda: self.clear_single_console(textbox))
                        menu.tk_popup(event.x_root, event.y_root)
                    except:
                        pass
                textbox.bind("<Button-3>", show_context_menu)
                textbox.bind("<Control-c>", lambda e: (self.copy_selected(textbox), "break"))
                textbox.bind("<Control-a>", lambda e: (self.select_all(textbox), "break"))
                textbox.bind("<Control-x>", lambda e: (self.cut_selected(textbox), "break"))
                textbox.bind("<Control-v>", lambda e: (self.paste_to_console(textbox), "break"))
                textbox.bind("<Button-1>", lambda e: textbox.focus_set())
                return
        
        # Если ConsoleManager найден, используем его
        if not hasattr(self, '_console_manager'):
            self._console_manager = ConsoleManager(self)
        self._console_manager.setup_console_context_menu(textbox)
    
    def copy_to_clipboard(self, text):
        """Копирует текст в буфер обмена"""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
        except:
            pass
    
    def copy_all_to_clipboard(self, textbox):
        """Копирует весь текст из консоли"""
        if hasattr(self, '_console_manager'):
            self._console_manager.copy_all_to_clipboard(textbox)
        else:
            try:
                text = textbox.get("1.0", "end-1c")
                self.clipboard_clear()
                self.clipboard_append(text)
            except:
                pass
    
    def copy_selected(self, textbox):
        """Копирует выделенный текст"""
        if hasattr(self, '_console_manager'):
            return self._console_manager.copy_selected(textbox)
        else:
            try:
                if textbox.tag_ranges("sel"):
                    selected = textbox.get("sel.first", "sel.last")
                    if selected:
                        self.clipboard_clear()
                        self.clipboard_append(selected)
                        return True
            except:
                pass
            return False
    
    def cut_selected(self, textbox):
        """Вырезает выделенный текст"""
        if hasattr(self, '_console_manager'):
            return self._console_manager.cut_selected(textbox)
        else:
            try:
                if textbox.tag_ranges("sel"):
                    selected = textbox.get("sel.first", "sel.last")
                    if selected:
                        self.clipboard_clear()
                        self.clipboard_append(selected)
                        textbox.configure(state="normal")
                        textbox.delete("sel.first", "sel.last")
                        textbox.configure(state="normal")
                        return True
            except:
                pass
            return False
    
    def paste_to_console(self, textbox):
        """Вставляет текст из буфера обмена"""
        if hasattr(self, '_console_manager'):
            return self._console_manager.paste_to_console(textbox)
        else:
            try:
                textbox.configure(state="normal")
                clipboard_text = self.clipboard_get()
                if clipboard_text:
                    textbox.insert("insert", clipboard_text)
                textbox.configure(state="normal")
                return True
            except:
                pass
            return False
    
    def select_all(self, textbox):
        """Выделяет весь текст"""
        if hasattr(self, '_console_manager'):
            self._console_manager.select_all(textbox)
        else:
            try:
                textbox.configure(state="normal")
                textbox.tag_add("sel", "1.0", "end")
                textbox.mark_set("insert", "1.0")
                textbox.see("1.0")
                textbox.configure(state="normal")
            except:
                pass
    
    def clear_single_console(self, textbox):
        """Очищает одну консоль"""
        if hasattr(self, '_console_manager'):
            self._console_manager.clear_single_console(textbox)
        else:
            try:
                textbox.configure(state="normal")
                textbox.delete("1.0", "end")
                textbox.configure(state="normal")
            except:
                pass

    def console_loop(self):
        """Оптимизированный цикл обработки логов"""
        batch_size = 10  # Обрабатываем по 10 сообщений за раз
        processed = 0
        
        while not self.log_queue.empty() and processed < batch_size:
            try:
                txt, tab = self.log_queue.get_nowait()
                console = self.consoles.get(tab)
                
                if console:
                    console.configure(state="normal")
                    console.insert("end", f"{txt}\n")
                    # Автопрокрутка только для активной вкладки
                    if getattr(self, 'current_console_tab', None) == tab:
                        console.see("end")
                processed += 1
            except (KeyError, AttributeError):
                break
        
        self.after(50, self.console_loop)
    
    
    # CLEANUP
    
    def on_close(self):
        """Обработчик закрытия окна - останавливает сервисы и очищает ресурсы"""
        # Отключаем обработчик, чтобы избежать повторных вызовов
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        
        def cleanup_and_close():
            try:
                # Останавливаем все сервисы в фоне (не блокируем UI)
                if self.service_manager and hasattr(self.service_manager, 'procs'):
                    for name in ["bot", "llm", "sd"]:
                        if self.service_manager.procs.get(name):
                            try:
                                # Останавливаем асинхронно, не ждем завершения
                                threading.Thread(
                                    target=self.service_manager.stop_service,
                                    args=(name,),
                                    daemon=True
                                ).start()
                            except:
                                pass
        
                # Убиваем процессы Ollama в фоне
                if self.installer:
                    try:
                        threading.Thread(
                            target=self.installer.kill_all_ollama_processes,
                            daemon=True
                        ).start()
                    except:
                        pass
                
                # Удаляем PID файл
                try:
                    if os.path.exists(FILE_PID):
                        os.remove(FILE_PID)
                except:
                    pass
                
                # Закрываем окно немедленно
                self.after(0, self.destroy)
            except:
                # Принудительно закрываем даже при ошибке
                try:
                    self.after(0, self.destroy)
                except:
                    pass
        
        # Запускаем очистку в отдельном потоке и сразу закрываем окно
        threading.Thread(target=cleanup_and_close, daemon=True).start()
        self.after(100, self.destroy)  # Закрываем через 100мс, давая время на инициализацию очистки
    
    
    def _delete_ollama(self):
        """Удаляет Ollama и все связанные файлы"""
        # Спрашиваем, сохранять ли модели
        save_models = self.show_confirm(
            t("ui.launcher.delete.ollama_save_models_title", default="Сохранение моделей"),
            t("ui.launcher.delete.ollama_save_models_message", default="Сохранить импортированные модели Ollama перед удалением?\n\n• Да - модели будут сохранены и восстановлены при следующей установке\n• Нет - все будет удалено полностью"),
            yes_text="Сохранить", no_text="Удалить всё"
        )
        
        # Подтверждение удаления
        models_text = t("ui.launcher.delete.models_saved", default="• Модели будут сохранены\n") if save_models else t("ui.launcher.delete.all_files_deleted", default="• Все импортированные модели\n")
        result = self.show_confirm(
            t("ui.launcher.delete.ollama_confirm_title", default="Подтверждение удаления"),
            t("ui.launcher.delete.ollama_confirm_message", default="Вы уверены, что хотите удалить Ollama?\n\nЭто действие удалит:\n• Ollama сервер (ollama.exe)\n{models_text}• Все данные Ollama\n\nЭто действие нельзя отменить!", models_text=models_text),
            yes_text="Удалить", danger=True
        )
        
        if not result:
            return
        
        try:
            self.log(t("ui.launcher.log.llm_deletion_start", default="🗑️ [LLM] Начало удаления Ollama..."), "LLM")
            
            # Останавливаем LLM сервис если он запущен
            if self.service_manager.procs.get("llm"):
                self.log(t("ui.launcher.log.llm_stopping_service", default="⏹️ [LLM] Остановка LLM сервиса..."), "LLM")
                self.service_manager.stop_service("llm")
                time.sleep(2)  # Даем время на остановку
            
            # Убиваем все процессы Ollama
            killed = self.installer.kill_all_ollama_processes()
            if killed > 0:
                time.sleep(1)  # Даем время на завершение процессов
            
            # Сохраняем модели если нужно
            models_backup_path = None
            if save_models and os.path.exists(OLLAMA_MODELS_DIR):
                try:
                    models_backup_path = os.path.join(DIR_TEMP, "ollama_models_backup")
                    os.makedirs(DIR_TEMP, exist_ok=True)
                    
                    # Удаляем старый бэкап если есть
                    if os.path.exists(models_backup_path):
                        shutil.rmtree(models_backup_path, ignore_errors=True)
                    
                    self.log(t("ui.launcher.log.llm_saving_models", default="💾 [LLM] Сохранение моделей в: {path}", path=models_backup_path), "LLM")
                    shutil.copytree(OLLAMA_MODELS_DIR, models_backup_path)
                    
                    # Подсчитываем размер сохраненных моделей
                    models_size = 0
                    for root, dirs, files in os.walk(models_backup_path):
                        for f in files:
                            try:
                                models_size += os.path.getsize(os.path.join(root, f))
                            except:
                                pass
                    
                    if models_size > 0:
                        size_mb = models_size / 1024 / 1024
                        if size_mb > 1024:
                            size_gb = size_mb / 1024
                            self.log(t("ui.launcher.log.llm_models_saved_gb", default="💾 [LLM] Сохранено моделей: {size} GB", size=f"{size_gb:.2f}"), "LLM")
                        else:
                            self.log(t("ui.launcher.log.llm_models_saved_mb", default="💾 [LLM] Сохранено моделей: {size} MB", size=f"{size_mb:.2f}"), "LLM")
                except Exception as e:
                    self.log(t("ui.launcher.log.llm_models_save_failed", default="⚠️ [LLM] Не удалось сохранить модели: {error}", error=str(e)), "LLM")
                    models_backup_path = None
            
            # Удаляем Ollama через официальный деинсталлятор
            ollama_install_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama")
            uninstaller_path = os.path.join(ollama_install_path, "unins000.exe")
            
            deleted_size = 0
            
            # Проверяем наличие официального деинсталлятора
            if os.path.exists(uninstaller_path):
                self.log(t("ui.launcher.log.llm_uninstaller_deleting", default="🗑️ [LLM] Удаление Ollama через официальный деинсталлятор..."), "LLM")
                
                # Подсчитываем размер перед удалением
                try:
                    for root, dirs, files in os.walk(ollama_install_path):
                        for f in files:
                            try:
                                fp = os.path.join(root, f)
                                deleted_size += os.path.getsize(fp)
                            except:
                                pass
                except:
                    pass
                
                # Запускаем деинсталлятор в тихом режиме
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    
                    proc = subprocess.Popen(
                        [uninstaller_path, "/SILENT", "/NORESTART"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        startupinfo=startupinfo,
                        shell=False
                    )
                    
                    self.log(t("ui.launcher.log.llm_waiting_uninstall", default="⏳ [LLM] Ожидание завершения деинсталляции..."), "LLM")
                    proc.wait(timeout=120)  # Максимум 2 минуты
                    
                    if proc.returncode == 0:
                        self.log(t("ui.launcher.log.llm_uninstalled_success", default="✅ [LLM] Ollama успешно удален через деинсталлятор"), "LLM")
                    else:
                        self.log(t("ui.launcher.log.llm_uninstaller_exit_code", default="⚠️ [LLM] Деинсталлятор завершился с кодом: {code}", code=proc.returncode), "LLM")
                    
                    # Ждем немного, чтобы файлы точно были удалены
                    time.sleep(2)
                    
                except subprocess.TimeoutExpired:
                    self.log(t("ui.launcher.log.llm_uninstall_timeout", default="⚠️ [LLM] Деинсталляция занимает слишком много времени..."), "LLM")
                    proc.kill()
                except Exception as e:
                    self.log(t("ui.launcher.log.llm_uninstaller_error", default="❌ [LLM] Ошибка при запуске деинсталлятора: {error}", error=str(e)), "LLM")
                    self.show_error(
                        t("ui.launcher.delete.error", default="Ошибка удаления"),
                        t("ui.launcher.delete.ollama_installer_error", default="Не удалось запустить деинсталлятор Ollama:\n{error}\n\nПопробуйте удалить вручную через Панель управления.", error=str(e))
                    )
                    return
            else:
                # Если деинсталлятор не найден, удаляем рабочую папку
                if os.path.exists(OLLAMA_DIR):
                    self.log(t("ui.launcher.log.llm_uninstaller_not_found", default="🗑️ [LLM] Деинсталлятор не найден, удаление рабочей папки: {path}", path=OLLAMA_DIR), "LLM")
                    
                    # Подсчитываем размер перед удалением
                    try:
                        for root, dirs, files in os.walk(OLLAMA_DIR):
                            for f in files:
                                try:
                                    fp = os.path.join(root, f)
                                    deleted_size += os.path.getsize(fp)
                                except:
                                    pass
                    except:
                        pass
                    
                    # Удаляем папку
                    try:
                        shutil.rmtree(OLLAMA_DIR, ignore_errors=True)
                        self.log(t("ui.launcher.log.llm_folder_deleted", default="✅ [LLM] Рабочая папка Ollama успешно удалена"), "LLM")
                    except Exception as e:
                        self.log(t("ui.launcher.log.llm_folder_delete_error", default="❌ [LLM] Ошибка при удалении папки: {error}", error=str(e)), "LLM")
                        self.show_error(
                            t("ui.launcher.delete.error", default="Ошибка удаления"),
                            t("ui.launcher.delete.ollama_folder_error", default="Не удалось удалить папку Ollama:\n{error}\n\nПопробуйте удалить вручную:\n{path}", error=str(e), path=OLLAMA_DIR)
                        )
                        return
                else:
                    self.log(t("ui.launcher.log.llm_folder_not_found", default="ℹ️ [LLM] Папка Ollama не найдена"), "LLM")
            
            # Показываем размер удаленных файлов
            if deleted_size > 0:
                size_mb = deleted_size / 1024 / 1024
                if size_mb > 1024:
                    size_gb = size_mb / 1024
                    self.log(t("ui.launcher.log.llm_space_freed_gb", default="📊 [LLM] Освобождено места: {size} GB", size=f"{size_gb:.2f}"), "LLM")
                else:
                    self.log(t("ui.launcher.log.llm_space_freed_mb", default="📊 [LLM] Освобождено места: {size} MB", size=f"{size_mb:.2f}"), "LLM")
            
            # Удаляем рабочую папку OLLAMA_DIR (если она существует отдельно)
            if os.path.exists(OLLAMA_DIR) and OLLAMA_DIR != ollama_install_path:
                try:
                    self.log(t("ui.launcher.log.llm_deleting_folder", default="🗑️ [LLM] Удаление рабочей папки: {path}", path=OLLAMA_DIR), "LLM")
                    shutil.rmtree(OLLAMA_DIR, ignore_errors=True)
                    self.log(t("ui.launcher.log.llm_folder_deleted_simple", default="✅ [LLM] Рабочая папка удалена"), "LLM")
                except Exception as e:
                    self.log(t("ui.launcher.log.llm_folder_delete_failed", default="⚠️ [LLM] Не удалось удалить рабочую папку: {error}", error=str(e)), "LLM")
            
            # Восстанавливаем модели если они были сохранены
            if models_backup_path and os.path.exists(models_backup_path):
                try:
                    # Создаем папку для моделей
                    os.makedirs(OLLAMA_MODELS_DIR, exist_ok=True)
                    
                    # Копируем модели обратно
                    self.log(t("ui.launcher.log.llm_restoring_models", default="📦 [LLM] Восстановление моделей..."), "LLM")
                    for item in os.listdir(models_backup_path):
                        src = os.path.join(models_backup_path, item)
                        dst = os.path.join(OLLAMA_MODELS_DIR, item)
                        if os.path.isdir(src):
                            shutil.copytree(src, dst, dirs_exist_ok=True)
                        else:
                            shutil.copy2(src, dst)
                    
                    self.log(t("ui.launcher.log.llm_models_restored", default="✅ [LLM] Модели успешно восстановлены"), "LLM")
                except Exception as e:
                    self.log(t("ui.launcher.log.llm_models_restore_failed", default="⚠️ [LLM] Не удалось восстановить модели: {error}", error=str(e)), "LLM")
            
            # Обновляем статус сервиса
            self._set_service_indicator("llm", COLORS['text_muted'])
            self._set_service_button("llm", text="▶", fg_color=COLORS['primary'])
            self._set_service_status_label("llm", text=t("ui.launcher.status.stopped", default="Остановлен"), color=COLORS['text_muted'])
            
            success_msg = t("ui.launcher.delete.ollama_success", default="Ollama успешно удален!\n\n")
            if save_models and models_backup_path and os.path.exists(models_backup_path):
                success_msg += t("ui.launcher.delete.models_saved", default="Модели сохранены и будут восстановлены при следующей установке.\n")
            else:
                success_msg += t("ui.launcher.delete.all_files_deleted", default="Все файлы и данные были удалены.\n")
            success_msg += t("ui.launcher.delete.ollama_will_reinstall", default="При следующем запуске LLM сервиса Ollama будет загружен заново.")
            
            self.show_success(t("ui.launcher.delete.complete", default="Удаление завершено"), success_msg)
            
        except Exception as e:
            self.log(t("ui.launcher.log.llm_deletion_error", default="❌ [LLM] Ошибка при удалении Ollama: {error}", error=str(e)), "LLM")
            self.show_error(
                t("ui.launcher.error.title", default="Ошибка"),
                t("ui.launcher.delete.ollama_error", default="Ошибка удаления: {error}", error=str(e))
            )
    
    def _delete_sd(self):
        """Удаляет Stable Diffusion и все связанные файлы"""
        # Спрашиваем, сохранять ли модели
        save_models = self.show_confirm(
            t("ui.launcher.delete.sd_save_models_title", default="Сохранение моделей"),
            t("ui.launcher.delete.sd_save_models_message", default="Сохранить модели изображений перед удалением?\n\n• Да - модели будут сохранены и восстановлены при следующей установке\n• Нет - все будет удалено полностью"),
            yes_text="Сохранить", no_text="Удалить всё"
        )
        
        # Подтверждение удаления
        models_text = t("ui.launcher.delete.models_saved", default="• Модели будут сохранены\n") if save_models else t("ui.launcher.delete.all_files_deleted", default="• Все модели изображений\n")
        result = self.show_confirm(
            t("ui.launcher.delete.sd_confirm_title", default="Подтверждение удаления"),
            t("ui.launcher.delete.sd_confirm_message", default="Вы уверены, что хотите удалить Stable Diffusion?\n\nЭто действие удалит:\n• Stable Diffusion WebUI (весь репозиторий)\n{models_text}• Все расширения (включая ADetailer)\n• Виртуальное окружение Python\n• Все настройки и конфигурации\n\nЭто действие нельзя отменить!", models_text=models_text),
            yes_text="Удалить", danger=True
        )
        
        if not result:
            return
        
        try:
            self.log(t("ui.launcher.log.sd_deletion_start", default="🗑️ [SD] Начало удаления Stable Diffusion..."), "SD")
            
            # Останавливаем SD сервис если он запущен
            if self.service_manager.procs.get("sd"):
                self.log(t("ui.launcher.log.sd_stopping_service", default="⏹️ [SD] Остановка SD сервиса..."), "SD")
                self.service_manager.stop_service("sd")
                time.sleep(2)  # Даем время на остановку
            
            # Убиваем все процессы SD (python с launch.py)
            killed = self._kill_all_sd_processes()
            if killed > 0:
                time.sleep(1)  # Даем время на завершение процессов
            
            # Сохраняем модели если нужно
            models_backup_path = None
            if save_models and os.path.exists(MODELS_SD_DIR):
                try:
                    models_backup_path = os.path.join(DIR_TEMP, "sd_models_backup")
                    os.makedirs(DIR_TEMP, exist_ok=True)
                    
                    # Удаляем старый бэкап если есть
                    if os.path.exists(models_backup_path):
                        shutil.rmtree(models_backup_path, ignore_errors=True)
                    
                    self.log(t("ui.launcher.log.sd_saving_models", default="💾 [SD] Сохранение моделей в: {path}", path=models_backup_path), "SD")
                    shutil.copytree(MODELS_SD_DIR, models_backup_path)
                    
                    # Подсчитываем размер сохраненных моделей
                    models_size = 0
                    for root, dirs, files in os.walk(models_backup_path):
                        for f in files:
                            try:
                                models_size += os.path.getsize(os.path.join(root, f))
                            except:
                                pass
                    
                    if models_size > 0:
                        size_mb = models_size / 1024 / 1024
                        if size_mb > 1024:
                            size_gb = size_mb / 1024
                            self.log(t("ui.launcher.log.sd_models_saved_gb", default="💾 [SD] Сохранено моделей: {size} GB", size=f"{size_gb:.2f}"), "SD")
                        else:
                            self.log(t("ui.launcher.log.sd_models_saved_mb", default="💾 [SD] Сохранено моделей: {size} MB", size=f"{size_mb:.2f}"), "SD")
                except Exception as e:
                    self.log(t("ui.launcher.log.sd_models_save_failed", default="⚠️ [SD] Не удалось сохранить модели: {error}", error=str(e)), "SD")
                    models_backup_path = None
            
            # Удаляем папку SD
            deleted_size = 0
            if os.path.exists(SD_DIR):
                self.log(t("ui.launcher.log.sd_deleting_folder", default="🗑️ [SD] Удаление папки Stable Diffusion: {path}", path=SD_DIR), "SD")
                
                # Подсчитываем размер перед удалением
                try:
                    for root, dirs, files in os.walk(SD_DIR):
                        for f in files:
                            try:
                                fp = os.path.join(root, f)
                                deleted_size += os.path.getsize(fp)
                            except:
                                pass
                except:
                    pass
                
                # Удаляем папку
                try:
                    shutil.rmtree(SD_DIR, ignore_errors=True)
                    self.log(t("ui.launcher.log.sd_folder_deleted", default="✅ [SD] Папка Stable Diffusion успешно удалена"), "SD")
                    
                    # Показываем размер удаленных файлов
                    if deleted_size > 0:
                        size_mb = deleted_size / 1024 / 1024
                        if size_mb > 1024:
                            size_gb = size_mb / 1024
                            self.log(t("ui.launcher.log.sd_space_freed_gb", default="📊 [SD] Освобождено места: {size} GB", size=f"{size_gb:.2f}"), "SD")
                        else:
                            self.log(t("ui.launcher.log.sd_space_freed_mb", default="📊 [SD] Освобождено места: {size} MB", size=f"{size_mb:.2f}"), "SD")
                except Exception as e:
                    self.log(t("ui.launcher.log.sd_folder_delete_error", default="❌ [SD] Ошибка при удалении папки: {error}", error=str(e)), "SD")
                    self.show_error(
                        t("ui.launcher.delete.error", default="Ошибка удаления"),
                        t("ui.launcher.delete.sd_folder_error", default="Не удалось удалить папку Stable Diffusion:\n{error}\n\nПопробуйте удалить вручную:\n{path}", error=str(e), path=SD_DIR)
                    )
                    return
            else:
                self.log(t("ui.launcher.log.sd_folder_not_found", default="ℹ️ [SD] Папка Stable Diffusion не найдена: {path}", path=SD_DIR), "SD")
            
            # Восстанавливаем модели если они были сохранены
            if models_backup_path and os.path.exists(models_backup_path):
                try:
                    # Создаем папку для моделей
                    os.makedirs(MODELS_SD_DIR, exist_ok=True)
                    
                    # Копируем модели обратно
                    self.log(t("ui.launcher.log.sd_restoring_models", default="📦 [SD] Восстановление моделей..."), "SD")
                    for item in os.listdir(models_backup_path):
                        src = os.path.join(models_backup_path, item)
                        dst = os.path.join(MODELS_SD_DIR, item)
                        if os.path.isdir(src):
                            shutil.copytree(src, dst, dirs_exist_ok=True)
                        else:
                            shutil.copy2(src, dst)
                    
                    self.log(t("ui.launcher.log.sd_models_restored", default="✅ [SD] Модели успешно восстановлены"), "SD")
                except Exception as e:
                    self.log(t("ui.launcher.log.sd_models_restore_failed", default="⚠️ [SD] Не удалось восстановить модели: {error}", error=str(e)), "SD")
            
            # Обновляем статус сервиса
            self._set_service_indicator("sd", COLORS['text_muted'])
            self._set_service_button("sd", text="▶", fg_color=COLORS['primary'])
            self._set_service_status_label("sd", text=t("ui.launcher.status.stopped", default="Остановлен"), color=COLORS['text_muted'])
            
            success_msg = t("ui.launcher.delete.sd_success", default="Stable Diffusion успешно удален!\n\n")
            if save_models and models_backup_path and os.path.exists(models_backup_path):
                success_msg += t("ui.launcher.delete.models_saved", default="Модели изображений сохранены и будут восстановлены при следующей установке.\n")
            else:
                success_msg += t("ui.launcher.delete.all_files_deleted", default="Все файлы и данные были удалены.\n")
            success_msg += t("ui.launcher.delete.sd_will_reinstall", default="При следующем запуске SD сервиса он будет установлен заново.")
            
            self.show_success(t("ui.launcher.delete.complete", default="Удаление завершено"), success_msg)
            
        except Exception as e:
            self.log(t("ui.launcher.log.sd_deletion_error", default="❌ [SD] Ошибка при удалении Stable Diffusion: {error}", error=str(e)), "SD")
            self.show_error(
                t("ui.launcher.delete.error", default="Ошибка удаления"),
                t("ui.launcher.delete.sd_error", default="Произошла ошибка при удалении Stable Diffusion:\n{error}", error=str(e))
            )
    
    def _kill_all_sd_processes(self):
        """Убивает все процессы Stable Diffusion, включая дочерние"""
        try:
            current_pid = os.getpid()
            killed_count = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    # Проверяем командную строку процесса
                    cmdline = proc.info.get('cmdline', [])
                    proc_exe = proc.info.get('exe', '')
                    
                    # Ищем процессы SD (python с launch.py в SD_DIR)
                    is_sd = False
                    if cmdline:
                        cmdline_str = ' '.join(str(arg) for arg in cmdline).lower()
                        # Проверяем наличие launch.py и SD_DIR в пути
                        if 'launch.py' in cmdline_str and SD_DIR.lower() in cmdline_str:
                            is_sd = True
                        # Также проверяем процессы python в SD_DIR
                        elif 'python' in cmdline_str and any(SD_DIR.lower() in str(arg).lower() for arg in cmdline):
                            is_sd = True
                    
                    if is_sd:
                        pid = proc.info['pid']
                        if pid != current_pid:
                            try:
                                p = psutil.Process(pid)
                                # Убиваем все дочерние процессы
                                for child in p.children(recursive=True):
                                    try:
                                        child.terminate()
                                    except:
                                        pass
                                # Убиваем сам процесс
                                p.terminate()
                                time.sleep(0.5)
                                if p.is_running():
                                    p.kill()
                                killed_count += 1
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if killed_count > 0:
                self.log(t("ui.launcher.log.sd_processes_killed", default="✅ [SYSTEM] Остановлено процессов SD: {count}", count=killed_count), "SYSTEM")
            return killed_count
        except Exception as e:
            # Не критично, просто игнорируем
            return 0
    
    
    def _update_sd_model_info(self, label):
        """Обновляет информацию о текущих моделях SD"""
        try:
            if not os.path.exists(MODELS_SD_DIR):
                label.configure(text=t("ui.launcher.model.folder_not_found", default="Папка с моделями не найдена"))
                return
            
            models = []
            total_size = 0
            for file in os.listdir(MODELS_SD_DIR):
                if file.lower().endswith(('.safetensors', '.ckpt')):
                    file_path = os.path.join(MODELS_SD_DIR, file)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        total_size += size
                        size_mb = size / 1024 / 1024
                        if size_mb > 1024:
                            size_str = f"{size_mb / 1024:.2f} GB"
                        else:
                            size_str = f"{size_mb:.2f} MB"
                        models.append(f"{file} ({size_str})")
            
            if models:
                total_mb = total_size / 1024 / 1024
                if total_mb > 1024:
                    total_str = f"{total_mb / 1024:.2f} GB"
                else:
                    total_str = f"{total_mb:.2f} MB"
                models_list = "\n".join(models[:3]) + ("..." if len(models) > 3 else "")
                label.configure(text=t("ui.launcher.model.models_info", default="Установлено моделей: {count}\nОбщий размер: {size}\n\n{list}", count=len(models), size=total_str, list=models_list))
            else:
                label.configure(text=t("ui.launcher.model.models_not_installed", default="Модели не установлены"))
        except Exception as e:
            label.configure(text=t("ui.launcher.model.info_error", default="Ошибка при получении информации: {error}", error=str(e)))

if __name__ == "__main__":
    def global_exception_handler(exc_type, exc_value, exc_traceback):
        """Глобальный обработчик необработанных исключений"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        import traceback
        error_msg = f"Критическая ошибка:\n{exc_type.__name__}: {exc_value}\n\n{traceback.format_exception(exc_type, exc_value, exc_traceback)}"
        
        # Логируем в файл
        try:
            log_file = os.path.join(DIR_LOGS, f"crash_{time.strftime('%Y%m%d_%H%M%S')}.log")
            os.makedirs(DIR_LOGS, exist_ok=True)
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(error_msg)
        except:
            pass
        
        # Показываем пользователю
        print(f"[FATAL ERROR]\n{error_msg}", flush=True)
        try:
            show_error("Критическая ошибка", f"Произошла критическая ошибка.\n\n{exc_type.__name__}: {exc_value}\n\nДетали сохранены в лог файл.")
        except:
            pass
    
    # Устанавливаем глобальный обработчик исключений
    sys.excepthook = global_exception_handler
    
    try:
        app = ModernLauncher()
        app.protocol("WM_DELETE_WINDOW", app.on_close)
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        import traceback
        error_msg = f"Критическая ошибка при запуске:\n{str(e)}\n\n{traceback.format_exc()}"
        print(f"[FATAL ERROR]\n{error_msg}", flush=True)
        try:
            show_error("Fatal Error", error_msg)
        except:
            pass
        try:
            input("Нажмите Enter для выхода...")
        except:
            pass
        sys.exit(1)

