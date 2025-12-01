import os
import subprocess
import sys
import threading
import time
import psutil
import queue
import urllib.request
from typing import Callable, Dict, Optional, Any

# Try relative import first, fallback to absolute
try:
    from .i18n import t
except (ImportError, ValueError):
    try:
        from i18n import t
    except ImportError:
        def t(key, default=None, **kwargs):
            return default or key

# Import config with fallback
try:
    from .config import (
        BASE_DIR, PYTHON_EXE, GIT_CMD, OLLAMA_EXE, OLLAMA_DIR, OLLAMA_MODELS_DIR,
        OLLAMA_DATA_DIR, SD_DIR, MODELS_SD_DIR, MODELS_LLM_DIR, FILE_ENV, DIR_CONFIGS, DIR_TEMP,
        USE_GPU
    )
except (ImportError, ValueError):
    from config import (
        BASE_DIR, PYTHON_EXE, GIT_CMD, OLLAMA_EXE, OLLAMA_DIR, OLLAMA_MODELS_DIR,
        OLLAMA_DATA_DIR, SD_DIR, MODELS_SD_DIR, MODELS_LLM_DIR, FILE_ENV, DIR_CONFIGS, DIR_TEMP,
        USE_GPU
    )

# Import other modules with fallback
try:
    from .installer import Installer
    from .model_manager import ModelManager
except (ImportError, ValueError):
    from installer import Installer
    from model_manager import ModelManager

