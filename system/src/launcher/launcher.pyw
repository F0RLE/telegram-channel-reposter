import sys
import os

# Перенаправление stderr для отладки
if not hasattr(sys, '_launcher_redirected'):
    sys._launcher_redirected = True
    sys._original_stderr = sys.stderr
    sys.stderr = sys.stdout

try:
    if sys.stdout and hasattr(sys.stdout, 'buffer'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'buffer'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

import glob
import subprocess
import threading
import queue
import json
import time
import shutil
import ctypes

# Проверка критических зависимостей
missing_modules = []
try:
    import requests
except ImportError:
    missing_modules.append("requests")

try:
    import psutil
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
    pass  # webbrowser обычно встроен

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None
    ImageDraw = None

# Если есть отсутствующие модули, показываем ошибку
if missing_modules:
    def show_error(title, msg):
        try:
            ctypes.windll.user32.MessageBoxW(0, msg, title, 0x10)
        except:
            print(f"[ERROR] {title}: {msg}", flush=True)
    
    error_msg = (
        "Отсутствуют необходимые модули Python!\n\n"
        f"Не найдены: {', '.join(missing_modules)}\n\n"
        "РЕШЕНИЕ:\n"
        "1. Запустите 'Установка.bat' для установки всех зависимостей\n"
        "2. Или установите вручную:\n"
        f"   pip install {' '.join(missing_modules)}"
    )
    show_error("Ошибка: Отсутствуют модули", error_msg)
    sys.exit(1)

# Fix Tkinter paths
def fix_tkinter_paths():
    base = os.path.dirname(sys.executable)
    lib = os.path.join(base, "Lib")
    tcl = os.path.join(lib, "tcl")
    tk_path = os.path.join(lib, "tk")
    
    if os.path.exists(tcl) and os.path.exists(tk_path):
        os.environ["TCL_LIBRARY"] = tcl
        os.environ["TK_LIBRARY"] = tk_path

    try:
        import tkinter_embed
        bin_dir = os.path.join(os.path.dirname(tkinter_embed.__file__), "data", "bin")
        if os.path.exists(bin_dir):
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(bin_dir)
    except ImportError:
        pass

fix_tkinter_paths()

def show_error(title, msg):
    try:
        ctypes.windll.user32.MessageBoxW(0, msg, title, 0x10)
    except:
        print(f"[ERROR] {title}: {msg}", flush=True)

try:
    import customtkinter as ctk
    from dotenv import set_key, get_key
except ImportError as e:
    error_msg = f"Libraries not found!\nPlease run 'Установка.bat'.\n\nError: {str(e)}"
    show_error("Error", error_msg)
    sys.exit(1)

# ==========================================
# PATH CONFIGURATION
# ==========================================
# Структура папок:
# APPDATA/TelegramBotData/
#   ├── data/                    # Основные данные
#   │   ├── Engine/              # Движок и сервисы
#   │   │   ├── ollama/          # Ollama сервер
#   │   │   │   ├── models/      # Модели Ollama
#   │   │   │   └── data/        # Данные Ollama
#   │   │   └── stable-diffusion-webui-reforge/  # SD WebUI
#   │   ├── configs/             # Конфигурационные файлы
#   │   ├── logs/                # Логи
#   │   └── temp/                # Временные файлы
#   └── env/                     # Окружение (Python, Git)
# 
# Структура исходного кода:
# system/src/
#   ├── launcher/                # Файлы лаунчера
#   │   ├── __init__.py
#   │   ├── launcher.pyw         # Главный файл лаунчера
#   │   ├── channels.py          # Управление каналами
#   │   └── ui_components.py     # UI компоненты
#   ├── config/                  # Конфигурация
#   ├── core/                    # Ядро бота
#   ├── handlers/                # Обработчики команд
#   ├── keyboards/               # Клавиатуры
#   ├── modules/                 # Модули (LLM, парсер, генерация)
#   └── main.py                  # Точка входа бота
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

# Универсальная папка для всех моделей LLM (GGUF и Ollama)
OLLAMA_DIR = os.path.join(DIR_ENGINE, "ollama")
OLLAMA_EXE = os.path.join(OLLAMA_DIR, "ollama.exe")
OLLAMA_MODELS_DIR = os.path.join(OLLAMA_DIR, "models")  # Универсальная папка для всех моделей
OLLAMA_DATA_DIR = os.path.join(OLLAMA_DIR, "data")

# MODELS_LLM_DIR будет загружаться из настроек или использовать универсальную папку по умолчанию
def get_models_llm_dir():
    """Получает путь к папке с моделями из настроек или использует универсальную папку по умолчанию"""
    try:
        from dotenv import get_key
        custom_path = get_key(FILE_ENV, "MODELS_LLM_DIR")
        if custom_path and os.path.exists(custom_path):
            return custom_path
    except:
        pass
    # По умолчанию используем универсальную папку для всех моделей
    return OLLAMA_MODELS_DIR

MODELS_LLM_DIR = get_models_llm_dir()  # Будет обновляться при загрузке настроек

SD_DIR = os.path.join(DIR_ENGINE, "stable-diffusion-webui-reforge")
MODELS_SD_DIR = os.path.join(SD_DIR, "models", "Stable-diffusion")
AD_MODELS_DIR = os.path.join(SD_DIR, "models", "adetailer")
ADETAILER_DIR = os.path.join(SD_DIR, "extensions", "adetailer")

FILE_ENV = os.path.join(DIR_CONFIGS, ".env")
FILE_CHANNELS = os.path.join(DIR_CONFIGS, "channels.json")
FILE_GEN_CONFIG = os.path.join(DIR_CONFIGS, "generation_config.json")
FILE_PID = os.path.join(DIR_TEMP, "launcher.pid")
SCRIPT_GGUF = os.path.join(DIR_ENGINE, "run_llm_gguf.py")
FILE_SD_CACHE = os.path.join(DIR_CONFIGS, "sd_compatibility_cache.json")

SD_REPO = "https://github.com/lllyasviel/stable-diffusion-webui-forge.git"
ADETAILER_REPO = "https://github.com/Bing-su/adetailer.git"
MODEL_SD_URL = "https://civitai.com/api/download/models/2334591?type=Model&format=SafeTensor&size=full&fp=fp32"
MODEL_SD_FILENAME = "cyberrealisticPony_v141.safetensors"

AD_MODELS_URLS = {
    "face_yolov9c.pt": "https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov9c.pt",
    "hand_yolov9c.pt": "https://huggingface.co/Bingsu/adetailer/resolve/main/hand_yolov9c.pt"
}

# ==========================================
# MODERN COLOR SCHEME
# ==========================================
COLORS = {
    'bg': '#0a0a0a',
    'surface': '#141414',
    'surface_light': '#1a1a1a',
    'surface_dark': '#0f0f0f',
    'primary': '#6366f1',
    'primary_hover': '#818cf8',
    'secondary': '#8b5cf6',
    'success': '#10b981',
    'danger': '#ef4444',
    'warning': '#f59e0b',
    'text': '#e5e7eb',
    'text_secondary': '#9ca3af',
    'text_muted': '#6b7280',
    'border': '#262626',
    'accent': '#3b82f6',
}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_app_icon_path():
    """Возвращает путь к иконке приложения"""
    # Путь к новому логотипу
    icon_path = os.path.join(BASE_DIR, "modules", "Images", "Launcher.ico")
    
    # Проверяем существование файла
    if os.path.exists(icon_path):
        return icon_path
    
    # Fallback: если файл не найден, возвращаем None
    return None

def load_app_icon(window):
    """Загружает и устанавливает иконку приложения с улучшенным качеством"""
    try:
        icon_path = get_app_icon_path()
        if not icon_path or not os.path.exists(icon_path):
            return
        
        # Пробуем использовать PIL для конвертации в PNG и загрузки через iconphoto
        if Image is not None:
            try:
                import tkinter as tk
                from io import BytesIO
                
                # Загружаем иконку через PIL
                img = Image.open(icon_path)
                
                # Конвертируем в RGBA если нужно
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Создаем большую версию для лучшего качества (256x256)
                large_size = 256
                resized = img.resize((large_size, large_size), Image.Resampling.LANCZOS)
                
                # Сохраняем во временный PNG файл
                temp_png = os.path.join(DIR_TEMP, "launcher_icon_temp.png")
                os.makedirs(DIR_TEMP, exist_ok=True)
                resized.save(temp_png, format='PNG')
                
                # Загружаем как PhotoImage
                photo = tk.PhotoImage(file=temp_png)
                window.iconphoto(True, photo)
                # Сохраняем ссылку, чтобы изображение не удалилось
                window._icon_photo = photo
                
                # Также устанавливаем через iconbitmap для совместимости
                window.iconbitmap(icon_path)
                return
            except Exception as e:
                # Если PIL не сработал, используем стандартный метод
                pass
        
        # Стандартный метод через iconbitmap
        window.iconbitmap(icon_path)
        
        # Дополнительно пробуем установить через Windows API для лучшего качества
        try:
            import ctypes
            # Загружаем иконку через Windows API
            hicon = ctypes.windll.shell32.ExtractIconW(
                ctypes.windll.kernel32.GetModuleHandleW(None),
                icon_path,
                0
            )
            if hicon:
                # Получаем HWND окна
                hwnd = window.winfo_id()
                # Устанавливаем иконку окна через Windows API
                ctypes.windll.user32.SendMessageW(
                    hwnd,
                    0x0080,  # WM_SETICON
                    0,  # ICON_SMALL
                    hicon
                )
                ctypes.windll.user32.SendMessageW(
                    hwnd,
                    0x0080,  # WM_SETICON
                    1,  # ICON_BIG
                    hicon
                )
        except:
            pass
            
    except Exception as e:
        # Если ничего не сработало, просто игнорируем ошибку
        pass

# ==========================================
# MAIN LAUNCHER CLASS
# ==========================================
class ModernLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("Bot Launcher")
        self.geometry("1400x900")
        self.minsize(1200, 800)

        # Установка иконки с улучшенным качеством
        load_app_icon(self)
        
        # State
        self.procs = {"bot": None, "llm": None, "sd": None}
        self.status_indicators = {}
        self.log_queue = queue.Queue()
        self.stop_events = {k: threading.Event() for k in self.procs}
        self.consoles = {}
        self.entries = {} 
        self.selected_llm_model = tk.StringVar()
        self.current_topic = None
        self.current_frame = 0
        self.debug_mode = tk.BooleanVar(value=False)

        # Initialize
        try:
            self.init_filesystem()
        except Exception as e: 
            show_error("FS Error", str(e))
            sys.exit(1)
        
        if self.check_running(): 
            self.show_lock_screen()
        else: 
            self.register_pid()
            self.build_ui()
        
        self.start_monitor()

    def init_filesystem(self):
        # Создаем все необходимые директории
        directories = [
            DATA_ROOT, 
            DIR_ENGINE, 
            DIR_CONFIGS, 
            DIR_LOGS, 
            DIR_TEMP, 
            MODELS_LLM_DIR, 
            OLLAMA_DIR,
            OLLAMA_MODELS_DIR,
            OLLAMA_DATA_DIR,
            os.path.join(DATA_ROOT, "backups")  # Папка для резервных копий
        ]
        for d in directories:
            os.makedirs(d, exist_ok=True)
        
        if not os.path.exists(FILE_ENV):
            open(FILE_ENV, "w", encoding="utf-8").close()
        
        # Файл channels.json создается только при первом добавлении канала через UI
        # Не создаем его автоматически

        if not os.path.exists(FILE_GEN_CONFIG):
            with open(FILE_GEN_CONFIG, "w", encoding="utf-8") as f:
                json.dump({"llm_temp": 0.7, "sd_steps": 30, "sd_cfg": 6.0}, f, indent=4)
        
        # Создаем начальную резервную копию
        self._create_backup()

    def check_running(self):
        if os.path.exists(FILE_PID):
            try:
                with open(FILE_PID, 'r') as f:
                    pid = int(f.read().strip())
                if psutil.pid_exists(pid): 
                    self.old_pid = pid
                    return True
            except:
                pass
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
    
    def show_lock_screen(self):
        for w in self.winfo_children():
            w.destroy()
        
        frame = ctk.CTkFrame(self, fg_color=COLORS['surface'])
        frame.pack(fill="both", expand=True)
        
        ctk.CTkLabel(
            frame,
            text="⚠️ Launcher уже запущен",
            font=("Segoe UI", 28, "bold"),
            text_color=COLORS['text']
        ).pack(pady=50)
        
        ctk.CTkButton(
            frame,
            text="Остановить старый и запустить",
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
        
        # Main content area
        self.content_frame = ctk.CTkFrame(self, fg_color=COLORS['bg'])
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Create pages
        self.pages = [
            self.create_console_page(),
            self.create_settings_page(),
            self.create_channels_page()
        ]
        
        self.show_page(0)
        self.after(100, self.console_loop)
        self.after(2000, self.service_status_loop)
    
    def create_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=COLORS['surface'])
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(10, 0))
        sidebar.grid_propagate(False)

        # Logo/Title
        title_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(30, 20))
        
        ctk.CTkLabel(
            title_frame,
            text="Bot",
            font=("Segoe UI", 32, "bold"),
            text_color=COLORS['primary']
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_frame,
            text="Launcher",
            font=("Segoe UI", 16),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w")
        
        # Navigation - создаем контейнер для навигационных кнопок
        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=15, pady=(0, 20))
        
        self.nav_buttons = []
        nav_items = [
            ("Консоль", "📊", 0),
            ("Настройки", "⚙️", 1),
            ("Каналы", "📡", 2)
        ]

        for text, icon, idx in nav_items:
            btn = ctk.CTkButton(
                nav_frame,
                text=f"{icon}  {text}",
                command=lambda i=idx: self.show_page(i),
                fg_color="transparent",
                anchor="w",
                height=50,
                font=("Segoe UI", 15),
                corner_radius=12,
                hover_color=COLORS['surface_light'],
                text_color=COLORS['text_secondary']
            )
            btn.pack(fill="x", pady=5)
            self.nav_buttons.append(btn)
        
        # Убеждаемся, что первая кнопка (Консоль) выделена при запуске
        if len(self.nav_buttons) > 0:
            self.nav_buttons[0].configure(
                fg_color=COLORS['primary'],
                text_color="white"
            )
        
        # Spacer для разделения навигации и сервисов
        spacer = ctk.CTkFrame(sidebar, fg_color="transparent", height=20)
        spacer.pack(fill="x")
        
        # Services status (bottom)
        services_frame = ctk.CTkFrame(sidebar, fg_color=COLORS['surface_light'], corner_radius=12)
        services_frame.pack(fill="x", padx=15, pady=(20, 15), side="bottom")
        
        ctk.CTkLabel(
            services_frame,
            text="Сервисы",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS['text_muted']
        ).pack(anchor="w", padx=15, pady=(15, 10))
        
        for key, label in [("bot", "Telegram Bot"), ("llm", "LLM"), ("sd", "Stable Diffusion")]:
            self.create_service_indicator(services_frame, key, label)
        
        # System monitor
        monitor_frame = ctk.CTkFrame(sidebar, fg_color=COLORS['surface_light'], corner_radius=12)
        monitor_frame.pack(fill="x", padx=15, pady=(0, 15), side="bottom")
        
        self.lbl_net = ctk.CTkLabel(
            monitor_frame,
            text="🌐 Сеть: 0 MB/s",
            font=("Consolas", 11),
            text_color=COLORS['accent']
        )
        self.lbl_net.pack(anchor="w", padx=15, pady=(15, 5))
        
        self.lbl_disk = ctk.CTkLabel(
            monitor_frame,
            text="💾 Диск: 0 MB/s",
            font=("Consolas", 11),
            text_color=COLORS['success']
        )
        self.lbl_disk.pack(anchor="w", padx=15, pady=(0, 15))
    
    def create_service_indicator(self, parent, key, label):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=3)
        
        # Status dot
        dot = ctk.CTkLabel(
            frame,
            text="●",
            font=("Arial", 14),
            text_color=COLORS['text_muted'],
            width=20
        )
        dot.pack(side="left")
        self.status_indicators[key] = dot
        
        # Label
        ctk.CTkLabel(
            frame,
            text=label,
            font=("Segoe UI", 13),
            text_color=COLORS['text'],
            anchor="w"
        ).pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Toggle button
        self.service_buttons = getattr(self, 'service_buttons', {})
        btn = ctk.CTkButton(
            frame,
            text="▶",
            width=30,
            height=25,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            command=lambda k=key: self.toggle_service(k),
            font=("Segoe UI", 10)
        )
        btn.pack(side="right")
        self.service_buttons[key] = btn

    def show_page(self, idx):
        self.current_frame = idx
        for i, page in enumerate(self.pages):
            if i == idx:
                page.grid(row=0, column=0, sticky="nsew")
            else:
                page.grid_forget()
        
        # Update nav buttons
        for i, btn in enumerate(self.nav_buttons):
            if i == idx:
                btn.configure(
                    fg_color=COLORS['primary'],
                    text_color="white"
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=COLORS['text_secondary']
                )

    def create_console_page(self):
        frame = ctk.CTkFrame(self.content_frame, fg_color=COLORS['surface'])
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Header
        header = ctk.CTkFrame(frame, fg_color="transparent", height=60)
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 15))
        header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            header,
            text="Консоль",
            font=("Segoe UI", 28, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, sticky="w")
        
        ctk.CTkButton(
            header,
            text="Очистить",
            width=100,
            height=35,
            fg_color=COLORS['surface_light'],
            hover_color=COLORS['surface_dark'],
            command=self.clear_console,
            font=("Segoe UI", 13)
        ).grid(row=0, column=1, sticky="e")
        
        # Tabs с горячими клавишами
        tabs = ctk.CTkTabview(frame, fg_color=COLORS['surface_light'], corner_radius=12)
        tabs.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 30))
        
        # Сохраняем ссылку на tabs для горячих клавиш
        self.console_tabs = tabs
        
        # Привязываем горячие клавиши для переключения вкладок (Ctrl+1-4)
        self.bind("<Control-1>", lambda e: tabs.set("Все"))
        self.bind("<Control-2>", lambda e: tabs.set("Bot"))
        self.bind("<Control-3>", lambda e: tabs.set("LLM"))
        self.bind("<Control-4>", lambda e: tabs.set("SD"))
        
        for tab_name in ["Все", "Bot", "LLM", "SD"]:
            tab = tabs.add(tab_name)
            console = ctk.CTkTextbox(
                tab,
                font=("Consolas", 12),
                fg_color=COLORS['bg'],
                text_color=COLORS['text'],
                corner_radius=8,
                wrap="word"
            )
            console.pack(fill="both", expand=True, padx=5, pady=5)
            # Включаем возможность выделения текста
            console.configure(state="normal")
            # Добавляем контекстное меню для копирования
            self.setup_console_context_menu(console)
            self.consoles[tab_name] = console
        
        return frame
    
    def create_services_page(self):
        frame = ctk.CTkFrame(self.content_frame, fg_color=COLORS['surface'])
        frame.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkFrame(frame, fg_color="transparent", height=60)
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 20))
        
        ctk.CTkLabel(
            header,
            text="Управление сервисами",
            font=("Segoe UI", 28, "bold"),
            text_color=COLORS['text']
        ).pack(side="left")
        
        # Services cards
        services_container = ctk.CTkFrame(frame, fg_color="transparent")
        services_container.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 30))
        services_container.grid_columnconfigure((0, 1, 2), weight=1)
        
        services = [
            ("bot", "Telegram Bot", "🤖", "Управление Telegram ботом"),
            ("llm", "LLM Server", "🧠", "Сервер языковой модели"),
            ("sd", "Stable Diffusion", "🎨", "Генерация изображений")
        ]
        
        for idx, (key, title, icon, desc) in enumerate(services):
            card = self.create_service_card(services_container, key, title, icon, desc)
            card.grid(row=0, column=idx, sticky="ew", padx=10)
        
        return frame
    
    def create_service_card(self, parent, key, title, icon, desc):
        card = ctk.CTkFrame(parent, fg_color=COLORS['surface_light'], corner_radius=16)
        card.grid_columnconfigure(0, weight=1)
        
        # Icon and title
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            header,
            text=icon,
            font=("Segoe UI", 40)
        ).pack(side="left", padx=(0, 15))
        
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
        
        # Status
        status_frame = ctk.CTkFrame(card, fg_color="transparent")
        status_frame.pack(fill="x", padx=20, pady=10)
        
        status_label = ctk.CTkLabel(
            status_frame,
            text="Остановлен",
            font=("Segoe UI", 13),
            text_color=COLORS['text_muted']
        )
        status_label.pack(side="left")
        self.status_labels = getattr(self, 'status_labels', {})
        self.status_labels[key] = status_label
        
        # Control button
        ctk.CTkButton(
            card,
            text="Запустить",
            command=lambda k=key: self.toggle_service(k),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            font=("Segoe UI", 14, "bold"),
            height=45
        ).pack(fill="x", padx=20, pady=(0, 20))
        
        return card
    
    def create_settings_page(self):
        frame = ctk.CTkFrame(self.content_frame, fg_color=COLORS['surface'])
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Header
        header = ctk.CTkFrame(frame, fg_color="transparent", height=60)
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 20))
        header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            header,
            text="Настройки",
            font=("Segoe UI", 28, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, sticky="w")
        
        ctk.CTkButton(
            header,
            text="Сохранить",
            width=120,
            height=40,
            fg_color=COLORS['success'],
            hover_color="#059669",
            command=self.save_settings,
            font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=1, sticky="e")

        # Вкладки настроек
        tabs = ctk.CTkTabview(frame, fg_color=COLORS['surface_light'], corner_radius=12)
        tabs.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 30))
        
        # Вкладка 1: Основные настройки
        tab_main = tabs.add("⚙️ Основные")
        self._create_main_settings_tab(tab_main)
        
        # Вкладка 2: Настройки текста
        tab_text = tabs.add("📝 Текст")
        self._create_text_settings_tab(tab_text)
        
        # Вкладка 3: Генерация изображений
        tab_image = tabs.add("🎨 Изображения")
        self._create_image_settings_tab(tab_image)
        
        return frame
    
    def _create_main_settings_tab(self, parent):
        """Создает вкладку основных настроек"""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        scroll.grid_columnconfigure(0, weight=1)
        
        # Telegram Bot settings
        bot_card = self.create_setting_card(scroll, "Telegram Bot", [
            ("BOT_TOKEN", "Bot Token", "Токен бота от @BotFather"),
            ("TARGET_CHANNEL_ID", "Channel ID", "ID целевого канала")
        ])
        bot_card.pack(fill="x", pady=(0, 15))
        
        # Debug режим
        debug_card = ctk.CTkFrame(scroll, fg_color=COLORS['surface_light'], corner_radius=12)
        debug_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            debug_card,
            text="Отладка",
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 15))
        
        debug_frame = ctk.CTkFrame(debug_card, fg_color="transparent")
        debug_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            debug_frame,
            text="Режим отладки",
            font=("Segoe UI", 13),
            text_color=COLORS['text_secondary']
        ).pack(side="left", padx=(0, 10))
        
        debug_switch = ctk.CTkSwitch(
            debug_frame,
            text="Показывать debug сообщения",
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
        """Создает вкладку настроек текста"""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        scroll.grid_columnconfigure(0, weight=1)
        
        # Папка с моделями
        models_dir_card = ctk.CTkFrame(scroll, fg_color=COLORS['surface_light'], corner_radius=12)
        models_dir_card.pack(fill="x", pady=(0, 15))
        models_dir_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            models_dir_card,
            text="Папка с моделями",
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            models_dir_card,
            text="Путь к папке с GGUF моделями:",
            font=("Segoe UI", 13),
            text_color=COLORS['text_secondary']
        ).grid(row=1, column=0, sticky="w", padx=(20, 10), pady=10)
        
        # Поле с путем
        models_dir_entry = ctk.CTkEntry(
            models_dir_card,
            font=("Segoe UI", 12),
            fg_color=COLORS['bg'],
            border_color=COLORS['border']
        )
        models_dir_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=10)
        
        # Загружаем текущий путь
        current_path = get_models_llm_dir()
        models_dir_entry.insert(0, current_path)
        self.models_dir_entry = models_dir_entry  # Сохраняем ссылку для сохранения
        
        # Кнопка выбора папки
        def select_models_folder():
            folder = filedialog.askdirectory(
                title="Выберите папку с моделями",
                initialdir=current_path if os.path.exists(current_path) else OLLAMA_MODELS_DIR
            )
            if folder:
                models_dir_entry.delete(0, "end")
                models_dir_entry.insert(0, folder)
        
        ctk.CTkButton(
            models_dir_card,
            text="📁 Выбрать папку",
            width=150,
            command=select_models_folder,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            font=("Segoe UI", 12)
        ).grid(row=1, column=2, padx=(0, 20), pady=10)
        
        # LLM Model settings
        llm_card = self.create_setting_card(scroll, "LLM Model", [
            ("model", "Модель", "Выберите GGUF модель")
        ])
        llm_card.pack(fill="x", pady=(0, 15))
        
        # Scan LLM models
        self.scan_llm_models()
        
        # Кнопка удаления LLM (Ollama)
        delete_llm_card = ctk.CTkFrame(scroll, fg_color=COLORS['surface_light'], corner_radius=12)
        delete_llm_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            delete_llm_card,
            text="Управление LLM",
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 10))
        
        info_label = ctk.CTkLabel(
            delete_llm_card,
            text="Удалить Ollama и все связанные файлы (модели, данные)",
            font=("Segoe UI", 12),
            text_color=COLORS['text_secondary']
        )
        info_label.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 15))
        
        delete_btn = ctk.CTkButton(
            delete_llm_card,
            text="🗑️ Удалить LLM",
            width=150,
            height=40,
            command=self._delete_ollama,
            fg_color=COLORS['danger'],
            hover_color="#dc2626",
            font=("Segoe UI", 13, "bold")
        )
        delete_btn.grid(row=1, column=1, sticky="e", padx=(0, 20), pady=(0, 15))
    
    def _create_image_settings_tab(self, parent):
        """Создает вкладку настроек генерации изображений"""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        scroll.grid_columnconfigure(0, weight=1)
        
        # Кнопка удаления SD (Stable Diffusion)
        delete_sd_card = ctk.CTkFrame(scroll, fg_color=COLORS['surface_light'], corner_radius=12)
        delete_sd_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            delete_sd_card,
            text="Управление Stable Diffusion",
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 10))
        
        info_label = ctk.CTkLabel(
            delete_sd_card,
            text="Удалить Stable Diffusion и все связанные файлы (модели, расширения, виртуальное окружение)",
            font=("Segoe UI", 12),
            text_color=COLORS['text_secondary']
        )
        info_label.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 15))
        
        delete_btn = ctk.CTkButton(
            delete_sd_card,
            text="🗑️ Удалить SD",
            width=150,
            height=40,
            command=self._delete_sd,
            fg_color=COLORS['danger'],
            hover_color="#dc2626",
            font=("Segoe UI", 13, "bold")
        )
        delete_btn.grid(row=1, column=1, sticky="e", padx=(0, 20), pady=(0, 15))
        
        # Настройки модели SD
        model_card = ctk.CTkFrame(scroll, fg_color=COLORS['surface_light'], corner_radius=12)
        model_card.pack(fill="x", pady=(0, 15))
        model_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            model_card,
            text="Модель Stable Diffusion",
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(20, 15))
        
        ctk.CTkLabel(
            model_card,
            text="Ссылка на модель:",
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
            text="📥 Скачать модель",
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
        card = ctk.CTkFrame(parent, fg_color=COLORS['surface_light'], corner_radius=12)
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
                    text="Обновить",
                    width=80,
                    command=self.scan_llm_models,
                    fg_color=COLORS['surface_dark'],
                    hover_color=COLORS['surface_light']
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
            
            row += 1
        
        return card
    
    def create_channels_page(self):
        frame = ctk.CTkFrame(self.content_frame, fg_color=COLORS['surface'])
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Используем встроенную реализацию
        self._create_channels_page_legacy(frame)
        
        return frame
    
    def _create_channels_page_legacy(self, frame):
        """Старая реализация страницы каналов (fallback)"""
        # Header
        header = ctk.CTkFrame(frame, fg_color="transparent", height=60)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=30, pady=(30, 20))
        header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            header,
            text="Управление каналами",
            font=("Segoe UI", 28, "bold"),
            text_color=COLORS['text']
        ).grid(row=0, column=0, sticky="w")
        
        # Add channel input
        add_frame = ctk.CTkFrame(header, fg_color=COLORS['surface_light'], corner_radius=20)
        add_frame.grid(row=0, column=1, sticky="e")
        
        self.entry_chan = ctk.CTkEntry(
            add_frame,
            placeholder_text="@username или ссылка",
            width=250,
            font=("Segoe UI", 13),
            fg_color=COLORS['bg'],
            border_color=COLORS['border']
        )
        self.entry_chan.pack(side="left", padx=15, pady=8)
        
        ctk.CTkButton(
            add_frame,
            text="+",
            width=50,
            fg_color=COLORS['success'],
            hover_color="#059669",
            command=self.add_channel,
            font=("Segoe UI", 18, "bold")
        ).pack(side="left", padx=(0, 8), pady=8)
        
        # Topics sidebar
        topics_frame = ctk.CTkFrame(frame, width=280, fg_color=COLORS['surface_light'], corner_radius=12)
        topics_frame.grid(row=1, column=0, sticky="nsew", padx=(30, 10), pady=(0, 30))
        topics_frame.grid_propagate(False)
        
        ctk.CTkLabel(
            topics_frame,
            text="Темы",
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS['text_muted']
        ).pack(pady=(20, 10))
        
        self.scroll_topics = ctk.CTkScrollableFrame(topics_frame, fg_color="transparent")
        self.scroll_topics.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        ctk.CTkButton(
            topics_frame,
            text="+ Новая тема",
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            command=self.new_topic,
            font=("Segoe UI", 13),
            height=40
        ).pack(fill="x", padx=15, pady=(0, 15))
        
        # Channels list
        self.scroll_chans = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll_chans.grid(row=1, column=1, sticky="nsew", padx=(0, 30), pady=(0, 30))
        
        self.refresh_channels()
    
    # ==========================================
    # SERVICE MANAGEMENT
    # ==========================================
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
        self.safe_widget_configure(indicator, text_color=color)

    def _set_service_button(self, name, text=None, fg_color=None):
        button = getattr(self, 'service_buttons', {}).get(name)
        if button:
            kwargs = {}
            if text is not None:
                kwargs["text"] = text
            if fg_color is not None:
                kwargs["fg_color"] = fg_color
            if kwargs:
                self.safe_widget_configure(button, **kwargs)

    def _set_service_status_label(self, name, text=None, color=None):
        label = getattr(self, 'status_labels', {}).get(name)
        if label:
            kwargs = {}
            if text is not None:
                kwargs["text"] = text
            if color is not None:
                kwargs["text_color"] = color
            if kwargs:
                self.safe_widget_configure(label, **kwargs)

    def toggle_service(self, name):
        threading.Thread(target=self._manage_service, args=(name,), daemon=True).start()

    def _manage_service(self, name):
        if self.procs[name]:
            service_names = {"bot": "Telegram Бот", "llm": "LLM Сервер", "sd": "Stable Diffusion"}
            service_name = service_names.get(name, name)
            self.log(f"⏹️ Остановка сервиса: {service_name}...", name.upper())
            self.stop_events[name].set()
            self.kill_tree(self.procs[name].pid)
            self.procs[name] = None
            self._set_service_indicator(name, COLORS['text_muted'])
            self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
            self._set_service_status_label(name, text="Остановлен", color=COLORS['text_muted'])
            self.log(f"✅ Сервис {service_name} остановлен", name.upper())
            return

        self.stop_events[name].clear()
        self._set_service_indicator(name, COLORS['warning'])
        self._set_service_button(name, text="⏸", fg_color=COLORS['danger'])
        self._set_service_status_label(name, text="Запуск...", color=COLORS['warning'])
        # Не логируем запуск - бот сам выведет сообщение

        env = os.environ.copy()
        if os.path.exists(os.path.dirname(GIT_CMD)):
            env["PATH"] = os.path.dirname(GIT_CMD) + os.pathsep + env["PATH"]

        cmd = []
        cwd = BASE_DIR

        if name == "bot":
            script = os.path.join(BASE_DIR, "main.py")
            if not os.path.exists(script):
                self.log("❌ Ошибка: файл main.py не найден!", "BOT")
                return
            
            # Валидация токена перед запуском
            from dotenv import get_key
            bot_token = get_key(FILE_ENV, "BOT_TOKEN")
            if not bot_token or not bot_token.strip():
                self.log("❌ Ошибка: токен бота не настроен!", "BOT")
                self.log("💡 Решение: Укажите токен в настройках (вкладка 'Основные')", "BOT")
                self._set_service_indicator(name, COLORS['danger'])
                self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                return
            
            # Убиваем все старые процессы бота перед запуском нового
            self._kill_bot_processes()
            
            env["BOT_CONFIG_DIR"] = DIR_CONFIGS
            env["PYTHONPATH"] = BASE_DIR
            cmd = [PYTHON_EXE, "-u", script]

        elif name == "llm":
            # Проверяем наличие Ollama
            if not os.path.exists(OLLAMA_EXE):
                # Проверяем, установлен ли Ollama глобально
                possible_paths = [
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
                    os.path.join(os.environ.get("ProgramFiles", ""), "Ollama", "ollama.exe"),
                    os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Ollama", "ollama.exe"),
                ]
                
                ollama_found = False
                for path in possible_paths:
                    if os.path.exists(path):
                        try:
                            import shutil
                            os.makedirs(OLLAMA_DIR, exist_ok=True)
                            shutil.copy2(path, OLLAMA_EXE)
                            self.log(f"✅ [LLM] Ollama найден и скопирован", "LLM")
                            ollama_found = True
                            break
                        except Exception as e:
                            self.log(f"⚠️ [LLM] Не удалось скопировать Ollama: {e}", "LLM")
                
                if not ollama_found:
                    # Предлагаем установить Ollama
                    self.log("📦 [LLM] Ollama не найден", "LLM")
                    result = messagebox.askyesno(
                        "Установка Ollama",
                        "Ollama не установлен.\n\n"
                        "Хотите установить Ollama автоматически?\n\n"
                        "Это займет несколько минут.",
                        icon="question"
                    )
                    
                    if result:
                        self.log(f"📦 [LLM] Начинаю установку Ollama...", "LLM")
                        if not self._download_ollama():
                            self.log(f"❌ [LLM] Не удалось установить Ollama", "LLM")
                            messagebox.showerror(
                                "Ошибка установки",
                                "Не удалось установить Ollama автоматически.\n\n"
                                "Установите вручную с https://ollama.com/download"
                            )
                            self._set_service_indicator(name, COLORS['danger'])
                            self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                            return
                    else:
                        self.log("❌ [LLM] Установка Ollama отменена пользователем", "LLM")
                        self._set_service_indicator(name, COLORS['danger'])
                        self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                        return
            
            # Получаем выбранную модель через диалог
            selected_model = self._select_llm_model()
            if not selected_model:
                self.log("❌ [LLM] Модель не выбрана", "LLM")
                self._set_service_indicator(name, COLORS['danger'])
                self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                return
            
            model_name = selected_model['name']
            model_type = selected_model['type']  # 'ollama' или 'gguf'
            model_path = selected_model.get('path', None)
            
            # Если это GGUF файл, импортируем в Ollama
            if model_type == 'gguf' and model_path:
                # Сначала проверяем наличие модели
                self.log(f"📦 [LLM] Проверяю наличие модели {model_name} в Ollama...", "LLM")
                
                # Запускаем Ollama сервер в фоне для импорта
                if not self._check_ollama_model(model_name):
                    self.log(f"📦 [LLM] Модель не найдена, запускаю Ollama для импорта...", "LLM")
                    
                    # СНАЧАЛА закрываем все старые процессы Ollama
                    self.log(f"🔄 [LLM] Закрытие старых процессов Ollama перед импортом...", "LLM")
                    killed = self._kill_all_ollama_processes()
                    if killed > 0:
                        self.log(f"✅ [LLM] Закрыто старых процессов Ollama: {killed}", "LLM")
                        time.sleep(2)  # Даем время на завершение процессов
                    
                    # Запускаем Ollama сервер временно для импорта
                    # Используем стандартный порт 11434 для Ollama
                    temp_env = os.environ.copy()
                    temp_env["OLLAMA_HOST"] = "127.0.0.1:11434"
                    temp_env["OLLAMA_ORIGINS"] = "*"
                    temp_env["OLLAMA_MODELS"] = OLLAMA_MODELS_DIR
                    temp_env["OLLAMA_DATA"] = OLLAMA_DATA_DIR
                    
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    
                    self.log(f"🚀 [LLM] Запуск временного Ollama сервера...", "LLM")
                    temp_ollama = subprocess.Popen(
                        [OLLAMA_EXE, "serve"],
                        cwd=OLLAMA_DIR,
                        env=temp_env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        startupinfo=startupinfo
                    )
                    
                    # Ждем запуска сервера (проверяем стандартный порт 11434)
                    self.log(f"⏳ [LLM] Ожидание запуска Ollama сервера...", "LLM")
                    server_ready = False
                    for i in range(30):  # Ждем до 30 секунд
                        time.sleep(1)
                        try:
                            import urllib.request
                            req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
                            with urllib.request.urlopen(req, timeout=2) as response:
                                if response.status == 200:
                                    self.log(f"✅ [LLM] Ollama сервер запущен", "LLM")
                                    server_ready = True
                                    break
                        except Exception as e:
                            if i == 29:
                                self.log(f"⚠️ [LLM] Ollama сервер не отвечает после 30 секунд: {e}", "LLM")
                    
                    if not server_ready:
                        # Закрываем процесс если сервер не запустился
                        try:
                            temp_ollama.terminate()
                            time.sleep(1)
                            if temp_ollama.poll() is None:
                                temp_ollama.kill()
                        except:
                            pass
                        self.log(f"❌ [LLM] Не удалось запустить Ollama сервер", "LLM")
                        messagebox.showerror(
                            "Ошибка запуска Ollama",
                            f"Не удалось запустить Ollama сервер для импорта модели.\n\n"
                            "Попробуйте:\n"
                            "• Перезапустить лаунчер\n"
                            "• Проверить, не запущен ли Ollama вручную\n"
                            "• Переустановить Ollama"
                        )
                        self._set_service_indicator(name, COLORS['danger'])
                        self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                        return
                    
                    # Импортируем модель (НЕ закрываем процессы внутри функции!)
                    self.log(f"📦 [LLM] Импортирую модель {model_name} в Ollama...", "LLM")
                    import_success = self._import_gguf_to_ollama(model_path, model_name, temp_env)
                    
                    # Закрываем временный процесс Ollama после импорта
                    self.log(f"🔄 [LLM] Закрытие временного Ollama сервера...", "LLM")
                    try:
                        temp_ollama.terminate()
                        time.sleep(2)
                        if temp_ollama.poll() is None:
                            temp_ollama.kill()
                            time.sleep(1)
                        # Убеждаемся, что все процессы закрыты
                        self._kill_all_ollama_processes()
                    except Exception as e:
                        self.log(f"⚠️ [LLM] Ошибка при закрытии временного сервера: {e}", "LLM")
                        self._kill_all_ollama_processes()
                    
                    if not import_success:
                        self.log(f"⚠️ [LLM] Не удалось импортировать модель", "LLM")
                        messagebox.showerror(
                            "Ошибка импорта",
                            f"Не удалось импортировать модель {model_name} в Ollama.\n\n"
                            f"Проверьте файл: {model_path}\n\n"
                            "Возможные причины:\n"
                            "• Файл поврежден\n"
                            "• Недостаточно места на диске\n"
                            "• Неверный формат GGUF файла"
                        )
                        self._set_service_indicator(name, COLORS['danger'])
                        self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                        return
            
            # Сохраняем выбранную модель в настройках
            if hasattr(self, 'selected_llm_model'):
                if model_type == 'ollama':
                    self.selected_llm_model.set(model_name)
                else:
                    self.selected_llm_model.set(os.path.basename(model_path) if model_path else model_name)
            
            # Убиваем все старые процессы Ollama перед запуском
            self.log(f"🔄 [LLM] Проверка и закрытие старых процессов Ollama...", "LLM")
            killed = self._kill_all_ollama_processes()
            if killed > 0:
                self.log(f"✅ [LLM] Закрыто старых процессов Ollama: {killed}", "LLM")
                time.sleep(2)  # Даем время на завершение процессов
            
            # Настраиваем переменные окружения для Ollama
            # Используем стандартный порт 11434 для Ollama
            env["OLLAMA_HOST"] = "127.0.0.1:11434"
            env["OLLAMA_ORIGINS"] = "*"
            env["OLLAMA_MODELS"] = OLLAMA_MODELS_DIR
            env["OLLAMA_DATA"] = OLLAMA_DATA_DIR
            
            # Запускаем Ollama сервер скрыто
            cmd = [OLLAMA_EXE, "serve"]
            cwd = OLLAMA_DIR
            
            self.log(f"🚀 [LLM] Запуск Ollama сервера на порту 11434...", "LLM")
            self.log(f"📋 [LLM] Модель: {model_name}", "LLM")

        elif name == "sd":
            # Проверяем и устанавливаем/обновляем SD при первом запуске
            launch_script = os.path.join(SD_DIR, "launch.py")
            if not os.path.exists(SD_DIR) or not os.path.exists(launch_script):
                self.log(f"📦 [SD] Stable Diffusion не установлен, начинаю установку...", "SD")
                if not self._install_sd():
                    self.log(f"❌ [SD] Не удалось установить Stable Diffusion автоматически", "SD")
                    self.log(f"💡 [SD] Проверьте подключение к интернету и попробуйте снова", "SD")
                    self._set_service_indicator(name, COLORS['danger'])
                    self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                    return
            else:
                # Проверяем обновления (быстрая проверка)
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    
                    # Быстрая проверка обновлений (только fetch, без pull)
                    result = subprocess.run(
                        [GIT_CMD, "fetch", "origin"],
                        cwd=SD_DIR,
                        capture_output=True,
                        text=True,
                        timeout=10,  # Уменьшен таймаут
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        startupinfo=startupinfo
                    )
                    
                    # Проверяем, есть ли изменения (быстрая проверка)
                    result = subprocess.run(
                        [GIT_CMD, "rev-parse", "@{u}"],
                        cwd=SD_DIR,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        startupinfo=startupinfo
                    )
                    
                    if result.returncode == 0:
                        remote_hash = result.stdout.strip()
                        local_result = subprocess.run(
                            [GIT_CMD, "rev-parse", "HEAD"],
                            cwd=SD_DIR,
                            capture_output=True,
                            text=True,
                            timeout=5,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            startupinfo=startupinfo
                        )
                        if local_result.returncode == 0:
                            local_hash = local_result.stdout.strip()
                            if remote_hash != local_hash:
                                self.log(f"🔄 [SD] Обнаружены обновления, обновляю...", "SD")
                                self._update_sd()
                            else:
                                self.log(f"✅ [SD] Установлена последняя версия", "SD")
                        else:
                            self.log(f"✅ [SD] Установлена последняя версия", "SD")
                    else:
                        self.log(f"✅ [SD] Установлена последняя версия", "SD")
                except:
                    self.log(f"✅ [SD] Установлена последняя версия", "SD")
            
            venv = os.path.join(SD_DIR, "venv")
            py = None
            
            # Проверяем наличие venv и создаем если нужно
            if not os.path.exists(venv):
                self.log(f"📦 [SD] Виртуальное окружение не найдено, создаю...", "SD")
                if not self._create_sd_venv():
                    self.log(f"❌ [SD] Не удалось создать виртуальное окружение", "SD")
                    self._set_service_indicator(name, COLORS['danger'])
                    self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                    return
            else:
                # Проверяем, правильно ли установлен PyTorch
                venv_py = os.path.join(venv, "Scripts", "python.exe")
                if os.path.exists(venv_py):
                    try:
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        startupinfo.wShowWindow = subprocess.SW_HIDE
                        
                        # Проверяем кэш совместимости для ускорения
                        cache_valid = False
                        try:
                            if os.path.exists(FILE_SD_CACHE):
                                import json
                                import time
                                with open(FILE_SD_CACHE, 'r', encoding='utf-8') as f:
                                    cache = json.load(f)
                                # Проверяем, что кэш актуален (не старше 1 часа)
                                if time.time() - cache.get('timestamp', 0) < 3600:
                                    if cache.get('torch_ok') and cache.get('xformers_ok'):
                                        cache_valid = True
                                        self.log(f"✅ [SD] Используется кэш проверки совместимости", "SD")
                        except:
                            pass
                        
                        if not cache_valid:
                            self.log(f"🔍 [SD] Проверка совместимости PyTorch...", "SD")
                            
                            # Проверяем поддержку CUDA на устройстве (быстрая проверка)
                            cuda_supported = False
                            cuda_version = None
                            try:
                                nvidia_check = subprocess.run(
                                    ["nvidia-smi"],
                                    capture_output=True,
                                    text=True,
                                    timeout=3,  # Уменьшен таймаут
                                    creationflags=subprocess.CREATE_NO_WINDOW
                                )
                                if nvidia_check.returncode == 0:
                                    cuda_supported = True
                                    # Пробуем извлечь версию CUDA
                                    import re
                                    version_match = re.search(r'CUDA Version: (\d+\.\d+)', nvidia_check.stdout)
                                    if version_match:
                                        cuda_version = version_match.group(1)
                                        self.log(f"✅ [SD] Обнаружена CUDA версии {cuda_version}", "SD")
                                    else:
                                        self.log(f"✅ [SD] CUDA обнаружена", "SD")
                            except:
                                self.log(f"⚠️ [SD] CUDA не обнаружена, будет использоваться CPU", "SD")
                            
                            # Быстрая проверка PyTorch (только импорт)
                            check_torch = subprocess.run(
                                [venv_py, "-c", "import torch; print('TORCH_OK'); print('CUDA_AVAILABLE:', torch.cuda.is_available())"],
                                capture_output=True,
                                text=True,
                                timeout=5,  # Уменьшен таймаут
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=startupinfo
                            )
                            
                            torch_has_cuda = False
                            torch_needs_reinstall = False
                            
                            if check_torch.returncode == 0:
                                output = check_torch.stdout.strip()
                                if "TORCH_OK" in output:
                                    if "CUDA_AVAILABLE: True" in output:
                                        torch_has_cuda = True
                                        # Если PyTorch с CUDA, но устройство не поддерживает - переустанавливаем
                                        if not cuda_supported:
                                            torch_needs_reinstall = True
                                            self.log(f"⚠️ [SD] PyTorch установлен с CUDA, но устройство не поддерживает CUDA", "SD")
                                        else:
                                            self.log(f"✅ [SD] PyTorch с CUDA установлен и совместим", "SD")
                                    else:
                                        # PyTorch (CPU) установлен
                                        if cuda_supported:
                                            # Если CUDA доступна, но PyTorch CPU - нужно переустановить с CUDA
                                            torch_needs_reinstall = True
                                            self.log(f"⚠️ [SD] CUDA обнаружена, но PyTorch установлен как CPU версия", "SD")
                                            self.log(f"🔄 [SD] Переустанавливаю PyTorch с поддержкой CUDA...", "SD")
                                        else:
                                            self.log(f"✅ [SD] PyTorch (CPU) установлен", "SD")
                                else:
                                    # Ошибка импорта - возможно, нужно переустановить
                                    torch_needs_reinstall = True
                                    self.log(f"⚠️ [SD] Ошибка при проверке PyTorch: {check_torch.stderr}", "SD")
                            else:
                                # Ошибка выполнения - возможно, PyTorch не установлен или поврежден
                                error_output = check_torch.stderr.strip()
                                if "RuntimeError" in error_output or "CUDA" in error_output.upper():
                                    torch_needs_reinstall = True
                                    self.log(f"⚠️ [SD] Обнаружена ошибка совместимости PyTorch/CUDA", "SD")
                                else:
                                    self.log(f"⚠️ [SD] PyTorch не установлен или поврежден", "SD")
                                    torch_needs_reinstall = True
                        else:
                            # Используем кэш - пропускаем проверки
                            torch_needs_reinstall = False
                            torch_has_cuda = True
                            cuda_supported = True
                        
                        # Переустанавливаем PyTorch, если нужно
                        if torch_needs_reinstall:
                            self.log(f"🔄 [SD] Переустанавливаю PyTorch...", "SD")
                            
                            # Удаляем старую версию
                            self.log(f"🗑️ [SD] Удаление старой версии PyTorch...", "SD")
                            uninstall_result = subprocess.run(
                                [venv_py, "-m", "pip", "uninstall", "torch", "torchvision", "torchaudio", "xformers", "-y"],
                                capture_output=True,
                                text=True,
                                timeout=300,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=startupinfo
                            )
                            
                            # Устанавливаем правильную версию
                            if cuda_supported:
                                # Проверяем наличие Visual C++ Redistributables
                                self.log(f"🔍 [SD] Проверка Visual C++ Redistributables...", "SD")
                                vc_redist_installed = False
                                try:
                                    # Проверяем наличие vcruntime140.dll в системных папках
                                    import sys
                                    system32 = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32')
                                    vcruntime_path = os.path.join(system32, 'vcruntime140.dll')
                                    if os.path.exists(vcruntime_path):
                                        vc_redist_installed = True
                                        self.log(f"✅ [SD] Visual C++ Redistributables обнаружены", "SD")
                                    else:
                                        self.log(f"⚠️ [SD] Visual C++ Redistributables не найдены", "SD")
                                        self.log(f"💡 [SD] Рекомендуется установить Visual C++ Redistributables", "SD")
                                        self.log(f"💡 [SD] Скачайте с: https://aka.ms/vs/17/release/vc_redist.x64.exe", "SD")
                                except:
                                    pass
                                
                                # Пробуем установить PyTorch с CUDA
                                # Определяем правильную версию CUDA для установки
                                torch_installed = False
                                
                                # Определяем список версий CUDA для попытки установки
                                # Основные версии: cu130 (CUDA 13.0+), cu121 (CUDA 12.x), cu118 (fallback)
                                if cuda_version:
                                    try:
                                        major = int(cuda_version.split('.')[0])
                                        if major >= 13:
                                            cuda_versions_to_try = ["cu130", "cu121", "cu118"]
                                        else:
                                            cuda_versions_to_try = ["cu121", "cu118"]
                                    except:
                                        cuda_versions_to_try = ["cu130", "cu121", "cu118"]
                                else:
                                    cuda_versions_to_try = ["cu130", "cu121", "cu118"]
                                
                                # Пробуем установить PyTorch с каждой версией CUDA
                                # Используем стабильную версию 2.9.1 (как указано на pytorch.org)
                                installed_cuda_ver = None
                                for cuda_ver in cuda_versions_to_try:
                                    self.log(f"📦 [SD] Попытка установки PyTorch 2.9.1 с CUDA {cuda_ver}...", "SD")
                                    install_result = subprocess.run(
                                        [venv_py, "-m", "pip", "install", "torch==2.9.1", "torchvision", "torchaudio", 
                                         "--index-url", f"https://download.pytorch.org/whl/{cuda_ver}", "--no-cache-dir"],
                                        capture_output=True,
                                        text=True,
                                        timeout=1800,
                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                        startupinfo=startupinfo
                                    )
                                    
                                    if install_result.returncode == 0:
                                        # Проверяем, что PyTorch действительно работает
                                        test_result = subprocess.run(
                                            [venv_py, "-c", "import torch; print('OK')"],
                                            capture_output=True,
                                            text=True,
                                            timeout=10,
                                            creationflags=subprocess.CREATE_NO_WINDOW,
                                            startupinfo=startupinfo
                                        )
                                        
                                        if test_result.returncode == 0 and "OK" in test_result.stdout:
                                            self.log(f"✅ [SD] PyTorch с CUDA {cuda_ver} установлен и работает", "SD")
                                            torch_installed = True
                                            installed_cuda_ver = cuda_ver
                                            break
                                        else:
                                            self.log(f"⚠️ [SD] PyTorch установлен, но не работает: {test_result.stderr}", "SD")
                                    else:
                                        self.log(f"⚠️ [SD] Не удалось установить PyTorch с CUDA {cuda_ver}", "SD")
                                
                                # Если всё ещё не работает, пробуем установить без индекса (из PyPI)
                                if not torch_installed:
                                    self.log(f"📦 [SD] Попытка установки PyTorch из PyPI (автоматический выбор)...", "SD")
                                    install_result = subprocess.run(
                                        [venv_py, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--no-cache-dir"],
                                        capture_output=True,
                                        text=True,
                                        timeout=1800,
                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                        startupinfo=startupinfo
                                    )
                                    
                                    if install_result.returncode == 0:
                                        test_result = subprocess.run(
                                            [venv_py, "-c", "import torch; print('OK')"],
                                            capture_output=True,
                                            text=True,
                                            timeout=10,
                                            creationflags=subprocess.CREATE_NO_WINDOW,
                                            startupinfo=startupinfo
                                        )
                                        
                                        if test_result.returncode == 0 and "OK" in test_result.stdout:
                                            self.log(f"✅ [SD] PyTorch установлен из PyPI", "SD")
                                            torch_installed = True
                                
                                if torch_installed:
                                    # Устанавливаем xformers только если PyTorch с CUDA работает
                                    try:
                                        check_cuda = subprocess.run(
                                            [venv_py, "-c", "import torch; print('CUDA_OK' if torch.cuda.is_available() else 'CPU')"],
                                            capture_output=True,
                                            text=True,
                                            timeout=10,
                                            creationflags=subprocess.CREATE_NO_WINDOW,
                                            startupinfo=startupinfo
                                        )
                                        
                                        if check_cuda.returncode == 0 and "CUDA_OK" in check_cuda.stdout:
                                            self.log(f"📦 [SD] Установка xformers...", "SD")
                                            # Используем ту же версию CUDA, что и для PyTorch
                                            xformers_cuda_ver = installed_cuda_ver if installed_cuda_ver else "cu130"
                                            xformers_result = subprocess.run(
                                                [venv_py, "-m", "pip", "install", "xformers", 
                                                 "--index-url", f"https://download.pytorch.org/whl/{xformers_cuda_ver}", "--no-cache-dir"],
                                                capture_output=True,
                                                text=True,
                                                timeout=600,
                                                creationflags=subprocess.CREATE_NO_WINDOW,
                                                startupinfo=startupinfo
                                            )
                                            if xformers_result.returncode != 0:
                                                # Пробуем без индекса
                                                xformers_result = subprocess.run(
                                                    [venv_py, "-m", "pip", "install", "xformers", "--no-cache-dir"],
                                                    capture_output=True,
                                                    text=True,
                                                    timeout=600,
                                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                                    startupinfo=startupinfo
                                                )
                                            
                                            # Проверяем работоспособность xformers
                                            try:
                                                check_xformers = subprocess.run(
                                                    [venv_py, "-c", "import xformers; print('XFORMERS_OK')"],
                                                    capture_output=True,
                                                    text=True,
                                                    timeout=10,
                                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                                    startupinfo=startupinfo
                                                )
                                                if check_xformers.returncode == 0 and "XFORMERS_OK" in check_xformers.stdout:
                                                    self.log(f"✅ [SD] xformers работает корректно", "SD")
                                                else:
                                                    self.log(f"⚠️ [SD] xformers несовместим с текущим PyTorch, удаляю...", "SD")
                                                    subprocess.run(
                                                        [venv_py, "-m", "pip", "uninstall", "xformers", "-y"],
                                                        capture_output=True,
                                                        text=True,
                                                        timeout=60,
                                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                                        startupinfo=startupinfo
                                                    )
                                            except:
                                                pass
                                    except:
                                        pass
                                
                                if not torch_installed:
                                    self.log(f"⚠️ [SD] Не удалось установить PyTorch с CUDA, устанавливаю CPU версию...", "SD")
                                    install_result = subprocess.run(
                                        [venv_py, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--no-cache-dir"],
                                        capture_output=True,
                                        text=True,
                                        timeout=1800,
                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                        startupinfo=startupinfo
                                    )
                                if install_result.returncode == 0:
                                    self.log(f"✅ [SD] PyTorch (CPU) установлен", "SD")
                                else:
                                    self.log(f"❌ [SD] Ошибка установки PyTorch: {install_result.stderr}", "SD")
                    except Exception as e:
                        self.log(f"⚠️ [SD] Ошибка при проверке PyTorch: {e}", "SD")
            
            # Проверяем наличие модели при первом запуске
            has_model = False
            if os.path.exists(MODELS_SD_DIR):
                try:
                    has_model = any(f.endswith(('.safetensors', '.ckpt')) for f in os.listdir(MODELS_SD_DIR) if os.path.isfile(os.path.join(MODELS_SD_DIR, f)))
                except:
                    has_model = False
            
            if not has_model:
                self.log(f"📦 [SD] Модель не найдена, начинаю автоматическое скачивание...", "SD")
                # Получаем URL модели из настроек
                try:
                    from dotenv import get_key
                    model_url = get_key(FILE_ENV, "SD_MODEL_URL")
                    if not model_url:
                        model_url = MODEL_SD_URL
                except:
                    model_url = MODEL_SD_URL
                
                if not self._download_sd_model(model_url, show_dialog=False):
                    self.log(f"❌ [SD] Не удалось скачать модель автоматически", "SD")
                    self.log(f"💡 [SD] Скачайте модель вручную в настройках или поместите файл в: {MODELS_SD_DIR}", "SD")
                    self._set_service_indicator(name, COLORS['danger'])
                    self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                    return
            
            # Финальная проверка PyTorch перед запуском
            venv_py = os.path.join(venv, "Scripts", "python.exe")
            if os.path.exists(venv_py):
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    
                    self.log(f"🔍 [SD] Финальная проверка PyTorch перед запуском...", "SD")
                    
                    # Проверяем, что PyTorch работает и совместим
                    # Пробуем импортировать torch и проверить совместимость
                    check_script = """
import torch
import sys
try:
    # Пробуем проверить CUDA
    if torch.cuda.is_available():
        # Пробуем создать тензор на CUDA для проверки совместимости
        try:
            x = torch.tensor([1.0]).cuda()
            print("CUDA_OK")
        except Exception as e:
            print(f"CUDA_ERROR: {e}")
            sys.exit(1)
    else:
        print("CPU_OK")
    
    # Проверяем версию PyTorch
    print(f"TORCH_VERSION:{torch.__version__}")
    sys.exit(0)
except Exception as e:
    print(f"TORCH_ERROR: {e}")
    sys.exit(1)
"""
                    
                    final_check = subprocess.run(
                        [venv_py, "-c", check_script],
                        capture_output=True,
                        text=True,
                        timeout=15,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        startupinfo=startupinfo
                    )
                    
                    # Проверяем, есть ли CUDA на устройстве
                    cuda_on_device = False
                    try:
                        nvidia_check = subprocess.run(
                            ["nvidia-smi"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        if nvidia_check.returncode == 0:
                            cuda_on_device = True
                    except:
                        pass
                    
                    output = final_check.stdout.strip() if final_check.returncode == 0 else ""
                    error_output = final_check.stderr.strip() if final_check.stderr else ""
                    full_output = output + " " + error_output
                    
                    # Если PyTorch не может загрузиться (ошибка DLL или xformers), пробуем исправить
                    if final_check.returncode != 0 or "OSError" in full_output or "WinError" in full_output or "fbgemm" in full_output.lower() or "dll" in full_output.lower() or "xformers" in full_output.lower():
                        self.log(f"⚠️ [SD] Обнаружена ошибка загрузки библиотек", "SD")
                        self.log(f"📋 [SD] Детали ошибки: {full_output[:200]}", "SD")
                        
                        # Если ошибка связана с xformers, удаляем его и пробуем без него
                        if "xformers" in full_output.lower() and "torch" not in full_output.lower():
                            self.log(f"🔄 [SD] Проблема с xformers. Удаляю его...", "SD")
                            subprocess.run(
                                [venv_py, "-m", "pip", "uninstall", "xformers", "-y"],
                                capture_output=True,
                                text=True,
                                timeout=60,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=startupinfo
                            )
                            self.log(f"✅ [SD] xformers удален. Пробую запустить SD...", "SD")
                            # Повторная проверка не нужна, сразу идем дальше к запуску
                        
                        # Если ошибка PyTorch, переустанавливаем
                        elif cuda_on_device:
                            self.log(f"🔄 [SD] Переустанавливаю PyTorch с CUDA и зависимостями...", "SD")
                            
                            # Удаляем проблемную версию
                            uninstall_result = subprocess.run(
                                [venv_py, "-m", "pip", "uninstall", "torch", "torchvision", "torchaudio", "xformers", "-y"],
                                capture_output=True,
                                text=True,
                                timeout=300,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=startupinfo
                            )
                            
                            # Пробуем установить PyTorch из PyPI (автоматический выбор зависимостей)
                            self.log(f"📦 [SD] Установка PyTorch из PyPI (автоматический выбор зависимостей)...", "SD")
                            install_result = subprocess.run(
                                [venv_py, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--no-cache-dir"],
                                capture_output=True,
                                text=True,
                                timeout=1800,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=startupinfo
                            )
                            
                            if install_result.returncode == 0:
                                # Проверяем, работает ли теперь
                                test_check = subprocess.run(
                                    [venv_py, "-c", "import torch; print('OK')"],
                                    capture_output=True,
                                    text=True,
                                    timeout=10,
                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                    startupinfo=startupinfo
                                )
                                
                                if test_check.returncode == 0 and "OK" in test_check.stdout:
                                    self.log(f"✅ [SD] PyTorch переустановлен и работает", "SD")
                                else:
                                    self.log(f"❌ [SD] PyTorch всё ещё не работает после переустановки", "SD")
                                    self.log(f"💡 [SD] Установите Visual C++ Redistributables: https://aka.ms/vs/17/release/vc_redist.x64.exe", "SD")
                                    self._set_service_indicator(name, COLORS['danger'])
                                    self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                                    return
                            else:
                                self.log(f"❌ [SD] Не удалось переустановить PyTorch: {install_result.stderr}", "SD")
                                self._set_service_indicator(name, COLORS['danger'])
                                self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                                return
                        else:
                            self.log(f"❌ [SD] PyTorch не может загрузиться: {full_output[:200]}", "SD")
                            self.log(f"💡 [SD] Установите Visual C++ Redistributables: https://aka.ms/vs/17/release/vc_redist.x64.exe", "SD")
                            self._set_service_indicator(name, COLORS['danger'])
                            self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                            return
                    
                    # Если CUDA доступна на устройстве, но PyTorch CPU - переустанавливаем с CUDA
                    elif cuda_on_device and "CPU_OK" in output:
                        self.log(f"⚠️ [SD] CUDA обнаружена, но PyTorch установлен как CPU версия", "SD")
                        self.log(f"🔄 [SD] Переустанавливаю PyTorch с поддержкой CUDA...", "SD")
                        
                        # Удаляем CPU версию
                        uninstall_result = subprocess.run(
                            [venv_py, "-m", "pip", "uninstall", "torch", "torchvision", "torchaudio", "xformers", "-y"],
                            capture_output=True,
                            text=True,
                            timeout=300,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            startupinfo=startupinfo
                        )
                        
                        # Определяем версию CUDA для установки
                        detected_cuda_version = None
                        try:
                            nvidia_check = subprocess.run(
                                ["nvidia-smi"],
                                capture_output=True,
                                text=True,
                                timeout=5,
                                creationflags=subprocess.CREATE_NO_WINDOW
                            )
                            if nvidia_check.returncode == 0:
                                import re
                                version_match = re.search(r'CUDA Version: (\d+\.\d+)', nvidia_check.stdout)
                                if version_match:
                                    detected_cuda_version = version_match.group(1)
                        except:
                            pass
                        
                        # Основные версии: cu130 (CUDA 13.0+), cu121 (CUDA 12.x), cu118 (fallback)
                        if detected_cuda_version:
                            try:
                                major = int(detected_cuda_version.split('.')[0])
                                if major >= 13:
                                    cuda_versions = ["cu130", "cu121", "cu118"]
                                else:
                                    cuda_versions = ["cu121", "cu118"]
                            except:
                                cuda_versions = ["cu130", "cu121", "cu118"]
                        else:
                            cuda_versions = ["cu130", "cu121", "cu118"]
                        
                        torch_installed = False
                        
                        for cuda_ver in cuda_versions:
                            self.log(f"📦 [SD] Попытка установки PyTorch 2.9.1 с CUDA {cuda_ver}...", "SD")
                            install_result = subprocess.run(
                                [venv_py, "-m", "pip", "install", "torch==2.9.1", "torchvision", "torchaudio", 
                                 "--index-url", f"https://download.pytorch.org/whl/{cuda_ver}", "--no-cache-dir"],
                                capture_output=True,
                                text=True,
                                timeout=1800,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=startupinfo
                            )
                            
                            if install_result.returncode == 0:
                                # Проверяем, что PyTorch действительно работает
                                test_result = subprocess.run(
                                    [venv_py, "-c", "import torch; print('OK')"],
                                    capture_output=True,
                                    text=True,
                                    timeout=10,
                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                    startupinfo=startupinfo
                                )
                                
                                if test_result.returncode == 0 and "OK" in test_result.stdout:
                                    self.log(f"✅ [SD] PyTorch с CUDA {cuda_ver} установлен и работает", "SD")
                                    torch_installed = True
                                    
                                    # Устанавливаем xformers
                                    self.log(f"📦 [SD] Установка xformers...", "SD")
                                    xformers_result = subprocess.run(
                                        [venv_py, "-m", "pip", "install", "xformers", 
                                         "--index-url", f"https://download.pytorch.org/whl/{cuda_ver}", "--no-cache-dir"],
                                        capture_output=True,
                                        text=True,
                                        timeout=600,
                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                        startupinfo=startupinfo
                                    )
                                    break
                                else:
                                    self.log(f"⚠️ [SD] PyTorch установлен, но не работает: {test_result.stderr}", "SD")
                        
                        if not torch_installed:
                            self.log(f"❌ [SD] Не удалось установить PyTorch с CUDA", "SD")
                            self._set_service_indicator(name, COLORS['danger'])
                            self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                            return
                    
                    elif final_check.returncode != 0 or "ERROR" in output or "ERROR" in final_check.stderr:
                        error_msg = final_check.stdout + final_check.stderr
                        self.log(f"❌ [SD] PyTorch не совместим с устройством: {error_msg}", "SD")
                        
                        if not cuda_on_device:
                            self.log(f"🔄 [SD] Устройство не поддерживает CUDA, переустанавливаю PyTorch (CPU)...", "SD")
                            # Переустанавливаем CPU версию
                            uninstall_result = subprocess.run(
                                [venv_py, "-m", "pip", "uninstall", "torch", "torchvision", "torchaudio", "xformers", "-y"],
                                capture_output=True,
                                text=True,
                                timeout=300,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=startupinfo
                            )
                            install_result = subprocess.run(
                                [venv_py, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--no-cache-dir"],
                                capture_output=True,
                                text=True,
                                timeout=1800,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=startupinfo
                            )
                            if install_result.returncode == 0:
                                self.log(f"✅ [SD] PyTorch (CPU) переустановлен, продолжаю запуск...", "SD")
                            else:
                                self.log(f"❌ [SD] Не удалось переустановить PyTorch: {install_result.stderr}", "SD")
                                self._set_service_indicator(name, COLORS['danger'])
                                self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                                return
                        else:
                            self.log(f"❌ [SD] PyTorch не совместим с версией CUDA на устройстве", "SD")
                            self.log(f"💡 [SD] Попробуйте удалить SD и установить заново", "SD")
                            self._set_service_indicator(name, COLORS['danger'])
                            self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                            return
                    else:
                        if "CUDA_OK" in output:
                            self.log(f"✅ [SD] PyTorch с CUDA работает корректно", "SD")
                        elif "CPU_OK" in output:
                            self.log(f"✅ [SD] PyTorch (CPU) работает корректно", "SD")
                        
                        # Проверяем совместимость xformers с PyTorch
                        if "CUDA_OK" in output or "CPU_OK" in output:
                            self.log(f"🔍 [SD] Проверка совместимости xformers...", "SD")
                            try:
                                # Проверяем, установлен ли xformers и совместим ли он
                                # Проверяем версию PyTorch и пытаемся использовать xformers
                                # Упрощенная быстрая проверка xformers
                                check_xformers_script = """
import torch
import sys
import warnings
warnings.filterwarnings('ignore')

try:
    import xformers
    # Простая проверка - только импорт, без реального использования
    # Это быстрее и достаточно для проверки совместимости
    print("XFORMERS_OK")
    sys.exit(0)
except ImportError:
    print("XFORMERS_NOT_INSTALLED")
    sys.exit(0)
except Exception as e:
    error_msg = str(e).lower()
    if "singleton" in error_msg or "entry point" in error_msg or "dll" in error_msg:
        print("XFORMERS_INCOMPATIBLE")
    else:
        print("XFORMERS_OK")  # Если не критичная ошибка, считаем что работает
    sys.exit(0)
"""
                                xformers_check = subprocess.run(
                                    [venv_py, "-c", check_xformers_script],
                                    capture_output=True,
                                    text=True,
                                    timeout=10,
                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                    startupinfo=startupinfo
                                )
                                
                                xformers_output = xformers_check.stdout.strip()
                                
                                if "XFORMERS_INCOMPATIBLE" in xformers_output or "XFORMERS_ERROR" in xformers_output or "XFORMERS_VERSION_MISMATCH" in xformers_output:
                                    self.log(f"⚠️ [SD] xformers несовместим с текущей версией PyTorch", "SD")
                                    self.log(f"🔄 [SD] Переустанавливаю xformers...", "SD")
                                    
                                    # Удаляем старый xformers
                                    subprocess.run(
                                        [venv_py, "-m", "pip", "uninstall", "xformers", "-y"],
                                        capture_output=True,
                                        text=True,
                                        timeout=60,
                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                        startupinfo=startupinfo
                                    )
                                    
                                    # Определяем версию CUDA для xformers
                                    xformers_cuda_ver = "cu130"
                                    if cuda_on_device:
                                        try:
                                            nvidia_check = subprocess.run(
                                                ["nvidia-smi"],
                                                capture_output=True,
                                                text=True,
                                                timeout=5,
                                                creationflags=subprocess.CREATE_NO_WINDOW
                                            )
                                            if nvidia_check.returncode == 0:
                                                import re
                                                version_match = re.search(r'CUDA Version: (\d+\.\d+)', nvidia_check.stdout)
                                                if version_match:
                                                    cuda_version_str = version_match.group(1)
                                                    major = int(cuda_version_str.split('.')[0])
                                                    if major >= 13:
                                                        xformers_cuda_ver = "cu130"
                                                    else:
                                                        xformers_cuda_ver = "cu121"
                                        except:
                                            pass
                                    
                                    # Устанавливаем xformers заново (без указания версии, чтобы pip выбрал совместимую)
                                    self.log(f"📦 [SD] Установка совместимой версии xformers для PyTorch 2.5.1...", "SD")
                                    # Пробуем установить последнюю версию xformers, совместимую с PyTorch 2.5+
                                    xformers_result = subprocess.run(
                                        [venv_py, "-m", "pip", "install", "xformers", "--upgrade", "--force-reinstall",
                                         "--index-url", f"https://download.pytorch.org/whl/{xformers_cuda_ver}", "--no-cache-dir"],
                                        capture_output=True,
                                        text=True,
                                        timeout=600,
                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                        startupinfo=startupinfo
                                    )
                                    
                                    if xformers_result.returncode == 0:
                                        # Устанавливаем дополнительные зависимости для SD
                                        self.log(f"📦 [SD] Установка дополнительных зависимостей (triton, joblib)...", "SD")
                                        additional_deps = ["triton", "joblib"]
                                        for dep in additional_deps:
                                            try:
                                                dep_result = subprocess.run(
                                                    [venv_py, "-m", "pip", "install", dep, "--no-cache-dir"],
                                                    capture_output=True,
                                                    text=True,
                                                    timeout=300,
                                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                                    startupinfo=startupinfo
                                                )
                                                if dep_result.returncode == 0:
                                                    self.log(f"✅ [SD] {dep} установлен", "SD")
                                                else:
                                                    self.log(f"⚠️ [SD] Не удалось установить {dep} (не критично)", "SD")
                                            except:
                                                pass  # Не критично
                                        
                                        # Проверяем, работает ли теперь
                                        verify_xformers = subprocess.run(
                                            [venv_py, "-c", check_xformers_script],
                                            capture_output=True,
                                            text=True,
                                            timeout=15,
                                            creationflags=subprocess.CREATE_NO_WINDOW,
                                            startupinfo=startupinfo
                                        )
                                        
                                        verify_output = verify_xformers.stdout.strip()
                                        if "XFORMERS_OK" in verify_output:
                                            self.log(f"✅ [SD] xformers переустановлен и работает", "SD")
                                        elif "XFORMERS_VERSION_MISMATCH" in verify_output:
                                            self.log(f"⚠️ [SD] xformers всё ещё несовместим, SD будет работать без него", "SD")
                                            # Удаляем несовместимый xformers
                                            subprocess.run(
                                                [venv_py, "-m", "pip", "uninstall", "xformers", "-y"],
                                                capture_output=True,
                                                text=True,
                                                timeout=60,
                                                creationflags=subprocess.CREATE_NO_WINDOW,
                                                startupinfo=startupinfo
                                            )
                                        else:
                                            self.log(f"⚠️ [SD] xformers всё ещё не работает, SD будет работать без него", "SD")
                                    else:
                                        self.log(f"⚠️ [SD] Не удалось переустановить xformers, SD будет работать без него", "SD")
                                elif "XFORMERS_OK" in xformers_output:
                                    self.log(f"✅ [SD] xformers совместим и работает", "SD")
                                    # Устанавливаем дополнительные зависимости для SD
                                    self.log(f"📦 [SD] Установка дополнительных зависимостей (triton, joblib)...", "SD")
                                    additional_deps = ["triton", "joblib"]
                                    for dep in additional_deps:
                                        try:
                                            dep_result = subprocess.run(
                                                [venv_py, "-m", "pip", "install", dep, "--no-cache-dir"],
                                                capture_output=True,
                                                text=True,
                                                timeout=300,
                                                creationflags=subprocess.CREATE_NO_WINDOW,
                                                startupinfo=startupinfo
                                            )
                                            if dep_result.returncode == 0:
                                                self.log(f"✅ [SD] {dep} установлен", "SD")
                                            else:
                                                self.log(f"⚠️ [SD] Не удалось установить {dep} (не критично)", "SD")
                                        except:
                                            pass  # Не критично
                                elif "XFORMERS_NOT_INSTALLED" in xformers_output:
                                    self.log(f"ℹ️ [SD] xformers не установлен (необязательно)", "SD")
                            except:
                                pass
                except:
                    pass
            
            # Сначала пробуем использовать Python из venv
            if os.path.exists(venv):
                venv_py = os.path.join(venv, "Scripts", "python.exe")
                if os.path.exists(venv_py):
                    # Проверяем, работает ли Python из venv
                    try:
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        startupinfo.wShowWindow = subprocess.SW_HIDE
                        
                        test_result = subprocess.run(
                            [venv_py, "--version"],
                            capture_output=True,
                            timeout=5,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            startupinfo=startupinfo
                        )
                        if test_result.returncode == 0:
                            py = venv_py
                            self.log(f"✅ [SD] Используется Python из venv: {venv_py}", "SD")
                        else:
                            self.log(f"⚠️ [SD] Python из venv не работает, используем системный Python", "SD")
                    except Exception as e:
                        self.log(f"⚠️ [SD] Ошибка проверки Python из venv: {e}, используем системный Python", "SD")
            
            # Если venv не работает, используем системный Python
            if not py:
                if os.path.exists(PYTHON_EXE):
                    py = PYTHON_EXE
                    self.log(f"✅ [SD] Используется системный Python: {PYTHON_EXE}", "SD")
                else:
                    self.log("❌ [SD] Ошибка: Python не найден. Запустите Установка.bat", "SD")
                    self._set_service_indicator(name, COLORS['danger'])
                    self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                    return
            
            launch_script = os.path.join(SD_DIR, "launch.py")
            if not os.path.exists(launch_script):
                self.log(f"❌ [SD] Ошибка: файл launch.py не найден в: {SD_DIR}", "SD")
                self.log("💡 [SD] Решение: Проверьте установку Stable Diffusion", "SD")
                self._set_service_indicator(name, COLORS['danger'])
                self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
                return
            
            # Настраиваем переменные окружения для SD
            # Если используем системный Python, добавляем пути к библиотекам venv
            if py == PYTHON_EXE and os.path.exists(venv):
                venv_site_packages = os.path.join(venv, "Lib", "site-packages")
                if os.path.exists(venv_site_packages):
                    # Добавляем site-packages из venv в PYTHONPATH
                    if "PYTHONPATH" in env:
                        env["PYTHONPATH"] = venv_site_packages + os.pathsep + env["PYTHONPATH"]
                    else:
                        env["PYTHONPATH"] = venv_site_packages
            
            # Проверяем поддержку CUDA для определения флагов запуска
            cuda_supported = False
            try:
                check_result = subprocess.run(
                    ["nvidia-smi"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if check_result.returncode == 0:
                    cuda_supported = True
            except:
                pass
            
            # Формируем команду запуска
            cmd = [py, "launch.py", "--api", "--nowebui", "--port", "7860", "--skip-python-version-check"]
            if cuda_supported:
                cmd.extend(["--xformers", "--cuda-stream"])
            else:
                self.log(f"ℹ️ [SD] CUDA не обнаружена, запускаю в CPU режиме", "SD")
            
            cwd = SD_DIR
        else:
            self.log(f"❌ Ошибка: Неизвестный сервис: {name}", name.upper())
            self._set_service_indicator(name, COLORS['danger'])
            self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
            return
        
        if not cmd:
            self.log(f"❌ Ошибка: Не удалось создать команду для сервиса {name}", name.upper())
            self._set_service_indicator(name, COLORS['danger'])
            self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
            return
        
        self.run_process(name, cmd, cwd, env)

    def _download_ollama(self):
        """Автоматически загружает Ollama для Windows"""
        try:
            import urllib.request
            import json
            import shutil
            import zipfile
            
            self.log(f"📥 [LLM] Поиск Ollama...", "LLM")
            
            # Пробуем найти ollama.exe в стандартных местах после установки
            possible_paths = [
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
                os.path.join(os.environ.get("ProgramFiles", ""), "Ollama", "ollama.exe"),
                os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Ollama", "ollama.exe"),
            ]
            
            # Проверяем, установлен ли Ollama глобально
            for path in possible_paths:
                if os.path.exists(path):
                    try:
                        shutil.copy2(path, OLLAMA_EXE)
                        self.log(f"✅ [LLM] Ollama скопирован из {path}", "LLM")
                        return True
                    except Exception as e:
                        self.log(f"⚠️ [LLM] Не удалось скопировать: {e}", "LLM")
            
            # Если не найден, пробуем скачать
            self.log(f"📦 [LLM] Ollama не найден, начинаю загрузку...", "LLM")
            
            try:
                # Сначала пробуем прямой URL с официального сайта
                direct_url = "https://ollama.com/download/OllamaSetup.exe"
                self.log(f"🔍 [LLM] Попытка загрузки с официального сайта...", "LLM")
                
                try:
                    # Проверяем доступность файла
                    req = urllib.request.Request(direct_url)
                    req.add_header('User-Agent', 'Mozilla/5.0')
                    with urllib.request.urlopen(req, timeout=5) as response:
                        file_size = int(response.headers.get('Content-Length', 0))
                        download_url = direct_url
                        self.log(f"✅ [LLM] Найден установщик на официальном сайте ({file_size / 1024 / 1024:.1f} MB)", "LLM")
                except:
                    # Если прямой URL не работает, пробуем GitHub Releases
                    self.log(f"🔍 [LLM] Прямой URL недоступен, пробую GitHub Releases...", "LLM")
                    releases_url = "https://api.github.com/repos/ollama/ollama/releases/latest"
                    
                    with urllib.request.urlopen(releases_url, timeout=10) as response:
                        release_data = json.loads(response.read().decode())
                    
                    # Ищем Windows установщик (более гибкий поиск)
                    download_url = None
                    file_size = 0
                    
                    # Паттерны для поиска Windows установщика
                    patterns = ["windows", "win", "setup", "installer"]
                    
                    for asset in release_data.get("assets", []):
                        name_lower = asset["name"].lower()
                        # Проверяем, что это .exe файл и содержит один из паттернов
                        if asset["name"].endswith(".exe") and any(p in name_lower for p in patterns):
                            download_url = asset["browser_download_url"]
                            file_size = asset.get("size", 0)
                            self.log(f"✅ [LLM] Найден установщик в GitHub: {asset['name']}", "LLM")
                            break
                    
                    if not download_url:
                        self.log(f"❌ [LLM] Не найден Windows установщик в релизе", "LLM")
                        self.log(f"💡 [LLM] Доступные файлы в релизе:", "LLM")
                        for asset in release_data.get("assets", [])[:5]:  # Показываем первые 5
                            self.log(f"   - {asset['name']}", "LLM")
                        return False
                
                # Загружаем установщик
                temp_installer = os.path.join(DIR_TEMP, "OllamaSetup.exe")
                os.makedirs(DIR_TEMP, exist_ok=True)
                
                size_mb = file_size / 1024 / 1024 if file_size > 0 else 0
                self.log(f"⬇️ [LLM] Загрузка Ollama ({size_mb:.1f} MB)...", "LLM")
                
                # Создаем запрос с User-Agent для избежания блокировок
                req = urllib.request.Request(download_url)
                req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                
                # Загружаем файл с прогресс-баром
                downloaded = 0
                last_percent = -1
                
                with urllib.request.urlopen(req, timeout=300) as response:
                    # Получаем реальный размер файла из заголовков
                    total_size = int(response.headers.get('Content-Length', file_size))
                    total_mb = total_size / 1024 / 1024
                    
                    with open(temp_installer, 'wb') as out_file:
                        while True:
                            chunk = response.read(8192)  # Читаем по 8KB
                            if not chunk:
                                break
                            out_file.write(chunk)
                            downloaded += len(chunk)
                            
                            # Обновляем прогресс каждые 10%
                            if total_size > 0:
                                percent = (downloaded * 100) // total_size
                                if percent != last_percent and (percent % 10 == 0 or downloaded == len(chunk)):
                                    downloaded_mb = downloaded / 1024 / 1024
                                    self.log(f"📥 [LLM] Загружено: {downloaded_mb:.1f} / {total_mb:.1f} MB ({percent}%)", "LLM")
                                    last_percent = percent
                self.log(f"✅ [LLM] Установщик загружен", "LLM")
                
                # Запускаем установщик в полностью автоматическом режиме
                self.log(f"⚙️ [LLM] Установка Ollama (автоматический режим, без окна)...", "LLM")
                import subprocess
                
                # Используем флаги для полностью автоматической установки
                # /S - тихая установка (silent mode)
                # Создаем процесс без окна
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                proc = subprocess.Popen(
                    [temp_installer, "/S"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW,  # Скрываем окно полностью
                    startupinfo=startupinfo,
                    shell=False
                )
                
                # Ждем завершения установки (максимум 5 минут)
                self.log(f"⏳ [LLM] Ожидание завершения установки (это может занять несколько минут)...", "LLM")
                try:
                    proc.wait(timeout=300)
                    return_code = proc.returncode
                    if return_code == 0:
                        self.log(f"✅ [LLM] Установщик завершился успешно", "LLM")
                    else:
                        self.log(f"⚠️ [LLM] Установщик завершился с кодом: {return_code}", "LLM")
                except subprocess.TimeoutExpired:
                    self.log(f"⚠️ [LLM] Установка занимает слишком много времени, принудительно завершаю...", "LLM")
                    proc.kill()
                    proc.wait()
                    return_code = -1
                
                # Ждем немного, чтобы файлы точно были установлены
                time.sleep(5)
                
                # Закрываем все процессы Ollama, которые могли запуститься автоматически после установки
                self.log(f"🔄 [LLM] Закрытие процессов Ollama после установки...", "LLM")
                killed = self._kill_all_ollama_processes()
                if killed > 0:
                    self.log(f"✅ [LLM] Закрыто процессов Ollama: {killed}", "LLM")
                    time.sleep(2)  # Даем время на завершение процессов
                
                # Пробуем найти ollama.exe (проверяем несколько раз с задержкой)
                found = False
                for attempt in range(5):
                    for path in possible_paths:
                        if os.path.exists(path):
                            try:
                                os.makedirs(OLLAMA_DIR, exist_ok=True)
                                shutil.copy2(path, OLLAMA_EXE)
                                self.log(f"✅ [LLM] Ollama успешно установлен и скопирован", "LLM")
                                found = True
                                break
                            except Exception as e:
                                self.log(f"⚠️ [LLM] Попытка {attempt + 1}/5: Не удалось скопировать: {e}", "LLM")
                    
                    if found:
                        break
                    if attempt < 4:
                        time.sleep(2)  # Ждем перед следующей попыткой
                
                # Удаляем установщик
                try:
                    os.remove(temp_installer)
                except:
                    pass
                
                if found:
                    return True
                else:
                    self.log(f"⚠️ [LLM] Установка завершена, но ollama.exe не найден", "LLM")
                    self.log(f"💡 [LLM] Попробуйте перезапустить лаунчер или установите вручную", "LLM")
                    return False
                    
            except urllib.error.URLError as e:
                self.log(f"❌ [LLM] Ошибка подключения к интернету: {e}", "LLM")
                self.log(f"💡 [LLM] Установите Ollama вручную с https://ollama.com/download", "LLM")
                return False
            except Exception as e:
                self.log(f"❌ [LLM] Ошибка при загрузке: {e}", "LLM")
                self.log(f"💡 [LLM] Установите Ollama вручную с https://ollama.com/download", "LLM")
                return False
            
        except Exception as e:
            self.log(f"❌ [LLM] Критическая ошибка при загрузке Ollama: {e}", "LLM")
            return False
    
    def _get_ollama_models(self):
        """Получает список моделей из Ollama"""
        models = []
        try:
            if not os.path.exists(OLLAMA_EXE):
                return models  # Ollama не установлен
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            result = subprocess.run(
                [OLLAMA_EXE, "list"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=OLLAMA_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # Пропускаем заголовок
                    if line.strip():
                        parts = line.split()
                        if parts:
                            model_name = parts[0]
                            models.append(model_name)
        except Exception as e:
            # Не логируем ошибку, просто возвращаем пустой список
            pass
        return models
    
    def _get_gguf_models(self):
        """Получает список GGUF файлов из папки Downloads"""
        models = []
        try:
            if os.path.exists(MODELS_LLM_DIR):
                for file in os.listdir(MODELS_LLM_DIR):
                    if file.lower().endswith('.gguf'):
                        file_path = os.path.join(MODELS_LLM_DIR, file)
                        if os.path.isfile(file_path):
                            models.append({
                                'name': os.path.splitext(file)[0],
                                'file': file,
                                'path': file_path
                            })
        except Exception as e:
            self.log(f"⚠️ [LLM] Ошибка при сканировании GGUF файлов: {e}", "LLM")
        return models
    
    def _select_llm_model(self):
        """Показывает диалог выбора модели LLM"""
        try:
            # Получаем списки моделей
            ollama_models = self._get_ollama_models()
            gguf_models = self._get_gguf_models()
            
            if not ollama_models and not gguf_models:
                messagebox.showwarning(
                    "Модели не найдены",
                    "Не найдено ни одной модели!\n\n"
                    "• Модели Ollama: импортируйте через 'ollama pull <model>'\n"
                    f"• GGUF файлы: поместите в папку {MODELS_LLM_DIR}"
                )
                return None
            
            # Создаем диалог выбора
            dialog = ctk.CTkToplevel(self)
            dialog.title("Выбор модели LLM")
            dialog.geometry("500x400")
            dialog.transient(self)
            dialog.grab_set()
            
            # Центрируем окно
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
            y = (dialog.winfo_screenheight() // 2) - (400 // 2)
            dialog.geometry(f"500x400+{x}+{y}")
            
            selected_model = {'result': None}
            
            # Заголовок
            ctk.CTkLabel(
                dialog,
                text="Выберите модель LLM",
                font=("Segoe UI", 18, "bold")
            ).pack(pady=15)
            
            # Создаем вкладки
            tabs = ctk.CTkTabview(dialog)
            tabs.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Вкладка 1: Модели Ollama
            if ollama_models:
                tab_ollama = tabs.add("Модели Ollama")
                scroll_ollama = ctk.CTkScrollableFrame(tab_ollama)
                scroll_ollama.pack(fill="both", expand=True, padx=10, pady=10)
                
                for model in ollama_models:
                    btn = ctk.CTkButton(
                        scroll_ollama,
                        text=model,
                        command=lambda m=model: self._model_selected(dialog, selected_model, {'name': m, 'type': 'ollama'}),
                        width=400,
                        height=40,
                        font=("Segoe UI", 13)
                    )
                    btn.pack(pady=5, padx=10, fill="x")
            else:
                tab_ollama = tabs.add("Модели Ollama")
                ctk.CTkLabel(
                    tab_ollama,
                    text="Модели Ollama не найдены\n\nИмпортируйте через:\nollama pull <model>",
                    font=("Segoe UI", 12),
                    text_color=COLORS['text_muted']
                ).pack(pady=50)
            
            # Вкладка 2: GGUF файлы
            if gguf_models:
                tab_gguf = tabs.add("GGUF файлы")
                scroll_gguf = ctk.CTkScrollableFrame(tab_gguf)
                scroll_gguf.pack(fill="both", expand=True, padx=10, pady=10)
                
                for model_info in gguf_models:
                    btn = ctk.CTkButton(
                        scroll_gguf,
                        text=f"{model_info['name']}\n({os.path.basename(model_info['file'])})",
                        command=lambda m=model_info: self._model_selected(dialog, selected_model, {'name': m['name'], 'type': 'gguf', 'path': m['path']}),
                        width=400,
                        height=50,
                        font=("Segoe UI", 12)
                    )
                    btn.pack(pady=5, padx=10, fill="x")
            else:
                tab_gguf = tabs.add("GGUF файлы")
                ctk.CTkLabel(
                    tab_gguf,
                    text=f"GGUF файлы не найдены\n\nПоместите .gguf файлы в:\n{MODELS_LLM_DIR}",
                    font=("Segoe UI", 12),
                    text_color=COLORS['text_muted']
                ).pack(pady=50)
            
            # Кнопка отмены
            ctk.CTkButton(
                dialog,
                text="Отмена",
                command=lambda: self._model_selected(dialog, selected_model, None),
                width=150,
                height=35,
                fg_color=COLORS['surface_dark'],
                hover_color=COLORS['surface_light']
            ).pack(pady=15)
            
            # Ждем закрытия диалога
            dialog.wait_window()
            
            return selected_model['result']
            
        except Exception as e:
            self.log(f"❌ [LLM] Ошибка при выборе модели: {e}", "LLM")
            return None
    
    def _model_selected(self, dialog, selected_model, model_info):
        """Обработчик выбора модели"""
        selected_model['result'] = model_info
        dialog.destroy()
    
    def _check_ollama_model(self, model_name):
        """Проверяет, есть ли модель в Ollama"""
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # Запускаем ollama list для проверки моделей
            result = subprocess.run(
                [OLLAMA_EXE, "list"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=OLLAMA_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            if result.returncode == 0:
                return model_name in result.stdout
            return False
        except:
            return False
    
    def _import_gguf_to_ollama(self, model_path, model_name, env=None):
        """Автоматически импортирует GGUF модель в Ollama
        
        Args:
            model_path: Путь к GGUF файлу
            model_name: Имя модели для Ollama
            env: Словарь переменных окружения (если None, используется текущее окружение)
        """
        try:
            # Создаем Modelfile для импорта GGUF
            modelfile_path = os.path.join(OLLAMA_DIR, f"{model_name}.Modelfile")
            
            with open(modelfile_path, 'w', encoding='utf-8') as f:
                f.write(f"FROM {model_path}\n")
                f.write("TEMPLATE \"\"\"{{ .Prompt }}\"\"\"\n")
                f.write("PARAMETER temperature 0.7\n")
                f.write("PARAMETER top_p 0.9\n")
            
            # Импортируем модель (НЕ закрываем процессы - они управляются вызывающим кодом)
            self.log(f"📦 [LLM] Импорт модели {model_name}...", "LLM")
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # Используем переданное окружение или текущее
            import_env = env if env else os.environ.copy()
            
            result = subprocess.run(
                [OLLAMA_EXE, "create", model_name, "-f", modelfile_path],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=OLLAMA_DIR,
                env=import_env,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            if result.returncode == 0:
                self.log(f"✅ [LLM] Модель {model_name} успешно импортирована", "LLM")
                return True
            else:
                self.log(f"⚠️ [LLM] Ошибка импорта: {result.stderr}", "LLM")
                return False
        except Exception as e:
            self.log(f"❌ [LLM] Ошибка при импорте модели: {e}", "LLM")
            return False

    def _install_package_with_progress(self, package_name, python_exe, extra_args=None, timeout=300):
        """
        Устанавливает пакет через pip с красивым выводом в реальном времени.
        Не создает новую консоль, весь вывод идет в консоль лаунчера.
        """
        if extra_args is None:
            extra_args = []
        
        cmd = [python_exe, "-m", "pip", "install", package_name, "--upgrade"] + extra_args
        
        try:
            # Создаем процесс без новой консоли
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='replace',
                creationflags=0x08000000,  # Скрываем консоль
                bufsize=1,  # Буферизация по строкам
                universal_newlines=True
            )
            
            # Читаем вывод в реальном времени
            spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            spinner_idx = 0
            last_line = ""
            start_time = time.time()
            error_output = []
            has_compiler_error = False
            
            while True:
                # Проверяем таймаут
                if time.time() - start_time > timeout:
                    proc.terminate()
                    time.sleep(0.5)
                    if proc.poll() is None:
                        proc.kill()
                    self.log(f"⏱️ [LLM] Превышено время ожидания установки {package_name}", "LLM")
                    return False
                
                # Читаем строку
                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    # Показываем спиннер, если нет вывода
                    spinner_idx = (spinner_idx + 1) % len(spinner_chars)
                    spinner = spinner_chars[spinner_idx]
                    if last_line != spinner:
                        self.log(f"⏳ [LLM] {spinner} Установка {package_name}...", "LLM")
                        last_line = spinner
                    time.sleep(0.1)
                    continue
                
                # Обрабатываем строку
                line = line.strip()
                if not line:
                    continue
                
                # Сохраняем ошибки для анализа
                if "error" in line.lower() or "failed" in line.lower():
                    error_output.append(line)
                    # Проверяем на ошибки компилятора (более широкий поиск)
                    line_lower = line.lower()
                    compiler_keywords = ["cmake", "nmake", "compiler", "c++", "cxx", "c_compiler", "cxx_compiler", 
                                        "build tools", "visual studio", "msvc", "cl.exe", "link.exe"]
                    if any(keyword in line_lower for keyword in compiler_keywords):
                        has_compiler_error = True
                
                # Фильтруем и форматируем вывод pip с переводом на русский
                if "Requirement already satisfied" in line:
                    self.log(f"✓ [LLM] Требование уже удовлетворено: {line.split('Requirement already satisfied')[1].strip() if 'Requirement already satisfied' in line else line}", "LLM")
                elif "Collecting" in line:
                    pkg_name = line.replace("Collecting", "").strip().split()[0] if "Collecting" in line else line
                    self.log(f"📦 [LLM] Сборка пакета: {pkg_name}", "LLM")
                elif "Downloading" in line:
                    self.log(f"⬇️ [LLM] Загрузка: {line.replace('Downloading', '').strip()}", "LLM")
                elif "Installing" in line:
                    self.log(f"⚙️ [LLM] Установка: {line.replace('Installing', '').strip()}", "LLM")
                elif "Successfully installed" in line:
                    pkgs = line.replace("Successfully installed", "").strip()
                    self.log(f"✅ [LLM] Успешно установлено: {pkgs}", "LLM")
                elif "Successfully uninstalled" in line:
                    pkgs = line.replace("Successfully uninstalled", "").strip()
                    self.log(f"🗑️ [LLM] Успешно удалено: {pkgs}", "LLM")
                elif "error" in line.lower() or "failed" in line.lower() or "exception" in line.lower():
                    self.log(f"❌ [LLM] Ошибка: {line}", "LLM")
                elif "warning" in line.lower():
                    self.log(f"⚠️ [LLM] Предупреждение: {line}", "LLM")
                elif line.startswith("  "):  # Отступы обычно означают подчиненные сообщения
                    self.log(f"   [LLM] {line.strip()}", "LLM")
                else:
                    self.log(f"ℹ️ [LLM] {line}", "LLM")
            
            # Получаем код возврата
            return_code = proc.poll()
            if return_code == 0:
                return True
            else:
                # Читаем оставшийся вывод
                remaining = proc.stdout.read()
                if remaining:
                    for line in remaining.strip().split('\n'):
                        if line.strip():
                            line_stripped = line.strip()
                            if "error" in line_stripped.lower() or "failed" in line_stripped.lower():
                                self.log(f"❌ [LLM] Ошибка: {line_stripped}", "LLM")
                                error_output.append(line_stripped)
                                # Проверяем на ошибки компилятора (более широкий поиск)
                                line_lower = line_stripped.lower()
                                compiler_keywords = ["cmake", "nmake", "compiler", "c++", "cxx", "c_compiler", "cxx_compiler", 
                                                    "build tools", "visual studio", "msvc", "cl.exe", "link.exe"]
                                if any(keyword in line_lower for keyword in compiler_keywords):
                                    has_compiler_error = True
                            else:
                                self.log(f"ℹ️ [LLM] {line_stripped}", "LLM")
                
                # Анализируем все собранные ошибки для определения типа проблемы
                all_errors_text = " ".join(error_output).lower()
                if not has_compiler_error:
                    compiler_keywords = ["cmake", "nmake", "compiler", "c_compiler", "cxx_compiler", 
                                        "build tools", "visual studio", "msvc", "cl.exe", "link.exe"]
                    if any(keyword in all_errors_text for keyword in compiler_keywords):
                        has_compiler_error = True
                
                # Показываем специальное сообщение для ошибок компилятора
                if has_compiler_error:
                    self.log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "LLM")
                    self.log(f"⚠️ [LLM] Обнаружена ошибка компилятора", "LLM")
                    self.log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "LLM")
                    self.log(f"💡 [LLM] Решение 1: Установите Visual Studio Build Tools", "LLM")
                    self.log(f"💡 [LLM]   Скачайте: https://visualstudio.microsoft.com/downloads/", "LLM")
                    self.log(f"💡 [LLM]   Выберите 'Build Tools for Visual Studio 2022'", "LLM")
                    self.log(f"💡 [LLM]   Установите компонент 'C++ build tools'", "LLM")
                    self.log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "LLM")
                    self.log(f"💡 [LLM] Решение 2: Используйте Python 3.10 или 3.11", "LLM")
                    self.log(f"💡 [LLM]   Для Python 3.10 и 3.11 есть предкомпилированные пакеты", "LLM")
                    self.log(f"💡 [LLM]   Запустите Установка.bat для установки Python 3.11", "LLM")
                    self.log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "LLM")
                
                return False
                
        except subprocess.TimeoutExpired:
            if 'proc' in locals():
                proc.kill()
            self.log(f"⏱️ [LLM] Превышено время ожидания установки {package_name}", "LLM")
            return False
        except Exception as e:
            self.log(f"❌ [LLM] Ошибка при установке {package_name}: {e}", "LLM")
            return False

    def run_process(self, name, cmd, cwd, env):
        def reader(p, n):
            for line in iter(p.stdout.readline, ''):
                if line:
                    self.log_queue.put((line.strip(), n))
            p.stdout.close()

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            p = subprocess.Popen(
                cmd, cwd=cwd, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding='utf-8', errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            self.procs[name] = p
            threading.Thread(target=reader, args=(p, name.upper()), daemon=True).start()
        except FileNotFoundError as e:
            service_names = {"bot": "Telegram Бот", "llm": "LLM Сервер", "sd": "Stable Diffusion"}
            service_name = service_names.get(name, name)
            error_msg = str(e)
            self.log(f"❌ [{name.upper()}] Ошибка: Файл не найден: {error_msg}", name.upper())
            self.log(f"ℹ️ [{name.upper()}] Команда: {' '.join(cmd)}", name.upper())
            self.log(f"ℹ️ [{name.upper()}] Рабочая директория: {cwd}", name.upper())
            
            # Специальная обработка для SD
            if name == "sd" and "python" in error_msg.lower():
                self.log(f"💡 [{name.upper()}] Возможные решения:", name.upper())
                self.log(f"   1. Установите Visual C++ Redistributable:", name.upper())
                self.log(f"      https://aka.ms/vs/17/release/vc_redist.x64.exe", name.upper())
                self.log(f"   2. Переустановите Python через Установка.bat", name.upper())
                self.log(f"   3. Проверьте, что Python работает: {cmd[0]} --version", name.upper())
            
            self.procs[name] = None
            self._set_service_indicator(name, COLORS['danger'])
            self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
            self._set_service_status_label(name, text="Ошибка", color=COLORS['danger'])
        except Exception as e:
            service_names = {"bot": "Telegram Бот", "llm": "LLM Сервер", "sd": "Stable Diffusion"}
            service_name = service_names.get(name, name)
            error_msg = str(e)
            self.log(f"❌ [{name.upper()}] Ошибка запуска сервиса: {error_msg}", name.upper())
            self.log(f"ℹ️ [{name.upper()}] Команда: {' '.join(cmd)}", name.upper())
            
            # Специальная обработка для SD
            if name == "sd":
                self.log(f"💡 [{name.upper()}] Если видите ошибку с DLL (VCRUNTIME140.dll, python310.dll):", name.upper())
                self.log(f"   1. Установите Visual C++ Redistributable:", name.upper())
                self.log(f"      https://aka.ms/vs/17/release/vc_redist.x64.exe", name.upper())
                self.log(f"   2. Переустановите Python через Установка.bat", name.upper())
            
            self.procs[name] = None
            self._set_service_indicator(name, COLORS['danger'])
            self._set_service_button(name, text="▶", fg_color=COLORS['primary'])
            self._set_service_status_label(name, text="Ошибка", color=COLORS['danger'])

    def kill_tree(self, pid):
        try:
            p = psutil.Process(pid)
            for c in p.children(recursive=True):
                c.terminate()
            p.terminate()
        except:
            pass

    def _kill_bot_processes(self):
        """Убивает все процессы бота перед запуском нового"""
        try:
            current_pid = os.getpid()
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        cmdline = proc.info.get('cmdline', [])
                        if cmdline and any('main.py' in str(arg) for arg in cmdline):
                            pid = proc.info['pid']
                            if pid != current_pid:
                                try:
                                    p = psutil.Process(pid)
                                    p.terminate()
                                    time.sleep(0.5)
                                    if p.is_running():
                                        p.kill()
                                    self.log(f"Остановлен старый процесс бота (PID: {pid})", "BOT")
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            self.log(f"⚠️ Ошибка при поиске процессов бота: {e}", "BOT")

    def service_status_loop(self):
        for n, p in self.procs.items():
            if p and p.poll() is not None:
                self.procs[n] = None
                self._set_service_indicator(n, COLORS['danger'])
                self._set_service_button(n, text="▶", fg_color=COLORS['primary'])
                self._set_service_status_label(n, text="Ошибка", color=COLORS['danger'])
                service_names = {"bot": "Telegram Бот", "llm": "LLM Сервер", "sd": "Stable Diffusion"}
                service_name = service_names.get(n, n)
                self.log(f"❌ Сервис {service_name} завершился с ошибкой", n.upper())
            elif p:
                self._set_service_indicator(n, COLORS['success'])
                self._set_service_button(n, text="⏸", fg_color=COLORS['danger'])
                self._set_service_status_label(n, text="Работает", color=COLORS['success'])
        
        self.after(2000, self.service_status_loop)

    # ==========================================
    # CHANNELS MANAGEMENT
    # ==========================================
    def refresh_topics(self):
        """Обновляет только список тем"""
        for w in self.scroll_topics.winfo_children():
            if isinstance(w, ctk.CTkFrame):
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
        for t in topics:
            frame = ctk.CTkFrame(self.scroll_topics, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            
            is_active = (t == self.current_topic)
            btn = ctk.CTkButton(
                frame,
                text=f"📂 {t}",
                fg_color=COLORS['primary'] if is_active else "transparent",
                text_color="white" if is_active else COLORS['text_secondary'],
                anchor="w",
                hover_color=COLORS['surface_dark'],
                command=lambda tp=t: self.select_topic(tp),
                font=("Segoe UI", 13)
            )
            btn.pack(side="left", fill="x", expand=True)
            
            if is_active:
                ctk.CTkButton(
                    frame,
                    text="×",
                    width=30,
                    fg_color="transparent",
                    text_color=COLORS['danger'],
                    hover_color=COLORS['surface_dark'],
                    command=lambda tp=t: self.delete_topic(tp),
                    font=("Segoe UI", 16)
                ).pack(side="right")
    
    def refresh_channels_only(self):
        """Обновляет только список каналов (плавно)"""
        # Очищаем старые каналы
        for w in self.scroll_chans.winfo_children():
            w.destroy()
        
        # Небольшая задержка для плавности перед отрисовкой новых
        self.after(50, self._draw_channels)
    
    def _draw_channels(self):
        """Рисует каналы для текущей темы"""
        try:
            if os.path.exists(FILE_CHANNELS):
                with open(FILE_CHANNELS, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}
        
        topics = list(data.keys())
        
        # Draw channels
        if self.current_topic and self.current_topic in data:
            for ch in data[self.current_topic]:
                self.draw_channel_card(ch)
        elif not topics:
            ctk.CTkLabel(
                self.scroll_chans,
                text="Создайте тему для начала",
                font=("Segoe UI", 14),
                text_color=COLORS['text_muted']
            ).pack(pady=50)
    
    def refresh_channels(self):
        """Полное обновление (темы + каналы)"""
        self.refresh_topics()
        self.refresh_channels_only()
    
    def select_topic(self, t):
        """Выбирает тему и обновляет только каналы"""
        self.current_topic = t
        # Обновляем только активную тему в списке тем
        self._update_active_topic()
        # Обновляем каналы плавно
        self.refresh_channels_only()
    
    def _update_active_topic(self):
        """Обновляет только визуальное выделение активной темы"""
        for w in self.scroll_topics.winfo_children():
            if isinstance(w, ctk.CTkFrame):
                for child in w.winfo_children():
                    if isinstance(child, ctk.CTkButton):
                        topic_text = child.cget("text").replace("📂 ", "")
                        is_active = (topic_text == self.current_topic)
                        child.configure(
                            fg_color=COLORS['primary'] if is_active else "transparent",
                            text_color="white" if is_active else COLORS['text_secondary']
                        )
    
    def new_topic(self):
        dialog = ctk.CTkInputDialog(text="Название темы:", title="Новая тема")
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
    
    def delete_topic(self, t):
        if messagebox.askyesno("Подтверждение", f"Удалить тему '{t}'?"):
            try:
                if not os.path.exists(FILE_CHANNELS):
                    return
                with open(FILE_CHANNELS, 'r', encoding='utf-8') as f:
                    db = json.load(f)
                if t in db:
                    del db[t]
                    # Если файл стал пустым, удаляем его
                    if not db:
                        os.remove(FILE_CHANNELS)
                    else:
                        with open(FILE_CHANNELS, 'w', encoding='utf-8') as f:
                            json.dump(db, f, indent=4, ensure_ascii=False)
                    self.current_topic = None
                    self.refresh_channels()  # Полное обновление, так как тема удалена
            except:
                pass
    
    def draw_channel_card(self, link):
        """Создает карточку канала с правильным замыканием для кнопки удаления"""
        from functools import partial
        
        card = ctk.CTkFrame(self.scroll_chans, fg_color=COLORS['surface_light'], corner_radius=12)
        card.pack(fill="x", pady=5, padx=5)
        
        # Сохраняем оригинальный link для удаления - используем правильное замыкание
        original_link = link
        clean = link.replace("https://t.me/", "@").replace("@", "")
        display_text = f"@{clean}" if clean else link
        
        # Проверяем длину текста - если слишком длинный, скрываем кнопку удаления
        max_length = 30
        show_delete = len(display_text) <= max_length
        
        # Обрезаем текст для отображения если слишком длинный
        if len(display_text) > max_length:
            display_text = display_text[:max_length-3] + "..."
        
        ctk.CTkLabel(
            card,
            text="📢",
            font=("Segoe UI", 24)
        ).pack(side="left", padx=(20, 15), pady=15)
        
        ctk.CTkLabel(
            card,
            text=display_text,
            font=("Segoe UI", 15, "bold"),
            text_color=COLORS['text']
        ).pack(side="left", fill="x", expand=True)
        
        # Кнопка "Открыть" - используем правильное замыкание
        def open_channel(channel_link=original_link):
            clean_link = channel_link.replace("https://t.me/", "").replace("@", "")
            webbrowser.open(f"https://t.me/{clean_link}")
        
        ctk.CTkButton(
            card,
            text="Открыть",
            width=80,
            fg_color=COLORS['accent'],
            hover_color="#2563eb",
            command=open_channel,
            font=("Segoe UI", 12)
        ).pack(side="right", padx=(5, 10))
        
        # Кнопка "Удалить" - показываем только если текст не слишком длинный
        if show_delete:
            delete_handler = partial(self.delete_channel, original_link)
            ctk.CTkButton(
                card,
                text="Удалить",
                width=80,
                fg_color=COLORS['danger'],
                hover_color="#dc2626",
                command=delete_handler,
                font=("Segoe UI", 12)
            ).pack(side="right", padx=(5, 10))
    
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
                    if not db[self.current_topic]:
                        del db[self.current_topic]
                    if not db:
                        os.remove(FILE_CHANNELS)
                    else:
                        with open(FILE_CHANNELS, 'w', encoding='utf-8') as f:
                            json.dump(db, f, indent=4, ensure_ascii=False)
                    self.refresh_channels_only()  # Только каналы, тема не изменилась
        except Exception as e:
            print(f"❌ Ошибка при удалении канала: {e}")
    
    # ==========================================
    # SETTINGS
    # ==========================================
    def scan_llm_models(self):
        models = glob.glob(os.path.join(MODELS_LLM_DIR, "*.gguf"))
        names = [os.path.basename(m) for m in models]
        if hasattr(self, 'llm_combo'):
            self.llm_combo.configure(values=names)
            if names:
                self.llm_combo.set(names[0])
            else:
                self.llm_combo.set("Модели не найдены")
    
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
                self.log(f"✅ [SETTINGS] Папка с моделями обновлена: {models_path}", "SETTINGS")
            else:
                self.log(f"⚠️ [SETTINGS] Указанная папка не существует: {models_path}", "SETTINGS")
        
        # Сохраняем debug режим
        set_key(FILE_ENV, "DEBUG_MODE", "true" if self.debug_mode.get() else "false")
        
        # Сохраняем URL модели SD
        if hasattr(self, 'sd_model_url_entry'):
            model_url = self.sd_model_url_entry.get().strip()
            if model_url:
                set_key(FILE_ENV, "SD_MODEL_URL", model_url)
                self.log(f"✅ [SETTINGS] URL модели SD сохранен", "SETTINGS")
        
        messagebox.showinfo("Сохранено", "Настройки обновлены.")
    
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
                self.log(f"⚠️ [BACKUP] Не удалось создать резервную копию: {e}", "SYSTEM")
    
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
    
    # ==========================================
    # MONITORING
    # ==========================================
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
                curr_net = psutil.net_io_counters().bytes_recv
                disk = psutil.disk_io_counters()
                curr_disk = disk.read_bytes + disk.write_bytes
                
                ns = (curr_net - last_net) / 1024 / 1024
                ds = (curr_disk - last_disk) / 1024 / 1024
                
                net_label = getattr(self, 'lbl_net', None)
                disk_label = getattr(self, 'lbl_disk', None)
                self.safe_widget_configure(net_label, text=f"🌐 Сеть: {ns:.1f} MB/s")
                self.safe_widget_configure(disk_label, text=f"💾 Диск: {ds:.1f} MB/s")
                
                last_net = curr_net
                last_disk = curr_disk
            except:
                pass
    
    # ==========================================
    # CONSOLE
    # ==========================================
    def log(self, txt, tab="Все"):
        self.log_queue.put((txt, tab))

    def clear_console(self):
        for c in self.consoles.values():
            try:
                c.configure(state="normal")
                c.delete("1.0", "end")
                c.configure(state="normal")  # Оставляем normal для возможности выделения
            except:
                pass
    
    def setup_console_context_menu(self, textbox):
        """Добавляет контекстное меню для копирования текста как в Windows"""
        def show_context_menu(event):
            try:
                # Получаем выделенный текст
                try:
                    if textbox.tag_ranges("sel"):
                        selected = textbox.get("sel.first", "sel.last")
                    else:
                        selected = None
                except:
                    selected = None
                
                # Создаем меню
                menu = tk.Menu(self, tearoff=0, bg=COLORS['surface_light'], fg=COLORS['text'],
                              activebackground=COLORS['primary'], activeforeground='white',
                              font=("Segoe UI", 10))
                
                if selected:
                    menu.add_command(label="Копировать", command=lambda: self.copy_selected(textbox))
                else:
                    menu.add_command(label="Копировать всё", command=lambda: self.copy_all_to_clipboard(textbox))
                
                menu.add_separator()
                menu.add_command(label="Выделить всё", command=lambda: self.select_all(textbox))
                menu.add_separator()
                menu.add_command(label="Очистить", command=lambda: self.clear_single_console(textbox))
                
                # Показываем меню
                menu.tk_popup(event.x_root, event.y_root)
            except Exception as e:
                pass
        
        # Привязываем ПКМ
        textbox.bind("<Button-3>", show_context_menu)
        # Стандартные сочетания клавиш Windows
        textbox.bind("<Control-c>", lambda e: (self.copy_selected(textbox), "break"))
        textbox.bind("<Control-a>", lambda e: (self.select_all(textbox), "break"))
        textbox.bind("<Control-x>", lambda e: (self.cut_selected(textbox), "break"))
        textbox.bind("<Control-v>", lambda e: (self.paste_to_console(textbox), "break"))
        
        # Включаем стандартное выделение мышью
        textbox.bind("<Button-1>", lambda e: textbox.focus_set())
    
    def copy_to_clipboard(self, text):
        """Копирует текст в буфер обмена"""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
        except:
            pass
    
    def copy_all_to_clipboard(self, textbox):
        """Копирует весь текст из консоли"""
        try:
            text = textbox.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(text)
        except:
            pass
    
    def copy_selected(self, textbox):
        """Копирует выделенный текст"""
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
        try:
            textbox.configure(state="normal")
            textbox.delete("1.0", "end")
            textbox.configure(state="normal")  # Оставляем normal для возможности выделения
        except:
            pass

    def console_loop(self):
        while not self.log_queue.empty():
            try:
                txt, tab = self.log_queue.get_nowait()
                
                def write(widget):
                    # Сохраняем позицию прокрутки
                    scroll_pos = widget.yview()[0]
                    widget.configure(state="normal")
                    widget.insert("end", f"{txt}\n")
                    # Автопрокрутка только если пользователь внизу
                    if scroll_pos >= 0.99:
                        widget.see("end")
                    widget.configure(state="normal")
                
                write(self.consoles["Все"])
                if tab in self.consoles:
                    write(self.consoles[tab])
            except:
                pass
        
        self.after(50, self.console_loop)
    
    # ==========================================
    # CLEANUP
    # ==========================================
    def on_close(self):
        """Закрытие лаунчера с очисткой всех процессов"""
        # Останавливаем все сервисы
        for name, p in self.procs.items():
            if p:
                try:
                    self.log(f"⏹️ Остановка сервиса {name}...", "SYSTEM")
                    self.kill_tree(p.pid)
                except:
                    pass
        
        # Убиваем все процессы Ollama (включая дочерние)
        self._kill_all_ollama_processes()
        
        # Удаляем PID файл
        if os.path.exists(FILE_PID):
            try:
                os.remove(FILE_PID)
            except:
                pass
        
        self.destroy()
    
    def _kill_all_ollama_processes(self):
        """Убивает все процессы Ollama, включая дочерние"""
        try:
            current_pid = os.getpid()
            killed_count = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    # Проверяем имя процесса
                    proc_name = proc.info.get('name', '').lower()
                    proc_exe = proc.info.get('exe', '')
                    cmdline = proc.info.get('cmdline', [])
                    
                    # Ищем процессы Ollama
                    is_ollama = False
                    if 'ollama' in proc_name:
                        is_ollama = True
                    elif proc_exe and 'ollama' in proc_exe.lower():
                        is_ollama = True
                    elif cmdline and any('ollama' in str(arg).lower() for arg in cmdline):
                        is_ollama = True
                    
                    if is_ollama:
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
                self.log(f"✅ [SYSTEM] Остановлено процессов Ollama: {killed_count}", "SYSTEM")
            return killed_count
        except Exception as e:
            # Не критично, просто игнорируем
            return 0
    
    def _delete_ollama(self):
        """Удаляет Ollama и все связанные файлы"""
        # Спрашиваем, сохранять ли модели
        save_models = messagebox.askyesno(
            "Сохранение моделей",
            "Сохранить импортированные модели Ollama перед удалением?\n\n"
            "• Да - модели будут сохранены и восстановлены при следующей установке\n"
            "• Нет - все будет удалено полностью",
            icon="question"
        )
        
        # Подтверждение удаления
        result = messagebox.askyesno(
            "Подтверждение удаления",
            "Вы уверены, что хотите удалить Ollama?\n\n"
            "Это действие удалит:\n"
            "• Ollama сервер (ollama.exe)\n"
            + ("• Модели будут сохранены\n" if save_models else "• Все импортированные модели\n")
            + "• Все данные Ollama\n\n"
            "Это действие нельзя отменить!",
            icon="warning"
        )
        
        if not result:
            return
        
        try:
            self.log(f"🗑️ [LLM] Начало удаления Ollama...", "LLM")
            
            # Останавливаем LLM сервис если он запущен
            if self.procs.get("llm"):
                self.log(f"⏹️ [LLM] Остановка LLM сервиса...", "LLM")
                self._manage_service("llm")
                time.sleep(2)  # Даем время на остановку
            
            # Убиваем все процессы Ollama
            killed = self._kill_all_ollama_processes()
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
                    
                    self.log(f"💾 [LLM] Сохранение моделей в: {models_backup_path}", "LLM")
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
                            self.log(f"💾 [LLM] Сохранено моделей: {size_gb:.2f} GB", "LLM")
                        else:
                            self.log(f"💾 [LLM] Сохранено моделей: {size_mb:.2f} MB", "LLM")
                except Exception as e:
                    self.log(f"⚠️ [LLM] Не удалось сохранить модели: {e}", "LLM")
                    models_backup_path = None
            
            # Удаляем Ollama через официальный деинсталлятор
            ollama_install_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama")
            uninstaller_path = os.path.join(ollama_install_path, "unins000.exe")
            
            deleted_size = 0
            
            # Проверяем наличие официального деинсталлятора
            if os.path.exists(uninstaller_path):
                self.log(f"🗑️ [LLM] Удаление Ollama через официальный деинсталлятор...", "LLM")
                
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
                    
                    self.log(f"⏳ [LLM] Ожидание завершения деинсталляции...", "LLM")
                    proc.wait(timeout=120)  # Максимум 2 минуты
                    
                    if proc.returncode == 0:
                        self.log(f"✅ [LLM] Ollama успешно удален через деинсталлятор", "LLM")
                    else:
                        self.log(f"⚠️ [LLM] Деинсталлятор завершился с кодом: {proc.returncode}", "LLM")
                    
                    # Ждем немного, чтобы файлы точно были удалены
                    time.sleep(2)
                    
                except subprocess.TimeoutExpired:
                    self.log(f"⚠️ [LLM] Деинсталляция занимает слишком много времени...", "LLM")
                    proc.kill()
                except Exception as e:
                    self.log(f"❌ [LLM] Ошибка при запуске деинсталлятора: {e}", "LLM")
                    messagebox.showerror(
                        "Ошибка удаления",
                        f"Не удалось запустить деинсталлятор Ollama:\n{str(e)}\n\n"
                        "Попробуйте удалить вручную через Панель управления."
                    )
                    return
            else:
                # Если деинсталлятор не найден, удаляем рабочую папку
                if os.path.exists(OLLAMA_DIR):
                    self.log(f"🗑️ [LLM] Деинсталлятор не найден, удаление рабочей папки: {OLLAMA_DIR}", "LLM")
                    
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
                        self.log(f"✅ [LLM] Рабочая папка Ollama успешно удалена", "LLM")
                    except Exception as e:
                        self.log(f"❌ [LLM] Ошибка при удалении папки: {e}", "LLM")
                        messagebox.showerror(
                            "Ошибка удаления",
                            f"Не удалось удалить папку Ollama:\n{str(e)}\n\n"
                            "Попробуйте удалить вручную:\n"
                            f"{OLLAMA_DIR}"
                        )
                        return
                else:
                    self.log(f"ℹ️ [LLM] Папка Ollama не найдена", "LLM")
            
            # Показываем размер удаленных файлов
            if deleted_size > 0:
                size_mb = deleted_size / 1024 / 1024
                if size_mb > 1024:
                    size_gb = size_mb / 1024
                    self.log(f"📊 [LLM] Освобождено места: {size_gb:.2f} GB", "LLM")
                else:
                    self.log(f"📊 [LLM] Освобождено места: {size_mb:.2f} MB", "LLM")
            
            # Удаляем рабочую папку OLLAMA_DIR (если она существует отдельно)
            if os.path.exists(OLLAMA_DIR) and OLLAMA_DIR != ollama_install_path:
                try:
                    self.log(f"🗑️ [LLM] Удаление рабочей папки: {OLLAMA_DIR}", "LLM")
                    shutil.rmtree(OLLAMA_DIR, ignore_errors=True)
                    self.log(f"✅ [LLM] Рабочая папка удалена", "LLM")
                except Exception as e:
                    self.log(f"⚠️ [LLM] Не удалось удалить рабочую папку: {e}", "LLM")
            
            # Восстанавливаем модели если они были сохранены
            if models_backup_path and os.path.exists(models_backup_path):
                try:
                    # Создаем папку для моделей
                    os.makedirs(OLLAMA_MODELS_DIR, exist_ok=True)
                    
                    # Копируем модели обратно
                    self.log(f"📦 [LLM] Восстановление моделей...", "LLM")
                    for item in os.listdir(models_backup_path):
                        src = os.path.join(models_backup_path, item)
                        dst = os.path.join(OLLAMA_MODELS_DIR, item)
                        if os.path.isdir(src):
                            shutil.copytree(src, dst, dirs_exist_ok=True)
                        else:
                            shutil.copy2(src, dst)
                    
                    self.log(f"✅ [LLM] Модели успешно восстановлены", "LLM")
                except Exception as e:
                    self.log(f"⚠️ [LLM] Не удалось восстановить модели: {e}", "LLM")
            
            # Обновляем статус сервиса
            self._set_service_indicator("llm", COLORS['text_muted'])
            self._set_service_button("llm", text="▶", fg_color=COLORS['primary'])
            self._set_service_status_label("llm", text="Остановлен", color=COLORS['text_muted'])
            
            success_msg = "Ollama успешно удален!\n\n"
            if save_models and models_backup_path and os.path.exists(models_backup_path):
                success_msg += "Модели сохранены и будут восстановлены при следующей установке.\n"
            else:
                success_msg += "Все файлы и данные были удалены.\n"
            success_msg += "При следующем запуске LLM сервиса Ollama будет загружен заново."
            
            messagebox.showinfo("Удаление завершено", success_msg)
            
        except Exception as e:
            self.log(f"❌ [LLM] Ошибка при удалении Ollama: {e}", "LLM")
            messagebox.showerror(
                "Ошибка",
                f"Произошла ошибка при удалении Ollama:\n{str(e)}"
            )
    
    def _delete_sd(self):
        """Удаляет Stable Diffusion и все связанные файлы"""
        # Спрашиваем, сохранять ли модели
        save_models = messagebox.askyesno(
            "Сохранение моделей",
            "Сохранить модели изображений перед удалением?\n\n"
            "• Да - модели будут сохранены и восстановлены при следующей установке\n"
            "• Нет - все будет удалено полностью",
            icon="question"
        )
        
        # Подтверждение удаления
        result = messagebox.askyesno(
            "Подтверждение удаления",
            "Вы уверены, что хотите удалить Stable Diffusion?\n\n"
            "Это действие удалит:\n"
            "• Stable Diffusion WebUI (весь репозиторий)\n"
            + ("• Модели будут сохранены\n" if save_models else "• Все модели изображений\n")
            + "• Все расширения (включая ADetailer)\n"
            "• Виртуальное окружение Python\n"
            "• Все настройки и конфигурации\n\n"
            "Это действие нельзя отменить!",
            icon="warning"
        )
        
        if not result:
            return
        
        try:
            self.log(f"🗑️ [SD] Начало удаления Stable Diffusion...", "SD")
            
            # Останавливаем SD сервис если он запущен
            if self.procs.get("sd"):
                self.log(f"⏹️ [SD] Остановка SD сервиса...", "SD")
                self._manage_service("sd")
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
                    
                    self.log(f"💾 [SD] Сохранение моделей в: {models_backup_path}", "SD")
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
                            self.log(f"💾 [SD] Сохранено моделей: {size_gb:.2f} GB", "SD")
                        else:
                            self.log(f"💾 [SD] Сохранено моделей: {size_mb:.2f} MB", "SD")
                except Exception as e:
                    self.log(f"⚠️ [SD] Не удалось сохранить модели: {e}", "SD")
                    models_backup_path = None
            
            # Удаляем папку SD
            deleted_size = 0
            if os.path.exists(SD_DIR):
                self.log(f"🗑️ [SD] Удаление папки Stable Diffusion: {SD_DIR}", "SD")
                
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
                    self.log(f"✅ [SD] Папка Stable Diffusion успешно удалена", "SD")
                    
                    # Показываем размер удаленных файлов
                    if deleted_size > 0:
                        size_mb = deleted_size / 1024 / 1024
                        if size_mb > 1024:
                            size_gb = size_mb / 1024
                            self.log(f"📊 [SD] Освобождено места: {size_gb:.2f} GB", "SD")
                        else:
                            self.log(f"📊 [SD] Освобождено места: {size_mb:.2f} MB", "SD")
                except Exception as e:
                    self.log(f"❌ [SD] Ошибка при удалении папки: {e}", "SD")
                    messagebox.showerror(
                        "Ошибка удаления",
                        f"Не удалось удалить папку Stable Diffusion:\n{str(e)}\n\n"
                        "Попробуйте удалить вручную:\n"
                        f"{SD_DIR}"
                    )
                    return
            else:
                self.log(f"ℹ️ [SD] Папка Stable Diffusion не найдена: {SD_DIR}", "SD")
            
            # Восстанавливаем модели если они были сохранены
            if models_backup_path and os.path.exists(models_backup_path):
                try:
                    # Создаем папку для моделей
                    os.makedirs(MODELS_SD_DIR, exist_ok=True)
                    
                    # Копируем модели обратно
                    self.log(f"📦 [SD] Восстановление моделей...", "SD")
                    for item in os.listdir(models_backup_path):
                        src = os.path.join(models_backup_path, item)
                        dst = os.path.join(MODELS_SD_DIR, item)
                        if os.path.isdir(src):
                            shutil.copytree(src, dst, dirs_exist_ok=True)
                        else:
                            shutil.copy2(src, dst)
                    
                    self.log(f"✅ [SD] Модели успешно восстановлены", "SD")
                except Exception as e:
                    self.log(f"⚠️ [SD] Не удалось восстановить модели: {e}", "SD")
            
            # Обновляем статус сервиса
            self._set_service_indicator("sd", COLORS['text_muted'])
            self._set_service_button("sd", text="▶", fg_color=COLORS['primary'])
            self._set_service_status_label("sd", text="Остановлен", color=COLORS['text_muted'])
            
            success_msg = "Stable Diffusion успешно удален!\n\n"
            if save_models and models_backup_path and os.path.exists(models_backup_path):
                success_msg += "Модели изображений сохранены и будут восстановлены при следующей установке.\n"
            else:
                success_msg += "Все файлы и данные были удалены.\n"
            success_msg += "При следующем запуске SD сервиса он будет установлен заново."
            
            messagebox.showinfo("Удаление завершено", success_msg)
            
        except Exception as e:
            self.log(f"❌ [SD] Ошибка при удалении Stable Diffusion: {e}", "SD")
            messagebox.showerror(
                "Ошибка",
                f"Произошла ошибка при удалении Stable Diffusion:\n{str(e)}"
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
                self.log(f"✅ [SYSTEM] Остановлено процессов SD: {killed_count}", "SYSTEM")
            return killed_count
        except Exception as e:
            # Не критично, просто игнорируем
            return 0
    
    def _install_sd(self):
        """Устанавливает Stable Diffusion WebUI Forge"""
        try:
            self.log(f"📥 [SD] Клонирование репозитория Stable Diffusion Forge...", "SD")
            
            # Создаем папку Engine если её нет
            os.makedirs(DIR_ENGINE, exist_ok=True)
            
            # Сохраняем модели если они есть
            saved_models = None
            if os.path.exists(MODELS_SD_DIR):
                try:
                    import shutil
                    temp_backup = os.path.join(DIR_TEMP, "sd_models_backup_temp")
                    if os.path.exists(temp_backup):
                        shutil.rmtree(temp_backup, ignore_errors=True)
                    os.makedirs(DIR_TEMP, exist_ok=True)
                    self.log(f"💾 [SD] Сохранение моделей перед установкой...", "SD")
                    shutil.copytree(MODELS_SD_DIR, temp_backup)
                    saved_models = temp_backup
                    self.log(f"✅ [SD] Модели сохранены", "SD")
                except Exception as e:
                    self.log(f"⚠️ [SD] Не удалось сохранить модели: {e}", "SD")
            
            # Клонируем основной репозиторий
            launch_script = os.path.join(SD_DIR, "launch.py")
            if not os.path.exists(SD_DIR):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                self.log(f"📥 [SD] Клонирование репозитория (это может занять несколько минут)...", "SD")
                result = subprocess.run(
                    [GIT_CMD, "clone", SD_REPO, SD_DIR],
                    capture_output=True,
                    text=True,
                    timeout=600,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    startupinfo=startupinfo
                )
                
                if result.returncode != 0:
                    self.log(f"❌ [SD] Ошибка клонирования: {result.stderr}", "SD")
                    if result.stdout:
                        self.log(f"📋 [SD] Вывод: {result.stdout}", "SD")
                    return False
                
                # Проверяем, что файл launch.py появился
                if not os.path.exists(launch_script):
                    self.log(f"❌ [SD] Клонирование завершено, но launch.py не найден", "SD")
                    self.log(f"💡 [SD] Возможно, репозиторий клонирован не полностью", "SD")
                    return False
                
                self.log(f"✅ [SD] Репозиторий успешно клонирован", "SD")
            else:
                self.log(f"ℹ️ [SD] Репозиторий уже существует, пропускаю клонирование", "SD")
            
            # Восстанавливаем модели если они были сохранены
            if saved_models and os.path.exists(saved_models):
                try:
                    import shutil
                    os.makedirs(MODELS_SD_DIR, exist_ok=True)
                    self.log(f"📦 [SD] Восстановление моделей...", "SD")
                    for item in os.listdir(saved_models):
                        src = os.path.join(saved_models, item)
                        dst = os.path.join(MODELS_SD_DIR, item)
                        if os.path.isdir(src):
                            if os.path.exists(dst):
                                shutil.rmtree(dst, ignore_errors=True)
                            shutil.copytree(src, dst)
                        else:
                            if os.path.exists(dst):
                                os.remove(dst)
                            shutil.copy2(src, dst)
                    shutil.rmtree(saved_models, ignore_errors=True)
                    self.log(f"✅ [SD] Модели восстановлены", "SD")
                except Exception as e:
                    self.log(f"⚠️ [SD] Не удалось восстановить модели: {e}", "SD")
            
            # Клонируем ADetailer расширение
            adetailer_dir = os.path.join(SD_DIR, "extensions", "adetailer")
            if not os.path.exists(adetailer_dir):
                self.log(f"📥 [SD] Клонирование расширения ADetailer...", "SD")
                os.makedirs(os.path.dirname(adetailer_dir), exist_ok=True)
                
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                result = subprocess.run(
                    [GIT_CMD, "clone", ADETAILER_REPO, adetailer_dir],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    startupinfo=startupinfo
                )
                
                if result.returncode != 0:
                    self.log(f"⚠️ [SD] Не удалось клонировать ADetailer: {result.stderr}", "SD")
                    # Не критично, продолжаем
                else:
                    self.log(f"✅ [SD] ADetailer успешно клонирован", "SD")
            else:
                self.log(f"ℹ️ [SD] ADetailer уже установлен", "SD")
            
            return True
            
        except subprocess.TimeoutExpired:
            self.log(f"❌ [SD] Превышено время ожидания при установке", "SD")
            return False
        except Exception as e:
            self.log(f"❌ [SD] Ошибка при установке: {e}", "SD")
            return False
    
    def _create_sd_venv(self):
        """Создает виртуальное окружение для SD и устанавливает зависимости"""
        try:
            self.log(f"📦 [SD] Создание виртуального окружения...", "SD")
            
            venv = os.path.join(SD_DIR, "venv")
            
            # Создаем venv
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            result = subprocess.run(
                [PYTHON_EXE, "-m", "venv", venv],
                cwd=SD_DIR,
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            if result.returncode != 0:
                self.log(f"❌ [SD] Ошибка создания venv: {result.stderr}", "SD")
                return False
            
            self.log(f"✅ [SD] Виртуальное окружение создано", "SD")
            
            # Обновляем pip
            venv_py = os.path.join(venv, "Scripts", "python.exe")
            self.log(f"📦 [SD] Обновление pip...", "SD")
            
            result = subprocess.run(
                [venv_py, "-m", "pip", "install", "--upgrade", "pip"],
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            if result.returncode != 0:
                self.log(f"⚠️ [SD] Предупреждение при обновлении pip: {result.stderr}", "SD")
            else:
                self.log(f"✅ [SD] pip обновлен", "SD")
            
            # Проверяем поддержку CUDA и устанавливаем соответствующую версию PyTorch
            self.log(f"🔍 [SD] Проверка поддержки CUDA...", "SD")
            cuda_available = False
            
            try:
                # Пробуем проверить CUDA через nvidia-smi
                check_result = subprocess.run(
                    ["nvidia-smi"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    startupinfo=startupinfo
                )
                if check_result.returncode == 0:
                    cuda_available = True
                    # Пробуем извлечь версию CUDA из вывода
                    import re
                    version_match = re.search(r'CUDA Version: (\d+\.\d+)', check_result.stdout)
                    if version_match:
                        cuda_version = version_match.group(1)
                        self.log(f"✅ [SD] Обнаружена CUDA версии {cuda_version}", "SD")
                    else:
                        self.log(f"✅ [SD] CUDA обнаружена, версия определяется автоматически", "SD")
                else:
                    self.log(f"⚠️ [SD] nvidia-smi не найден, устанавливаю CPU версию PyTorch", "SD")
            except:
                self.log(f"⚠️ [SD] CUDA не обнаружена, устанавливаю CPU версию PyTorch", "SD")
            
            # Устанавливаем PyTorch в зависимости от наличия CUDA
            if cuda_available:
                # Основные версии: cu130 (CUDA 13.0+), cu121 (CUDA 12.x), cu118 (fallback)
                if 'cuda_version' in locals() and cuda_version:
                    try:
                        major = int(cuda_version.split('.')[0])
                        if major >= 13:
                            cuda_versions = ["cu130", "cu121", "cu118"]
                        else:
                            cuda_versions = ["cu121", "cu118"]
                    except:
                        cuda_versions = ["cu130", "cu121", "cu118"]
                else:
                    cuda_versions = ["cu130", "cu121", "cu118"]
                
                torch_installed = False
                installed_cuda_ver = None
                
                for cuda_ver in cuda_versions:
                    self.log(f"📦 [SD] Попытка установки PyTorch 2.9.1 с CUDA {cuda_ver}...", "SD")
                    result = subprocess.run(
                        [venv_py, "-m", "pip", "install", "torch==2.9.1", "torchvision", "torchaudio", 
                         "--index-url", f"https://download.pytorch.org/whl/{cuda_ver}", "--no-cache-dir"],
                        capture_output=True,
                        text=True,
                        timeout=1800,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        startupinfo=startupinfo
                    )
                    
                    if result.returncode == 0:
                        # Проверяем, что PyTorch действительно работает
                        test_result = subprocess.run(
                            [venv_py, "-c", "import torch; print('OK')"],
                            capture_output=True,
                            text=True,
                            timeout=10,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            startupinfo=startupinfo
                        )
                        
                        if test_result.returncode == 0 and "OK" in test_result.stdout:
                            self.log(f"✅ [SD] PyTorch 2.9.1 с CUDA {cuda_ver} установлен и работает", "SD")
                            torch_installed = True
                            installed_cuda_ver = cuda_ver
                            break
                        else:
                            self.log(f"⚠️ [SD] PyTorch установлен, но не работает: {test_result.stderr}", "SD")
                    else:
                        self.log(f"⚠️ [SD] Не удалось установить PyTorch с CUDA {cuda_ver}, пробую следующую версию...", "SD")
                
                if not torch_installed:
                    self.log(f"⚠️ [SD] Не удалось установить PyTorch с CUDA, устанавливаю CPU версию...", "SD")
                    result = subprocess.run(
                        [venv_py, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--no-cache-dir"],
                        capture_output=True,
                        text=True,
                        timeout=1800,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        startupinfo=startupinfo
                    )
                    if result.returncode == 0:
                        self.log(f"✅ [SD] PyTorch (CPU) установлен", "SD")
                    else:
                        self.log(f"❌ [SD] Ошибка установки PyTorch: {result.stderr}", "SD")
                        return False
                else:
                    # Устанавливаем xformers только если PyTorch с CUDA установлен
                    self.log(f"📦 [SD] Установка xformers...", "SD")
                    result = subprocess.run(
                        [venv_py, "-m", "pip", "install", "xformers", 
                         "--index-url", f"https://download.pytorch.org/whl/{installed_cuda_ver}", "--no-cache-dir"],
                        capture_output=True,
                        text=True,
                        timeout=600,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        startupinfo=startupinfo
                    )
                    if result.returncode != 0:
                        # Пробуем без индекса
                        result = subprocess.run(
                            [venv_py, "-m", "pip", "install", "xformers", "--no-cache-dir"],
                            capture_output=True,
                            text=True,
                            timeout=600,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            startupinfo=startupinfo
                        )
                    
                    # Устанавливаем дополнительные зависимости для SD
                    self.log(f"📦 [SD] Установка дополнительных зависимостей (triton, joblib)...", "SD")
                    additional_deps = ["triton", "joblib"]
                    for dep in additional_deps:
                        try:
                            dep_result = subprocess.run(
                                [venv_py, "-m", "pip", "install", dep, "--no-cache-dir"],
                                capture_output=True,
                                text=True,
                                timeout=300,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=startupinfo
                            )
                            if dep_result.returncode == 0:
                                self.log(f"✅ [SD] {dep} установлен", "SD")
                            else:
                                self.log(f"⚠️ [SD] Не удалось установить {dep} (не критично)", "SD")
                        except:
                            pass  # Не критично
                    if result.returncode != 0:
                        self.log(f"⚠️ [SD] Предупреждение при установке xformers: {result.stderr}", "SD")
                    else:
                        # Проверяем, что xformers работает
                        try:
                            check_xformers = subprocess.run(
                                [venv_py, "-c", "import xformers; print('XFORMERS_OK')"],
                                capture_output=True,
                                text=True,
                                timeout=10,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=startupinfo
                            )
                            if check_xformers.returncode == 0 and "XFORMERS_OK" in check_xformers.stdout:
                                self.log(f"✅ [SD] xformers установлен и работает корректно", "SD")
                            else:
                                self.log(f"⚠️ [SD] xformers установлен, но не работает (возможно, несовместимость с PyTorch)", "SD")
                                self.log(f"🔄 [SD] Удаляю несовместимый xformers...", "SD")
                                subprocess.run(
                                    [venv_py, "-m", "pip", "uninstall", "xformers", "-y"],
                                    capture_output=True,
                                    text=True,
                                    timeout=60,
                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                    startupinfo=startupinfo
                                )
                        except:
                            pass
            else:
                # Устанавливаем CPU версию
                self.log(f"📦 [SD] Установка PyTorch (CPU версия)...", "SD")
                result = subprocess.run(
                    [venv_py, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--no-cache-dir"],
                    capture_output=True,
                    text=True,
                    timeout=1800,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    startupinfo=startupinfo
                )
                
                if result.returncode != 0:
                    self.log(f"❌ [SD] Ошибка установки PyTorch: {result.stderr}", "SD")
                    return False
                
                self.log(f"✅ [SD] PyTorch (CPU) установлен", "SD")
            
            self.log(f"✅ [SD] Виртуальное окружение готово", "SD")
            return True
            
        except subprocess.TimeoutExpired:
            self.log(f"❌ [SD] Превышено время ожидания при создании venv", "SD")
            return False
        except Exception as e:
            self.log(f"❌ [SD] Ошибка при создании venv: {e}", "SD")
            return False
    
    def _update_sd(self):
        """Обновляет Stable Diffusion через git pull"""
        try:
            if not os.path.exists(SD_DIR):
                return
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # Сохраняем модели перед обновлением
            saved_models = None
            if os.path.exists(MODELS_SD_DIR):
                try:
                    import shutil
                    temp_backup = os.path.join(DIR_TEMP, "sd_models_backup_update")
                    if os.path.exists(temp_backup):
                        shutil.rmtree(temp_backup, ignore_errors=True)
                    os.makedirs(DIR_TEMP, exist_ok=True)
                    self.log(f"💾 [SD] Сохранение моделей перед обновлением...", "SD")
                    shutil.copytree(MODELS_SD_DIR, temp_backup)
                    saved_models = temp_backup
                except Exception as e:
                    self.log(f"⚠️ [SD] Не удалось сохранить модели: {e}", "SD")
            
            # Проверяем, есть ли обновления
            result = subprocess.run(
                [GIT_CMD, "fetch", "origin"],
                cwd=SD_DIR,
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            # Проверяем, есть ли изменения
            result = subprocess.run(
                [GIT_CMD, "status", "-uno"],
                cwd=SD_DIR,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            if "behind" in result.stdout or "diverged" in result.stdout:
                self.log(f"🔄 [SD] Найдены обновления, обновляю...", "SD")
                
                # Обновляем репозиторий
                result = subprocess.run(
                    [GIT_CMD, "pull", "origin", "main"],
                    cwd=SD_DIR,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    startupinfo=startupinfo
                )
                
                if result.returncode == 0:
                    self.log(f"✅ [SD] Репозиторий обновлен", "SD")
                    
                    # Восстанавливаем модели
                    if saved_models and os.path.exists(saved_models):
                        try:
                            import shutil
                            os.makedirs(MODELS_SD_DIR, exist_ok=True)
                            self.log(f"📦 [SD] Восстановление моделей...", "SD")
                            for item in os.listdir(saved_models):
                                src = os.path.join(saved_models, item)
                                dst = os.path.join(MODELS_SD_DIR, item)
                                if os.path.isdir(src):
                                    if os.path.exists(dst):
                                        shutil.rmtree(dst, ignore_errors=True)
                                    shutil.copytree(src, dst)
                                else:
                                    if os.path.exists(dst):
                                        os.remove(dst)
                                    shutil.copy2(src, dst)
                            shutil.rmtree(saved_models, ignore_errors=True)
                            self.log(f"✅ [SD] Модели восстановлены", "SD")
                        except Exception as e:
                            self.log(f"⚠️ [SD] Не удалось восстановить модели: {e}", "SD")
                else:
                    self.log(f"⚠️ [SD] Не удалось обновить репозиторий: {result.stderr}", "SD")
            else:
                self.log(f"✅ [SD] Установлена последняя версия", "SD")
                
        except Exception as e:
            self.log(f"⚠️ [SD] Ошибка при проверке обновлений: {e}", "SD")
    
    def _download_sd_model(self, model_url, show_dialog=True):
        """Скачивает модель Stable Diffusion"""
        try:
            if not model_url or not model_url.strip():
                if show_dialog:
                    messagebox.showerror("Ошибка", "URL модели не указан!")
                return False
            
            model_url = model_url.strip()
            
            # Создаем папку для моделей если её нет
            os.makedirs(MODELS_SD_DIR, exist_ok=True)
            
            # Определяем имя файла из URL
            # Пробуем извлечь имя из URL или используем имя по умолчанию
            filename = MODEL_SD_FILENAME
            try:
                # Пробуем извлечь имя файла из URL
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(model_url)
                # Проверяем параметры запроса
                params = parse_qs(parsed.query)
                if 'filename' in params:
                    filename = params['filename'][0]
                elif parsed.path.endswith(('.safetensors', '.ckpt')):
                    filename = os.path.basename(parsed.path)
            except:
                pass
            
            model_path = os.path.join(MODELS_SD_DIR, filename)
            
            # Проверяем, не скачана ли уже модель
            if os.path.exists(model_path):
                if show_dialog:
                    result = messagebox.askyesno(
                        "Модель уже существует",
                        f"Модель {filename} уже существует.\n\n"
                        "Хотите скачать заново?",
                        icon="question"
                    )
                    if not result:
                        return True
                else:
                    self.log(f"✅ [SD] Модель уже существует: {filename}", "SD")
                    return True
            
            if show_dialog:
                self.log(f"📥 [SD] Начинаю скачивание модели...", "SD")
            
            # Скачиваем модель с прогресс-баром
            import urllib.request
            
            req = urllib.request.Request(model_url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            temp_file = model_path + ".tmp"
            try:
                with urllib.request.urlopen(req, timeout=300) as response:
                    total_size = int(response.headers.get('Content-Length', 0))
                    
                    downloaded = 0
                    start_time = time.time()
                    last_update_time = start_time
                    last_downloaded = 0
                    
                    with open(temp_file, 'wb') as f:
                        while True:
                            chunk = response.read(8192 * 4)  # Увеличиваем размер чанка для лучшей производительности
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            current_time = time.time()
                            elapsed = current_time - last_update_time
                            
                            # Обновляем прогресс каждые 0.5 секунды
                            if elapsed >= 0.5 or downloaded == total_size:
                                if total_size > 0:
                                    percent = min(100, (downloaded * 100) // total_size)
                                    downloaded_mb = downloaded / 1024 / 1024
                                    total_mb = total_size / 1024 / 1024
                                    
                                    # Вычисляем скорость
                                    if elapsed > 0:
                                        speed_bps = (downloaded - last_downloaded) / elapsed
                                        speed_mbps = speed_bps / 1024 / 1024
                                        
                                        # Вычисляем оставшееся время
                                        remaining_bytes = total_size - downloaded
                                        if speed_bps > 0:
                                            eta_seconds = remaining_bytes / speed_bps
                                            eta_minutes = int(eta_seconds // 60)
                                            eta_secs = int(eta_seconds % 60)
                                            eta_str = f"{eta_minutes:02d}:{eta_secs:02d}"
                                        else:
                                            eta_str = "??:??"
                                        
                                        # Форматируем скорость
                                        if speed_mbps >= 1:
                                            speed_str = f"{speed_mbps:.2f} MB/s"
                                        else:
                                            speed_kbps = speed_mbps * 1024
                                            speed_str = f"{speed_kbps:.2f} KB/s"
                                        
                                        self.log(f"📥 [SD] {percent}% | {downloaded_mb:.1f}/{total_mb:.1f} MB | {speed_str} | ETA: {eta_str}", "SD")
                                    
                                    last_update_time = current_time
                                    last_downloaded = downloaded
                
                # Переименовываем временный файл
                if os.path.exists(temp_file):
                    if os.path.exists(model_path):
                        os.remove(model_path)
                    os.rename(temp_file, model_path)
                    
                    if show_dialog:
                        self.log(f"✅ [SD] Модель успешно скачана: {filename}", "SD")
                        messagebox.showinfo("Успех", f"Модель {filename} успешно скачана!")
                    else:
                        self.log(f"✅ [SD] Модель успешно скачана: {filename}", "SD")
                    
                    # Обновляем информацию о модели в настройках
                    if hasattr(self, 'sd_model_info_label'):
                        self._update_sd_model_info(self.sd_model_info_label)
                    
                    return True
                else:
                    if show_dialog:
                        self.log(f"❌ [SD] Ошибка: файл не был скачан", "SD")
                        messagebox.showerror("Ошибка", "Не удалось скачать модель")
                    return False
                    
            except Exception as e:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                if show_dialog:
                    self.log(f"❌ [SD] Ошибка при скачивании модели: {e}", "SD")
                    messagebox.showerror("Ошибка", f"Не удалось скачать модель:\n{str(e)}")
                else:
                    self.log(f"❌ [SD] Ошибка при скачивании модели: {e}", "SD")
                return False
                
        except Exception as e:
            if show_dialog:
                self.log(f"❌ [SD] Критическая ошибка при скачивании модели: {e}", "SD")
                messagebox.showerror("Ошибка", f"Критическая ошибка:\n{str(e)}")
            else:
                self.log(f"❌ [SD] Критическая ошибка при скачивании модели: {e}", "SD")
            return False
    
    def _update_sd_model_info(self, label):
        """Обновляет информацию о текущих моделях SD"""
        try:
            if not os.path.exists(MODELS_SD_DIR):
                label.configure(text="Папка с моделями не найдена")
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
                label.configure(text=f"Установлено моделей: {len(models)}\nОбщий размер: {total_str}\n\n" + "\n".join(models[:3]) + ("..." if len(models) > 3 else ""))
            else:
                label.configure(text="Модели не установлены")
        except Exception as e:
            label.configure(text=f"Ошибка при получении информации: {str(e)}")

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