class ServiceManager:
    def __init__(self, log_callback: Callable[[str, str], None], 
                 status_callback: Callable[[str, str, str], None],
                 installer: Installer,
                 log_queue: queue.Queue):
        self.log = log_callback
        self.update_status = status_callback
        self.installer = installer
        self.log_queue = log_queue
        self.procs = {"bot": None, "llm": None, "sd": None}
        self.stop_events = {k: threading.Event() for k in self.procs}
        self.selected_llm_model = None
        self.model_manager = ModelManager(log_callback=log_callback)

    def _get_service_name(self, key: str) -> str:
        """Get localized service name"""
        names = {
            "bot": t("ui.launcher.service.telegram_bot", default="Telegram Bot"),
            "llm": t("ui.launcher.service.llm_server", default="LLM Server"),
            "sd": t("ui.launcher.service.stable_diffusion", default="Stable Diffusion")
        }
        return names.get(key, key.upper())

    def kill_tree(self, pid):
        """Kill process and all its children recursively with extreme prejudice"""
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            # Add parent to the list
            children.append(parent)
            
            # First try graceful termination
            for p in children:
                try:
                    p.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Wait for them to die
            gone, alive = psutil.wait_procs(children, timeout=3)
            
            # Force kill the survivors
            for p in alive:
                try:
                    p.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    def stop_all_services(self):
        """Stops all running services"""
        self.log(t("ui.launcher.log.stopping_all", default="🛑 Stopping all services..."), "SYSTEM")
        
        # Stop in reverse order of dependency (Bot -> SD -> LLM)
        threads = []
        for service in ["bot", "sd", "llm"]:
            if self.procs.get(service):
                t = threading.Thread(target=self.stop_service, args=(service,))
                t.start()
                threads.append(t)
        
        for t in threads:
            t.join()
            
        self.log(t("ui.launcher.log.all_stopped", default="✅ All services stopped"), "SYSTEM")

    def start_all_services(self):
        """Starts all services sequentially"""
        def run():
            self.log(t("ui.launcher.log.starting_all", default="🚀 Starting all services..."), "SYSTEM")
            
            # Check for model selection for LLM
            # We need to pick a default model if none selected
            llm_model = None
            if self.selected_llm_model:
                 llm_model = self.selected_llm_model
            else:
                # Try to find a default model
                models = self.model_manager.get_ollama_models()
                if models:
                    # Prefer a model with '7b' or 'mistral' or 'llama'
                    for m in models:
                        if 'mistral' in m.lower() or 'llama' in m.lower():
                            llm_model = {'name': m, 'type': 'ollama'}
                            break
                    if not llm_model:
                        llm_model = {'name': models[0], 'type': 'ollama'}
            
            # Start LLM
            if llm_model:
                self.start_service("llm", llm_model)
                time.sleep(2) # Wait a bit
            else:
                self.log(t("ui.launcher.log.no_llm_model", default="⚠️ No LLM model found, skipping LLM start"), "LLM")
            
            # Start SD
            self.start_service("sd")
            time.sleep(5) # Give SD a head start
            
            # Start Bot
            self.start_service("bot")
            
        threading.Thread(target=run, daemon=True).start()

    def _kill_process_on_port(self, port: int):
        """Убивает процесс, занимающий указанный порт"""
        try:
            import socket
            # Проверяем, занят ли порт
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:  # Порт занят
                self.log(t("ui.launcher.log.port_in_use", default="⚠️ Порт {port} занят, освобождаю...", port=port), "SYSTEM")
                
                # Находим процесс, занимающий порт (правильный способ для Windows)
                # Используем netstat для более надежного поиска на Windows
                try:
                    # Пробуем через netstat (работает без прав администратора)
                    netstat_result = subprocess.run(
                        ["netstat", "-ano"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if netstat_result.returncode == 0:
                        for line in netstat_result.stdout.split('\n'):
                            if f':{port}' in line and 'LISTENING' in line:
                                parts = line.split()
                                if len(parts) >= 5:
                                    try:
                                        pid = int(parts[-1])
                                        self.log(t("ui.launcher.log.killing_process_on_port", default="🔄 Убиваю процесс {pid} на порту {port}...", pid=pid, port=port), "SYSTEM")
                                        self.kill_tree(pid)
                                        time.sleep(2)  # Даем время на освобождение порта
                                        return
                                    except (ValueError, psutil.NoSuchProcess):
                                        continue
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                    pass
                
                # Fallback: пробуем через psutil (может не работать для всех процессов без прав админа)
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        # Используем proc.connections() с обработкой ошибок доступа
                        connections = proc.connections(kind='inet')
                        if connections:
                            for conn in connections:
                                if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port:
                                    pid = proc.pid
                                    self.log(t("ui.launcher.log.killing_process_on_port", default="🔄 Убиваю процесс {pid} на порту {port}...", pid=pid, port=port), "SYSTEM")
                                    self.kill_tree(pid)
                                    time.sleep(2)  # Даем время на освобождение порта
                                    return
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError, OSError):
                        continue
        except Exception as e:
            self.log(t("ui.launcher.log.port_check_error", default="⚠️ Ошибка проверки порта {port}: {error}", port=port, error=str(e)), "SYSTEM")

    def stop_service(self, name: str):
        proc = self.procs.get(name)
        if proc:
            service_name = self._get_service_name(name)
            self.log(t("ui.launcher.log.service_stopping", default="⏹️ Stopping service: {service}...", service=service_name), name.upper())
            self.stop_events[name].set()
            
            # Для бота используем более мягкое завершение
            if name == "bot":
                try:
                    # Сначала отправляем SIGTERM для graceful shutdown
                    parent = psutil.Process(proc.pid)
                    parent.terminate()
                    # Ждем до 10 секунд для graceful shutdown (удаление сообщений может занять время)
                    try:
                        parent.wait(timeout=10)
                        self.log(t("ui.launcher.log.service_stopped_gracefully", default="✅ Service {service} stopped gracefully", service=service_name), name.upper())
                    except psutil.TimeoutExpired:
                        # Если не завершился, убиваем принудительно
                        self.log(t("ui.launcher.log.service_force_stop", default="⚠️ Force stopping service {service}...", service=service_name), name.upper())
                        self.kill_tree(proc.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            else:
                # Для других сервисов используем обычное завершение
                try:
                    self.kill_tree(proc.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            self.procs[name] = None
            self.update_status(name, "stopped", "gray")
            self.log(t("ui.launcher.log.service_stopped", default="⏹️ Service {service} stopped", service=service_name), name.upper())

    def _kill_bot_processes(self):
        try:
            current_pid = os.getpid()
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        cmdline = proc.info.get('cmdline', [])
                        if cmdline and any('main.py' in str(arg) for arg in cmdline):
                            pid = proc.info['pid']
                            if pid != current_pid:
                                p = psutil.Process(pid)
                                p.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError, TypeError):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def _check_and_fix_torch(self, venv_py):
        """Checks if torch has CUDA support and reinstalls if needed"""
        self.log(f"🔍 [SD] Checking PyTorch CUDA support (USE_GPU={USE_GPU})...", "SD")
        
        if not USE_GPU:
            self.log("⚠️ [SD] GPU usage disabled in settings, skipping CUDA check", "SD")
            return

        check_script = (
            "import torch; "
            "print(f'CUDA_AVAILABLE={torch.cuda.is_available()}'); "
            "print(f'TORCH_VERSION={torch.__version__}'); "
            "print(f'CUDA_VERSION={torch.version.cuda}')"
        )
        
        try:
            result = subprocess.run(
                [venv_py, "-c", check_script],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            output = result.stdout.strip()
            self.log(f"📋 [SD] PyTorch check output: {output}", "SD")
            
            # More robust check for CPU version or missing CUDA
            # If output is empty, something is wrong, assume we need to fix it
            is_cpu = not output or "+cpu" in output or "CUDA_AVAILABLE=False" in output or "CUDA_VERSION=None" in output
            
            if is_cpu:
                self.log(t("ui.launcher.log.sd_reinstalling_pytorch_cuda", default="🔄 [SD] Reinstalling PyTorch with CUDA support..."), "SD")
                
                # Uninstall current torch
                subprocess.run(
                    [venv_py, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # Install torch with CUDA 12.1
                install_cmd = [
                    venv_py, "-m", "pip", "install",
                    "torch", "torchvision", "torchaudio",
                    "--index-url", "https://download.pytorch.org/whl/cu121"
                ]
                
                process = subprocess.Popen(
                    install_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # Stream output
                for line in iter(process.stdout.readline, ''):
                    if line:
                        self.log(f"📦 [SD] {line.strip()}", "SD")
                process.wait()
                
                if process.returncode == 0:
                     self.log(t("ui.launcher.log.sd_pytorch_cuda_installed", default="✅ [SD] PyTorch with CUDA installed"), "SD")
                else:
                     self.log(t("ui.launcher.log.sd_pytorch_cuda_install_failed", default="❌ [SD] Failed to install PyTorch with CUDA"), "SD")

        except Exception as e:
            self.log(f"⚠️ [SD] Error checking/fixing torch: {e}", "SD")

    def start_service(self, name: str, llm_model_info=None):
        self.stop_events[name].clear()
        self.update_status(name, "starting", "orange")
        
        env = os.environ.copy()
        if os.path.exists(os.path.dirname(GIT_CMD)):
            env["PATH"] = os.path.dirname(GIT_CMD) + os.pathsep + env.get("PATH", "")

        cmd = []
        cwd = BASE_DIR

        try:
            if name == "bot":
                if not os.path.exists(PYTHON_EXE):
                    self.log(t("ui.launcher.log.python_not_found", default="❌ [BOT] Python not found"), "BOT")
                    raise FileNotFoundError("Python not found")
                
                script = os.path.join(BASE_DIR, "main.py")
                if not os.path.exists(script):
                    self.log(t("ui.launcher.log.main_not_found", default="❌ [BOT] main.py not found"), "BOT")
                    raise FileNotFoundError("main.py not found")
                
                # Check bot token
                from dotenv import get_key
                bot_token = get_key(FILE_ENV, "BOT_TOKEN")
                if not bot_token or not bot_token.strip():
                    self.log(t("ui.launcher.log.bot_token_not_set", default="❌ [BOT] Bot token not set"), "BOT")
                    raise ValueError("Bot token not set")
                
                self._kill_bot_processes()
                
                env["BOT_CONFIG_DIR"] = DIR_CONFIGS
                env["PYTHONPATH"] = BASE_DIR
                cmd = [PYTHON_EXE, "-u", script]

            elif name == "llm":
                if not os.path.exists(OLLAMA_EXE):
                    if not self.installer.download_ollama():
                        raise Exception("Ollama installation failed")

                if not llm_model_info:
                     raise Exception("Model not selected")

                model_name = llm_model_info['name']
                model_type = llm_model_info['type']
                model_path = llm_model_info.get('path')

                # Проверяем и загружаем модель Ollama, если она не загружена
                if model_type == 'ollama':
                    # Проверяем наличие модели в Ollama
                    if not self.model_manager.check_ollama_model(model_name):
                        self.log(f"📦 [LLM] Модель {model_name} не найдена, загружаю...", "LLM")
                        
                        # Останавливаем все процессы Ollama перед началом
                        self.installer.kill_all_ollama_processes()
                        time.sleep(2)
                        
                        # Запускаем временный Ollama server для загрузки
                        temp_env = env.copy()
                        temp_env["OLLAMA_HOST"] = "127.0.0.1:11434"
                        temp_env["OLLAMA_ORIGINS"] = "*"
                        temp_env["OLLAMA_MODELS"] = MODELS_LLM_DIR
                        temp_env["OLLAMA_DATA"] = OLLAMA_DATA_DIR
                        # Force GPU
                        # temp_env["CUDA_VISIBLE_DEVICES"] = "0" # Removed to allow auto-discovery
                        temp_env["OLLAMA_DEBUG"] = "1"
                        
                        temp_ollama = None
                        try:
                            # Стартуем временный сервер
                            self.log(f"🔧 [LLM] Запуск временного Ollama сервера...", "LLM")
                            temp_ollama = subprocess.Popen(
                                [OLLAMA_EXE, "serve"],
                                cwd=OLLAMA_DIR,
                                env=temp_env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=subprocess.STARTUPINFO()
                            )
                            
                            # Ждем запуска сервера
                            server_started = False
                            for i in range(30):
                                time.sleep(1)
                                try:
                                    req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
                                    with urllib.request.urlopen(req, timeout=2) as response:
                                        if response.status == 200:
                                            server_started = True
                                            self.log(f"✅ [LLM] Временный сервер запущен", "LLM")
                                            break
                                except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError):
                                    if i == 29:
                                        raise Exception("Ollama server failed to start")
                            
                            if not server_started:
                                raise Exception("Failed to start temporary Ollama server")
                            
                            # Загружаем модель через ollama pull
                            self.log(f"⬇️ [LLM] Загрузка модели {model_name}...", "LLM")
                            
                            pull_startupinfo = subprocess.STARTUPINFO()
                            pull_startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                            pull_startupinfo.wShowWindow = subprocess.SW_HIDE
                            
                            # Используем Popen для отслеживания прогресса
                            pull_process = subprocess.Popen(
                                [OLLAMA_EXE, "pull", model_name],
                                cwd=OLLAMA_DIR,
                                env=temp_env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=pull_startupinfo
                            )
                            
                            # Отслеживаем прогресс, показываем каждые 5%
                            last_logged_percent = -5
                            for line in iter(pull_process.stdout.readline, ''):
                                if line:
                                    line_stripped = line.strip()
                                    
                                    # Извлекаем процент из строки (формат: "pulling... 26%")
                                    if "pulling" in line_stripped.lower() and "%" in line_stripped:
                                        try:
                                            # Ищем процент в строке
                                            percent_str = line_stripped.split("%")[0].split()[-1]
                                            current_percent = int(percent_str)
                                            
                                            # Логируем каждые 5%
                                            if current_percent >= last_logged_percent + 5:
                                                self.log(f"⬇️ [LLM] Загрузка: {current_percent}%", "LLM")
                                                last_logged_percent = current_percent
                                        except (ValueError, IndexError):
                                            pass
                                    # Логируем важные сообщения (success, error, verifying)
                                    elif any(keyword in line_stripped.lower() for keyword in ['success', 'error', 'verifying', 'failed']):
                                        self.log(f"📥 [LLM] {line_stripped}", "LLM")
                            
                            pull_process.wait(timeout=600)
                            
                            if pull_process.returncode == 0:
                                self.log(f"✅ [LLM] Модель {model_name} успешно загружена", "LLM")
                            else:
                                raise Exception(f"Pull command failed with code {pull_process.returncode}")
                                
                        except subprocess.TimeoutExpired:
                            self.log(f"❌ [LLM] Таймаут при загрузке модели {model_name}", "LLM")
                            if pull_process:
                                pull_process.kill()
                            raise Exception("Model download timeout")
                        except Exception as e:
                            self.log(f"❌ [LLM] Ошибка при загрузке модели: {e}", "LLM")
                            raise
                        finally:
                            # Останавливаем временный сервер
                            if temp_ollama:
                                try:
                                    temp_ollama.terminate()
                                    temp_ollama.wait(timeout=5)
                                except (subprocess.TimeoutExpired, ProcessLookupError):
                                    if temp_ollama.poll() is None:
                                        temp_ollama.kill()
                            time.sleep(2)
                            self.installer.kill_all_ollama_processes()

                # Import GGUF model if needed
                if model_type == 'gguf' and model_path:
                    if not self.model_manager.check_ollama_model(model_name):
                        self.log(t("ui.launcher.log.model_not_found", default="📦 [LLM] Model not found, importing..."), "LLM")
                        self.installer.kill_all_ollama_processes()
                        time.sleep(2)
                        
                        # Start temporary Ollama server for import
                        temp_env = env.copy()
                        temp_env["OLLAMA_HOST"] = "127.0.0.1:11434"
                        temp_env["OLLAMA_ORIGINS"] = "*"
                        temp_env["OLLAMA_MODELS"] = MODELS_LLM_DIR  # Use unified models directory
                        temp_env["OLLAMA_DATA"] = OLLAMA_DATA_DIR
                        # Force GPU
                        # temp_env["CUDA_VISIBLE_DEVICES"] = "0" # Removed
                        temp_env["OLLAMA_DEBUG"] = "1"
                        
                        temp_ollama = None
                        try:
                            temp_ollama = subprocess.Popen(
                                [OLLAMA_EXE, "serve"],
                                cwd=OLLAMA_DIR,
                                env=temp_env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=subprocess.STARTUPINFO()
                            )
                            
                            # Wait for server to start
                            for i in range(30):
                                time.sleep(1)
                                try:
                                    req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
                                    with urllib.request.urlopen(req, timeout=2) as response:
                                        if response.status == 200:
                                            break
                                except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError):
                                    if i == 29:
                                        raise Exception("Ollama server failed to start")
                            
                            # Import model
                            if not self.model_manager.import_gguf_to_ollama(model_path, model_name, temp_env):
                                raise Exception("Model import failed")
                        finally:
                            # Stop temporary server
                            if temp_ollama:
                                try:
                                    temp_ollama.terminate()
                                    temp_ollama.wait(timeout=5)
                                except (subprocess.TimeoutExpired, ProcessLookupError):
                                    if temp_ollama.poll() is None:
                                        temp_ollama.kill()
                            time.sleep(2)
                            self.installer.kill_all_ollama_processes()

                self.installer.kill_all_ollama_processes()

                env["OLLAMA_HOST"] = "127.0.0.1:11434"
                env["OLLAMA_ORIGINS"] = "*"
                # env["OLLAMA_MODELS"] = MODELS_LLM_DIR  # Removed to use default system path
                env["OLLAMA_DATA"] = OLLAMA_DATA_DIR
                
                # Ollama automatically detects and uses GPU by default
                # Only enable debug mode to monitor GPU usage
                if USE_GPU:
                    env["OLLAMA_DEBUG"] = "1"  # Enable debug for GPU info
                # Note: DO NOT set CUDA_VISIBLE_DEVICES="" or OLLAMA_LLM_LIBRARY="cpu"
                # This prevents GPU usage. Ollama's default behavior is to use GPU when available.
                
                # Remove CPU-only flag if present (legacy cleanup)
                if "OLLAMA_VULKAN" in env:
                    del env["OLLAMA_VULKAN"]
                
                cmd = [OLLAMA_EXE, "serve"]
                cwd = OLLAMA_DIR

            elif name == "sd":
                launch_script = os.path.join(SD_DIR, "launch.py")
                if not os.path.exists(SD_DIR) or not os.path.exists(launch_script):
                    if not self.installer.install_sd():
                        raise Exception("SD installation failed")
                
                venv = os.path.join(SD_DIR, "venv")
                if not os.path.exists(venv):
                     if not self.installer.create_sd_venv():
                        raise Exception("SD venv creation failed")
                
                venv_py = os.path.join(venv, "Scripts", "python.exe")
                if not os.path.exists(venv_py):
                    raise FileNotFoundError("SD venv Python not found")
                
                # Check and fix torch if needed
                self._check_and_fix_torch(venv_py)
                
                # Pre-install build dependencies to fix 'invalid command bdist_wheel'
                try:
                    self.log(t("ui.launcher.log.updating_deps", default="🔧 [SD] Updating build dependencies..."), "SD")
                    subprocess.run(
                        [venv_py, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
                        check=True,
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                except Exception as e:
                    self.log(f"⚠️ [SD] Failed to update build deps: {e}", "SD")

                # Проверяем и освобождаем порт 7860
                self._kill_process_on_port(7860)
                
                # Check for CUDA support
                cuda_supported = False
                if USE_GPU:
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
                    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                        pass
                
                # Use python -c to bootstrap execution and force sys.path setup
                # This fixes ModuleNotFoundError by ensuring SD_DIR is in sys.path
                sd_dir_forward = SD_DIR.replace(os.sep, '/')
                launch_script_forward = os.path.join(SD_DIR, "launch.py").replace(os.sep, '/')
                
                python_code = (
                    f"import sys; "
                    f"sys.path.insert(0, '{sd_dir_forward}'); "
                    f"sys.argv[0] = '{launch_script_forward}'; "
                    f"import runpy; "
                    f"runpy.run_path('{launch_script_forward}', run_name='__main__')"
                )
                
                cmd = [venv_py, "-c", python_code, "--api", "--nowebui", "--port", "7860", "--skip-python-version-check"]
                
                if cuda_supported and USE_GPU:
                    # Add skip-torch-cuda-test to bypass strict startup checks
                    # Removed --cuda-stream as it is risky (can cause black images/OOM)
                    # Add --disable-gpu-warning to suppress low VRAM warnings
                    cmd.extend(["--xformers", "--skip-torch-cuda-test", "--disable-gpu-warning"])
                else:
                    # Removed --no-half as it is obsolete in Forge
                    cmd.extend(["--use-cpu", "all", "--skip-torch-cuda-test"])
                
                # Suppress git errors
                env["GIT_PYTHON_REFRESH"] = "quiet"
                
                # Add SD directory to PYTHONPATH to fix ModuleNotFoundError
                # Add SD directory AND current directory to PYTHONPATH
                # Also ensure it's exported to the environment for subprocesses
                env["PYTHONPATH"] = SD_DIR + os.pathsep + "." + os.pathsep + env.get("PYTHONPATH", "")
                
                # Explicitly set PYTHONPATH for the process environment too
                os.environ["PYTHONPATH"] = env["PYTHONPATH"]
                self.log(f"🔧 [SD] PYTHONPATH: {env['PYTHONPATH']}", "SD")
                    
                cwd = SD_DIR

            # Launch process
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            service_name = self._get_service_name(name)
            self.log(t("ui.launcher.log.service_launching", default=f"🚀 [{name.upper()}] Launching {service_name}...", service=service_name), name.upper())
            
            p = subprocess.Popen(
                cmd, cwd=cwd, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,  # Separate stderr
                encoding='utf-8', errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            self.procs[name] = p
            self.update_status(name, "running", "green")
            self.log(t("ui.launcher.log.service_pid", default=f"✅ [{name.upper()}] Process started (PID: {p.pid})", service=service_name, pid=p.pid), name.upper())
            
            def reader():
                try:
                    for line in iter(p.stdout.readline, ''):
                        if line and not self.stop_events[name].is_set():
                            self.log_queue.put((line.strip(), name.upper()))
                except (OSError, ValueError, AttributeError):
                    pass
                finally:
                    try:
                        p.stdout.close()
                    except (OSError, AttributeError):
                        pass
                    if self.procs.get(name) == p:  # If this is still the active process
                        self.procs[name] = None
                        self.update_status(name, "stopped", "gray")
            
            def error_reader():
                try:
                    for line in iter(p.stderr.readline, ''):
                        if line and not self.stop_events[name].is_set():
                            # Log errors with warning prefix
                            self.log_queue.put((f"⚠️ {line.strip()}", name.upper()))
                except (OSError, ValueError, AttributeError):
                    pass
                finally:
                    try:
                        p.stderr.close()
                    except (OSError, AttributeError):
                        pass
            
            threading.Thread(target=reader, daemon=True).start()
            threading.Thread(target=error_reader, daemon=True).start()

        except Exception as e:
            service_name = self._get_service_name(name)
            self.log(t("ui.launcher.log.service_start_error", default=f"❌ [{name.upper()}] Error starting service: {{error}}", service=service_name, error=str(e)), name.upper())
            self.update_status(name, "error", "red")

